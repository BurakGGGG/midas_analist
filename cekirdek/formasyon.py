"""Formasyon, Fibonacci ve çoklu zaman dilimi analizi.

UYARI — bu modülü yazmanın en dürüst yolu şudur: formasyonlar geçmiş grafikte
herkese görünür, gerçek zamanda görünmez. Bir "omuz-baş-omuz" ancak tamamlandıktan
sonra omuz-baş-omuzdur; tamamlanmadan önce sadece dalgalı bir grafiktir.

Bu yüzden burada süslü formasyon isimleri yok. Ölçülebilir YAPI var:
tepe/dip dizilimi, sıkışma, Fibonacci seviyeleri, sahte kırılım oranı.
Hepsi sayıya çevrilebilir, dolayısıyla test edilebilir.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .gostergeler import atr, ema, sma


# ─────────────────────────────────────────────────── tepe / dip

def tepeler_dipler(df: pd.DataFrame, pencere: int = 5) -> tuple[pd.Series, pd.Series]:
    """Yerel tepe ve dipler (fractal). pencere kadar sağ-sol teyit ister.

    Dikkat: son `pencere` bar için tepe/dip KESİNLEŞMEZ — sağ tarafı henüz
    oluşmadı. Bu yüzden sonuç kaydırılır; geleceğe bakma olmaz.
    """
    y, d = df["High"], df["Low"]
    tepe = (y == y.rolling(pencere * 2 + 1, center=True).max())
    dip = (d == d.rolling(pencere * 2 + 1, center=True).min())
    # merkezli pencere geleceği kullanır; teyit ancak `pencere` bar sonra gelir
    return tepe.shift(pencere).fillna(False), dip.shift(pencere).fillna(False)


def yapi(df: pd.DataFrame, pencere: int = 5, bak: int = 120) -> dict:
    """Trend yapısı: daha yüksek tepeler / daha yüksek dipler var mı?

    Trendin gerçek tanımı budur — hareketli ortalama değil. Yükselen trend
    'her tepe bir öncekinden yüksek, her dip bir öncekinden yüksek' demektir.
    """
    t, d = tepeler_dipler(df, pencere)
    son = df.tail(bak)
    t, d = t.tail(bak), d.tail(bak)

    tepe_f = son.loc[t, "High"].tail(3)
    dip_f = son.loc[d, "Low"].tail(3)

    if len(tepe_f) < 2 or len(dip_f) < 2:
        return {"yapi": "belirsiz", "aciklama": "yeterli tepe/dip oluşmamış",
                "tepeler": list(tepe_f), "dipler": list(dip_f)}

    yuksek_tepe = tepe_f.iloc[-1] > tepe_f.iloc[-2]
    yuksek_dip = dip_f.iloc[-1] > dip_f.iloc[-2]

    if yuksek_tepe and yuksek_dip:
        ad, aciklama = "YÜKSELEN", "Daha yüksek tepe + daha yüksek dip. Trend sağlam."
    elif not yuksek_tepe and not yuksek_dip:
        ad, aciklama = "DÜŞEN", "Daha alçak tepe + daha alçak dip. Alım için erken."
    elif yuksek_dip and not yuksek_tepe:
        ad, aciklama = "sıkışan", "Dipler yükseliyor ama tepe kırılamıyor — sıkışma. Kırılım yakın olabilir."
    else:
        ad, aciklama = "bozulan", "Tepe yükseldi ama dip kırıldı — trend bozuluyor, dikkat."

    return {
        "yapi": ad, "aciklama": aciklama,
        "tepeler": [round(float(x), 2) for x in tepe_f],
        "dipler": [round(float(x), 2) for x in dip_f],
        "son_tepe": float(tepe_f.iloc[-1]), "son_dip": float(dip_f.iloc[-1]),
    }


# ─────────────────────────────────────────────────── Fibonacci

FIB = [0.236, 0.382, 0.5, 0.618, 0.786]


def fibonacci(df: pd.DataFrame, bak: int = 120) -> dict:
    """Son belirgin hareketin Fibonacci geri çekilme seviyeleri.

    Fibonacci'nin işe yaramasının sebebi gizemli bir doğa yasası değil,
    çok sayıda kişinin aynı seviyelere bakması ve oraya emir koymasıdır.
    Kendi kendini gerçekleştiren bir beklentidir — ve tam bu yüzden
    herkesin stop'u aynı yerdeyse orası kırılmaya açıktır.
    """
    son = df.tail(bak)
    if len(son) < 20:
        return {"hata": "yetersiz veri"}

    dip_i = son["Low"].idxmin()
    tepe_i = son["High"].idxmax()
    dip, tepe = float(son["Low"].min()), float(son["High"].max())
    if tepe <= dip:
        return {"hata": "geçersiz aralık"}

    yukari = tepe_i > dip_i        # hareket aşağıdan yukarı mı?
    aralik = tepe - dip
    seviyeler = {}
    for f in FIB:
        seviyeler[f] = (tepe - aralik * f) if yukari else (dip + aralik * f)

    fiyat = float(df["Close"].iloc[-1])
    yakin = min(seviyeler.items(), key=lambda kv: abs(kv[1] - fiyat))

    return {
        "yon": "yükseliş" if yukari else "düşüş",
        "dip": round(dip, 2), "tepe": round(tepe, 2),
        "dip_tarih": str(dip_i.date()), "tepe_tarih": str(tepe_i.date()),
        "seviyeler": {f"%{int(f*100)}": round(v, 2) for f, v in seviyeler.items()},
        "fiyat": round(fiyat, 2),
        "en_yakin": {"seviye": f"%{int(yakin[0]*100)}", "fiyat": round(yakin[1], 2),
                     "uzaklik_yuzde": round((fiyat / yakin[1] - 1) * 100, 2)},
        "not": "Fibonacci tek başına sinyal değildir. Seviyeye gelen fiyatın orada "
               "NE YAPTIĞINA bak — hacimle tepki veriyor mu, yoksa geçip gidiyor mu?",
    }


# ─────────────────────────────────────────────────── sahte kırılım

def sahte_kirilim_orani(df: pd.DataFrame, don: int = 20, teyit: int = 3) -> dict:
    """Bu hissede kırılımların yüzde kaçı SAHTE çıkmış — geçmişten ölçülür.

    'Kırılımların çoğu sahtedir' herkesin bildiği bir sözdür ama kimse hisse
    bazında ölçmez. Oysa bazı hisselerde kırılım tutar, bazılarında tutmaz.
    """
    if len(df) < don + teyit + 30:
        return {"hata": "yetersiz veri"}

    ust = df["High"].rolling(don, min_periods=don).max().shift(1)
    kirilim = df["Close"] > ust
    idx = np.where(kirilim.fillna(False).values)[0]
    idx = idx[idx < len(df) - teyit]
    if len(idx) < 5:
        return {"hata": f"yeterli kırılım örneği yok ({len(idx)})"}

    kapanis = df["Close"].values
    tutan = 0
    for i in idx:
        # teyit barları içinde kırılım seviyesinin altına dönmediyse "tuttu"
        seviye = float(ust.iloc[i])
        if np.min(kapanis[i + 1: i + 1 + teyit]) >= seviye:
            tutan += 1

    oran = tutan / len(idx) * 100
    return {
        "kirilim_sayisi": len(idx), "tutan": tutan,
        "tutma_orani_yuzde": round(oran, 1),
        "sahte_orani_yuzde": round(100 - oran, 1),
        "yorum": (f"{len(idx)} kırılımın {tutan}'i tuttu (%{oran:.0f}). " +
                  ("Bu hissede kırılımlar görece güvenilir." if oran >= 55 else
                   "Bu hissede kırılımların çoğu sahte — hacim teyidi olmadan girme.")),
    }


# ─────────────────────────────────────────────────── çoklu zaman dilimi

def cok_zamanli(gunluk: pd.DataFrame) -> dict:
    """Günlük + haftalık + aylık uyum kontrolü.

    Kural: BÜYÜK zaman dilimi yönü belirler, küçük zaman dilimi zamanlamayı.
    Haftalık düşüş trendindeyken günlük alım sinyali, akıntıya karşı yüzmektir.
    """
    if len(gunluk) < 220:
        return {"hata": "yetersiz veri"}

    def ozet(d: pd.DataFrame, etiket: str, uzun: int, orta: int) -> dict:
        k = d["Close"]
        e_orta, e_uzun = ema(k, orta), sma(k, uzun)
        son = float(k.iloc[-1])
        yon = ("yukarı" if son > float(e_uzun.iloc[-1]) and
               float(e_orta.iloc[-1]) > float(e_uzun.iloc[-1]) else
               "aşağı" if son < float(e_uzun.iloc[-1]) else "yatay")
        return {"dilim": etiket, "yon": yon, "fiyat": round(son, 2),
                "orta_ort": round(float(e_orta.iloc[-1]), 2),
                "uzun_ort": round(float(e_uzun.iloc[-1]), 2),
                "bar": len(d)}

    haftalik = gunluk.resample("W").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()
    aylik = gunluk.resample("ME").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna()

    dilimler = [ozet(gunluk, "günlük", 200, 20)]
    if len(haftalik) >= 40:
        dilimler.append(ozet(haftalik, "haftalık", 40, 10))
    if len(aylik) >= 24:
        dilimler.append(ozet(aylik, "aylık", 24, 6))

    yonler = [d["yon"] for d in dilimler]
    if all(y == "yukarı" for y in yonler):
        uyum, aciklama = "TAM UYUM (yukarı)", "Her zaman diliminde yükseliş. Alım için en elverişli durum."
    elif all(y == "aşağı" for y in yonler):
        uyum, aciklama = "TAM UYUM (aşağı)", "Her zaman diliminde düşüş. Uzun taraf için girme."
    elif yonler[-1] == "aşağı" and yonler[0] == "yukarı":
        uyum, aciklama = "ÇELİŞKİ", "Büyük resim aşağı, günlük yukarı. Bu bir tepki alımıdır — kısa tut, hedefi küçült."
    else:
        uyum, aciklama = "kısmi uyum", "Zaman dilimleri tam hizalanmamış. Pozisyonu küçült."

    return {"dilimler": dilimler, "uyum": uyum, "aciklama": aciklama,
            "kural": "Büyük dilim yönü belirler, küçük dilim zamanlamayı verir."}


def tam_analiz(df: pd.DataFrame) -> dict:
    return {
        "yapi": yapi(df),
        "fibonacci": fibonacci(df),
        "sahte_kirilim": sahte_kirilim_orani(df),
        "cok_zamanli": cok_zamanli(df),
    }
