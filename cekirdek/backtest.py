"""Gerçekçi backtest motoru.

Bu motorun amacı stratejiyi güzel göstermek DEĞİL, ne kadar kazandırıp
kaybettirdiğini dürüstçe ölçmektir. Bu yüzden şunlar bilerek modellenmiştir:

  * Sinyal t kapanışında üretilir, işlem t+1 AÇILIŞINDA yapılır (look-ahead yok)
  * Alışta yukarı, satışta aşağı kayma (slippage) uygulanır
  * Tavan/taban kuralı: ertesi gün tavanda açılan hisse alınamaz
  * Boşluklu (gap) açılışta stop, stop fiyatından değil AÇILIŞTAN çalışır
  * Aynı gün hem stop hem hedef görüldüyse kötümser varsayım: stop çalıştı
  * Nakit sınırlıdır; para yoksa sinyal kaçırılır (gerçek hayattaki gibi)
  * Midas BIST komisyonu 0 - ama kayma sıfır değildir
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .risk import RiskAyarlari, kademeye_yuvarla
from .strateji import Strateji, Filtreler, filtre_maskesi

TAVAN_ORANI = 1.195   # BIST ana pazar günlük tavan ~%20; %19.5 üstü "alınamaz"


@dataclass
class Islem:
    sembol: str
    giris_tarih: pd.Timestamp
    giris: float
    adet: int
    stop: float
    hedef: float
    cikis_tarih: pd.Timestamp | None = None
    cikis: float = 0.0
    sebep: str = ""

    @property
    def kar(self) -> float:
        return (self.cikis - self.giris) * self.adet

    @property
    def kar_yuzde(self) -> float:
        return (self.cikis / self.giris - 1) * 100 if self.giris else 0.0

    @property
    def gun(self) -> int:
        if self.cikis_tarih is None:
            return 0
        return int(np.busday_count(self.giris_tarih.date(), self.cikis_tarih.date()))


@dataclass
class Sonuc:
    islemler: list[Islem] = field(default_factory=list)
    ozkaynak: pd.Series = field(default_factory=pd.Series)
    kacirilan: int = 0          # nakit/slot yokken kaçan sinyal sayısı
    ayarlar: dict = field(default_factory=dict)

    def metrikler(self, kiyas: pd.Series | None = None) -> dict:
        return metrik_hesapla(self, kiyas)


def calistir(
    veriler: dict[str, pd.DataFrame],
    strateji: Strateji,
    risk_ayar: RiskAyarlari,
    filtre: Filtreler | None = None,
    kayma_bp: float = 15.0,          # tek yön kayma, baz puan (15bp = %0.15)
    baslangic: str | None = None,
    bitis: str | None = None,
) -> Sonuc:
    filtre = filtre or Filtreler()
    kayma = kayma_bp / 10_000.0

    # --- sinyalleri önceden vektörel hesapla (döngüde tekrar hesaplamamak için)
    hazir: dict[str, pd.DataFrame] = {}
    for sem, g in veriler.items():
        if g is None or len(g) < filtre.asgari_veri:
            continue
        d = g.copy()
        d["_giris"] = strateji.giris(d)
        d["_cikis"] = strateji.cikis(d)
        d["_uygun"] = filtre_maskesi(d, filtre)
        hazir[sem] = d

    if not hazir:
        return Sonuc(ayarlar={"hata": "yeterli veri yok"})

    takvim = sorted(set().union(*[set(d.index) for d in hazir.values()]))
    takvim = pd.DatetimeIndex(takvim)
    if baslangic:
        takvim = takvim[takvim >= pd.Timestamp(baslangic)]
    if bitis:
        takvim = takvim[takvim <= pd.Timestamp(bitis)]

    nakit = risk_ayar.sermaye
    acik: dict[str, Islem] = {}
    kapali: list[Islem] = []
    bekleyen_giris: list[str] = []
    bekleyen_cikis: set[str] = set()
    # Son bilinen fiyat. Bir hisse o gün işlem görmediyse (tatil, durdurma,
    # veri boşluğu) pozisyon değerlemeden DÜŞMEMELİ - yoksa özkaynak eğrisinde
    # olmayan bir çöküş görünür.
    son_fiyat: dict[str, float] = {}
    ozkaynak_kayit: list[tuple[pd.Timestamp, float]] = []
    kacirilan = 0

    for tarih in takvim:
        # ---------------------------------------------- 1) AÇILIŞTA ÇIKIŞLAR
        for sem in list(acik.keys()):
            d = hazir.get(sem)
            if d is None or tarih not in d.index:
                continue
            bar = d.loc[tarih]
            islem = acik[sem]

            gap_stop = bar["Open"] <= islem.stop      # stop'un altında açıldı
            sinyal_cikis = sem in bekleyen_cikis
            sure_doldu = int(np.busday_count(islem.giris_tarih.date(), tarih.date())) >= strateji.azami_tutma

            if gap_stop or sinyal_cikis or sure_doldu:
                fiyat = float(bar["Open"]) * (1 - kayma)
                islem.cikis = round(fiyat, 4)
                islem.cikis_tarih = tarih
                islem.sebep = "boşluklu stop" if gap_stop else ("sinyal" if sinyal_cikis else "süre doldu")
                nakit += islem.cikis * islem.adet
                kapali.append(islem)
                del acik[sem]
        bekleyen_cikis.clear()

        # ---------------------------------------------- 2) AÇILIŞTA GİRİŞLER
        for sem in bekleyen_giris:
            if sem in acik:
                continue
            if len(acik) >= risk_ayar.azami_es_zamanli:
                kacirilan += 1
                continue
            d = hazir.get(sem)
            if d is None or tarih not in d.index:
                continue
            bar = d.loc[tarih]
            konum = d.index.get_loc(tarih)
            if konum == 0:
                continue
            onceki_kapanis = float(d["Close"].iloc[konum - 1])

            # tavanda açılan hisse alınamaz - emir gerçekleşmez
            if float(bar["Open"]) >= onceki_kapanis * TAVAN_ORANI:
                kacirilan += 1
                continue

            alis = float(bar["Open"]) * (1 + kayma)
            atr_deger = float(bar.get("ATR14", np.nan))
            if not np.isfinite(atr_deger) or atr_deger <= 0:
                continue

            stop = kademeye_yuvarla(alis - strateji.atr_stop_kat * atr_deger)
            hedef = kademeye_yuvarla(alis + strateji.atr_hedef_kat * atr_deger, yukari=True)
            if stop >= alis:
                continue

            # pozisyon boyutu: canlı özkaynağa göre (sabit sermayeye göre değil)
            ozk = nakit + sum(a.adet * son_fiyat.get(s, a.giris) for s, a in acik.items())
            risk_butcesi = ozk * risk_ayar.islem_basi_risk_yuzde / 100
            adet = int(min(
                risk_butcesi / (alis - stop),
                (ozk * risk_ayar.azami_pozisyon_yuzde / 100) / alis,
                nakit / alis,
            ))
            if adet < 1:
                kacirilan += 1
                continue

            nakit -= adet * alis
            acik[sem] = Islem(sem, tarih, round(alis, 4), adet, stop, hedef)
            son_fiyat[sem] = float(bar["Close"]) if np.isfinite(bar["Close"]) else alis
        bekleyen_giris = []

        # ---------------------------------------------- 3) GÜN İÇİ STOP/HEDEF
        for sem in list(acik.keys()):
            d = hazir.get(sem)
            if d is None or tarih not in d.index:
                continue
            bar = d.loc[tarih]
            islem = acik[sem]
            if islem.giris_tarih == tarih:
                # aynı gün girdi: açılış zaten kontrol edildi, gün içi de bakılır
                pass
            if float(bar["Low"]) <= islem.stop:
                islem.cikis = islem.stop * (1 - kayma)
                islem.sebep = "stop"
            elif float(bar["High"]) >= islem.hedef:
                islem.cikis = islem.hedef * (1 - kayma)
                islem.sebep = "hedef"
            else:
                continue
            islem.cikis_tarih = tarih
            nakit += islem.cikis * islem.adet
            kapali.append(islem)
            del acik[sem]

        # ---------------------------------------------- 4) KAPANIŞTA DEĞERLEME
        for sem, islem in acik.items():
            d = hazir.get(sem)
            if d is not None and tarih in d.index:
                son_fiyat[sem] = float(d.loc[tarih, "Close"])
            son_fiyat.setdefault(sem, islem.giris)
        piyasa = sum(a.adet * son_fiyat[s] for s, a in acik.items())
        ozkaynak_kayit.append((tarih, nakit + piyasa))

        # ---------------------------------------------- 5) YARIN İÇİN SİNYAL
        if len(acik) < risk_ayar.azami_es_zamanli:
            adaylar = []
            for sem, d in hazir.items():
                if sem in acik or tarih not in d.index:
                    continue
                bar = d.loc[tarih]
                if bool(bar["_giris"]) and bool(bar["_uygun"]):
                    # aynı gün birden çok sinyalde en güçlü momentumu tercih et
                    adaylar.append((float(bar.get("GG60", 0) if np.isfinite(bar.get("GG60", np.nan)) else 0), sem))
            adaylar.sort(reverse=True)
            bekleyen_giris = [s for _, s in adaylar[: risk_ayar.azami_es_zamanli * 2]]

        for sem in acik:
            d = hazir.get(sem)
            if d is not None and tarih in d.index and bool(d.loc[tarih, "_cikis"]):
                bekleyen_cikis.add(sem)

    # açık kalanları son fiyattan kapat (raporlama için)
    son = takvim[-1]
    for sem, islem in acik.items():
        d = hazir[sem]
        if son in d.index:
            islem.cikis = float(d.loc[son, "Close"])
            islem.cikis_tarih = son
            islem.sebep = "dönem sonu (açık)"
            kapali.append(islem)

    ozk_seri = pd.Series(dict(ozkaynak_kayit)).sort_index()
    return Sonuc(
        islemler=kapali,
        ozkaynak=ozk_seri,
        kacirilan=kacirilan,
        ayarlar={
            "strateji": strateji.ad, "sermaye": risk_ayar.sermaye,
            "risk_yuzde": risk_ayar.islem_basi_risk_yuzde,
            "azami_pozisyon": risk_ayar.azami_es_zamanli,
            "kayma_bp": kayma_bp, "hisse_sayisi": len(hazir),
        },
    )


# Türkiye'de mevduat/tahvil faizi. BU ÖNEMLİ: %40 faizin olduğu ülkede
# %27 getiren strateji, risksiz alternatifin ALTINDADIR. Risksiz getiriyi
# çıkarmayan bir Sharpe, her stratejiyi olduğundan iyi gösterir —
# `istatistik.performans` bunu baştan beri doğru yapıyordu, backtest
# yapmıyordu ve iki yerde iki farklı sayı üretiliyordu.
RISKSIZ_YILLIK = 40.0


def metrik_hesapla(sonuc: Sonuc, kiyas: pd.Series | None = None,
                   risksiz_yillik: float = RISKSIZ_YILLIK) -> dict:
    ozk = sonuc.ozkaynak
    if len(ozk) < 2:
        return {"hata": "yetersiz veri"}

    bas, bit = float(ozk.iloc[0]), float(ozk.iloc[-1])
    gun_sayisi = len(ozk)
    yil = gun_sayisi / 252.0

    getiri = (bit / bas - 1) * 100
    cagr = ((bit / bas) ** (1 / yil) - 1) * 100 if yil > 0 and bas > 0 else 0.0

    gunluk = ozk.pct_change().dropna()
    oynaklik = gunluk.std(ddof=0) * np.sqrt(252) * 100 if len(gunluk) > 1 else 0.0
    # FAZLA getiri: günlük getiriden günlük risksiz getiri çıkarılır.
    # Bu satır olmadan Sharpe "getiri / oynaklık" olur ve mevduatın
    # altında kalan bir strateji 1,9 gibi mükemmel bir skor alır.
    rf_gunluk = (1 + risksiz_yillik / 100) ** (1 / 252) - 1
    fazla = gunluk - rf_gunluk
    sharpe = (fazla.mean() / gunluk.std(ddof=0) * np.sqrt(252)) if gunluk.std(ddof=0) > 0 else 0.0
    negatif = fazla[fazla < 0]
    sortino = (fazla.mean() / negatif.std(ddof=0) * np.sqrt(252)) if len(negatif) > 1 and negatif.std(ddof=0) > 0 else 0.0
    dd = (ozk / ozk.cummax() - 1) * 100
    azami_dd = float(dd.min())

    islemler = [i for i in sonuc.islemler if i.cikis_tarih is not None]
    kazanan = [i for i in islemler if i.kar > 0]
    kaybeden = [i for i in islemler if i.kar <= 0]
    kazanc_top = sum(i.kar for i in kazanan)
    kayip_top = abs(sum(i.kar for i in kaybeden))

    m = {
        "baslangic": round(bas, 2), "bitis": round(bit, 2),
        "toplam_getiri_yuzde": round(getiri, 2),
        "yillik_getiri_yuzde": round(cagr, 2),
        "gun_sayisi": gun_sayisi, "yil": round(yil, 2),
        "gunluk_ort_yuzde": round(float(gunluk.mean()) * 100, 4),
        "oynaklik_yuzde": round(float(oynaklik), 2),
        "sharpe": round(float(sharpe), 2),
        "risksiz_yillik": risksiz_yillik,
        "sortino": round(float(sortino), 2),
        "azami_dusus_yuzde": round(azami_dd, 2),
        "islem_sayisi": len(islemler),
        "kazanma_orani": round(len(kazanan) / len(islemler) * 100, 1) if islemler else 0.0,
        "ort_kazanc_yuzde": round(float(np.mean([i.kar_yuzde for i in kazanan])), 2) if kazanan else 0.0,
        "ort_kayip_yuzde": round(float(np.mean([i.kar_yuzde for i in kaybeden])), 2) if kaybeden else 0.0,
        "kar_faktoru": round(kazanc_top / kayip_top, 2) if kayip_top > 0 else float("inf"),
        "ort_tutma_gun": round(float(np.mean([i.gun for i in islemler])), 1) if islemler else 0.0,
        "kacirilan_sinyal": sonuc.kacirilan,
        "en_iyi_islem_yuzde": round(max((i.kar_yuzde for i in islemler), default=0), 2),
        "en_kotu_islem_yuzde": round(min((i.kar_yuzde for i in islemler), default=0), 2),
    }
    if islemler:
        m["islem_basi_gun"] = round(gun_sayisi / len(islemler), 1)

    if kiyas is not None and len(kiyas) > 1:
        k = kiyas.reindex(ozk.index).ffill().dropna()
        if len(k) > 1:
            k_get = (float(k.iloc[-1]) / float(k.iloc[0]) - 1) * 100
            m["kiyas_getiri_yuzde"] = round(k_get, 2)
            m["alfa_yuzde"] = round(getiri - k_get, 2)
            k_dd = float(((k / k.cummax() - 1) * 100).min())
            m["kiyas_azami_dusus_yuzde"] = round(k_dd, 2)
    return m
