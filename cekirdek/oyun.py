"""Sanal İşlem oyunu — piyasayı biz üretiyoruz.

NEDEN GERÇEK VERİ DEĞİL: geçmiş bir tarihi yeniden oynatmak iki şeyi
birden bozuyordu. Sonucu merak eden kullanıcı gerçek grafiğe bakıp
"cevabı" görebiliyordu, ve aynı tarih ikinci kez oynandığında hiçbir
şey öğretmiyordu. Üretilmiş piyasa her oyunda farklı; kimse sonucu
önceden bilemez.

TOHUMDAN ÜRETİLİYOR: aynı tohum + aynı zorluk her zaman aynı piyasayı
veriyor. Sunucu hiçbir şey saklamıyor — telefon tohumu tutuyor, oyun
gerektiğinde birebir yeniden üretiliyor. API'nin durumsuzluğu bozulmuyor.

FİYATLAR UYDURMA, KODLAR GERÇEK: kullanıcı tanıdık kodlarla oynamak
istedi. Bu yüzden her ekranda oyun olduğu açıkça yazılı — ekran
görüntüsü gerçek kotasyon sanılmamalı.

BİR OYUN TEK SEFERDE ÜRETİLİYOR: bütün günler, haberler ve analist
sinyalleri tek çağrıda hesaplanıp telefona gidiyor. Sonrası tamamen
çevrimdışı; gün ilerletmek için ağ gerekmiyor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Göstergelerin ısınması için oyun başlangıcından ÖNCEKİ gün sayısı.
# SMA200 en uzun pencere; 260 gün hem onu doyuruyor hem de kullanıcıya
# grafikte "bu hisse nereden geldi" diye bakacak bir geçmiş bırakıyor.
ISINMA = 260

# Telefona GÖNDERİLEN geçmiş. Isınmanın tamamı gerekmiyor: sinyaller
# sunucuda hesaplanıyor, telefonun ihtiyacı yalnızca grafikte gösterecek
# kadar geçmiş. 260 gönderince zor mod 363 KB'a çıkıyordu.
GOSTERILEN_GECMIS = 110


@dataclass
class Zorluk:
    ad: str
    aciklama: str
    hisse_sayisi: int
    sermaye: float
    gun: int
    # Trendin ne kadar belirgin olduğu. Yüksek = yön uzun süre korunuyor,
    # göstergeler işe yarıyor. Düşük = testere ağzı.
    trend_netligi: float
    trend_kaliciligi: float      # AR(1) katsayısı
    oynaklik: float              # günlük standart sapma çarpanı
    yalanci_kirilma: float       # gün başına sahte sıçrama olasılığı
    haber_dogrulugu: float       # haberin yönü gerçekten tutma oranı
    kayma_bp: float

    def sozluk(self) -> dict:
        return {"ad": self.ad, "aciklama": self.aciklama,
                "hisse_sayisi": self.hisse_sayisi, "sermaye": self.sermaye,
                "gun": self.gun, "kayma_bp": self.kayma_bp,
                "haber_dogrulugu": self.haber_dogrulugu}


ZORLUKLAR: dict[str, Zorluk] = {
    "kolay": Zorluk(
        ad="Kolay",
        aciklama="Trendler temiz, haberler dürüst, kayma yok. "
                 "Kuralları öğrenmek için.",
        hisse_sayisi=8, sermaye=50_000, gun=40,
        trend_netligi=1.6, trend_kaliciligi=0.94, oynaklik=0.75,
        yalanci_kirilma=0.00, haber_dogrulugu=1.00, kayma_bp=0.0),
    "normal": Zorluk(
        ad="Normal",
        aciklama="Gerçeğe yakın: trendler var ama gürültü de var, "
                 "haberler bazen yanıltır.",
        hisse_sayisi=14, sermaye=25_000, gun=60,
        trend_netligi=1.0, trend_kaliciligi=0.88, oynaklik=1.00,
        yalanci_kirilma=0.02, haber_dogrulugu=0.80, kayma_bp=15.0),
    "zor": Zorluk(
        ad="Zor",
        aciklama="Testere ağzı piyasa, yalancı kırılmalar, yanıltıcı "
                 "haberler, geniş makas. Sermaye dar, hisse çok.",
        hisse_sayisi=22, sermaye=10_000, gun=90,
        trend_netligi=0.55, trend_kaliciligi=0.72, oynaklik=1.45,
        yalanci_kirilma=0.06, haber_dogrulugu=0.55, kayma_bp=40.0),
}


# ── evren ──────────────────────────────────────────────────────────────────

def _evren() -> list[dict]:
    """Oyunda kullanılabilecek hisseler: kod, ad, sektör.

    Sektör iki işe yarıyor: aynı sektördeki hisseler birlikte hareket
    ediyor (gerçekte de öyle) ve haber metinleri sektöre göre yazılıyor.
    """
    from . import evren as _ev

    adlar: dict[str, str] = {}
    try:
        from . import semboller as _s
        adlar = {x["k"]: x["a"] for x in _s.liste()}
    except Exception:
        pass

    sektorler: dict[str, str] = {}
    try:
        from . import temel_veri
        for kod in _ev.evren_getir("bist100"):
            f = temel_veri.finansal_cek(kod, onbellek_saat=24 * 365)
            s = getattr(f, "sektor", "") if f else ""
            if s:
                sektorler[kod] = s
    except Exception:
        pass

    cikti = []
    for kod in _ev.evren_getir("bist100"):
        cikti.append({"kod": kod, "ad": adlar.get(kod, kod),
                      "sektor": sektorler.get(kod, "Diğer")})
    return cikti


# ── fiyat üretimi ──────────────────────────────────────────────────────────

def _rejim_serisi(rng: np.random.Generator, n: int, z: Zorluk) -> np.ndarray:
    """Piyasanın günlük getirisi.

    Rejim yavaş değişiyor (boğa → yatay → ayı) ve tek tek hisseler bunun
    üstüne biniyor. Rejimsiz üretilen piyasada bütün hisseler bağımsız
    hareket eder ve "her şey aynı anda düştü" günü hiç yaşanmaz — oysa
    portföy riskini asıl öğreten gün odur.
    """
    # Rejim ortalaması yavaş bir AR(1); işaret değiştirdiğinde piyasa
    # yön değiştirmiş oluyor.
    mu = np.zeros(n)
    m = rng.normal(0, 0.0004)
    for i in range(n):
        m = 0.985 * m + rng.normal(0, 0.00035)
        mu[i] = m
    gurultu = rng.normal(0, 0.009 * z.oynaklik, n)
    return mu + gurultu


def _hisse_serisi(rng: np.random.Generator, n: int, piyasa: np.ndarray,
                  z: Zorluk, baslangic: float) -> pd.DataFrame:
    """Tek hissenin OHLCV serisi.

    Getiri üç parçadan: piyasa (beta ile), hisseye özgü YAVAŞ trend ve
    gürültü. Yavaş trend olmadan seri saf rastgele yürüyüş olurdu ve
    hiçbir strateji hiçbir şey bulamazdı — oyun da öğretici olmazdı.
    """
    beta = rng.uniform(0.55, 1.45)
    ozgun_oynaklik = rng.uniform(0.010, 0.026) * z.oynaklik

    # Hisseye özgü trend: AR(1). Kalıcılık yüksekse yön uzun sürüyor.
    mu = np.zeros(n)
    m = 0.0
    surtunme = z.trend_kaliciligi
    itki = 0.0009 * z.trend_netligi
    for i in range(n):
        m = surtunme * m + rng.normal(0, itki)
        mu[i] = m

    getiri = beta * piyasa + mu + rng.normal(0, ozgun_oynaklik, n)

    # Yalancı kırılma: bir gün sert yukarı, ertesi gün geri alıyor.
    # Kırılım stratejisinin tuzağa düşmesi için gerekli.
    if z.yalanci_kirilma > 0:
        for i in range(20, n - 2):
            if rng.random() < z.yalanci_kirilma:
                sicrama = rng.uniform(0.045, 0.09)
                getiri[i] += sicrama
                getiri[i + 1] -= sicrama * rng.uniform(0.8, 1.15)

    kapanis = baslangic * np.exp(np.cumsum(getiri))
    kapanis = np.maximum(kapanis, 0.5)

    # OHLC: gün içi aralık oynaklıkla orantılı, açılış boşluklu.
    aralik = np.abs(rng.normal(0, ozgun_oynaklik, n)) + ozgun_oynaklik * 0.6
    onceki = np.concatenate([[kapanis[0]], kapanis[:-1]])
    acilis = onceki * (1 + rng.normal(0, ozgun_oynaklik * 0.45, n))
    yuksek = np.maximum(acilis, kapanis) * (1 + aralik * 0.5)
    dusuk = np.minimum(acilis, kapanis) * (1 - aralik * 0.5)
    hacim = rng.lognormal(15.5, 0.6, n) * (1 + np.abs(getiri) * 8)

    return pd.DataFrame({"Open": acilis, "High": yuksek, "Low": dusuk,
                         "Close": kapanis, "Volume": hacim})


# ── haberler ───────────────────────────────────────────────────────────────

# Başlık kalıpları. `{ad}` şirket adıyla doluyor.
# İkinci alan: haberin İMA ETTİĞİ yön (+1 iyi, -1 kötü).
_KALIPLAR: list[tuple[str, int]] = [
    ("{ad} beklentinin üzerinde kâr açıkladı", +1),
    ("{ad} çeyrek bilançosunda ciro %{n} arttı", +1),
    ("{ad} yeni bir ihaleyi kazandı", +1),
    ("{ad} kapasite artırım yatırımını duyurdu", +1),
    ("{ad} temettü dağıtım kararı aldı", +1),
    ("{ad} yurt dışında yeni sözleşme imzaladı", +1),
    ("{ad} hisse geri alım programı başlattı", +1),
    ("Analistler {ad} için hedef fiyatı yükseltti", +1),
    ("{ad} kârında %{n} gerileme bildirdi", -1),
    ("{ad} yatırım planını erteledi", -1),
    ("{ad} üretimde geçici duruş açıkladı", -1),
    ("{ad} aleyhine soruşturma başlatıldı", -1),
    ("{ad} borçlanma maliyetinin arttığını duyurdu", -1),
    ("Analistler {ad} için tavsiyeyi düşürdü", -1),
    ("{ad} genel müdürü görevden ayrıldı", -1),
    ("{ad} sözleşmesi feshedildi", -1),
]

_SEKTOR_KALIP: list[tuple[str, int]] = [
    ("{sektor} sektöründe talep canlanması bekleniyor", +1),
    ("{sektor} hisselerine yabancı ilgisi arttı", +1),
    ("{sektor} sektöründe maliyet baskısı sürüyor", -1),
    ("{sektor} için düzenleme değişikliği gündemde", -1),
]

_PIYASA_KALIP: list[tuple[str, int]] = [
    ("Merkez Bankası faizi sabit tuttu", +1),
    ("Enflasyon beklentinin altında geldi", +1),
    ("Yabancı yatırımcı girişi hızlandı", +1),
    ("Küresel piyasalarda risk iştahı zayıfladı", -1),
    ("Faiz kararı öncesi temkinli seyir", -1),
    ("Jeopolitik gerginlik borsayı baskıladı", -1),
]

_SEKTOR_TR = {
    "Industrials": "Sanayi", "Basic Materials": "Temel malzeme",
    "Financial Services": "Bankacılık", "Consumer Cyclical": "Perakende",
    "Consumer Defensive": "Gıda", "Utilities": "Enerji",
    "Technology": "Teknoloji", "Communication Services": "İletişim",
    "Healthcare": "Sağlık", "Energy": "Enerji",
    "Real Estate": "Gayrimenkul", "Diğer": "Piyasa",
}


def _kisa_ad(ad: str) -> str:
    """Haber başlığı için kısaltılmış şirket adı.

    Tam unvan başlıkta boğuyor: "Anadolu Efes Biracılık ve Malt Sanayii
    beklentinin üzerinde kâr açıkladı" okunmuyor.
    """
    kelimeler = [k for k in ad.split() if k.lower() not in ("ve", "ile")]
    return " ".join(kelimeler[:2]) if kelimeler else ad


def _haberler(rng: np.random.Generator, hisseler: list[dict],
              z: Zorluk) -> list[dict]:
    """Oyun günlerine dağıtılmış haberler.

    `dogru` alanı haberin yönünün gerçekten tutup tutmadığını söylüyor.
    Zor modda haberlerin yarıya yakını yanıltıcı — çünkü gerçekte de
    öyle: iyi haberle açılan hisse gün sonunda eksiye dönebilir.

    Haber fiyatı DEĞİŞTİRMİYOR. Fiyatlar zaten üretildi; haber onların
    üstüne anlatı olarak biniyor ve o günün gerçek hareketiyle
    eşleştiriliyor. Tersini yapsaydık haberi okuyan kullanıcı sonucu
    kesin bilirdi ve oyun biterdi.
    """
    cikti = []
    # Son kullanılan başlıklar: aynı cümlenin iki gün üst üste çıkması
    # haberi anlamsızlaştırıyor ve üretilmiş olduğunu ele veriyor.
    son_kullanilan: list[str] = []

    for gun in range(z.gun):
        adet = rng.poisson(1.4)
        for _ in range(int(min(adet, 3))):
            tur = rng.random()
            if tur < 0.65:
                h = hisseler[rng.integers(len(hisseler))]
                kalip, yon = _KALIPLAR[rng.integers(len(_KALIPLAR))]
                baslik = kalip.format(ad=_kisa_ad(h["ad"]),
                                      n=int(rng.integers(4, 38)))
                sembol = h["kod"]
            elif tur < 0.85:
                h = hisseler[rng.integers(len(hisseler))]
                kalip, yon = _SEKTOR_KALIP[rng.integers(len(_SEKTOR_KALIP))]
                sektor = _SEKTOR_TR.get(h["sektor"], "Piyasa")
                baslik = kalip.format(sektor=sektor)
                sembol = ""
            else:
                kalip, yon = _PIYASA_KALIP[rng.integers(len(_PIYASA_KALIP))]
                baslik = kalip
                sembol = ""
            if baslik in son_kullanilan:
                continue
            son_kullanilan.append(baslik)
            if len(son_kullanilan) > 12:
                son_kullanilan.pop(0)
            cikti.append({
                "gun": gun, "sembol": sembol, "baslik": baslik,
                "yon": int(yon),
                "guvenilir": bool(rng.random() < z.haber_dogrulugu),
            })
    return cikti


# ── analist sinyalleri ─────────────────────────────────────────────────────

def _sinyaller(seriler: dict[str, pd.DataFrame], endeks: pd.Series,
               z: Zorluk, evren_bilgi: dict[str, dict]) -> list[dict]:
    """Her oyun günü için sistemin sinyalleri.

    GELECEĞE BAKMIYOR: göstergeler kayan pencere, giriş koşulları
    vektörel hesaplanıp gün gün okunuyor — t günündeki değer yalnızca
    t'ye kadarki veriden çıkıyor.

    Göstergeler HER GÜN AYRI hesaplanmıyor: backtest'in yaptığı gibi bir
    kez vektörel hesaplanıp okunuyor. Gün gün hesaplamak 22 hisse x 90
    gün için yirmi saniyeye çıkıyordu.
    """
    from . import gostergeler
    from .strateji import (Filtreler, STRATEJILER, aktif_stratejiler,
                           skorla)
    from .risk import RiskAyarlari, pozisyon_hesapla

    ra = RiskAyarlari(sermaye=z.sermaye)
    filtre = Filtreler()
    cikti: list[dict] = []

    for kod, ham in seriler.items():
        try:
            g = gostergeler.gosterge_seti(ham, endeks)
        except Exception:
            continue
        girisler = {}
        for ad, st in aktif_stratejiler().items():
            try:
                girisler[ad] = st.giris(g).to_numpy()
            except Exception:
                girisler[ad] = np.zeros(len(g), dtype=bool)

        for gun in range(z.gun):
            i = ISINMA + gun
            if i >= len(g):
                break
            veren = [ad for ad, m in girisler.items() if bool(m[i])]
            if not veren:
                continue
            dilim = g.iloc[: i + 1]
            try:
                uygun, _ = filtre.gecer_mi(dilim)
                if not uygun:
                    continue
                r = skorla(dilim)
            except Exception:
                continue
            for ad in veren:
                st = STRATEJILER[ad]
                poz = pozisyon_hesapla(kod, r["fiyat"], r["atr"], ra,
                                       stop_kat=st.atr_stop_kat,
                                       hedef_kat=st.atr_hedef_kat)
                cikti.append({
                    "gun": gun, "sembol": kod, "strateji": ad,
                    "skor": r["skor"], "fiyat": round(r["fiyat"], 2),
                    "stop": poz.stop, "hedef": poz.hedef,
                    "adet": poz.adet, "maliyet": poz.maliyet,
                    "risk_tl": poz.risk_tl,
                    "alinabilir": bool(poz.uygulanabilir),
                    "uyari": poz.uyari, "vade": st.vade,
                    "ad": evren_bilgi.get(kod, {}).get("ad", kod),
                })
    cikti.sort(key=lambda x: (x["gun"], -x["skor"]))
    return cikti


# ── oyun ───────────────────────────────────────────────────────────────────

def tohum_uret() -> int:
    """Yeni oyun için tohum. Tekrar etmemesi tek şartı."""
    import secrets
    return secrets.randbelow(2**31 - 1) + 1


def uret(tohum: int, zorluk: str = "normal") -> dict:
    """Bir oyunun TAMAMI: hisseler, fiyatlar, haberler, sinyaller.

    Tek seferde üretilip telefona gidiyor; sonrası çevrimdışı. Bir
    oyunun boyutu zor modda ~150 KB.
    """
    z = ZORLUKLAR.get((zorluk or "normal").lower())
    if z is None:
        raise ValueError(f"bilinmeyen zorluk: {zorluk}")

    rng = np.random.default_rng(int(tohum))
    n = ISINMA + z.gun

    havuz = _evren()
    secim = rng.permutation(len(havuz))[: z.hisse_sayisi]
    hisseler = [havuz[i] for i in sorted(secim)]

    piyasa = _rejim_serisi(rng, n, z)

    # Sektör ortak hareketi: aynı sektördeki hisseler birlikte oynasın.
    sektor_itki: dict[str, np.ndarray] = {}
    for h in hisseler:
        s = h["sektor"]
        if s not in sektor_itki:
            sektor_itki[s] = rng.normal(0, 0.004, n)

    seriler: dict[str, pd.DataFrame] = {}
    for h in hisseler:
        baslangic = float(rng.uniform(8, 320))
        d = _hisse_serisi(rng, n, piyasa + sektor_itki[h["sektor"]] * 0.5,
                          z, baslangic)
        # Tarih yerine gün numarası: oyun takvimi gerçek tarihlere
        # bağlı değil. İş günü hizalaması da gerekmiyor.
        d.index = pd.RangeIndex(n)
        d.index = pd.to_datetime("2000-01-03") + pd.to_timedelta(
            np.arange(n) * 1, unit="D")
        seriler[h["kod"]] = d

    endeks_seri = pd.Series(
        100.0 * np.exp(np.cumsum(piyasa)), index=list(seriler.values())[0].index)

    bilgi = {h["kod"]: h for h in hisseler}
    sinyaller = _sinyaller(seriler, endeks_seri, z, bilgi)
    haberler = _haberler(rng, hisseler, z)

    # Telefona giden fiyatlar: ısınma DAHİL (grafikte geçmiş görünsün)
    # ama yuvarlanmış — tam hassasiyet 3 kat yer kaplıyor ve kuruşun
    # altındaki basamak oyunda hiçbir şey ifade etmiyor.
    kirp = ISINMA - GOSTERILEN_GECMIS

    def _bar(d: pd.DataFrame) -> list[list]:
        k = d.iloc[kirp:]
        return [[round(float(a), 2), round(float(y), 2), round(float(u), 2),
                 round(float(kp), 2), int(h)]
                for a, y, u, kp, h in zip(k["Open"], k["High"], k["Low"],
                                          k["Close"], k["Volume"])]

    return {
        "tohum": int(tohum),
        "zorluk": zorluk.lower(),
        "ayar": z.sozluk(),
        "isinma": GOSTERILEN_GECMIS,
        "gun_sayisi": z.gun,
        "hisseler": [
            {"kod": h["kod"], "ad": h["ad"],
             "sektor": _SEKTOR_TR.get(h["sektor"], "Diğer"),
             "barlar": _bar(seriler[h["kod"]])}
            for h in hisseler
        ],
        "endeks": [round(float(v), 2) for v in endeks_seri[kirp:]],
        "sinyaller": sinyaller,
        "haberler": haberler,
    }
