"""Makroekonomik bağlam: BIST'te tek tek hisselerden daha çok bunlar belirler.

Türkiye'de bir hissenin fiyatı üç şeyin çarpımıdır:
    şirketin kârı  ×  piyasanın verdiği çarpan  ×  TL'nin değeri
Teknik ve temel analiz ilk ikisine bakar. Bu modül üçüncüyü ve çarpanı
belirleyen faiz/enflasyon/kur rejimini izler.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import veri

GOSTERGELER = {
    "usdtry":   ("TRY=X",      "USD/TRY",          "kur"),
    "eurtry":   ("EURTRY=X",   "EUR/TRY",          "kur"),
    "altin":    ("GC=F",       "Altın (ons, $)",   "emtia"),
    "brent":    ("BZ=F",       "Brent petrol ($)", "emtia"),
    "bakir":    ("HG=F",       "Bakır ($)",        "emtia"),
    "abd10y":   ("^TNX",       "ABD 10y faiz",     "faiz"),
    "abd2y":    ("^FVX",       "ABD 2y faiz",      "faiz"),
    "vix":      ("^VIX",       "VIX (korku)",      "risk"),
    "dxy":      ("DX-Y.NYB",   "Dolar endeksi",    "risk"),
    "sp500":    ("^GSPC",      "S&P 500",          "kuresel"),
    "em":       ("EEM",        "Gelişen piyasalar","kuresel"),
    "xu100":    ("XU100.IS",   "BIST 100",         "yerel"),
}

# Makro değişkenin sektörlere etkisi: +1 olumlu, -1 olumsuz
ETKI = {
    "usdtry_artis": {
        "Basic Materials": +1, "Industrials": +1, "Technology": +1,
        "Consumer Cyclical": -1, "Utilities": -1, "Consumer Defensive": -1,
        "_not": "TL zayıflarsa ihracatçı ve dolar geliri olan kazanır; "
                "ithal girdi kullanan ve borcu dövizli olan kaybeder.",
    },
    "faiz_artis": {
        "Financial Services": +1, "Real Estate": -1, "Consumer Cyclical": -1,
        "Industrials": -1, "Utilities": -1,
        "_not": "Faiz artışı bankada marjı açar; borçla büyüyen inşaat, GYO ve "
                "dayanıklı tüketimi vurur. Ayrıca borsanın çarpanını düşürür.",
    },
    "petrol_artis": {
        "Energy": +1, "Basic Materials": -1, "Industrials": -1,
        "Consumer Cyclical": -1,
        "_not": "Havayolu (THYAO, PGSUS) ve nakliye en çok etkilenen; "
                "rafineri (TUPRS) stok kârı yazabilir.",
    },
    "enflasyon_artis": {
        "Consumer Defensive": +1, "Real Estate": +1, "Financial Services": -1,
        "_not": "Fiyatı hızlı geçirebilen perakende korunur; sabit getirili "
                "varlık tutan kaybeder. Uzun vadede herkes kaybeder.",
    },
}


@dataclass
class MakroDurum:
    degerler: dict
    enflasyon: dict
    tarih: str

    def oz(self, anahtar: str) -> dict | None:
        return self.degerler.get(anahtar)


def _degisim(s: pd.Series, gun: int) -> float:
    if s is None or len(s) < 2:
        return np.nan
    g = s.dropna()
    if len(g) < 2:
        return np.nan
    ref = g.iloc[-min(gun, len(g))]
    return (g.iloc[-1] / ref - 1) * 100 if ref else np.nan


def enflasyon_cek() -> dict:
    """TÜFE — borsapy üzerinden TCMB verisi, anahtar gerektirmez."""
    try:
        import borsapy as bp
        d = bp.Inflation().tufe()
        son = d.iloc[0]
        return {
            "yillik": float(son["YearlyInflation"]),
            "aylik": float(son["MonthlyInflation"]),
            "donem": str(son["YearMonth"]),
            "kaynak": "TCMB/TÜİK",
        }
    except Exception:
        # borsapy yoksa makul bir varsayılan; hesaplar buna göre kayar
        return {"yillik": 31.75, "aylik": 1.78, "donem": "tahmini", "kaynak": "varsayılan"}


def durum(gun: int = 400, onbellek_saat: float = 6.0) -> MakroDurum:
    """Tüm makro göstergeleri çeker, değişimleriyle birlikte döndürür."""
    sonuc = {}
    for anahtar, (kod, ad, grup) in GOSTERGELER.items():
        # BIST dışı semboller ham çekilir ('.IS' eklenmez)
        df = veri.fiyat_cek(kod, gun=gun, onbellek_saat=onbellek_saat,
                            ham=not kod.endswith(".IS"))
        if df.empty:
            continue
        k = df["Close"]
        sonuc[anahtar] = {
            "ad": ad, "grup": grup, "kod": kod,
            "son": float(k.iloc[-1]),
            "g1": _degisim(k, 2), "g5": _degisim(k, 6),
            "g30": _degisim(k, 22), "g90": _degisim(k, 64), "g365": _degisim(k, 252),
            "seri": k,
        }
    return MakroDurum(sonuc, enflasyon_cek(),
                      pd.Timestamp.now().strftime("%Y-%m-%d"))


def _sayi(v, basamak: int = 1) -> str:
    """Türkçe ondalık ayracı ile sayı.

    NEDEN VAR: bu notlar doğrudan kullanıcıya gösteriliyor (Makro ekranı,
    Bugün kartı, Telegram, push). Uygulamanın geri kalanı virgül
    kullanırken buradan nokta çıkıyordu ve aynı ekranda "VIX 14.6" ile
    "14,63" yan yana duruyordu.
    """
    try:
        return f"{float(v):.{basamak}f}".replace(".", ",")
    except Exception:
        return "—"


def rejim(m: MakroDurum) -> dict:
    """Piyasa rejimi: risk iştahı açık mı, TL baskı altında mı?

    Rejim, hangi stratejinin işe yarayacağını belirler. Momentum stratejileri
    risk iştahı açıkken çalışır; savunma rejiminde nakitte beklemek kazançtır.
    """
    puan, notlar = 0, []

    vix = m.oz("vix")
    if vix:
        if vix["son"] < 16:   puan += 2; notlar.append(f"VIX {_sayi(vix['son'])} — küresel risk iştahı açık")
        elif vix["son"] > 25: puan -= 2; notlar.append(f"VIX {_sayi(vix['son'])} — küresel korku yüksek")
        else:                 notlar.append(f"VIX {_sayi(vix['son'])} — nötr")

    usd = m.oz("usdtry")
    if usd and np.isfinite(usd["g30"]):
        aylik_enf = m.enflasyon.get("aylik", 1.8)
        if usd["g30"] > aylik_enf * 2:
            puan -= 2; notlar.append(f"USD/TRY 1 ayda %{_sayi(usd['g30'])} — TL hızlı değer kaybediyor")
        elif usd["g30"] < aylik_enf * 0.5:
            puan += 1; notlar.append(f"USD/TRY 1 ayda %{_sayi(usd['g30'])} — TL sakin, reel değerleniyor")
        else:
            notlar.append(f"USD/TRY 1 ayda %{_sayi(usd['g30'])} — enflasyona paralel seyir")

    em, xu = m.oz("em"), m.oz("xu100")
    if em and xu and np.isfinite(em["g90"]) and np.isfinite(xu["g90"]):
        fark = xu["g90"] - em["g90"]
        if fark > 10:  puan += 1; notlar.append(f"BIST gelişen piyasaları {_sayi(fark, 0)} puan geçiyor")
        elif fark < -10: puan -= 1; notlar.append(f"BIST gelişen piyasaların {_sayi(abs(fark), 0)} puan gerisinde")

    abd = m.oz("abd10y")
    if abd and np.isfinite(abd["g90"]):
        if abd["g90"] > 8:
            puan -= 1; notlar.append(f"ABD 10y faizi 3 ayda %{_sayi(abd['g90'])} arttı — gelişen piyasalardan çıkış baskısı")

    if puan >= 3:    ad, aciklama = "RİSK AÇIK", "Momentum ve kırılım stratejileri için elverişli"
    elif puan >= 1:  ad, aciklama = "ılımlı", "Normal işlem, pozisyon boyutunu abartma"
    elif puan >= -1: ad, aciklama = "temkinli", "Filtreleri sıkılaştır, daha az pozisyon taşı"
    else:            ad, aciklama = "SAVUNMA", "Nakit oranını yükselt; bu rejimde kaybetmemek kazanmaktır"

    return {"rejim": ad, "puan": puan, "aciklama": aciklama, "notlar": notlar}


def sektor_etkisi(sektor: str, m: MakroDurum) -> list[str]:
    """Bu makro ortamda bu sektör rüzgârı arkasına mı alıyor, karşısına mı?"""
    sonuc = []
    usd = m.oz("usdtry")
    if usd and np.isfinite(usd["g90"]) and abs(usd["g90"]) > 5:
        yon = "usdtry_artis"
        e = ETKI[yon].get(sektor)
        if e:
            olumlu = (e > 0) == (usd["g90"] > 0)
            sonuc.append(f"{'✓' if olumlu else '✗'} USD/TRY 3 ayda %{usd['g90']:+.1f} — "
                         f"{ETKI[yon]['_not']}")
    brent = m.oz("brent")
    if brent and np.isfinite(brent["g90"]) and abs(brent["g90"]) > 10:
        e = ETKI["petrol_artis"].get(sektor)
        if e:
            olumlu = (e > 0) == (brent["g90"] > 0)
            sonuc.append(f"{'✓' if olumlu else '✗'} Brent 3 ayda %{brent['g90']:+.1f} — "
                         f"{ETKI['petrol_artis']['_not']}")
    enf = m.enflasyon.get("yillik", 0)
    e = ETKI["enflasyon_artis"].get(sektor)
    if e and enf > 25:
        sonuc.append(f"{'✓' if e > 0 else '✗'} Enflasyon %{enf:.1f} — {ETKI['enflasyon_artis']['_not']}")
    return sonuc
