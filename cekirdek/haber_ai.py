"""Haberleri Claude ile hisseye bağlama.

NEDEN GEREKLİ: kelime eşlemesi (`haber_esleme`) 147 haberde 4 eşleşme
buluyor. Bu bir hata değil, kasıtlı katılık — "TÜRK" kelimesi THYAO'ya
eşleşmesin diye. Ama gerçek boşluk da burada: "gıda devinde yönetim
değişikliği" başlığı ULKER'i ilgilendirir ve hiçbir takma ad listesi bunu
yakalayamaz. Sınıflandırma dil işidir, kalıp işi değil.

ÜÇ GÜVENLİK KURALI — hepsi ihlal edilirse sistem sessizce yanlış üretir:

  1. Model YALNIZCA bizim evrenimizden kod seçebilir. Döndürdüğü her kod
     evrende var mı diye doğrulanır; uydurulmuş kod atılır.
  2. Model fiyat, hedef, tahmin ÜRETMEZ. Sadece sınıflandırır: hangi hisse,
     ne tür haber, önemli mi.
  3. Kelime eşlemesi TABANDIR, model onu değiştirmez — üstüne ekler.
     Model çökse de eski davranış aynen sürer.

Maliyet: 147 başlık tek çağrıda ~4.200 giriş tokenı. Haiku ile ~0,39 TL.
Toplu (batch) API %50 ucuz olurdu ama 24 saate kadar gecikebilir; gün özeti
aynı akşam okunduğu için buna değmez.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from . import ai, evren

# Modelin seçebileceği haber türleri. Serbest metin bırakırsak her gün
# başka bir etiket üretir ve sayamayız.
TURLER = ["bilanco", "temettu", "sermaye_artirimi", "yonetim", "sozlesme",
          "yatirim", "duzenleme", "dava", "kredi_derecelendirme",
          "ortaklik_degisimi", "diger"]


class HaberBagi(BaseModel):
    """Tek bir haberin tek bir hisseyle bağı."""
    sira: int = Field(description="Haberin listedeki sıra numarası")
    sembol: str = Field(description="BIST kodu, verilen listeden birebir")
    tur: str = Field(description=f"Şunlardan biri: {', '.join(TURLER)}")
    onemli: bool = Field(
        description="Fiyatı etkileyebilecek somut bir gelişme mi? "
                    "Genel piyasa yorumu veya rutin haber ise false.")
    gerekce: str = Field(description="En fazla 12 kelime, Türkçe")


class HaberSonuc(BaseModel):
    baglar: list[HaberBagi] = Field(
        description="Yalnızca gerçekten bir hisseyi ilgilendiren haberler. "
                    "Emin değilsen ekleme — boş liste geçerli bir cevaptır.")


SISTEM = """Sen BIST haber akışını hisselere bağlayan bir sınıflandırıcısın.

KURALLAR — hepsi kesindir:
- SADECE sana verilen hisse listesindeki kodları kullan. Listede olmayan bir
  kod ÜRETME. Haber liste dışı bir şirketle ilgiliyse o haberi atla.
- Fiyat, hedef fiyat, tahmin, yön görüşü ÜRETME. İşin sınıflandırmak.
- Emin değilsen ATLA. Yanlış eşleşme, eşleşmemekten daha zararlıdır:
  kullanıcı olmayan bir gerekçeye dayanıp işlem yapar.
- Genel ekonomi haberleri (enflasyon, faiz, kur, "borsa yükseldi") hiçbir
  hisseye bağlanmaz — bunlar makro haberdir, atla.
- Bir haber birden çok hisseyi ilgilendiriyorsa her biri için ayrı kayıt ver.
- Türkçe başlıklarda şirket adı çekim ekiyle geçebilir ("Ülker'in",
  "Vestel'e"). Kök adı tanı."""


def _evren_metni(semboller: list[str]) -> str:
    """Modele verilecek izinli kod listesi."""
    return ", ".join(sorted(semboller))


def sinifla(haberler: list[dict], semboller: list[str] | None = None,
            azami: int = 150) -> tuple[list[dict], str | None]:
    """Haberleri hisselere bağla.

    Döner: (eşleşmeler, hata). Hata varsa liste boştur — çağıran taraf
    kelime eşlemesinin sonucuyla devam eder.
    """
    if not haberler:
        return [], None
    semboller = semboller or evren.evren_getir("bist100")
    izinli = {s.upper() for s in semboller}
    kirp = haberler[:azami]

    satirlar = []
    for i, h in enumerate(kirp):
        baslik = (h.get("baslik") or "").strip()
        ozet = (h.get("ozet") or "").strip()
        # Özet uzun olabiliyor; başlık asıl sinyal, özetten sadece bir tutam.
        satir = f"{i}. {baslik}"
        if ozet and ozet.casefold() != baslik.casefold():
            satir += f" — {ozet[:160]}"
        satirlar.append(satir)

    mesaj = f"""İZİNLİ HİSSE KODLARI (yalnızca bunlar):
{_evren_metni(list(izinli))}

HABER BAŞLIKLARI:
{chr(10).join(satirlar)}

Her haberi değerlendir. Hangi haber hangi hisseyi ilgilendiriyor?
Emin olmadığını atla."""

    c, hata = ai._cagir("haber_sinifla", SISTEM, mesaj,
                        azami=4000, sema=HaberSonuc)
    if hata:
        return [], hata

    try:
        sonuc = c.parsed_output
    except Exception as e:
        return [], f"AI çıktısı okunamadı: {str(e)[:120]}"
    if sonuc is None:
        return [], "AI boş çıktı döndü"

    cikti = []
    for b in sonuc.baglar:
        # KURAL 1: uydurulmuş kod atılır.
        sem = (b.sembol or "").strip().upper()
        if sem not in izinli:
            continue
        if not (0 <= b.sira < len(kirp)):
            continue
        h = kirp[b.sira]
        if not h.get("id"):
            continue
        cikti.append({
            "haber_id": h["id"],
            "sembol": sem,
            "ifade": f"ai:{b.tur if b.tur in TURLER else 'diger'}"
                     f"{'' if b.onemli else '?'}",
            "tur": b.tur if b.tur in TURLER else "diger",
            "onemli": bool(b.onemli),
            "gerekce": (b.gerekce or "")[:120],
        })
    return cikti, None


def birlestir(kelime_eslesme: list[dict],
              ai_eslesme: list[dict]) -> tuple[list[dict], dict]:
    """Kelime eşlemesi taban, AI üstüne ekler.

    Aynı (haber, hisse) çifti ikisinde de varsa kelime eşlemesi kazanır —
    o eşleşme elle yazılmış takma ad listesinden gelir, daha güvenilirdir.
    """
    var = {(e["haber_id"], e["sembol"]) for e in kelime_eslesme}
    yeni = [e for e in ai_eslesme if (e["haber_id"], e["sembol"]) not in var]
    return kelime_eslesme + yeni, {
        "kelime": len(kelime_eslesme),
        "ai_yeni": len(yeni),
        "ai_onemli": sum(1 for e in yeni if e.get("onemli")),
    }


def ozet_metni(eslesmeler: list[dict]) -> str:
    """İnsan okuması için kısa döküm."""
    if not eslesmeler:
        return "AI eşleşmesi yok"
    sayac: dict[str, int] = {}
    for e in eslesmeler:
        sayac[e.get("tur", "diger")] = sayac.get(e.get("tur", "diger"), 0) + 1
    return json.dumps(sayac, ensure_ascii=False)
