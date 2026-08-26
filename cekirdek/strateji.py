"""Stratejiler ve skorlama.

Tasarım kuralı: her strateji t günü KAPANIŞINDA sinyal üretir, işlem t+1
AÇILIŞINDA yapılır. Bu yüzden hiçbir sinyal aynı günün kapanışını "bilerek"
kullanamaz - geleceğe bakma (look-ahead) hatası engellenmiş olur.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- filtreler

@dataclass
class Filtreler:
    """Bir hisse hiç değerlendirmeye alınmalı mı?"""
    asgari_tl_hacim: float = 20_000_000     # günlük ort. TL hacim tabanı
    azami_atr_yuzde: float = 7.0            # günlük %7+ oynaklık = kumar / brüt takas riski
    asgari_atr_yuzde: float = 0.8           # hiç oynamayan hisseden getiri çıkmaz
    tavan_esigi: float = 9.0                # gün içi %9+ artış = tavana yakın, ertesi gün alım riskli
    asgari_veri: int = 220                  # SMA200 için yeterli geçmiş

    def gecer_mi(self, g: pd.DataFrame, i: int = -1) -> tuple[bool, str]:
        if len(g) < self.asgari_veri:
            return False, "yetersiz geçmiş veri"
        s = g.iloc[i]
        if not np.isfinite(s.get("TL_hacim_ort20", np.nan)):
            return False, "hacim verisi yok"
        if s["TL_hacim_ort20"] < self.asgari_tl_hacim:
            return False, f"likidite düşük ({s['TL_hacim_ort20']/1e6:.0f}M TL)"
        if not np.isfinite(s.get("ATR_yuzde", np.nan)):
            return False, "ATR hesaplanamadı"
        if s["ATR_yuzde"] > self.azami_atr_yuzde:
            return False, f"aşırı oynak (ATR %{s['ATR_yuzde']:.1f})"
        if s["ATR_yuzde"] < self.asgari_atr_yuzde:
            return False, f"hareketsiz (ATR %{s['ATR_yuzde']:.1f})"
        gunluk = (s["Close"] / g["Close"].iloc[i - 1] - 1) * 100 if len(g) > 1 else 0
        if gunluk > self.tavan_esigi:
            return False, f"tavana yakın (+%{gunluk:.1f})"
        return True, "uygun"


def filtre_maskesi(g: pd.DataFrame, f: Filtreler) -> pd.Series:
    """Backtest için vektörel filtre - her gün için True/False."""
    gunluk = g["Close"].pct_change() * 100
    return (
        (g["TL_hacim_ort20"] >= f.asgari_tl_hacim)
        & (g["ATR_yuzde"] <= f.azami_atr_yuzde)
        & (g["ATR_yuzde"] >= f.asgari_atr_yuzde)
        & (gunluk <= f.tavan_esigi)
        & g["SMA200"].notna()
    ).fillna(False)


# ---------------------------------------------------------------- stratejiler

@dataclass
class Strateji:
    ad: str
    aciklama: str
    giris: object            # (g: DataFrame) -> pd.Series[bool]
    cikis: object            # (g: DataFrame) -> pd.Series[bool]
    azami_tutma: int = 15    # bu kadar günde çıkmadıysa zorla çık
    atr_stop_kat: float = 2.0
    atr_hedef_kat: float = 3.5


def _trend_giris(g: pd.DataFrame) -> pd.Series:
    """Yükselen trendde EMA20'ye geri çekilip toparlanma."""
    trend = (g["Close"] > g["SMA200"]) & (g["EMA20"] > g["EMA50"])
    geri_cekilme = (g["Low"].rolling(3).min() <= g["EMA20"] * 1.01)
    toparlanma = (g["Close"] > g["Open"]) & (g["Close"] > g["EMA20"])
    guc = g["ADX14"] > 18
    return (trend & geri_cekilme & toparlanma & guc).fillna(False)


def _trend_cikis(g: pd.DataFrame) -> pd.Series:
    return ((g["Close"] < g["EMA50"]) | (g["RSI14"] > 80)).fillna(False)


def _tepki_giris(g: pd.DataFrame) -> pd.Series:
    """Sadece uzun vadeli yükseliş trendindeki hisselerde aşırı satım tepkisi.
    SMA200 filtresi olmadan bu strateji düşen bıçağı yakalamaya dönüşür."""
    trend = g["Close"] > g["SMA200"]
    asiri_satim = (g["RSI2"] < 10) & (g["BB_konum"] < 0.20)
    cokme_degil = g["Close"] > g["Close"].shift(1) * 0.90   # tabana yakın panik değil
    return (trend & asiri_satim & cokme_degil).fillna(False)


def _tepki_cikis(g: pd.DataFrame) -> pd.Series:
    return ((g["RSI2"] > 70) | (g["Close"] > g["EMA10"])).fillna(False)


def _kirilim_giris(g: pd.DataFrame) -> pd.Series:
    """20 günlük zirvenin hacimle kırılması."""
    kirilim = g["Close"] > g["DON_ust"]
    hacim = g["Hacim_orani"] > 1.4
    trend = (g["Close"] > g["SMA200"]) & (g["ADX14"] > 20)
    return (kirilim & hacim & trend).fillna(False)


def _kirilim_cikis(g: pd.DataFrame) -> pd.Series:
    don10 = g["Low"].rolling(10, min_periods=10).min().shift(1)
    return ((g["Close"] < don10) | (g["Close"] < g["EMA20"])).fillna(False)


