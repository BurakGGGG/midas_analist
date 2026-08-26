"""İkinci kaynak ve çapraz doğrulama.

NEDEN VAR: fiyat, temel veri ve makro — üçü de yfinance'ten geliyor. Tek
kaynak sessizce bozulursa sistem yanlış veriyle çalışır ve bunu fark etmez.
EUREN'de görülen sahte −%63,6 çöküş (bkz. veri.py, repair notu) tam bu
sınıftandı: veri yanlıştı ama hiçbir şey şikâyet etmedi.

Bu modül karar ÜRETMEZ, yalnızca ikinci bir kaynağa sorup farkı bildirir.
Amaç yfinance'i değiştirmek değil, sessiz bozulmayı sesli hale getirmek.

ÖLÇÜM (2026-08-25, 8 hisse × 38 ortak gün): İş Yatırım ile yfinance
kapanışları ortalama %0,00, azami %0,23 farkla örtüşüyor. Eşiği %1 seçmemizin
sebebi bu — normal gürültünün dört katı, ama gerçek bir bozulmanın çok altı.

KAYNAKLAR
  İş Yatırım  — BIST fiyat + piyasa değeri + USD bazlı fiyat.
                Resmi API değil, aracı kurumun kendi ucu.
  TCMB        — günlük döviz kuru. RESMİ ve belgelenmiş; anahtar istemez,
                geçmiş günler de çekilebilir. yfinance'in TRY=X'i bir piyasa
                kotasyonu, TCMB'ninki merkez bankası kuru — aynı şey değil.
"""
from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")

IY_UCU = ("https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/"
          "Common/Data.aspx/HisseTekil")
TCMB_BUGUN = "https://www.tcmb.gov.tr/kurlar/today.xml"
TCMB_GECMIS = "https://www.tcmb.gov.tr/kurlar/{yil:04d}{ay:02d}/{gun:02d}{ay:02d}{yil:04d}.xml"

# Ölçülen normal sapmanın (%0,23) yaklaşık dört katı.
ESIK_YUZDE = 1.0


def _cek(url: str, baslik: dict | None = None, zaman_asimi: float = 25.0) -> bytes | None:
    try:
        b = {"User-Agent": _UA}
        b.update(baslik or {})
        istek = urllib.request.Request(url, headers=b)
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as c:
            return c.read()
    except Exception:
        return None


# ── İş Yatırım ─────────────────────────────────────────────────────────────

def isyatirim_fiyat(kod: str, gun: int = 60) -> dict[str, dict]:
    """{'YYYY-MM-DD': {...}} — İş Yatırım'dan günlük fiyat ve büyüklükler.

    kod: '.IS' eki OLMADAN (AKBNK). Boş sözlük = kaynak ulaşılamadı ya da
    kod tanınmadı; çağıran bunu 'veri yok' sayar, 'fiyat sıfır' değil.
    """
    kod = kod.replace(".IS", "").strip().upper()
    bit = date.today()
    bas = bit - timedelta(days=gun)
    url = (f"{IY_UCU}?hisse={kod}"
           f"&startdate={bas.strftime('%d-%m-%Y')}"
           f"&enddate={bit.strftime('%d-%m-%Y')}")
    ham = _cek(url, {"Referer": "https://www.isyatirim.com.tr/"})
    if not ham:
        return {}
    try:
        d = json.loads(ham)
    except Exception:
        return {}
    if not d.get("ok") or not isinstance(d.get("value"), list):
        return {}

    cikti: dict[str, dict] = {}
    for x in d["value"]:
        try:
            kapanis = x.get("HGDG_KAPANIS")
            t = x.get("HGDG_TARIH")
            if kapanis is None or not t:
                continue
            g, a, y = t.split("-")
            cikti[f"{y}-{a}-{g}"] = {
                "kapanis": float(kapanis),
                "dusuk": float(x["HGDG_MIN"]) if x.get("HGDG_MIN") else None,
                "yuksek": float(x["HGDG_MAX"]) if x.get("HGDG_MAX") else None,
                "hacim": float(x["HGDG_HACIM"]) if x.get("HGDG_HACIM") else None,
                # BIST'te asıl soru bu: TL'de yükselmiş ama dolarda ne olmuş?
                "usd_fiyat": (float(x["DOLAR_BAZLI_FIYAT"])
                              if x.get("DOLAR_BAZLI_FIYAT") else None),
                "piyasa_degeri": float(x["PD"]) if x.get("PD") else None,
                "piyasa_degeri_usd": float(x["PD_USD"]) if x.get("PD_USD") else None,
            }
        except Exception:
            continue
    return cikti


