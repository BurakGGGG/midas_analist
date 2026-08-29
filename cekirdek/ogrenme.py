"""Kendi kendini ölçme: sistemin ürettiği sinyaller gerçekte ne yaptı?

BU MODÜL, "kendini geliştirme" iddiasının GERÇEK olan kısmıdır.

Bir sistem internetten okuyarak daha iyi analist OLMAZ. Ama şunları yapabilir
ve bunlar ölçülebilir gerçek geri bildirimdir:
  · Ürettiği her sinyali kaydeder
  · 1, 5 ve 20 gün sonra o sinyale ne olduğunu ölçer
  · Zamanla gerçek bir sicil biriktirir
  · Backtest ile CANLI performans arasındaki farkı gösterir

Son madde en değerlisidir: backtest geçmişe uydurulmuş olabilir, canlı sicil
uydurulamaz. İkisi ayrışmaya başlarsa kenar aşınıyor demektir.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from . import ambar, veri

VADELER = (1, 5, 20)


def sinyalleri_kaydet(tarih: str, adaylar: list) -> int:
    """Bugünkü taramanın ürettiği sinyalleri ambara yazar."""
    satirlar = []
    for a in adaylar:
        d = a.sozluk() if hasattr(a, "sozluk") else a
        for st in (d.get("sinyaller") or []):
            poz = d.get("pozisyon") or {}
            satirlar.append({
                "tarih": tarih, "sembol": d["sembol"], "strateji": st,
                "skor": d.get("skor"), "fiyat": d.get("fiyat"),
                "stop": poz.get("stop"), "hedef": poz.get("hedef"),
                "rsi": d.get("rsi"), "adx": d.get("adx"),
                "sma200_ustu": 1 if d.get("sma200_ustu") else 0,
                "alinabilir": 1 if (poz.get("adet") or 0) >= 1 else 0,
            })
    return ambar.sinyal_yaz(satirlar)


def sonuclari_olc(sessiz: bool = True) -> dict:
    """Vadesi gelmiş sinyallerin gerçekte ne yaptığını ölçer.

    Giriş varsayımı backtest ile aynı: sinyal t günü kapanışında üretilir,
    işlem t+1 AÇILIŞINDA yapılır. Aksi halde canlı sicil, backtestten daha
    iyimser çıkar ve kıyas anlamsızlaşır.
    """
    toplam = {}
    for gun in VADELER:
        bekleyen = ambar.sonuclanmamis_sinyaller(gun)
        if not bekleyen:
            toplam[gun] = 0
            continue

        # Hisse başına tek veri çekimi
        semboller = sorted({s["sembol"] for s in bekleyen})
        fiyatlar = {}
        for sem in semboller:
            df = veri.fiyat_cek(sem, gun=400, onbellek_saat=12.0)
            if not df.empty:
                fiyatlar[sem] = df

        sonuclar = []
        for s in bekleyen:
            df = fiyatlar.get(s["sembol"])
            if df is None or df.empty:
                continue
            try:
                sinyal_gun = datetime.fromisoformat(s["tarih"]).date()
            except Exception:
                continue

            sonrasi = df[df.index.date > sinyal_gun]
            if len(sonrasi) < gun + 1:
                continue                      # henüz yeterli gün geçmemiş

            giris = float(sonrasi["Open"].iloc[0])       # t+1 açılış
            pencere = sonrasi.iloc[: gun + 1]
            cikis = float(pencere["Close"].iloc[-1])
            if giris <= 0:
                continue

            stop = s.get("stop") or 0
            hedef = s.get("hedef") or 0

            # KURAL BAZLI ÇIKIŞ — backtestle kıyaslanabilir olması için şart.
            # Ham "N gün tut" ölçümü stop'u yok sayar, kaybedeni sonuna kadar
            # taşır ve sistemi olduğundan kötü gösterir. Backtest ise stop'ta
            # çıkar. İkisini kıyaslamak elmayla armut kıyaslamaktır.
            kural_cikis, sebep = cikis, "sure"
            for j in range(1, len(pencere)):
                bar = pencere.iloc[j]
                if stop and float(bar["Low"]) <= stop:
                    kural_cikis, sebep = stop, "stop"
                    break
                if hedef and float(bar["High"]) >= hedef:
                    kural_cikis, sebep = hedef, "hedef"
                    break

            sonuclar.append({
                "sinyal_id": s["id"], "gun": gun,
                "tarih": pencere.index[-1].date().isoformat(),
                "fiyat": round(cikis, 4),
                "getiri": round((cikis / giris - 1) * 100, 3),
                "kural_getiri": round((kural_cikis / giris - 1) * 100, 3),
                "cikis_sebep": sebep,
                "stop_gordu": int(bool(stop) and float(pencere["Low"].min()) <= stop),
                "hedef_gordu": int(bool(hedef) and float(pencere["High"].max()) >= hedef),
            })
        toplam[gun] = ambar.sonuc_yaz(sonuclar)
        if not sessiz and sonuclar:
            print(f"    {gun} günlük vade: {len(sonuclar)} sinyal sonuçlandı")
    return toplam


def karne(yol=None) -> dict:
    """Sistemin canlı sicili — vadelere ve stratejilere göre."""
    from .strateji import STRATEJILER
    cikti = {"vadeler": {}, "stratejiler": {}}
    for gun in VADELER:
        cikti["vadeler"][gun] = ambar.sinyal_karnesi(gun, yol=yol)
    for st in STRATEJILER:
        k = ambar.sinyal_karnesi(20, strateji=st, yol=yol)
        if k.get("sinyal"):
            cikti["stratejiler"][st] = k
    return cikti


# Backtest referans değerleri (3,28 yıl, BIST 100, 15bp kayma)
# 2023-05-15 -> 2026-08-24 backtestinden, fiyat onarımı (repair=True) açıkken.
# Veri katmanı değişirse `analist.py backtest` ile yeniden ölç ve burayı güncelle.
BACKTEST_REFERANS = {
    # Sinyal seviyesinde, 20 günlük vade, kural bazlı çıkış (stop/hedef).
    # Evren: o GÜNKÜ 20 günlük TL hacmine göre ilk 100 hisse — 570 BIST
    # şirketi üzerinden, 2025-05 → 2026-07 (16 ay).
    #
    # İKİ ESKİ HATA BİRDEN DÜZELTİLDİ (2026-08-25):
    #
    # 1) ELMA-ARMUT: eski referans bir PORTFÖY backtestinden geliyordu —
    #    aynı anda en fazla 4 pozisyon, nakit kısıtı, seçilmiş altküme.
    #    Canlı sicil ise TÜM sinyalleri sayar. İkisini kıyaslamak canlıyı
    #    yapısal olarak kötü gösteriyordu.
    #
    # 2) HAYATTA KALANIN YANILGISI: eski referans BUGÜNÜN BIST 100 listesini
    #    geçmişe uyguluyordu. Listeye sonradan girenler oraya iyi performansla
    #    girdi. Ölçüldü: trend %51,0 -> %48,4, kirilim %52,3 -> %48,9
    #    (tepki'de fark yok). Zamanında hacim sırası geleceği bilmez.
    "kirilim": {"kazanma_orani": 48.9, "ort_kazanc": 14.3, "ort_kayip": -9.6},
    "trend":   {"kazanma_orani": 48.4, "ort_kazanc": 13.5, "ort_kayip": -7.8},
    "tepki":   {"kazanma_orani": 56.1, "ort_kazanc": 9.6,  "ort_kayip": -8.1},
}


def olcum_kapsami(yol=None) -> dict:
    """Sicilin hangi dönemi ve kaç sinyali kapsadığı — yorumdan ÖNCE bilinmeli."""
    with ambar.baglan(yol) as con:
        r = con.execute("""SELECT MIN(tarih) a, MAX(tarih) b, COUNT(*) n
                           FROM sinyal""").fetchone()
    gun = 0
    if r and r["a"] and r["b"]:
        try:
            gun = (datetime.fromisoformat(r["b"]).date()
                   - datetime.fromisoformat(r["a"]).date()).days
        except Exception:
            pass
    return {"ilk": r["a"] if r else None, "son": r["b"] if r else None,
            "sinyal": r["n"] if r else 0, "takvim_gun": gun,
            "ay": round(gun / 30.4, 1) if gun else 0}


# Canlı sicil ile backtest arasındaki YAPISAL farklar. Bunlar bilinmeden
# "kenar aşınıyor" yorumu yapılamaz.
KIYAS_UYARILARI = [
    "Backtest aynı anda en fazla 4 pozisyon taşır ve birden çok sinyalde en "
    "güçlü momentumu seçer. Canlı sicil TÜM sinyalleri sayar — zayıf olanlar "
    "da dahil. Bu tek başına canlıyı daha kötü gösterir.",
    "Backtest 3,28 yılı kapsar, birden çok piyasa rejimi görür. Canlı sicil "
    "şu an çok daha kısa bir dönemi ve muhtemelen tek bir rejimi kapsıyor.",
    "Backtest nakit kısıtı uygular; sermaye bittiğinde sinyal kaçırır. Canlı "
    "sicilde böyle bir kısıt yok.",
    "30 sinyalin altındaki hiçbir kıyas anlamlı değildir; 100 altında bile "
    "gürültü payı yüksektir.",
    "Sinyaller BAĞIMSIZ DEĞİL: hepsi uzun yönlü ve aynı anda açık. Aynı ayın "
    "sinyalleri aynı kaderi paylaşır — ölçülen aylık kazanma oranı %17 ile %81 "
    "arasında savruluyor. Gerçek örneklem büyüklüğü sinyal sayısı değil, AY "
    "sayısıdır. Bu yüzden kıyas artık aylık bloklarla yeniden örneklenir.",
]




# Tarihsel aylık kazanma oranları — 20 günlük vade, kural bazlı çıkış,
# ayda en az 8 sonuçlanmış sinyal. 2025-05 → 2026-07 (16 ay).
#
# NEDEN AY: sinyaller bağımsız değil. Hepsi uzun yönlü ve aynı anda açık,
# yani aynı ayın sinyalleri aynı kaderi paylaşır. Aşağıdaki savrulma bunu
# gösteriyor — trend %16,9 ile %81,2 arasında gidiyor. Kazanma oranını
# "769 bağımsız gözlem" sayarak yorumlamak, gürültüyü kesinlik sanmaktır.
#
# KALAN SINIR: evren bugün borsada olan şirketlerden kuruluyor. Kotasyondan
# tamamen çıkmış şirketler hâlâ eksik, yani küçük bir yanlılık kalıyor —
# ama "endeksten düştü" etkisi artık giderildi.
BACKTEST_AYLIK = {
    # Aynı temiz evren (o günkü hacimde ilk 100), aylık kazanma oranları.
    # Ayda en az 8 sonuçlanmış sinyal. 2025-05 → 2026-07.
    "trend":   [49.3, 37.7, 65.8, 69.2, 29.0, 31.4, 34.3, 56.1,
                65.4, 79.2, 25.3, 68.6, 66.7, 26.6, 33.5, 26.4],
    "tepki":   [19.2, 48.3, 84.2, 85.0, 62.5, 58.8, 65.9, 61.2,
                72.9, 61.9, 38.8, 58.4, 45.8, 45.1, 55.6, 48.3],
    "kirilim": [50.0, 30.8, 77.8, 78.3, 31.2, 24.0, 43.5, 48.4,
                65.8, 74.0, 23.1, 76.2, 44.9, 28.6, 27.6, 11.1],
}


def _canli_ay_sayisi(strateji: str, gun: int = 20, yol=None) -> int:
    """Canlı sicilin kaç FARKLI ayı kapsadığı — gerçek örneklem büyüklüğü."""
    with ambar.baglan(yol) as con:
        r = con.execute("""
            SELECT COUNT(DISTINCT substr(s.tarih, 1, 7)) n
            FROM sinyal s JOIN sinyal_sonuc r ON r.sinyal_id = s.id
            WHERE r.gun = ? AND s.strateji = ? AND r.kural_getiri IS NOT NULL""",
            (gun, strateji)).fetchone()
    return int(r["n"] or 0)


def beklenen_aralik(strateji: str, ay_sayisi: int, tekrar: int = 4000) -> dict:
    """k aylık bir pencerede kazanma oranının tarihsel olarak nereye düştüğü.

    Aylar bütün olarak çekilir (blok önyükleme): sinyaller bağımsız olmadığı
    için tek tek çekmek örneklemi olduğundan büyük gösterir, aralığı yapay
    daraltır ve her farkı 'anlamlı' yapar.

    Aylar eşit ağırlıklı alınır. Sinyal sayısına göre ağırlıklandırmak, çok
    sinyal üreten tek bir ayın sonucu belirlemesine yol açardı — oysa asıl
    sormak istediğimiz "tipik bir ay ne yapar".

    Tohum sabit: aynı veriye aynı cevap. Uyarı bir gün çıkıp ertesi gün
    kaybolursa kimse sicile güvenmez.
    """
    aylik = BACKTEST_AYLIK.get(strateji)
    if not aylik or ay_sayisi < 1:
        return {"yeterli_mi": False, "not": "tarihsel aylık dağılım yok."}
    if ay_sayisi > len(aylik):
        ay_sayisi = len(aylik)

    rng = np.random.default_rng(20260825)
    a = np.array(aylik, dtype=float)
    ornek = rng.choice(a, size=(tekrar, ay_sayisi), replace=True).mean(axis=1)
    return {
        "yeterli_mi": True,
        "ay": ay_sayisi,
        "tarihsel_ay": len(aylik),
        "alt": round(float(np.percentile(ornek, 5)), 1),
        "dusuk_ceyrek": round(float(np.percentile(ornek, 25)), 1),
        "medyan": round(float(np.percentile(ornek, 50)), 1),
        "ust": round(float(np.percentile(ornek, 95)), 1),
    }



# Karantina eşikleri — hangi stratejinin önerileceğine karar verir.
KARANTINA_ASGARI_AY = 2      # tek ay bir gözlemdir, hüküm çıkmaz
KARANTINA_ASGARI_SINYAL = 30


def strateji_siniflari(gun: int = 20, yol=None) -> dict[str, dict]:
    """Her stratejiyi canlı siciline göre sınıflandırır.

    Amaç stratejiyi KAPATMAK değil, ÖNERMEYİ durdurmak. Sinyal üretilmeye
    devam eder ve ambara yazılır — yoksa strateji hakkında yeni kanıt asla
    birikmez ve karantina kalıcı bir hapse dönüşür.

    Sınıflar canlı kazanma oranının, o kadar aylık bir pencerede TARİHSEL
    olarak beklenen dağılımın neresine düştüğüne bakar:

      normal     — beklenenin alt çeyreğinin üstünde
      izlemede   — alt %5 ile alt çeyrek arasında; önerilir ama işaretli
      karantina  — beklenenin alt %5'inin altında; ÖNERİLMEZ
      hüküm_yok  — yeterli ay/sinyal yok

    Eşik veriye bağlı, sabit bir strateji adına bağlı DEĞİL: bozulan
    kendiliğinden karantinaya girer, düzelen kendiliğinden çıkar.
    """
    from .strateji import STRATEJILER

    cikti: dict[str, dict] = {}
    for st in BACKTEST_AYLIK:
        canli = ambar.sinyal_karnesi(gun, strateji=st, yol=yol)
        n = canli.get("sinyal", 0)
        ay = _canli_ay_sayisi(st, gun=gun, yol=yol)
        tanim = STRATEJILER.get(st)
        aktif = tanim.aktif if tanim else True
        temel = {"strateji": st, "sinyal": n, "ay": ay, "aktif": aktif,
                 "kazanma_orani": canli.get("kazanma_orani")}

        # KAPATILAN strateji karantinadan farklı: karantina veriye bakıp
        # geçici olarak önermeyi durduruyor ve sinyal üretmeye devam
        # ediyor. Kapatma kalıcı bir karar ve sinyal de üretilmiyor —
        # ikisini aynı etiketle göstermek yanıltıcı olurdu.
        if not aktif:
            cikti[st] = {**temel, "sinif": "kapalı", "onerilir": False,
                         "gerekce": (
                             "Bu strateji KAPATILDI: 1250 günlük ölçümde "
                             "hem geliştirme hem dokunulmaz dönemde para "
                             "kaybetti. Yeni sinyal üretmiyor; geçmiş "
                             "sicili kayıt olarak duruyor.")}
            continue

        if ay < KARANTINA_ASGARI_AY or n < KARANTINA_ASGARI_SINYAL or \
                "kazanma_orani" not in canli:
            cikti[st] = {**temel, "sinif": "hüküm_yok", "onerilir": True,
                         "gerekce": (f"{ay} ay / {n} sinyal — sınıflandırma için "
                                     f"en az {KARANTINA_ASGARI_AY} ay ve "
                                     f"{KARANTINA_ASGARI_SINYAL} sinyal gerekir.")}
            continue

        aralik = beklenen_aralik(st, ay)
        if not aralik.get("yeterli_mi"):
            cikti[st] = {**temel, "sinif": "hüküm_yok", "onerilir": True,
                         "gerekce": aralik.get("not", "tarihsel dağılım yok")}
            continue

        oran = canli["kazanma_orani"]
        if oran < aralik["alt"]:
            sinif, onerilir = "karantina", False
            gerekce = (f"Canlı %{oran}; {ay} aylık pencerede beklenen alt sınır "
                       f"%{aralik['alt']}. Bunun altında kalan bir strateji "
                       f"önerilmez — ama sinyal üretmeye devam eder, yoksa "
                       f"hakkında yeni kanıt birikmez.")
        elif oran < aralik["dusuk_ceyrek"]:
            sinif, onerilir = "izlemede", True
            gerekce = (f"Canlı %{oran}; beklenenin alt çeyreğinin "
                       f"(%{aralik['dusuk_ceyrek']}) altında ama alt sınırın "
                       f"(%{aralik['alt']}) üstünde. Önerilir, ama izlemede.")
        else:
            sinif, onerilir = "normal", True
            gerekce = (f"Canlı %{oran}; {ay} aylık pencerede beklenen aralığın "
                       f"(%{aralik['alt']}-%{aralik['ust']}) normal bölgesinde.")

        cikti[st] = {**temel, "sinif": sinif, "onerilir": onerilir,
                     "aralik": aralik, "gerekce": gerekce}
    return cikti


def kayma_analizi(yol=None) -> list[dict]:
    """Canlı sicil ile backtest arasındaki fark — kenar aşınıyor mu?

    Az sayıda sinyalle yapılan kıyas gürültüdür. 30 sinyalin altında
    'yeterli veri yok' denir; bu eşik bilinçlidir.
    """
    cikti = []
    for st, ref in BACKTEST_REFERANS.items():
        canli = ambar.sinyal_karnesi(20, strateji=st, yol=yol)
        n = canli.get("sinyal", 0)
        if n < 30:
            cikti.append({
                "strateji": st, "sinyal": n, "yeterli_mi": False,
                "not": f"{n} sinyal — anlamlı kıyas için en az 30 gerekir. "
                       "Erken yargı, gürültüyü sinyal sanmaktır.",
            })
            continue
        if "kazanma_orani" not in canli:
            cikti.append({"strateji": st, "sinyal": n, "yeterli_mi": False,
                          "not": "kural bazlı sonuç yok — `doldur` komutunu "
                                 "yeniden çalıştır"})
            continue
        fark_kazanma = canli["kazanma_orani"] - ref["kazanma_orani"]
        fark_kazanc = canli["ort_kazanc"] - ref["ort_kazanc"]

        # Sabit puan eşiği yerine güven aralığı. Eski hâlde ±8 puanlık fark
        # "kenar aşınıyor" sayılıyordu; oysa aylık kazanma oranı %17-%81
        # arasında savruluyor, yani 8 puan gürültünün çok altında bir eşik.
        ay_n = _canli_ay_sayisi(st, gun=20, yol=yol)
        aralik = beklenen_aralik(st, ay_n)
        if aralik.get("yeterli_mi") and ay_n >= 2:
            canli_oran = canli["kazanma_orani"]
            if canli_oran < aralik["alt"]:
                durum = "canlı DAHA KÖTÜ — beklenen aralığın altında"
            elif canli_oran > aralik["ust"]:
                durum = "canlı DAHA İYİ — beklenen aralığın üstünde"
            else:
                durum = "beklenen aralıkta — fark gürültüyle açıklanabilir"
            aciklama = (f"Canlı %{canli_oran}. {ay_n} aylık bir pencerede "
                        f"tarihsel olarak beklenen aralık "
                        f"%{aralik['alt']}-%{aralik['ust']} (medyan "
                        f"%{aralik['medyan']}). Bu kadar kısa bir pencerede "
                        f"aylık kazanma oranı zaten çok savruluyor.")
        else:
            durum = "hüküm verilemez"
            aciklama = (f"Canlı sicil yalnızca {ay_n} ay kapsıyor. Sinyaller "
                        f"bağımsız olmadığı için gerçek örneklem SİNYAL değil "
                        f"AY sayısıdır; en az 2 ay gerekir.")

        cikti.append({
            "strateji": st, "sinyal": n, "yeterli_mi": True,
            "canli": canli, "backtest": ref,
            "kazanma_farki": round(fark_kazanma, 1),
            "kazanc_farki": round(fark_kazanc, 2),
            "aralik": aralik,
            "durum": durum,
            "not": aciklama + " Kıyas KURAL BAZLI getiriyle yapılır "
                   "(stop/hedef uygulanmış) — backtestle aynı çıkış mantığı.",
        })
    return cikti


def filtre_etkisi(gun: int = 20, yol=None) -> dict:
    """Sistemin filtreleri gerçekten iş görüyor mu?

    Karşılaştırma: SMA200 üstündeki sinyaller vs altındakiler.
    """
    with ambar.baglan(yol) as con:
        satirlar = [dict(r) for r in con.execute("""
            SELECT s.sma200_ustu, s.alinabilir, r.kural_getiri AS getiri
            FROM sinyal s JOIN sinyal_sonuc r ON r.sinyal_id = s.id
            WHERE r.gun = ? AND r.kural_getiri IS NOT NULL""", (gun,)).fetchall()]

    if len(satirlar) < 20:
        return {"yeterli_mi": False, "sinyal": len(satirlar),
                "not": "Filtre etkisini ölçmek için en az 20 sonuçlanmış sinyal gerekir."}

    def ozet(liste):
        if not liste:
            return None
        g = [x["getiri"] for x in liste]
        return {"n": len(g), "ortalama": round(float(np.mean(g)), 2),
                "kazanma": round(sum(1 for x in g if x > 0) / len(g) * 100, 1)}

    return {
        "yeterli_mi": True, "vade_gun": gun,
        "sma200_ustu": ozet([x for x in satirlar if x["sma200_ustu"]]),
        "sma200_alti": ozet([x for x in satirlar if not x["sma200_ustu"]]),
        "alinabilir": ozet([x for x in satirlar if x["alinabilir"]]),
        "alinamaz": ozet([x for x in satirlar if not x["alinabilir"]]),
        "not": "SMA200 üstü grubun ortalaması belirgin yüksekse filtre iş görüyor "
               "demektir. Değilse filtre gereksiz karmaşıklık ekliyordur.",
    }
