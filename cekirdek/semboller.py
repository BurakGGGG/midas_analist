"""Hisse kodu ↔ şirket adı: aranabilir sembol listesi.

NEDEN VAR: kullanıcı "thy" yazınca "THYAO — Türk Hava Yolları" çıkmalı.
Bugün sembolü harfi harfine bilmek zorunda; yanlış yazınca "veri yok"
diyoruz ve neyi yanlış yazdığını söylemiyoruz.

ARAMA TELEFONDA ÇALIŞIYOR, SUNUCUDA DEĞİL. Liste bir kez inip
saklanıyor (sözlük ve müfredat ile aynı kalıp). Üç sebep:
  · Tuş başına ağ isteği kabul edilemez — ilk harfte 200 ms gecikme
    aramayı ölü hissettirir.
  · Sunucuda arama altyapısı yok: ambarda sembol tablosu bile yok.
  · Çevrimdışı çalışır. Sözlük zaten tam bu gerekçeyle önbellekli.

NORMALİZE EDİLMİŞ AD SUNUCUDA HESAPLANIYOR ve veriyle birlikte
gönderiliyor. Sebebi ölçüldü: Python'da 'İ'.lower() İKİ kod noktası
üretiyor (i + birleşen nokta), Dart'ta TEK rune. Aynı normalleştirmeyi
iki dilde ayrı yazmak sessizce farklı sonuç verir ve hata ancak
"neden İŞ BANKASI çıkmıyor" şikâyetiyle görünür. Telefon yalnızca
SORGUYU normalleştiriyor; o da altı çiftlik deterministik bir zincir
ve iki dilde aynı çıktı verdiği testle kilitli.
"""
from __future__ import annotations

from .haber_esleme import TAKMA_ADLAR, normalize

# İstemci bu sayı artınca listeyi yeniden indirir. ARTIRMAYI UNUTMA:
# yeni hisse eklendiğinde telefon eski listeyle kalır ve kullanıcı
# aradığını bulamaz.
SURUM = 1

# Unvanın sonundan atılacak hukuki biçimler. Sıra önemli: uzun olan
# önce, yoksa "A.Ş." kısa hâli "T.A.Ş."nin içinden kesip "T." bırakır.
HUKUKI_SONEK = [
    "ANONİM ORTAKLIĞI", "ANONIM ORTAKLIGI",
    "ANONİM ŞİRKETİ", "ANONIM SIRKETI",
    "T.A.Ş.", "T.A.O.", "A.Ş.", "A.O.", "T.A.Ş", "A.Ş",
]

# Ayırt edici olmayan kuyruklar. "HOLDİNG" burada YOK: "Alarko Holding"
# şirketin bilinen adının parçası, atılırsa tanınmaz hale gelir.
JENERIK_KUYRUK = [
    "SANAYİ VE TİCARET", "SANAYI VE TICARET",
    "SANAYİİ VE TİCARET", "VE TİCARET", "VE TICARET",
    "TİCARET VE SANAYİ", "TICARET VE SANAYI",
]


def _kucult(t: str) -> str:
    """Türkçe küçültme. Python'un .lower()'ı I harfini bozuyor."""
    return t.replace("I", "ı").replace("İ", "i").lower()


def _buyut_ilk(k: str) -> str:
    """Kelimenin ilk harfini Türkçe kurallı büyütür."""
    if not k:
        return k
    ilk = k[0]
    ilk = "İ" if ilk == "i" else ("I" if ilk == "ı" else ilk.upper())
    return ilk + k[1:]


# Büyütülmeyen bağlaçlar — "Anadolu Efes Biracılık ve Malt" doğru,
# "Ve Malt" yanlış.
_KUCUK_KALAN = {"ve", "ile", "de", "da"}


def gosterim_adi(unvan: str) -> str:
    """KAP unvanından okunabilir ad.

    'TÜRK HAVA YOLLARI A.O.' → 'Türk Hava Yolları'
    """
    if not unvan:
        return ""
    t = " ".join(unvan.split()).strip().rstrip(",")
    üst = t.upper()
    for sonek in HUKUKI_SONEK:
        if üst.endswith(sonek):
            t = t[: len(t) - len(sonek)].strip().rstrip(",-").strip()
            üst = t.upper()
            break
    for kuyruk in JENERIK_KUYRUK:
        if üst.endswith(kuyruk):
            t = t[: len(t) - len(kuyruk)].strip().rstrip(",-").strip()
            break
    if not t:
        return unvan.strip()

    kelimeler = []
    for i, k in enumerate(_kucult(t).split()):
        kelimeler.append(k if i > 0 and k in _KUCUK_KALAN else _buyut_ilk(k))
    return " ".join(kelimeler)


