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
görüldüyse kötümser varsayımla stop sayılır, hedefin üstünde açan hisse
hedef fiyatından çıkar. Alıştırmada stop başka türlü çalışsaydı kullanıcı
yanlış şey öğrenir ve gerçek işlemde şaşırırdı — alıştırmanın tek işi
gerçeğe hazırlamak. Bu eşitlik testle kilitli (test_alistirma.py):
gerçek backtest koşulup her işlemin çıkışı burada yeniden üretiliyor.

TEK BİLİNEN FARK: backtest'in süre-doldu ve strateji-çıkış kuralları
burada yok. Simülatörde stopu ve hedefi kullanıcı koyuyor, arkasında
bir strateji olmayabilir; pozisyonu zorla kapatmak kullanıcının kendi
kararını elinden almak olurdu.

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

# Simülasyonun veri derinliği.
#
# BU SAYI KÜÇÜK OLURSA GEÇMİŞ VERİ SİLİNİR. `veri.fiyat_cek` önbellek
# bayatsa seriyi yeniden indirir ve dosyanın üzerine YALNIZCA istenen
# derinlikle yazar. Eskiden 420'ydi: tek bir "2024-06-12'nin fiyatı ne"
# sorusu, diskteki 2024 verisini silip sonraki soruyu "veri yok"
# bırakabiliyordu. Günlük iş 750 ile yazdığı için tesadüfen kapalıydı.
#
# 1300 gün ≈ 3,5 yıl: kullanıcının seçebileceği en erken tarihten
# rahatça geride, ve göstergelerin (SMA200) ısınma payını da kapsıyor.
GECMIS_GUN = 1300


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


def _seri(sembol: str, gun: int = GECMIS_GUN) -> pd.DataFrame:
    d = veri.fiyat_cek(sembol, gun=gun, onbellek_saat=12.0)
    if d is None or d.empty:
        return pd.DataFrame()
    d = d.copy()
    d["ATR14"] = atr(d, 14)
    return d


def barlar(sembol: str, bitis: str | None = None, adet: int = 1,
           gun: int = GECMIS_GUN) -> list[Bar]:
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
      3) Hedefin ÜSTÜNDE açan hisse yine HEDEF fiyatından çıkar, açılıştan
         değil. Gerçekte limit satışın açılışta dolardı ve daha çok
         kazanırdın — ama backtest böyle modellemiyor (backtest.py:194) ve
         iki yerin farklı davranması, simülatörün backtest'ten sistematik
         olarak daha iyi görünmesi demekti. Kullanıcı hangi rakama
         güveneceğini bilemezdi. Boşluk AŞAĞI yönde açılıştan işleniyor
         (madde 1); ikisi de kullanıcının aleyhine ve bu bilinçli.
    """
    stop = float(pozisyon.get("stop") or 0)
    hedef = float(pozisyon.get("hedef") or 0)
    sem = pozisyon.get("sembol", "")

    if stop > 0 and bar.acilis <= stop:
        return Cikis(sem, bar.acilis, "stop", bar.tarih)
    if stop > 0 and bar.dusuk <= stop:
        return Cikis(sem, stop, "stop", bar.tarih)
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


# ══════════════════════════════════════════════════════ simülasyon motoru
#
# Buradan aşağısı "Sanal İşlem" ekranını besliyor: tarih seç, al, günleri
# ilerlet, portföyünü izle. Yukarıdaki tek-bar yardımcıları duruyor —
# bunlar onların çok günlü ve çok sembollü hâli.
#
# KAYMA BACKTEST İLE AYNI. Kum havuzunun ilk hâli kayma uygulamıyordu ve
# bu, simülatörü backtest'ten sistematik olarak ~%0,3 daha iyi
# gösteriyordu. İki ekranın farklı gerçeklik anlatması, kullanıcının
# hangisine güveneceğini bilememesi demek.
KAYMA_BP = 15.0        # tek yön, baz puan (15bp = %0,15)

# Pozisyonu olmayan kullanıcı da günleri ilerletebilmeli. Takvim bir
# referans sembolden okunuyor; endeksin kendisi değil çünkü XU100
# serisi bazı günlerde hisselerden ayrışıyor.
TAKVIM_SEMBOLU = "THYAO"

# Sinyal hesabında göstergelerin ısınması için kaç satır yeterli.
# SMA200 en uzun pencere; 400 satır iki kat pay bırakıyor.
ISINMA_SATIRI = 400

# Süreç içi seri önbelleği. `/alistirma/adim` bir haftayı tek turda
# ilerletirken aynı seriyi 5 kez okumamalı; disk okuması + ATR hesabı
# sembol başına ~1,5 ms ve 100 sembolde bu 0,75 saniyeye çıkıyor.
_SERI_ONBELLEK: dict[str, tuple[float, pd.DataFrame]] = {}
_ONBELLEK_OMRU_SN = 300.0


def _onbellekli_seri(sembol: str) -> pd.DataFrame:
    import time
    simdi = time.time()
    kayit = _SERI_ONBELLEK.get(sembol)
    if kayit and simdi - kayit[0] < _ONBELLEK_OMRU_SN:
        return kayit[1]
    d = _seri(sembol)
    _SERI_ONBELLEK[sembol] = (simdi, d)
    return d


def onbellegi_bosalt() -> None:
    """Testler ve uzun süreçler için."""
    _SERI_ONBELLEK.clear()


def seri(sembol: str, baslangic: str | None = None,
         bitis: str | None = None) -> pd.DataFrame:
    """Tarih aralığının OHLCV + ATR'si. Simülatörün tek veri kapısı."""
    d = _onbellekli_seri(sembol)
    if d.empty:
        return d
    try:
        if baslangic:
            d = d[d.index >= pd.Timestamp(baslangic)]
        if bitis:
            d = d[d.index <= pd.Timestamp(bitis)]
    except Exception:
        return pd.DataFrame()
    return d


