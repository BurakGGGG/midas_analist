"""Teknik göstergeler. Saf pandas/numpy - harici TA kütüphanesi yok.

Her fonksiyon look-ahead içermez: t anındaki değer yalnızca <= t verisini kullanır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def rsi(kapanis: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI."""
    fark = kapanis.diff()
    art = fark.clip(lower=0.0)
    azal = (-fark).clip(lower=0.0)
    # Wilder yumuşatma = alpha 1/n'lik EMA
    ort_art = art.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ort_azal = azal.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = ort_art / ort_azal.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range - stop-loss mesafesinin temeli."""
    yuksek, dusuk, kapanis = df["High"], df["Low"], df["Close"]
    onceki = kapanis.shift(1)
    gercek_aralik = pd.concat(
        [yuksek - dusuk, (yuksek - onceki).abs(), (dusuk - onceki).abs()], axis=1
    ).max(axis=1)
    return gercek_aralik.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def macd(kapanis: pd.Series, hizli: int = 12, yavas: int = 26, sinyal: int = 9):
    cizgi = ema(kapanis, hizli) - ema(kapanis, yavas)
    sinyal_cizgi = ema(cizgi, sinyal)
    return cizgi, sinyal_cizgi, cizgi - sinyal_cizgi


def bollinger(kapanis: pd.Series, n: int = 20, k: float = 2.0):
    orta = sma(kapanis, n)
    sapma = kapanis.rolling(n, min_periods=n).std(ddof=0)
    return orta - k * sapma, orta, orta + k * sapma


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Trendin gücü (yönü değil). >25 trendli, <20 yatay kabul edilir."""
    yuksek, dusuk = df["High"], df["Low"]
    art_dm = yuksek.diff()
    azal_dm = -dusuk.diff()
    art_dm = art_dm.where((art_dm > azal_dm) & (art_dm > 0), 0.0)
    azal_dm = azal_dm.where((azal_dm > art_dm) & (azal_dm > 0), 0.0)

    tr = atr(df, n) * n  # yumuşatılmış TR toplamına yakın ölçek
    art_di = 100 * art_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / tr.replace(0, np.nan) * n
    azal_di = 100 * azal_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / tr.replace(0, np.nan) * n
    dx = 100 * (art_di - azal_di).abs() / (art_di + azal_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def donchian(df: pd.DataFrame, n: int = 20):
    """n günlük en yüksek/en düşük. Kırılım stratejisinin temeli.
    shift(1) şart: bugünün barı kendi kırılımını doğrulayamaz."""
    return df["High"].rolling(n, min_periods=n).max().shift(1), \
           df["Low"].rolling(n, min_periods=n).min().shift(1)


def hacim_orani(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Bugünkü hacim / n günlük ortalama. >1.5 = ilgi artışı."""
    ort = df["Volume"].rolling(n, min_periods=n).mean()
    return df["Volume"] / ort.replace(0, np.nan)


def gerceklesen_oynaklik(kapanis: pd.Series, n: int = 20) -> pd.Series:
    """Yıllıklandırılmış oynaklık (BIST'te ~252 işlem günü)."""
    return kapanis.pct_change().rolling(n, min_periods=n).std(ddof=0) * np.sqrt(252)


def goreli_guc(kapanis: pd.Series, endeks: pd.Series, n: int = 60) -> pd.Series:
    """Hissenin endekse göre n günlük göreli performansı (yüzde puan).
    Pozitif = endeksi yeniyor. Momentum seçiminin kalbi."""
    hisse_get = kapanis / kapanis.shift(n) - 1
    endeks_hiz = endeks.reindex(kapanis.index).ffill()
    endeks_get = endeks_hiz / endeks_hiz.shift(n) - 1
    return (hisse_get - endeks_get) * 100


def dususten_kayip(kapanis: pd.Series) -> pd.Series:
    """Zirveden geri çekilme yüzdesi (negatif)."""
    return (kapanis / kapanis.cummax() - 1) * 100


def gosterge_seti(df: pd.DataFrame, endeks: pd.Series | None = None) -> pd.DataFrame:
    """Tek çağrıda tüm göstergeleri hesaplayıp DataFrame'e ekler."""
    d = df.copy()
    k = d["Close"]

    d["EMA10"] = ema(k, 10)
    d["EMA20"] = ema(k, 20)
    d["EMA50"] = ema(k, 50)
    d["SMA200"] = sma(k, 200)
    d["RSI14"] = rsi(k, 14)
    d["RSI2"] = rsi(k, 2)
    d["ATR14"] = atr(d, 14)
    d["ATR_yuzde"] = d["ATR14"] / k * 100
    d["MACD"], d["MACD_sinyal"], d["MACD_fark"] = macd(k)
    d["BB_alt"], d["BB_orta"], d["BB_ust"] = bollinger(k)
    d["BB_konum"] = (k - d["BB_alt"]) / (d["BB_ust"] - d["BB_alt"]).replace(0, np.nan)
    d["ADX14"] = adx(d, 14)
    d["DON_ust"], d["DON_alt"] = donchian(d, 20)
    d["Hacim_orani"] = hacim_orani(d, 20)
    d["Oynaklik"] = gerceklesen_oynaklik(k, 20)
    d["Zirveden"] = dususten_kayip(k)
    d["Getiri_5g"] = (k / k.shift(5) - 1) * 100
    d["Getiri_20g"] = (k / k.shift(20) - 1) * 100
    d["Getiri_60g"] = (k / k.shift(60) - 1) * 100
    # TL cinsinden günlük işlem hacmi - likidite filtresi için
    d["TL_hacim"] = d["Close"] * d["Volume"]
    d["TL_hacim_ort20"] = d["TL_hacim"].rolling(20, min_periods=5).mean()

    if endeks is not None and len(endeks) > 0:
        d["GG20"] = goreli_guc(k, endeks, 20)
        d["GG60"] = goreli_guc(k, endeks, 60)
    else:
        d["GG20"] = np.nan
        d["GG60"] = np.nan

    return d