def arama_terimleri(kod: str, unvan: str) -> list[str]:
    """Bu hissenin eşleşebileceği normalize metinler.

    Kod da listede: kullanıcı "thyao" yazdığında ad üzerinden değil kod
    üzerinden bulunuyor ve sıralamada en üste çıkıyor.
    """
    terimler = {normalize(kod)}
    if unvan:
        terimler.add(normalize(unvan))
    for takma in TAKMA_ADLAR.get(kod.upper(), []):
        terimler.add(normalize(takma))
    return sorted(t for t in terimler if t)


def liste(evren_adi: str = "hepsi", yalnizca_evren: bool = False) -> list[dict]:
    """Aranabilir hisse listesi.

    `yalnizca_evren=False` (varsayılan): KAP'taki BÜTÜN kodlar. Kullanıcı
    takip etmediğimiz bir hisseyi arayabilmeli — bulamamak "yanlış
    yazdım" sanmasına yol açar. Takip edilenler `izleniyor` ile işaretli.
    """
    from . import evren as _evren, kap

    izlenen = set(_evren.evren_getir(evren_adi))
    try:
        kodlar = kap.kod_haritasi()
    except Exception:
        kodlar = {}

    # KAP çekilemese bile evren aranabilir kalmalı.
    for s in izlenen:
        kodlar.setdefault(s, "")

    cikti = []
    for kod, unvan in kodlar.items():
        # 3 harfli kayıtlar borsada işlem görmeyen KAP üyeleri (denetim
        # şirketleri, yatırım bankaları) — arama sonucunda gürültü.
        if len(kod) < 4 and kod not in izlenen:
            continue
        if yalnizca_evren and kod not in izlenen:
            continue
        ad = gosterim_adi(unvan) if unvan else ""
        cikti.append({
            "k": kod,
            "a": ad or kod,
            "n": arama_terimleri(kod, unvan),
            "i": 1 if kod in izlenen else 0,
        })
    cikti.sort(key=lambda x: (-x["i"], x["k"]))
    return cikti


def ara(sorgu: str, kayitlar: list[dict] | None = None,
        azami: int = 10) -> list[dict]:
    """Sunucu tarafı arama — istemcinin karşılığı, testler için.

    Mobil aynı sıralamayı uyguluyor; ikisi ayrışırsa aynı sorgu iki
    yerde farklı sonuç verir. Bu yüzden kurallar burada yazılı ve
    test_semboller.py ikisini de aynı örneklerle sınıyor.
    """
    q = normalize(sorgu).strip()
    if not q:
        return []
    kayitlar = kayitlar if kayitlar is not None else liste()

    puanli = []
    for r in kayitlar:
        p = _puan(q, r)
        if p is not None:
            puanli.append((_sira(p, r), r))
    puanli.sort(key=lambda x: x[0])
    return [r for _, r in puanli[:azami]]


def _sira(puan: int, kayit: dict) -> tuple:
    """Sıralama anahtarı. TAKİP EDİLEN, tam kod eşleşmesi DIŞINDA öne geçer.

    Neden: "koç" yazan kullanıcı Koç Holding'i arıyor. Ama KOCFN'nin
    KODU da "KOC" ile başlıyor ve kod ön eki ad eşleşmesinden güçlü —
    bu kural "thy" için doğru, "koç" için yanlış sonuç veriyordu.

    Tam kod eşleşmesi (puan 0) mutlak kalıyor: "KOCFN" yazan kişi tam
    olarak onu istiyor, takip etmesek de birinci sırada çıkmalı.
    """
    return (0 if puan == 0 else 1, -kayit.get("i", 0), puan, kayit["k"])


def _puan(q: str, kayit: dict) -> int | None:
    """Küçük puan = üstte. None = eşleşmedi."""
    kod = kayit["k"]
    if kod == q:
        return 0                       # tam kod
    if kod.startswith(q):
        return 1                       # kod ön eki: "thy" → THYAO
    en_iyi = None
    for t in kayit.get("n", []):
        if t == kod:
            continue
        if t == q:
            en_iyi = min(en_iyi if en_iyi is not None else 9, 2)
        elif t.startswith(q):
            en_iyi = min(en_iyi if en_iyi is not None else 9, 3)
        elif any(p.startswith(q) for p in t.split()):
            en_iyi = min(en_iyi if en_iyi is not None else 9, 4)
        elif q in t:
            en_iyi = min(en_iyi if en_iyi is not None else 9, 5)
    if en_iyi is None and q in kod:
        return 6                       # kodun içinde geçiyor
    return en_iyi