def takvim(baslangic: str, bitis: str | None = None,
           sembol: str = TAKVIM_SEMBOLU) -> list[str]:
    """Aralıktaki işlem günleri — VERİ ENDEKSİNDEN.

    Tatil tablosu kullanılmıyor: `gunluk.TATILLER_2026` yalnızca 2026'yı
    biliyor ve `np.busday_count` Türk tatillerini hiç bilmiyor. Borsanın
    açık olduğu günler zaten serinin endeksinde duruyor.
    """
    d = seri(sembol, baslangic, bitis)
    return [t.strftime("%Y-%m-%d") for t in d.index]


def aralik(sembol: str = TAKVIM_SEMBOLU) -> dict:
    """Kullanıcının takvimden seçebileceği en erken/en geç gün.

    Sabit bir tarih yazmak yanlış olurdu: aralık önbellekteki veriye
    bağlı ve kurulumdan kuruluma değişiyor.
    """
    d = _onbellekli_seri(sembol)
    if d.empty:
        return {"en_erken": "", "en_gec": "", "gun_sayisi": 0}
    # Son gün DIŞARIDA: kullanıcı son güne başlarsa "sonraki gün" hemen
    # tükenir ve simülasyon başlar başlamaz biter.
    return {"en_erken": d.index[0].strftime("%Y-%m-%d"),
            "en_gec": d.index[-2].strftime("%Y-%m-%d") if len(d) > 1
                      else d.index[-1].strftime("%Y-%m-%d"),
            "gun_sayisi": len(d)}


# ── değerleme ──────────────────────────────────────────────────────────────

