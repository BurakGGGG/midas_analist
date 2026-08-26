"""Finansal tablo katmanı — kur tuzağına karşı korumalı.

KRİTİK: BIST şirketlerinin bir kısmı (THYAO gibi ihracatçılar, havayolları)
finansallarını USD cinsinden açıklar ama hisseleri TL işlem görür. yfinance'in
hazır oranları bu ikisini karıştırır ve saçmalar:

    THYAO info F/S = 15.66   →  gerçek F/S = 0.36  (43 kat hata)

Bu modülün kuralı:
  * Tablodan tabloya oranlar (marj, ROE, cari oran) para biriminden BAĞIMSIZDIR
    — doğrudan hesaplanır, dönüşüm yapılmaz.
  * Fiyat/piyasa değeri ile tabloyu karıştıran oranlar (F/K, PD/DD, FD/FAVÖK)
    ZORUNLU dönüşümden geçer, yoksa hesaplanmaz.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from .evren import yf_kodu, sade_kod

ONBELLEK = Path(__file__).resolve().parent.parent / "veri" / "temel"
ONBELLEK.mkdir(parents=True, exist_ok=True)

# yfinance kalem adları sürüme ve şirkete göre değişir; sırayla denenir.
KALEMLER = {
    "hasilat":        ["Total Revenue", "Operating Revenue"],
    "brut_kar":       ["Gross Profit"],
    "faaliyet_kari":  ["Operating Income", "Total Operating Income As Reported"],
    "favok":          ["EBITDA", "Normalized EBITDA"],
    "favok_oncesi":   ["EBIT"],
    "net_kar":        ["Net Income", "Net Income Common Stockholders",
                       "Net Income From Continuing Operation Net Minority Interest"],
    "faiz_gideri":    ["Interest Expense"],
    "amortisman":     ["Reconciled Depreciation"],

    "toplam_varlik":  ["Total Assets"],
    "ozsermaye":      ["Stockholders Equity", "Common Stock Equity",
                       "Total Equity Gross Minority Interest"],
    "toplam_borc":    ["Total Debt"],
    "nakit":          ["Cash And Cash Equivalents",
                       "Cash Cash Equivalents And Short Term Investments"],
    "donen_varlik":   ["Current Assets", "Total Current Assets"],
    "kisa_borc":      ["Current Liabilities", "Total Current Liabilities"],
    "stok":           ["Inventory"],

    "faaliyet_nakit": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "serbest_nakit":  ["Free Cash Flow"],
    "yatirim_harcama":["Capital Expenditure"],
}


def _kalem(df: pd.DataFrame | None, anahtar: str, sutun: int = 0) -> float:
    """Tablodan kalemi çeker. Bulamazsa NaN — sessizce 0 DÖNMEZ.

    0 dönmek tehlikeli olurdu: borcu bulunamayan şirket 'borçsuz' görünür."""
    if df is None or df.empty:
        return np.nan
    for ad in KALEMLER.get(anahtar, [anahtar]):
        if ad in df.index:
            try:
                v = df.loc[ad].iloc[sutun]
                if pd.notna(v):
                    return float(v)
            except (IndexError, ValueError, TypeError):
                continue
    return np.nan


@dataclass
class Finansallar:
    sembol: str
    ad: str = ""
    sektor: str = ""
    sanayi: str = ""

    fiyat: float = np.nan
    piyasa_degeri: float = np.nan        # TL
    hisse_adedi: float = np.nan
    fiyat_para: str = "TRY"
    tablo_para: str = "TRY"
    kur: float = 1.0                     # tablo → TL çarpanı

    gelir_yillik: pd.DataFrame | None = None
    gelir_ceyrek: pd.DataFrame | None = None
    bilanco: pd.DataFrame | None = None
    nakit_akis: pd.DataFrame | None = None
    temettu: pd.Series | None = None
    ham_info: dict = field(default_factory=dict)

    @property
    def kur_uyusmazligi(self) -> bool:
        """Finansallar hisse fiyatından farklı para biriminde mi?"""
        return self.tablo_para != self.fiyat_para

    def enflasyon_referansi(self, tufe: float = 31.75) -> float:
        """Büyüme ve ROE'yi HANGİ enflasyonla kıyaslamalı?

        USD raporlayan bir şirketin (THYAO gibi) dolar hasılatını Türkiye
        TÜFE'siyle kıyaslamak geçersizdir — o şirket dolar dünyasında iş yapar.
        Yanlış referans, sağlıklı şirketi 'reel küçülüyor' diye damgalar."""
        return {"USD": 3.0, "EUR": 2.5}.get(self.tablo_para, tufe)

    @property
    def donemler(self) -> list[str]:
        if self.gelir_yillik is None or self.gelir_yillik.empty:
            return []
        return [str(c.date()) for c in self.gelir_yillik.columns]

    def al(self, anahtar: str, tablo: str = "gelir", donem: int = 0) -> float:
        """Ham kalem, tablonun kendi para biriminde."""
        df = {"gelir": self.gelir_yillik, "ceyrek": self.gelir_ceyrek,
              "bilanco": self.bilanco, "nakit": self.nakit_akis}.get(tablo)
        return _kalem(df, anahtar, donem)

    def al_tl(self, anahtar: str, tablo: str = "gelir", donem: int = 0) -> float:
        """Kalem, TL'ye çevrilmiş. Fiyatla karşılaştırılacaksa BUNU kullan."""
        return self.al(anahtar, tablo, donem) * self.kur

    def son_12_ay(self, anahtar: str) -> float:
        """Son 4 çeyreğin toplamı (TTM). Yıllık tablodan daha güncel.

        4 çeyrek yoksa NaN döner — 3 çeyreği toplayıp yıllık gibi sunmak
        şirketi olduğundan ucuz gösterirdi."""
        df = self.gelir_ceyrek
        if df is None or df.empty or df.shape[1] < 4:
            return np.nan
        toplam = 0.0
        for i in range(4):
            v = _kalem(df, anahtar, i)
            if not np.isfinite(v):
                return np.nan
            toplam += v
        return toplam