STRATEJILER: dict[str, Strateji] = {
    "trend": Strateji(
        ad="trend",
        aciklama="Yükselen trendde geri çekilme alımı (pullback)",
        giris=_trend_giris, cikis=_trend_cikis,
        azami_tutma=20, atr_stop_kat=2.0, atr_hedef_kat=4.0,
    ),
    "tepki": Strateji(
        ad="tepki",
        aciklama="Trend içi aşırı satım tepkisi (RSI2 mean-reversion)",
        giris=_tepki_giris, cikis=_tepki_cikis,
        azami_tutma=6, atr_stop_kat=2.5, atr_hedef_kat=2.5,
    ),
    "kirilim": Strateji(
        ad="kirilim",
        aciklama="20 günlük zirvenin hacimli kırılması (breakout)",
        giris=_kirilim_giris, cikis=_kirilim_cikis,
        azami_tutma=25, atr_stop_kat=2.5, atr_hedef_kat=5.0,
    ),
}


# ---------------------------------------------------------------- skorlama

def _olcekle(deger: float, dusuk: float, yuksek: float) -> float:
    """deger'i [dusuk, yuksek] aralığından 0-1'e sıkıştır."""
    if not np.isfinite(deger):
        return 0.0
    return float(np.clip((deger - dusuk) / (yuksek - dusuk), 0.0, 1.0))


def skorla(g: pd.DataFrame, i: int = -1) -> dict:
    """0-100 arası bileşik skor + alt kırılımlar.

    Skor bir 'kesinlik' değil, sıralama aracıdır. 85 puanlık hisse 40 puanlıktan
    daha iyi konumlanmıştır; ama yine de zarar edebilir.
    """
    s = g.iloc[i]
    onceki = g.iloc[i - 1] if len(g) > 1 else s

    # 1) TREND (0-30): fiyat uzun ve orta vadeli ortalamaların neresinde?
    trend = 0.0
    if np.isfinite(s.get("SMA200", np.nan)):
        trend += 12 if s["Close"] > s["SMA200"] else 0
        trend += 6 * _olcekle((s["Close"] / s["SMA200"] - 1) * 100, 0, 25)
    if np.isfinite(s.get("EMA50", np.nan)):
        trend += 7 if s["EMA20"] > s["EMA50"] else 0
        trend += 5 if s["Close"] > s["EMA20"] else 0

    # 2) MOMENTUM (0-25): endeksi yeniyor mu?
    momentum = 12 * _olcekle(s.get("GG60", 0), -15, 25)
    momentum += 8 * _olcekle(s.get("GG20", 0), -10, 15)
    momentum += 5 * _olcekle(s.get("Getiri_20g", 0), -10, 20)

    # 3) ZAMANLAMA (0-25): şu an girmek için iyi bir nokta mı?
    # Kasten aşırı alım cezalandırılır - zirveden alım en pahalı hatadır.
    rsi = s.get("RSI14", 50)
    if rsi < 30:      zamanlama = 25.0          # aşırı satım, tepki potansiyeli
    elif rsi < 45:    zamanlama = 22.0
    elif rsi < 60:    zamanlama = 17.0
    elif rsi < 70:    zamanlama = 10.0
    elif rsi < 80:    zamanlama = 4.0
    else:             zamanlama = 0.0           # aşırı alım - kovalama
    bb = s.get("BB_konum", 0.5)
    if np.isfinite(bb):
        zamanlama = zamanlama * 0.7 + (25 * (1 - _olcekle(bb, 0.0, 1.0))) * 0.3

    # 4) KALİTE (0-20): likidite, oynaklık, hacim teyidi
    kalite = 8 * _olcekle(np.log10(max(s.get("TL_hacim_ort20", 1), 1)), 7.0, 9.5)
    atr_y = s.get("ATR_yuzde", 0)
    kalite += 7 * (1 - abs(_olcekle(atr_y, 0.5, 6.0) - 0.45) / 0.55)   # 2-3% ideal
    kalite += 5 * _olcekle(s.get("Hacim_orani", 1), 0.7, 2.0)
    kalite = max(0.0, kalite)

    toplam = trend + momentum + zamanlama + kalite

    # aktif strateji sinyalleri
    sinyaller = []
    for ad, st in STRATEJILER.items():
        try:
            if bool(st.giris(g).iloc[i]):
                sinyaller.append(ad)
        except Exception:
            pass

    return {
        "skor": round(float(np.clip(toplam, 0, 100)), 1),
        "trend": round(trend, 1),
        "momentum": round(momentum, 1),
        "zamanlama": round(zamanlama, 1),
        "kalite": round(kalite, 1),
        "sinyaller": sinyaller,
        "fiyat": float(s["Close"]),
        "gunluk_degisim": round(float(s["Close"] / onceki["Close"] - 1) * 100, 2),
        "rsi": round(float(rsi), 1),
        "atr": float(s.get("ATR14", 0)),
        "atr_yuzde": round(float(atr_y), 2),
        "adx": round(float(s.get("ADX14", 0)), 1),
        "gg60": round(float(s.get("GG60", 0)), 1) if np.isfinite(s.get("GG60", np.nan)) else None,
        "tl_hacim": float(s.get("TL_hacim_ort20", 0)),
        "sma200_ustu": bool(s["Close"] > s["SMA200"]) if np.isfinite(s.get("SMA200", np.nan)) else None,
    }