def deger(pozisyonlar: list[dict], nakit: float, tarih: str) -> dict:
    """Portföyün o günkü değeri.

    İŞLEM GÖRMEYEN GÜNDE SON BİLİNEN FİYAT KORUNUR (backtest de öyle
    yapıyor). Fiyatı bulunamayan hisseyi sıfır saymak özkaynak eğrisinde
    sahte bir çöküş çizerdi ve kullanıcı olmayan bir kaybı öğrenirdi.
    """
    satirlar, piyasa, maliyet = [], 0.0, 0.0
    for p in pozisyonlar or []:
        sem = p.get("sembol", "")
        adet = int(p.get("adet") or 0)
        giris = float(p.get("giris") or 0)
        b = gun(sem, tarih)
        fiyat = b.kapanis if b else giris     # fiyat yoksa girişe düş
        d_maliyet = adet * giris
        d_piyasa = adet * fiyat
        piyasa += d_piyasa
        maliyet += d_maliyet
        stop = float(p.get("stop") or 0)
        hedef = float(p.get("hedef") or 0)
        satirlar.append({
            "sembol": sem, "adet": adet, "giris": round(giris, 4),
            "fiyat": round(fiyat, 4),
            "tarih": b.tarih if b else tarih,
            "maliyet": round(d_maliyet, 2), "deger": round(d_piyasa, 2),
            "kar": round(d_piyasa - d_maliyet, 2),
            "kar_yuzde": round((fiyat / giris - 1) * 100, 2) if giris else 0.0,
            "stop": stop, "hedef": hedef,
            # "stopa %2 kaldı" uyarısı bu iki sayıdan çıkıyor.
            "stop_uzaklik": round((fiyat - stop) / fiyat * 100, 2)
                            if fiyat > 0 and stop > 0 else None,
            "hedef_uzaklik": round((hedef - fiyat) / fiyat * 100, 2)
                             if fiyat > 0 and hedef > 0 else None,
            "veri_var": b is not None,
        })
    ozkaynak = nakit + piyasa
    return {"tarih": tarih, "nakit": round(nakit, 2),
            "piyasa": round(piyasa, 2), "maliyet": round(maliyet, 2),
            "ozkaynak": round(ozkaynak, 2),
            "acik_kar": round(piyasa - maliyet, 2),
            "acik_kar_yuzde": round((piyasa / maliyet - 1) * 100, 2)
                              if maliyet > 0 else 0.0,
            "satirlar": satirlar}


# ── işlem ──────────────────────────────────────────────────────────────────

def al_kontrol(bar: Bar, adet: int, nakit: float,
               kayma_bp: float = KAYMA_BP) -> dict:
    """Alım gerçekleşir mi, hangi fiyattan.

    TAVAN KURALI BURADA UYGULANIYOR. Eskiden yalnızca `Bar.tavan_mi`
    bayrağı dönüyordu ve telefon onu sadece uyarı olarak gösteriyordu —
    yani kullanıcı tavanda açan hisseyi alabiliyordu. Backtest bunu
    engelliyor; simülatör engellemezse ikisi farklı sonuç üretir.
    """
    if bar is None:
        return {"gecti": False, "sebep": "O tarihte veri yok."}
    if adet < 1:
        return {"gecti": False, "sebep": "Adet en az 1 olmalı."}
    if bar.tavan_mi:
        return {"gecti": False,
                "sebep": (f"{bar.tarih}: tavana yakın açtı "
                          f"({bar.onceki_kapanis:.2f} → {bar.acilis:.2f} ₺). "
                          "Tavanda satıcı yoktur — emir gerçekleşmez.")}
    fiyat = bar.kapanis * (1 + kayma_bp / 10_000.0)
    fiyat = _risk_yuvarla(fiyat, yukari=True)
    maliyet = adet * fiyat
    if maliyet > nakit + 1e-9:
        return {"gecti": False, "fiyat": round(fiyat, 4),
                "maliyet": round(maliyet, 2),
                "sebep": (f"Bakiye yetmiyor: {maliyet:,.2f} ₺ gerekiyor, "
                          f"{nakit:,.2f} ₺ var.")}
    return {"gecti": True, "fiyat": round(fiyat, 4),
            "ham_fiyat": round(bar.kapanis, 4),
            "kayma": round(fiyat - bar.kapanis, 4),
            "maliyet": round(maliyet, 2), "tarih": bar.tarih, "sebep": ""}


def sat(pozisyon: dict, bar: Bar, adet: int = 0,
        kayma_bp: float = KAYMA_BP) -> dict:
    """Elle satış. `adet=0` → tamamı. Kısmi satış destekli."""
    if bar is None:
        return {"gecti": False, "sebep": "O tarihte veri yok."}
    acik = int(pozisyon.get("adet") or 0)
    if acik < 1:
        return {"gecti": False, "sebep": "Açık pozisyon yok."}
    n = acik if adet <= 0 else min(adet, acik)
    fiyat = bar.kapanis * (1 - kayma_bp / 10_000.0)
    fiyat = _risk_yuvarla(fiyat, yukari=False)
    return {"gecti": True, "sembol": pozisyon.get("sembol", ""),
            "adet": n, "fiyat": round(fiyat, 4),
            "ham_fiyat": round(bar.kapanis, 4),
            "kayma": round(bar.kapanis - fiyat, 4),
            "hasilat": round(n * fiyat, 2), "kalan_adet": acik - n,
            "tarih": bar.tarih, "sebep": "elle"}