# ── TCMB resmi kur ─────────────────────────────────────────────────────────

def tcmb_kur(gun: date | None = None, geriye: int = 5) -> dict[str, float]:
    """{'USD': 48.0117, 'EUR': ...} — TCMB resmi döviz alış kuru.

    Hafta sonu ve tatilde kur yayınlanmaz (404). O yüzden `geriye` gün kadar
    geriye yürünür; bulunamazsa boş sözlük döner.
    """
    for i in range(geriye + 1):
        if gun is None and i == 0:
            url = TCMB_BUGUN
        else:
            g = (gun or date.today()) - timedelta(days=i)
            url = TCMB_GECMIS.format(yil=g.year, ay=g.month, gun=g.day)
        ham = _cek(url, zaman_asimi=20.0)
        if not ham:
            continue
        try:
            kok = ET.fromstring(ham)
        except Exception:
            continue
        kurlar: dict[str, float] = {}
        for c in kok.findall("Currency"):
            kod = c.get("Kod")
            alis = (c.findtext("ForexBuying") or "").strip()
            birim = (c.findtext("Unit") or "1").strip()
            if kod and alis:
                try:
                    # JPY gibi bazı kurlar 100 birim üzerinden yayınlanır.
                    kurlar[kod] = float(alis) / float(birim or 1)
                except Exception:
                    continue
        if kurlar:
            return kurlar
    return {}


# ── Çapraz kontrol ─────────────────────────────────────────────────────────

def capraz_kontrol(semboller, fiyat_getir, gun: int = 30,
                   esik_yuzde: float = ESIK_YUZDE,
                   asgari_ortak_gun: int = 5) -> list[dict]:
    """yfinance kapanışlarını İş Yatırım'la karşılaştırır, sapmaları döndürür.

    fiyat_getir: sembol -> {'YYYY-MM-DD': kapanış} veren çağrılabilir. Test
    edilebilir kalsın diye dışarıdan geçilir; üretimde veri.fiyat_cek sarmalı.

    Dönen her kayıt bir UYARIDIR, hüküm değil. İki kaynağın ayrışması
    "yfinance yanlış" demek değil — "birine güvenmeden önce bak" demek.
    Kaynağa ulaşılamazsa sessizce atlanır: ağ arızası veri arızası değildir.
    """
    uyarilar = []
    for sem in semboller:
        kod = sem.replace(".IS", "")
        ikinci = isyatirim_fiyat(kod, gun=gun + 15)
        if not ikinci:
            continue
        birinci = fiyat_getir(sem) or {}
        if not birinci:
            continue

        ortak = sorted(set(birinci) & set(ikinci))[-gun:]
        if len(ortak) < asgari_ortak_gun:
            continue

        farklar = []
        for t in ortak:
            a, b = birinci[t], ikinci[t]["kapanis"]
            if not a or a <= 0:
                continue
            farklar.append((t, abs(a - b) / a * 100.0))
        if not farklar:
            continue

        en_kotu_gun, en_kotu = max(farklar, key=lambda x: x[1])
        ort = sum(f for _, f in farklar) / len(farklar)
        if en_kotu >= esik_yuzde:
            uyarilar.append({
                "sembol": sem,
                "azami_fark_yuzde": round(en_kotu, 2),
                "ortalama_fark_yuzde": round(ort, 2),
                "gun": en_kotu_gun,
                "yfinance": round(birinci[en_kotu_gun], 4),
                "isyatirim": round(ikinci[en_kotu_gun]["kapanis"], 4),
                "karsilastirilan_gun": len(farklar),
            })
    return uyarilar
