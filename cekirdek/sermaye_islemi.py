"""Bedelsiz ve sermaye artırımı uyarısı.

NEDEN VAR: bedelsiz sermaye artırımından sonra fiyat MEKANİK olarak
düşer. Hisse ucuzlamamıştır — ikiye bölünmüştür ve senin adedin
katlanmıştır. Bunu bilmeyen kullanıcı aracı kurum ekranında -%50 görüp
panik satar; hayatının en pahalı yanlış kararını, hiçbir şey olmadığı
bir günde verir.

BU TUZAĞI SİSTEM ZATEN YAŞADI. Fiyatlar `auto_adjust=True` ile
saklanıyor, yani BİZİM grafiğimizde düşüş görünmüyor; ama Midas
ekranında görünüyor. İkisinin ayrışması CVKMD'de -%61,88, KTLEV'de
+%238 gibi sahte hareketler üretmişti (bkz. kapanis_onarim.py).
Kullanıcı da aynı ayrışmayı yaşıyor ve kimse ona sebebini söylemiyor.

TESPİT KESİN, ORAN "ÇIKARABİLİRSEM":
  Hangi hissede sermaye işlemi olduğu KAP'ın kendi konu başlığından
  geliyor ve güvenilir. Oran ise serbest metinde ve KAP her şirkette
  aynı cümleyi kurmuyor — çıkaramadığımızda oran YAZILMIYOR, uyarı
  yine veriliyor. Yanlış oran yazmak, hiç yazmamaktan kötü.
"""
from __future__ import annotations

import re

# KAP konu başlıkları — KAP'ın kendi listesinden geliyor, serbest metin
# değil. Tespit bu yüzden güvenilir.
#
# TÜRKÇE ÇEKİM TUZAĞI: "Sermaye Artırımı" ile "Sermayenin Artırılmasına"
# aynı olayı anlatıyor ama kelime farklı. Kök üzerinden eşleştiriyoruz
# ("artır"), yoksa gerçek bildirimlerin bir kısmı sessizce kaçıyordu —
# canlı KAP'ta ilk denemede tam olarak bu oldu.
KONULAR: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bedelsiz sermaye artırımı", ("bedelsiz",)),
    ("sermaye artırımı", ("sermaye", "artır")),
    ("sermaye azaltımı", ("sermaye", "azalt")),
    ("birleşme", ("birleşme",)),
    ("bölünme", ("bölünme",)),
    ("pay birleştirme", ("pay birleştir",)),
)

# Rutin/mekanik bildirimler: "kayıtlı sermaye tavanı süre uzatımı"
# sermaye artırımı DEĞİL, yalnızca izin tavanının uzatılması. Bunları
# uyarıya çevirmek, her ay boşuna panik yaratırdı.
HARIC = ("süre uzatım", "tavanı süre", "genel bilgi formu")

# "Fiyat mekanik olarak düşecek" uyarısını hak edenler. Sermaye azaltımı
# ve birleşme de fiyatı yeniden hesaplatıyor ama yönü tek değil.
BOLUNME_KONULARI = ("bedelsiz", "bölünme", "pay birleştirme")

# Oran kalıpları. Sıra önemli: en açık ifade önce.
_ORAN_DESENLERI = [
    re.compile(r"bedelsiz[^.%]{0,40}?%\s*([\d.,]+)", re.IGNORECASE),
    re.compile(r"%\s*([\d.,]+)\s*(?:oran(?:ında|ıyla)|bedelsiz)", re.IGNORECASE),
    re.compile(r"bedelsiz\s+sermaye\s+artırım\s+oranı[^%\d]{0,20}([\d.,]+)",
               re.IGNORECASE),
]


def _sayi(metin: str) -> float | None:
    try:
        d = float(metin.replace(".", "").replace(",", "."))
    except Exception:
        return None
    # %0 ya da %10.000 gibi değerler ayrıştırma hatasıdır; oran yazmamak
    # yanlış oran yazmaktan iyidir.
    return d if 0 < d <= 2000 else None


def oran_cikar(metin: str) -> float | None:
    """Bedelsiz oranını metinden çıkarmayı DENER. Emin değilse None."""
    if not metin:
        return None
    for desen in _ORAN_DESENLERI:
        m = desen.search(metin)
        if m:
            o = _sayi(m.group(1))
            if o is not None:
                return o
    return None


def ilgili_mi(baslik: str, ozet: str = "") -> str:
    """Bu bildirim bir sermaye işlemi mi? Konu adını döner, değilse ''."""
    metin = f"{baslik or ''} {ozet or ''}".lower()
    if any(h in metin for h in HARIC):
        return ""
    for ad, parcalar in KONULAR:
        if all(p in metin for p in parcalar):
            return ad
    return ""


def fiyat_bolunur_mu(konu: str) -> bool:
    """Bu işlem fiyatı mekanik olarak böler mi?"""
    return any(k in (konu or "").lower() for k in BOLUNME_KONULARI)


def aciklama(sembol: str, konu: str, oran: float | None = None) -> str:
    """Kullanıcıya gösterilecek metin — jargon değil, olacak şey."""
    if fiyat_bolunur_mu(konu):
        pay = (f"%{oran:g} oranında " if oran else "")
        return (
            f"{sembol} {pay}bedelsiz sermaye artırımı açıkladı.\n\n"
            "İşlem gününde fiyat MEKANİK olarak düşecek — hisse "
            "ucuzlamıyor, adedin artıyor. Toplam paran değişmiyor. "
            "Aracı kurum ekranında büyük bir düşüş göreceksin; bu bir "
            "kayıp değil."
        )
    if "azaltım" in konu:
        return (
            f"{sembol} sermaye azaltımı açıkladı.\n\n"
            "Adet sayısı azalacak, birim fiyat yükselecek. Toplam "
            "değerin bundan doğrudan etkilenmiyor."
        )
    return (
        f"{sembol} sermaye yapısını değiştiren bir işlem açıkladı "
        f"({konu}).\n\nBildirimin ayrıntısına bakmadan pozisyon kararı "
        "verme: bu tür işlemlerde fiyat mekanik olarak yeniden hesaplanır."
    )


def bul(semboller: list[str], gun: int = 30, yol=None) -> list[dict]:
    """Verilen hisselerde son `gun` gündeki sermaye işlemi bildirimleri.

    Yalnızca KULLANICININ hisseleri sorulur: bütün evreni taramak,
    ilgisiz 90 hissenin bildirimini de göstermek olurdu.
    """
    from . import ambar

    cikti: list[dict] = []
    gorulen: set[tuple[str, str]] = set()
    for sem in {s.upper().strip() for s in semboller if s}:
        try:
            haberler = ambar.hisse_haberleri(sem, gun=gun, yol=yol)
        except Exception:
            continue
        for h in haberler:
            konu = ilgili_mi(h.get("baslik", ""), h.get("ozet", ""))
            if not konu:
                continue
            anahtar = (sem, h.get("tarih", ""))
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            metin = f"{h.get('baslik', '')} {h.get('ozet', '')}"
            cikti.append({
                "sembol": sem,
                "tarih": h.get("tarih", ""),
                "konu": konu,
                "baslik": h.get("baslik", ""),
                "url": h.get("url", ""),
                "oran": oran_cikar(metin),
                "fiyat_bolunur": fiyat_bolunur_mu(konu),
                "aciklama": aciklama(sem, konu, oran_cikar(metin)),
            })
    cikti.sort(key=lambda x: x["tarih"], reverse=True)
    return cikti
