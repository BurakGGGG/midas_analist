"""Portföy inşası: varlık dağılımı, ağırlıklandırma, yeniden dengeleme.

Küçük sermayede acı gerçek: BIST'te kesirli hisse yoktur. 1.000 TL ile
"portföyün %15'i şu hisse" diyemezsin — 400 TL'lik hisseden 1 adet zaten %40.
Bu modül hedef ağırlığı değil, ULAŞILABİLİR ağırlığı hesaplar.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


# Risk profiline göre nakit/hisse dengesi
PROFILLER = {
    "temkinli": {"hisse": 40, "nakit": 60, "azami_pozisyon": 4,
                 "aciklama": "Öğrenme aşaması veya savunma rejimi. Nakit bir pozisyondur."},
    "dengeli":  {"hisse": 70, "nakit": 30, "azami_pozisyon": 4,
                 "aciklama": "Varsayılan. Fırsat için nakit tutar, fazla dağılmaz."},
    "agresif":  {"hisse": 95, "nakit": 5, "azami_pozisyon": 5,
                 "aciklama": "Yalnızca sistemi en az 6 ay işlettiysen ve rejim açıksa."},
}


@dataclass
class Hedef:
    sembol: str
    hedef_yuzde: float
    fiyat: float
    adet: int
    tutar: float
    gercek_yuzde: float
    sapma: float
    not_: str = ""


def dagitim(adaylar: list[tuple[str, float]], sermaye: float,
            profil: str = "dengeli", esit_agirlik: bool = True) -> dict:
    """Adaylara sermayeyi dağıt — tam adet kısıtını hesaba katarak.

    adaylar: [(sembol, fiyat), ...] skor sırasına göre
    """
    p = PROFILLER.get(profil, PROFILLER["dengeli"])
    hisse_butce = sermaye * p["hisse"] / 100
    n = min(len(adaylar), p["azami_pozisyon"])
    if n == 0:
        return {"hata": "aday yok"}

    hedef_pay = 100 / n if esit_agirlik else None
    hedefler: list[Hedef] = []
    kalan = hisse_butce

    for i, (sem, fiyat) in enumerate(adaylar[:n]):
        pay = hedef_pay if esit_agirlik else (100 / n)
        istenen = hisse_butce * pay / 100
        adet = int(math.floor(min(istenen, kalan) / fiyat)) if fiyat > 0 else 0
        tutar = adet * fiyat
        kalan -= tutar
        gercek = tutar / sermaye * 100
        not_ = ""
        if adet == 0:
            not_ = f"alınamıyor — 1 adet {fiyat:.2f} TL, bütçe payı {istenen:.0f} TL"
        elif abs(gercek - pay * p["hisse"] / 100) > 8:
            not_ = "tam adet kısıtı yüzünden hedeften saptı"
        hedefler.append(Hedef(sem, round(pay * p["hisse"] / 100, 1), fiyat, adet,
                              round(tutar, 2), round(gercek, 1),
                              round(gercek - pay * p["hisse"] / 100, 1), not_))

    yatirilan = sum(h.tutar for h in hedefler)
    return {
        "profil": profil, "aciklama": p["aciklama"],
        "hedefler": hedefler,
        "yatirilan": round(yatirilan, 2),
        "nakit": round(sermaye - yatirilan, 2),
        "nakit_yuzde": round((sermaye - yatirilan) / sermaye * 100, 1),
        "hedef_nakit_yuzde": p["nakit"],
        "uyari": ("Tam adet kısıtı yüzünden nakit oranı hedeften saptı. "
                  "Küçük sermayede bu kaçınılmazdır — zorlamak için pahalı "
                  "hisseyi atlamak, ucuz ama kötü hisseye yönelmekten iyidir."
                  if abs((sermaye - yatirilan) / sermaye * 100 - p["nakit"]) > 12 else ""),
    }


def dengeleme_gerekli_mi(pozisyonlar: list, guncel_fiyatlar: dict,
                         sapma_esigi: float = 10.0) -> dict:
    """Ağırlıklar hedeften ne kadar saptı? Dengeleme zamanı geldi mi?

    Yeniden dengeleme kazananı satıp kaybedeni almaktır — sezgiye aykırıdır
    ama riski hedefte tutar. Momentum sisteminde ise TERSİ doğrudur: kazananı
    tutar, kaybedeni stop keser. Karıştırma.
    """
    if not pozisyonlar:
        return {"gerekli": False, "sebep": "pozisyon yok"}

    degerler = {}
    for p in pozisyonlar:
        f = guncel_fiyatlar.get(p.sembol)
        if f is None:
            continue
        degerler[p.sembol] = p.adet * f
    if not degerler:
        return {"gerekli": False, "sebep": "güncel fiyat alınamadı"}

    toplam = sum(degerler.values())
    hedef = 100 / len(degerler)
    sapmalar = {s: (v / toplam * 100 - hedef) for s, v in degerler.items()}
    en_buyuk = max(sapmalar.items(), key=lambda kv: abs(kv[1]))

    return {
        "gerekli": abs(en_buyuk[1]) > sapma_esigi,
        "toplam_deger": round(toplam, 2),
        "hedef_agirlik": round(hedef, 1),
        "agirliklar": {s: round(v / toplam * 100, 1) for s, v in degerler.items()},
        "sapmalar": {s: round(v, 1) for s, v in sapmalar.items()},
        "en_sapan": {"sembol": en_buyuk[0], "sapma": round(en_buyuk[1], 1)},
        "not": ("Momentum sistemi kullanıyorsan yeniden dengeleme YAPMA — "
                "kazananı satmak stratejinin mantığına aykırıdır. Dengeleme, "
                "uzun vadeli al-tut portföyleri içindir."),
    }


def nakit_orani_onerisi(rejim: str, dusus_yuzde: float = 0.0) -> dict:
    """Piyasa rejimine ve mevcut düşüşüne göre nakit oranı.

    Nakit bir pozisyondur. Kötü rejimde kaybetmemek, iyi rejimde kazanmak
    kadar değerlidir — çünkü %50 kaybı telafi etmek %100 kazanç gerektirir.
    """
    taban = {"RİSK AÇIK": 15, "ılımlı": 30, "temkinli": 45, "SAVUNMA": 70}.get(rejim, 30)
    if dusus_yuzde < -15:
        taban = min(taban + 20, 85)
        ek = (f"Portföy zirveden %{abs(dusus_yuzde):.0f} aşağıda — nakit oranını "
              "yükseltmek yeni pozisyonu değil, HAYATTA KALMAYI korur.")
    else:
        ek = ""
    return {
        "onerilen_nakit_yuzde": taban,
        "rejim": rejim,
        "gerekce": ek or f"'{rejim}' rejiminde standart nakit oranı.",
        "matematik": "Sermayeni %50 kaybedersen başa dönmek için %100 kazanman "
                     "gerekir. Düşüşü sınırlamak, yükselişi kovalamaktan önemlidir.",
    }