def _kur_getir(tarih=None) -> float:
    try:
        d = yf.Ticker("TRY=X").history(period="5d")
        return float(d["Close"].iloc[-1])
    except Exception:
        return np.nan


def finansal_cek(sembol: str, onbellek_saat: float = 24.0,
                 zorla: bool = False) -> Finansallar | None:
    """Bir hissenin tüm finansal tablolarını çeker.

    Finansal tablolar günlük değişmez; önbellek 24 saat.
    """
    sem = sade_kod(sembol)
    yol = ONBELLEK / f"{sem}.pkl"

    if not zorla and yol.exists() and (time.time() - yol.stat().st_mtime) < onbellek_saat * 3600:
        try:
            return pd.read_pickle(yol)
        except Exception:
            pass

    try:
        t = yf.Ticker(yf_kodu(sem))
        info = t.info or {}
        if not info.get("marketCap") and not info.get("regularMarketPrice"):
            return None

        f = Finansallar(
            sembol=sem,
            ad=info.get("longName") or info.get("shortName") or sem,
            sektor=info.get("sector", "") or "",
            sanayi=info.get("industry", "") or "",
            fiyat=float(info.get("currentPrice") or info.get("regularMarketPrice") or np.nan),
            piyasa_degeri=float(info.get("marketCap") or np.nan),
            hisse_adedi=float(info.get("sharesOutstanding") or np.nan),
            fiyat_para=(info.get("currency") or "TRY").upper(),
            tablo_para=(info.get("financialCurrency") or info.get("currency") or "TRY").upper(),
            ham_info=info,
        )

        # Kur çarpanı: tablo para birimi → TL
        if f.tablo_para == f.fiyat_para:
            f.kur = 1.0
        elif f.tablo_para == "USD" and f.fiyat_para == "TRY":
            f.kur = _kur_getir()
        else:
            f.kur = np.nan   # bilinmeyen çift: hesaplama yapma, sessizce yanlış olma

        for ad, cek in [("gelir_yillik", lambda: t.income_stmt),
                        ("gelir_ceyrek", lambda: t.quarterly_income_stmt),
                        ("bilanco", lambda: t.balance_sheet),
                        ("nakit_akis", lambda: t.cashflow)]:
            try:
                setattr(f, ad, cek())
            except Exception:
                setattr(f, ad, None)
        try:
            f.temettu = t.dividends
        except Exception:
            f.temettu = None

        try:
            pd.to_pickle(f, yol)
        except Exception:
            pass
        return f
    except Exception:
        return None


def toplu_finansal(semboller: list[str], onbellek_saat: float = 24.0,
                   sessiz: bool = False) -> dict[str, Finansallar]:
    sonuc = {}
    for i, s in enumerate(semboller, 1):
        if not sessiz and i % 20 == 0:
            print(f"    finansal {i}/{len(semboller)}...")
        f = finansal_cek(s, onbellek_saat)
        if f is not None:
            sonuc[sade_kod(s)] = f
    return sonuc
