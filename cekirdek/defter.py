"""Karar günlüğü — kullanıcının ne YAPTIĞI.

`sinyal` tablosu sistemin ne önerdiğini tutar. Bu modül kullanıcının ne
yaptığını tutar. İkisi ayrı, çünkü ölçülmek istenen şey ARADAKİ FARK:

  Sistem bir gün 7 sinyal üretiyor, kullanıcı 2'sini alıyor. Asıl beceri
  o seçimde — ve şimdiye kadar hiçbir yerde kayıtlı değildi. Sicil "sistem
  ne yaptı" sorusunu cevaplıyordu; "ben ne yaptım" sorusunun cevabı yoktu.

DEĞİŞTİRİLEMEZ GÜNLÜK: satır güncellenmez, yalnızca eklenir. Satış da ayrı
bir karardır ve alımı silmez. Sonradan "ben zaten biliyordum" demeyi
imkânsız kılan tek şey budur — psikoloji modülünün tamamı bu tek yanılgı
üzerine kurulu (bkz. d1003 teyit önyargısı).

KARAR ANINDA DONDURULAN BİLGİ: alım kaydedilirken o gün sistemin ne
dediği (sinyal var mıydı, hangi strateji, önerilir miydi, skor kaç) aynı
satıra yazılır. Sonradan sorgulanmaz — çünkü sonradan bakınca sistemin
"aslında uyarmıştı" görünmesi kolaydır.

KAĞIT / GERÇEK: `kagit=1` varsayılan. Gerçek parayla başlamadan önce
kağıt üzerinde takip, riski sıfır ölçümü gerçek olan tek ara adımdır.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from . import ambar


# Sinyal kaç gün TAZE sayılır. Bu pencere olmadan, hissenin aylar
# önce bir kez sinyal vermiş olması bugünkü alımı "sinyalli" yapar ve
# "sistemi takip etme oranı" ölçümü anlamını yitirir — her hisse bir
# gün sinyal vermiştir. 5 gün ≈ bir işlem haftası.
SINYAL_TAZELIK_GUN = 5


def _sistem_ne_diyordu(sembol: str, gun: str | None = None) -> dict:
    """Karar anında sistemin bu hisse için ne dediği."""
    gun = gun or date.today().isoformat()
    en_eski = (date.fromisoformat(gun)
               - timedelta(days=SINYAL_TAZELIK_GUN)).isoformat()
    bos = {"sinyal_var": 0, "strateji": None, "onerilir": None, "skor": None}
    with ambar.baglan() as con:
        # Son işlem haftasındaki sinyal: bugün iş çalışmadıysa dünküne
        # bakılır, çünkü kararlar kapanış verisiyle veriliyor. Ama aylar
        # öncesine bakılmaz.
        r = con.execute("""
            SELECT strateji, skor FROM sinyal
            WHERE sembol = ? AND tarih <= ? AND tarih >= ?
            ORDER BY tarih DESC, skor DESC LIMIT 1""",
            (sembol, gun, en_eski)).fetchone()
    if not r:
        return bos
    try:
        from . import ogrenme
        siniflar = ogrenme.strateji_siniflari()
        onerilir = siniflar.get(r["strateji"], {}).get("onerilir", True)
    except Exception:
        onerilir = None
    return {"sinyal_var": 1, "strateji": r["strateji"],
            "onerilir": int(onerilir) if onerilir is not None else None,
            "skor": r["skor"]}


def alim(sembol: str, fiyat: float, adet: int = 1, kagit: bool = True,
         stop: float = 0.0, hedef: float = 0.0, gerekce: str = "") -> dict:
    sembol = sembol.upper().replace(".IS", "").strip()
    simdi = datetime.now()
    bilgi = _sistem_ne_diyordu(sembol)
    kayit = {
        "zaman": simdi.isoformat(timespec="seconds"),
        "tarih": simdi.date().isoformat(),
        "tur": "alim", "sembol": sembol, "adet": int(adet),
        "fiyat": float(fiyat), "kagit": 1 if kagit else 0,
        "stop": float(stop or 0), "hedef": float(hedef or 0),
        "gerekce": gerekce, **bilgi,
    }
    ambar.kur()
    with ambar.baglan() as con:
        con.execute("""
            INSERT INTO karar (zaman,tarih,tur,sembol,adet,fiyat,kagit,
                               stop,hedef,sinyal_var,strateji,onerilir,skor,gerekce)
            VALUES (:zaman,:tarih,:tur,:sembol,:adet,:fiyat,:kagit,
                    :stop,:hedef,:sinyal_var,:strateji,:onerilir,:skor,:gerekce)""",
                    kayit)
    return kayit


def satim(sembol: str, fiyat: float, adet: int = 0, gerekce: str = "") -> dict:
    """adet=0 ise açık pozisyonun tamamı satılır."""
    sembol = sembol.upper().replace(".IS", "").strip()
    acik = acik_pozisyon(sembol)
    if not acik:
        return {"hata": f"{sembol} için açık pozisyon yok"}
    adet = int(adet) or acik["adet"]
    adet = min(adet, acik["adet"])

    simdi = datetime.now()
    kayit = {
        "zaman": simdi.isoformat(timespec="seconds"),
        "tarih": simdi.date().isoformat(),
        "tur": "satim", "sembol": sembol, "adet": adet, "fiyat": float(fiyat),
        "kagit": acik.get("kagit", 1), "stop": 0.0, "hedef": 0.0,
        "sinyal_var": 0, "strateji": acik.get("strateji"),
        "onerilir": None, "skor": None, "gerekce": gerekce,
    }
    ambar.kur()
    with ambar.baglan() as con:
        con.execute("""
            INSERT INTO karar (zaman,tarih,tur,sembol,adet,fiyat,kagit,
                               stop,hedef,sinyal_var,strateji,onerilir,skor,gerekce)
            VALUES (:zaman,:tarih,:tur,:sembol,:adet,:fiyat,:kagit,
                    :stop,:hedef,:sinyal_var,:strateji,:onerilir,:skor,:gerekce)""",
                    kayit)
    getiri = (float(fiyat) / acik["giris"] - 1) * 100 if acik["giris"] else 0.0
    kayit["getiri"] = round(getiri, 2)
    kayit["giris"] = acik["giris"]
    # Stop'a uyuldu mu: disiplin ölçümünün tek somut göstergesi.
    kayit["stopun_altinda_satildi"] = bool(
        acik.get("stop") and float(fiyat) < float(acik["stop"]))
    return kayit


def _kararlar(kagit: bool | None = None) -> list[dict]:
    ambar.kur()
    with ambar.baglan() as con:
        sorgu = "SELECT * FROM karar"
        p: list = []
        if kagit is not None:
            sorgu += " WHERE kagit = ?"
            p.append(1 if kagit else 0)
        sorgu += " ORDER BY zaman"
        return [dict(r) for r in con.execute(sorgu, p)]


def acik_pozisyonlar(kagit: bool | None = None) -> list[dict]:
    """Kararlardan türetilir — ayrı bir 'pozisyon' tablosu YOK.

    Sebep: iki kaynak tutulursa biri diğerinden sapar ve hangisinin doğru
    olduğu bilinmez. Günlük tek gerçek kaynak; pozisyon onun sonucu.
    """
    havuz: dict[str, list[dict]] = {}
    for k in _kararlar(kagit):
        s = k["sembol"]
        if k["tur"] == "alim":
            havuz.setdefault(s, []).append(dict(k))
        else:
            # FIFO: en eski alımdan düşülür.
            kalan = k["adet"]
            while kalan > 0 and havuz.get(s):
                ilk = havuz[s][0]
                dus = min(kalan, ilk["adet"])
                ilk["adet"] -= dus
                kalan -= dus
                if ilk["adet"] <= 0:
                    havuz[s].pop(0)

    cikti = []
    for s, liste in havuz.items():
        liste = [x for x in liste if x["adet"] > 0]
        if not liste:
            continue
        adet = sum(x["adet"] for x in liste)
        maliyet = sum(x["adet"] * x["fiyat"] for x in liste)
        cikti.append({
            "sembol": s, "adet": adet,
            "giris": round(maliyet / adet, 4) if adet else 0.0,
            "maliyet": round(maliyet, 2),
            "stop": liste[0].get("stop") or 0.0,
            "hedef": liste[0].get("hedef") or 0.0,
            "strateji": liste[0].get("strateji"),
            "kagit": liste[0].get("kagit", 1),
            "tarih": liste[0]["tarih"],
        })
    return sorted(cikti, key=lambda x: x["sembol"])


def acik_pozisyon(sembol: str) -> dict | None:
    sembol = sembol.upper().replace(".IS", "").strip()
    for p in acik_pozisyonlar():
        if p["sembol"] == sembol:
            return p
    return None


def kapali_islemler(kagit: bool | None = None) -> list[dict]:
    """Eşleşmiş alım-satım çiftleri, getirileriyle."""
    havuz: dict[str, list[dict]] = {}
    cikti = []
    for k in _kararlar(kagit):
        s = k["sembol"]
        if k["tur"] == "alim":
            havuz.setdefault(s, []).append(dict(k))
            continue
        kalan = k["adet"]
        while kalan > 0 and havuz.get(s):
            ilk = havuz[s][0]
            dus = min(kalan, ilk["adet"])
            getiri = ((k["fiyat"] / ilk["fiyat"] - 1) * 100
                      if ilk["fiyat"] else 0.0)
            cikti.append({
                "sembol": s, "adet": dus,
                "giris": ilk["fiyat"], "cikis": k["fiyat"],
                "getiri": round(getiri, 2),
                "alim_tarih": ilk["tarih"], "satim_tarih": k["tarih"],
                "strateji": ilk.get("strateji"),
                "sinyal_var": ilk.get("sinyal_var", 0),
                "onerilir": ilk.get("onerilir"),
                "stop": ilk.get("stop") or 0.0,
                "kagit": ilk.get("kagit", 1),
            })
            ilk["adet"] -= dus
            kalan -= dus
            if ilk["adet"] <= 0:
                havuz[s].pop(0)
    return cikti


def karne(kagit: bool | None = None) -> dict:
    """Kullanıcının kendi sicili — sistemin sicilinden AYRI.

    Ölçülen dört şey:
      1) kapanan işlemlerde kazanma oranı ve ortalama getiri
      2) sistemi ne kadar takip ettin (sinyalli alım oranı)
      3) karantinadaki stratejiden kaç alım yaptın
      4) stop disiplini — stopun altına düşen pozisyonu taşıdın mı
    """
    kapali = kapali_islemler(kagit)
    alimlar = [k for k in _kararlar(kagit) if k["tur"] == "alim"]

    d: dict = {
        "alim_sayisi": len(alimlar),
        "kapanan": len(kapali),
        "acik": len(acik_pozisyonlar(kagit)),
    }
    if not alimlar:
        d["not"] = ("Henüz karar kaydı yok. Bot'tan /aldim ile "
                    "başlayabilirsin.")
        return d

    sinyalli = sum(1 for a in alimlar if a.get("sinyal_var"))
    d["sinyalli_alim"] = sinyalli
    d["sistem_takip_orani"] = round(sinyalli / len(alimlar) * 100, 1)
    karantinali = sum(1 for a in alimlar if a.get("onerilir") == 0)
    d["karantinali_alim"] = karantinali

    if kapali:
        g = [k["getiri"] for k in kapali]
        kaz = [x for x in g if x > 0]
        d["kazanma_orani"] = round(len(kaz) / len(g) * 100, 1)
        d["ortalama_getiri"] = round(sum(g) / len(g), 2)
        d["en_iyi"] = round(max(g), 2)
        d["en_kotu"] = round(min(g), 2)

        # Sinyalli vs kendi fikri: seçim becerisi buradan görünür.
        for ad, alt in (("sinyalli", [k for k in kapali if k.get("sinyal_var")]),
                        ("kendi_fikrin", [k for k in kapali
                                          if not k.get("sinyal_var")])):
            if alt:
                gg = [k["getiri"] for k in alt]
                d[ad] = {"n": len(gg),
                         "kazanma": round(sum(1 for x in gg if x > 0)
                                          / len(gg) * 100, 1),
                         "ortalama": round(sum(gg) / len(gg), 2)}

        # Disiplin: stopun altında kapanan işlem, stopa uyulmadığını gösterir.
        stoplu = [k for k in kapali if k.get("stop")]
        if stoplu:
            asildi = sum(1 for k in stoplu if k["cikis"] < k["stop"])
            d["stop_disiplini"] = {
                "stoplu_islem": len(stoplu), "stopun_altinda_kapanan": asildi,
                "not": ("Stopun altında kapanan işlem, stopa zamanında "
                        "uyulmadığını gösterir." if asildi else
                        "Stoplu işlemlerin hepsi stop seviyesinde ya da "
                        "üstünde kapandı.")}

    # Örneklem uyarısı: sistemin sicilinde uygulanan aynı dürüstlük.
    if len(kapali) < 20:
        d["uyari"] = (f"{len(kapali)} kapanan işlem — hüküm çıkarmak için "
                      f"çok az. Kendi kazanma oranın en az 20-30 işlemden "
                      f"sonra anlam kazanır.")
    return d