def _risk_yuvarla(fiyat: float, yukari: bool) -> float:
    """BIST fiyat kademesine yuvarla. risk.py yoksa ham fiyat."""
    try:
        from .risk import kademeye_yuvarla
        return kademeye_yuvarla(fiyat, yukari=yukari)
    except Exception:
        return round(fiyat, 2)


# ── motor ──────────────────────────────────────────────────────────────────

def adim(pozisyonlar: list[dict], nakit: float, tarih: str,
         adim_sayisi: int = 1, izlenen: list[str] | None = None,
         kayma_bp: float = KAYMA_BP,
         azami_adim: int = 260) -> dict:
    """`adim_sayisi` işlem günü ilerletir.

    Her gün SIRAYLA (backtest.py:110-211 ile aynı sıra):
      1) boşluklu açılışta stop/hedef  2) gün içi stop, hedeften ÖNCE
      3) kapanışta değerleme → özkaynak noktası

    `adim_sayisi <= 0` → pozisyonların hepsi kapanana kadar (azami
    `azami_adim` gün). Kullanıcı "kapanana kadar" düğmesine bastığında
    bu çalışıyor; pozisyon yoksa tek gün ilerliyor.

    Pozisyon olmadan da ilerler: takvim referans sembolden okunuyor.
    Eskiden sembol listesi boşsa uç 400 dönüyordu ve kullanıcı tarih
    seçip "yarına bakayım" dediğinde hata alıyordu.
    """
    poz = [dict(p) for p in (pozisyonlar or [])]
    semboller = sorted({p.get("sembol", "") for p in poz if p.get("sembol")}
                       | set(izlenen or []))
    kapanana_kadar = adim_sayisi <= 0
    kalan = azami_adim if kapanana_kadar else min(int(adim_sayisi), azami_adim)

    gunler = takvim(tarih)
    # `takvim` başlangıcı DAHİL veriyor; ilerleme sonrakinden başlıyor.
    ileri = [g for g in gunler if g > tarih][:kalan]
    if not ileri:
        return {"tarih": tarih, "gunler": [], "cikislar": [],
                "pozisyonlar": poz, "nakit": round(nakit, 2),
                "ozkaynak_noktalari": [], "fiyatlar": {},
                "bitti": True,
                "sebep": "Veri burada bitiyor — daha ileri gidilemiyor."}

    cikislar: list[dict] = []
    noktalar: list[dict] = []
    fiyatlar: dict[str, dict] = {}
    islenen: list[str] = []

    for g in ileri:
        islenen.append(g)
        kalanlar = []
        for p in poz:
            b = gun(p.get("sembol", ""), g)
            if b is None:
                kalanlar.append(p)
                continue
            fiyatlar[p["sembol"]] = b.sozluk()
            c = cikis_kontrol(p, b)
            if c is None:
                kalanlar.append(p)
                continue
            # Çıkışta kayma AŞAĞI: backtest de öyle (backtest.py:192-195).
            cikis_fiyat = _risk_yuvarla(
                c.fiyat * (1 - kayma_bp / 10_000.0), yukari=False)
            nakit += p["adet"] * cikis_fiyat
            cikislar.append({"sembol": c.sembol, "adet": p["adet"],
                             "fiyat": round(cikis_fiyat, 4),
                             "ham_fiyat": round(c.fiyat, 4),
                             "sebep": c.sebep, "tarih": c.tarih,
                             "giris": p.get("giris"),
                             "giris_tarih": p.get("tarih")})
        poz = kalanlar
        d = deger(poz, nakit, g)
        noktalar.append({"t": g, "d": d["ozkaynak"]})
        # Ayrıca fiyat sözlüğünü kalan pozisyonlar için tazele
        for s in d["satirlar"]:
            if s["veri_var"] and s["sembol"] not in fiyatlar:
                b2 = gun(s["sembol"], g)
                if b2:
                    fiyatlar[s["sembol"]] = b2.sozluk()
        if kapanana_kadar and not poz:
            break

    son_tarih = islenen[-1] if islenen else tarih
    son_deger = deger(poz, nakit, son_tarih)
    return {"tarih": son_tarih, "gunler": islenen, "cikislar": cikislar,
            "pozisyonlar": poz, "nakit": round(nakit, 2),
            "ozkaynak_noktalari": noktalar, "fiyatlar": fiyatlar,
            "deger": son_deger, "bitti": False, "sebep": ""}


