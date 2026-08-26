"""Yatırım tezi: alımdan ÖNCE yazılır, sonradan değiştirilemez.

Bir hisseyi neden aldığını yazmadan alırsan, düştüğünde neden tuttuğunu da
bilemezsin. O boşluğu duygular doldurur. Bu modülün tek işi şu: alım anındaki
düşünceni kaydetmek ve sonradan seni ona bağlamak.

En kritik alan `yanilma_kosulu`. "Hangi durumda yanıldığımı kabul edeceğim?"
sorusunun cevabı ÖNCEDEN yazılmazsa, sonradan hiçbir zaman yazılmaz —
her düşüş "geçici" görünür.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path

import numpy as np

from . import evren

DOSYA = Path(__file__).resolve().parent.parent / "tezler.json"

SORULAR = [
    ("neden_sirket",    "Neden BU şirket? Ne iş yapıyor, neden kazanacak?"),
    ("neden_fiyat",     "Neden BU fiyat? Değerine göre ucuz mu, katalizör mü var?"),
    ("hakli_kosul",     "Hangi durumda haklı çıkmış olacaksın? (somut, ölçülebilir)"),
    ("yanilma_kosulu",  "Hangi durumda YANILDIĞINI kabul edeceksin? (fiyat/olay)"),
    ("hedef",           "Hedefin ne? (fiyat ya da getiri)"),
    ("sure",            "Yatırım süren ne kadar? (gün/ay/yıl)"),
    ("alternatif",      "Bu para yerine mevduata/fona konsa ne olurdu? Neden daha kötü?"),
    ("en_buyuk_risk",   "Bu tezi bozacak EN BÜYÜK risk ne?"),
]


@dataclass
class Tez:
    sembol: str
    tarih: str
    fiyat: float
    adet: int = 0
    risk_tl: float = 0.0

    neden_sirket: str = ""
    neden_fiyat: str = ""
    hakli_kosul: str = ""
    yanilma_kosulu: str = ""
    hedef: str = ""
    sure: str = ""
    alternatif: str = ""
    en_buyuk_risk: str = ""

    # Sistem otomatik dolduruyor — sonradan "ben biliyordum" demeyi engeller
    anlik: dict = field(default_factory=dict)
    kapanis: dict | None = None

    @property
    def acik(self) -> bool:
        return self.kapanis is None

    def eksikler(self) -> list[str]:
        return [s for a, s in SORULAR if not (getattr(self, a, "") or "").strip()]

    def tam_mi(self) -> bool:
        return not self.eksikler()


def yukle() -> list[Tez]:
    if not DOSYA.exists():
        return []
    try:
        return [Tez(**t) for t in json.loads(DOSYA.read_text(encoding="utf-8"))]
    except Exception:
        return []


def kaydet(tezler: list[Tez]) -> None:
    DOSYA.write_text(json.dumps([asdict(t) for t in tezler], ensure_ascii=False, indent=2),
                     encoding="utf-8")


def anlik_goruntu(sembol: str, sermaye: float = 1000.0) -> dict:
    """Alım anındaki objektif durum — sistemin kendi ölçümü.

    Bu, tezin 'kontrol grubu'dur. Altı ay sonra "aslında o zaman da pahalıydı"
    demek yerine, o günkü gerçek rakamlara bakarsın.
    """
    g = {"tarih": date.today().isoformat()}
    try:
        from . import tarayici
        from .risk import RiskAyarlari
        r = tarayici.tek_hisse(sembol, RiskAyarlari(sermaye=sermaye))
        if r:
            s = r["skor"]
            g["teknik"] = {"skor": s["skor"], "rsi": s["rsi"], "adx": s["adx"],
                           "sinyaller": s["sinyaller"], "fiyat": s["fiyat"],
                           "sma200_ustu": s["sma200_ustu"], "gg60": s["gg60"]}
    except Exception:
        pass
    try:
        from . import temel_veri, temel, degerleme
        f = temel_veri.finansal_cek(sembol)
        if f:
            o = temel.oranlar(f)
            g["temel"] = {
                "kalite_skoru": temel.kalite_skoru(f, o)["skor"],
                "sektor": f.sektor,
                "kirmizi_bayrak": temel.kirmizi_bayraklar(f, o),
            }
            c = degerleme.carpanlar(f)
            g["degerleme"] = {ad: (round(x.deger, 2) if x.var_mi and x.gecerli else None)
                              for ad, x in c.items()}
            d = degerleme.ters_dcf(f)
            g["ima_edilen_buyume"] = d.get("ima_edilen_buyume")
    except Exception:
        pass
    try:
        from . import makro
        m = makro.durum()
        g["makro"] = {"rejim": makro.rejim(m)["rejim"],
                      "enflasyon": m.enflasyon.get("yillik"),
                      "usdtry": m.oz("usdtry")["son"] if m.oz("usdtry") else None}
    except Exception:
        pass
    return g


def olustur(sembol: str, fiyat: float, cevaplar: dict, adet: int = 0,
            risk_tl: float = 0.0, sermaye: float = 1000.0) -> Tez:
    sem = evren.sade_kod(sembol)
    t = Tez(sembol=sem, tarih=date.today().isoformat(), fiyat=fiyat,
            adet=adet, risk_tl=risk_tl, anlik=anlik_goruntu(sem, sermaye))
    for a, _ in SORULAR:
        if a in cevaplar:
            setattr(t, a, str(cevaplar[a]).strip())
    tezler = [x for x in yukle() if not (x.sembol == sem and x.acik)]
    tezler.append(t)
    kaydet(tezler)
    return t


def kapat(sembol: str, cikis_fiyat: float, sebep: str, ders: str = "") -> Tez | None:
    """Pozisyonu kapatırken tezi de kapat — ve ne öğrendiğini yaz.

    Kapanış notu olmayan işlem, tekrarlanacak hatadır.
    """
    sem = evren.sade_kod(sembol)
    tezler = yukle()
    for t in tezler:
        if t.sembol == sem and t.acik:
            getiri = (cikis_fiyat / t.fiyat - 1) * 100 if t.fiyat else 0
            t.kapanis = {
                "tarih": date.today().isoformat(), "fiyat": cikis_fiyat,
                "getiri_yuzde": round(getiri, 2),
                "kar_tl": round((cikis_fiyat - t.fiyat) * t.adet, 2),
                "sebep": sebep, "ders": ders,
                "gun": int(np.busday_count(datetime.fromisoformat(t.tarih).date(), date.today())),
                "tez_dogru_muydu": None,
            }
            kaydet(tezler)
            return t
    return None


def kontrol(sermaye: float = 1000.0) -> list[dict]:
    """Açık tezleri bugünkü gerçekle karşılaştır: tez hâlâ geçerli mi?"""
    sonuc = []
    for t in [x for x in yukle() if x.acik]:
        simdi = anlik_goruntu(t.sembol, sermaye)
        eski_fiyat = t.fiyat
        yeni_fiyat = (simdi.get("teknik") or {}).get("fiyat")
        degisim = ((yeni_fiyat / eski_fiyat - 1) * 100
                   if yeni_fiyat and eski_fiyat else None)

        bozulmalar = []
        e_temel = (t.anlik.get("temel") or {}).get("kalite_skoru")
        y_temel = (simdi.get("temel") or {}).get("kalite_skoru")
        if e_temel and y_temel and y_temel < e_temel - 10:
            bozulmalar.append(f"Kalite skoru {e_temel} → {y_temel} (şirket temeli bozuluyor)")

        y_bayrak = set((simdi.get("temel") or {}).get("kirmizi_bayrak", []))
        e_bayrak = set((t.anlik.get("temel") or {}).get("kirmizi_bayrak", []))
        for b in y_bayrak - e_bayrak:
            bozulmalar.append(f"YENİ kırmızı bayrak: {b}")

        e_tek = (t.anlik.get("teknik") or {}).get("sma200_ustu")
        y_tek = (simdi.get("teknik") or {}).get("sma200_ustu")
        if e_tek and not y_tek:
            bozulmalar.append("Fiyat 200 günlük ortalamanın ALTINA düştü (trend kırıldı)")

        sonuc.append({
            "tez": t, "guncel_fiyat": yeni_fiyat, "degisim_yuzde": degisim,
            "gun": int(np.busday_count(datetime.fromisoformat(t.tarih).date(), date.today())),
            "bozulmalar": bozulmalar,
            "hatirlatma": t.yanilma_kosulu,
            "soru": ("Yazdığın yanılma koşulu gerçekleşti mi? Gerçekleştiyse "
                     "SAT — 'biraz daha bekleyeyim' cümlesi buradan başlar."),
        })
    return sonuc


def gecmis_ozet() -> dict:
    """Kapanmış tezlerden çıkan istatistik — kendi karnen."""
    kapali = [t for t in yukle() if not t.acik]
    if not kapali:
        return {"islem": 0}
    getiriler = [t.kapanis["getiri_yuzde"] for t in kapali]
    kazanan = [g for g in getiriler if g > 0]
    tam_tez = [t for t in kapali if t.tam_mi()]
    eksik_tez = [t for t in kapali if not t.tam_mi()]

    def ort(lst):
        return round(float(np.mean([t.kapanis["getiri_yuzde"] for t in lst])), 2) if lst else None

    return {
        "islem": len(kapali),
        "kazanma_orani": round(len(kazanan) / len(kapali) * 100, 1),
        "ortalama_getiri": round(float(np.mean(getiriler)), 2),
        "en_iyi": round(max(getiriler), 2), "en_kotu": round(min(getiriler), 2),
        "tam_tezle_ortalama": ort(tam_tez),
        "eksik_tezle_ortalama": ort(eksik_tez),
        "tam_tez_sayisi": len(tam_tez), "eksik_tez_sayisi": len(eksik_tez),
        "dersler": [t.kapanis.get("ders") for t in kapali if t.kapanis.get("ders")],
        "yorum": ("Tam tez yazdığın işlemlerle yazmadıkların arasındaki fark, "
                  "disiplinin sana ne kazandırdığının ölçüsüdür."),
    }
