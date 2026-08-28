"""Alıştırma kum havuzu — sanal parayla işlem öğrenme.

NEDEN AYRI: kullanıcı borsaya yeni başlıyor ve "stop, hedef, tutar ne
demek" diye soruyor. Dersler bunları anlatıyor (d802, d805) ama okumakla
yapmak farklı. Burada hata yapabilmesi gerekiyor — gerçek portföyde
yapamaz, karar defterinde de yapmamalı (orası ölçüm kaydı).

KUM HAVUZU GERÇEKTEN AYRI: kendi sanal bakiyesi var, istendiğinde
sıfırlanıyor, karar defterine ve sermaye defterine HİÇ dokunmuyor.
Öğrenmek için batırabilmek şart; batırdığın hesap ölçülen hesap olmamalı.

İKİ MOD (kullanıcı başlangıçta seçiyor):
  GEÇMİŞ — geçmişte bir tarihe gidilir, alım yapılır, "sonraki gün"
           düğmesiyle ilerlenir. 20 günlük sonuç 20 saniyede alınır.
           Öğrenme döngüsü haftalar değil saniyeler sürer.
  CANLI  — bugünün gerçek fiyatları, sonuç gerçek günlerde gelir.
           Daha gerçekçi ama yavaş.

ÇIKIŞ KURALLARI BACKTEST İLE BİREBİR AYNI (bkz. cekirdek/backtest.py):
boşluklu açılışta stop AÇILIŞTAN çalışır, aynı gün hem stop hem hedef
görüldüyse kötümser varsayımla stop sayılır. Alıştırmada stop başka
türlü çalışsaydı kullanıcı yanlış şey öğrenir ve gerçek işlemde
şaşırırdı — alıştırmanın tek işi gerçeğe hazırlamak.

DURUM TELEFONDA: bu modül saf hesap yapıyor, hiçbir şey saklamıyor.
Kum havuzunun bakiyesi ve pozisyonları telefonda yaşıyor ve bulut
yedeğiyle taşınıyor — API'nin durumsuzluğu korunuyor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import veri
from .gostergeler import atr

BASLANGIC_BAKIYE = 10_000.0

# Backtest ile aynı: ertesi gün önceki kapanışın %19,5 üstünde açan
# hisse alınamaz sayılır (backtest.TAVAN_ORANI).
TAVAN_ORANI = 1.195

# Geçmiş modunda kaç gün geriye gidilebilir. yfinance ~1 yıl veriyor;
# sınırı biraz altında tutmak "veri yok" hatasını azaltıyor.
AZAMI_GERI_GUN = 300


@dataclass
class Bar:
    """Bir günün fiyatları. Alıştırma bunun dışında bir şey görmez."""
    tarih: str
    acilis: float
    yuksek: float
    dusuk: float
    kapanis: float
    onceki_kapanis: float
    atr: float

    @property
    def tavan_mi(self) -> bool:
        """Açılış tavana yakınsa alım yapılamaz — gerçekte satıcı yoktur."""
        if self.onceki_kapanis <= 0:
            return False
        return self.acilis >= self.onceki_kapanis * TAVAN_ORANI

    def sozluk(self) -> dict:
        return {"tarih": self.tarih, "acilis": round(self.acilis, 4),
                "yuksek": round(self.yuksek, 4), "dusuk": round(self.dusuk, 4),
                "kapanis": round(self.kapanis, 4),
                "onceki_kapanis": round(self.onceki_kapanis, 4),
                "atr": round(self.atr, 4), "tavan_mi": self.tavan_mi}


@dataclass
class Cikis:
    sembol: str
    fiyat: float
    sebep: str          # "stop" | "hedef"
    tarih: str


def _seri(sembol: str, gun: int = 420) -> pd.DataFrame:
    d = veri.fiyat_cek(sembol, gun=gun, onbellek_saat=12.0)
    if d is None or d.empty:
        return pd.DataFrame()
    d = d.copy()
    d["ATR14"] = atr(d, 14)
    return d


def barlar(sembol: str, bitis: str | None = None, adet: int = 1,
           gun: int = 420) -> list[Bar]:
    """`bitis` tarihine kadar (dahil) son `adet` günün barları.

    Tarih işlem günü değilse (hafta sonu, tatil) o tarihten ÖNCEKİ en
    yakın işlem günü kullanılır — kullanıcı takvimden cumartesi seçtiğinde
    "veri yok" demek yerine cumayı göstermek doğrusu.
    """
    d = _seri(sembol, gun=gun)
    if d.empty:
        return []
    if bitis:
        try:
            sinir = pd.Timestamp(bitis)
        except Exception:
            return []
        d = d[d.index <= sinir]
    if d.empty:
        return []

    d = d.tail(max(1, adet) + 1)          # +1: önceki kapanış için
    cikti: list[Bar] = []
    onceki = float(d["Close"].iloc[0])
    for i in range(1, len(d)) if len(d) > 1 else range(0, 1):
        s = d.iloc[i]
        a = float(s.get("ATR14", np.nan))
        cikti.append(Bar(
            tarih=d.index[i].strftime("%Y-%m-%d"),
            acilis=float(s["Open"]), yuksek=float(s["High"]),
            dusuk=float(s["Low"]), kapanis=float(s["Close"]),
            onceki_kapanis=onceki,
            atr=a if np.isfinite(a) else 0.0))
        onceki = float(s["Close"])
    return cikti[-adet:] if cikti else []


def gun(sembol: str, tarih: str | None = None) -> Bar | None:
    b = barlar(sembol, bitis=tarih, adet=1)
    return b[0] if b else None


def sonraki_gun(sembol: str, tarih: str) -> Bar | None:
    """`tarih`ten SONRAKİ ilk işlem günü. Geçmiş modunun motoru bu."""
    d = _seri(sembol)
    if d.empty:
        return None
    try:
        sinir = pd.Timestamp(tarih)
    except Exception:
        return None
    sonra = d[d.index > sinir]
    if sonra.empty:
        return None
    onceki_dilim = d[d.index <= sinir]
    onceki = (float(onceki_dilim["Close"].iloc[-1])
              if not onceki_dilim.empty else float(sonra["Close"].iloc[0]))
    s = sonra.iloc[0]
    a = float(s.get("ATR14", np.nan))
    return Bar(tarih=sonra.index[0].strftime("%Y-%m-%d"),
               acilis=float(s["Open"]), yuksek=float(s["High"]),
               dusuk=float(s["Low"]), kapanis=float(s["Close"]),
               onceki_kapanis=onceki, atr=a if np.isfinite(a) else 0.0)


def cikis_kontrol(pozisyon: dict, bar: Bar) -> Cikis | None:
    """Bu barda stop ya da hedef çalıştı mı?

    KURALLAR BACKTEST İLE AYNI ve sırası önemli:
      1) Boşluklu açılış: açılış stopun altındaysa çıkış STOP FİYATINDAN
         DEĞİL AÇILIŞTAN olur. "Stopum 100'dü" desen de hisse 92'den
         açtıysa 92'den çıkarsın.
      2) Gün içi stop, hedeften ÖNCE bakılır: aynı gün ikisi de görüldüyse
         kötümser varsayım. Hangisinin önce olduğunu günlük barla bilemeyiz;
         iyimser varsaymak sonuçları sistematik olarak güzelleştirirdi.
    """
    stop = float(pozisyon.get("stop") or 0)
    hedef = float(pozisyon.get("hedef") or 0)
    sem = pozisyon.get("sembol", "")

    if stop > 0 and bar.acilis <= stop:
        return Cikis(sem, bar.acilis, "stop", bar.tarih)
    if stop > 0 and bar.dusuk <= stop:
        return Cikis(sem, stop, "stop", bar.tarih)
    if hedef > 0 and bar.acilis >= hedef:
        return Cikis(sem, bar.acilis, "hedef", bar.tarih)
    if hedef > 0 and bar.yuksek >= hedef:
        return Cikis(sem, hedef, "hedef", bar.tarih)
    return None


def adet_oner(bakiye: float, fiyat: float, stop: float,
              risk_yuzde: float = 1.5, azami_pozisyon_yuzde: float = 35.0) -> dict:
    """Pozisyon boyutu — d802'deki hesabın aynısı.

    Alıştırmanın öğretmesi gereken şey tam olarak bu: adedi 'içine sinen
    miktar' değil STOP MESAFESİ belirler. Stop uzaksa daha az adet alırsın.
    """
    if fiyat <= 0:
        return {"adet": 0, "sebep": "fiyat geçersiz"}
    if stop <= 0 or stop >= fiyat:
        return {"adet": 0, "sebep": "stop giriş fiyatının altında olmalı"}

    risk_butcesi = bakiye * risk_yuzde / 100
    hisse_basi_risk = fiyat - stop
    riskten = risk_butcesi / hisse_basi_risk
    tavandan = (bakiye * azami_pozisyon_yuzde / 100) / fiyat
    nakitten = bakiye / fiyat
    adet = int(min(riskten, tavandan, nakitten))

    baglayici = "risk bütçesi"
    if tavandan <= riskten and tavandan <= nakitten:
        baglayici = "tek hisse tavanı"
    elif nakitten <= riskten:
        baglayici = "nakit"

    return {"adet": max(0, adet),
            "risk_butcesi": round(risk_butcesi, 2),
            "hisse_basi_risk": round(hisse_basi_risk, 4),
            "maliyet": round(max(0, adet) * fiyat, 2),
            "baglayici": baglayici}