# ── o gün sistem ne diyordu ────────────────────────────────────────────────

def sinyaller(tarih: str, sermaye: float = 10_000.0,
              evren_adi: str = "bist100", azami: int = 8) -> dict:
    """Verilen GEÇMİŞ tarihte sistemin ürettiği sinyaller.

    Simülatörün en değerli parçası: kullanıcı sisteme güvenip
    güvenmeyeceğini gerçek parayla değil burada öğreniyor.

    GELECEĞE BAKMAMA: seri T gününe kadar KESİLİYOR ve göstergeler o
    dilimden hesaplanıyor (gunluk.geriye_doldur ile aynı kural). Aksi
    halde sinyaller o gün bilinmesi imkânsız bilgiyle üretilir ve
    kullanıcı gerçekte var olmayan bir fırsatı kaçırdığını sanır.
    """
    from . import evren as _evren, gostergeler
    from .strateji import Filtreler, STRATEJILER, skorla
    from .risk import RiskAyarlari, pozisyon_hesapla

    try:
        sinir = pd.Timestamp(tarih)
    except Exception:
        return {"tarih": tarih, "sinyaller": [], "hata": "tarih okunamadı"}

    ra = RiskAyarlari(sermaye=sermaye)
    filtre = Filtreler()
    ek_ham = _onbellekli_seri(_evren.ENDEKS)
    ek = ek_ham["Close"] if not ek_ham.empty else None

    cikti = []
    for sem in _evren.evren_getir(evren_adi):
        ham = _onbellekli_seri(sem)
        if ham.empty:
            continue
        # ÖNCE KES, SONRA HESAPLA. Göstergeleri 1300 satır için hesaplayıp
        # sonra kesmek üç kat daha uzun sürüyordu. SMA200 kayan pencere
        # olduğu için 400 satırlık dilimde son değerler BİREBİR AYNI
        # çıkıyor (test_sinyal_dilimi_tam_seriyle_ayni bunu kilitliyor).
        kesik = ham[ham.index <= sinir].tail(ISINMA_SATIRI)
        # SMA200'ün ısınması için yeterli geçmiş yoksa o gün bu hisse
        # hakkında hiçbir şey söylenemez — tahmin etmek yerine atla.
        if len(kesik) < 220:
            continue
        try:
            dilim = gostergeler.gosterge_seti(kesik, ek)
        except Exception:
            continue
        try:
            uygun, _ = filtre.gecer_mi(dilim)
            r = skorla(dilim)
        except Exception:
            continue
        if not uygun or not r["sinyaller"]:
            continue
        for st_ad in r["sinyaller"]:
            st = STRATEJILER.get(st_ad)
            poz = pozisyon_hesapla(
                sem, r["fiyat"], r["atr"], ra,
                stop_kat=st.atr_stop_kat if st else None,
                hedef_kat=st.atr_hedef_kat if st else None)
            cikti.append({
                "sembol": sem, "strateji": st_ad, "skor": r["skor"],
                "fiyat": r["fiyat"], "stop": poz.stop, "hedef": poz.hedef,
                "adet": poz.adet, "maliyet": poz.maliyet,
                "risk_tl": poz.risk_tl,
                "alinabilir": bool(poz.uygulanabilir),
                "uyari": poz.uyari,
                "vade": st.vade if st else "",
                "rsi": r["rsi"], "adx": r["adx"],
                "sma200_ustu": bool(r["sma200_ustu"]),
            })

    cikti.sort(key=lambda x: -x["skor"])
    gercek_tarih = ""
    d = _onbellekli_seri(TAKVIM_SEMBOLU)
    if not d.empty:
        onceki = d[d.index <= sinir]
        if not onceki.empty:
            gercek_tarih = onceki.index[-1].strftime("%Y-%m-%d")
    return {"tarih": gercek_tarih or tarih, "istenen_tarih": tarih,
            "sinyaller": cikti[:azami], "toplam": len(cikti)}
