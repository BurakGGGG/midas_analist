"""Kapanış fiyatı onarımı.

BULUNAN ARIZA (28 Ağustos 2026): günlük iş 18:10'da çalışıyordu ama
BIST'in KAPANIŞ SEANSI (açık artırma) 18:00-18:10 arasında bitiyor ve
resmî kapanış fiyatı ancak ondan sonra yayına giriyor. İş, henüz
kesinleşmemiş fiyatı yakalayıp ambara YAZIYORDU.

Ölçüldü: 24 Ağustos örneğinde 20 hissenin 17'sinde kayıtlı kapanış
yanlıştı, fark %0,93'e kadar çıkıyordu.

NEDEN ÖNEMLİ — bu bir görüntü hatası değil:
  · `sinyal_sonuc` tablosu bu fiyatlarla hesaplanıyor, yani sistemin
    CANLI SİCİLİ yanlış fiyatlardan ölçülüyor
  · karantina kararı o sicile bakıyor
  · gün içi değişim yüzdesi kullanıcıya yanlış gösteriliyor

Sistemin tüm iddiası dürüst ölçüm; ölçtüğü sayı yanlışsa geri kalanı da
tartışmalı hale gelir.

BU MODÜL geçmişi düzeltir. Zamanlamanın kendisi ayrıca 19:00'a alındı ki
yeni kayıtlar baştan doğru olsun.
"""
from __future__ import annotations

import warnings
from datetime import date, timedelta

from . import ambar, evren

# Bu farkın altındaki sapma yuvarlama gürültüsüdür, kayıt değiştirmeye
# değmez. Üstü gerçek fiyat farkı.
ESIK = 0.005

# Önerilen düzeltme bir günde bundan fazla hareket ima ediyorsa KABUL
# EDİLMEZ. BIST ana pazar günlük tavanı ~%20; onun üstü fiyat değil veri
# hatasıdır.
#
# Bu koruma pahalı bir dersle eklendi: KTLEV'in 29 Temmuz kaydı için
# Yahoo 156,00 veriyordu, komşu günler 46,52 ve 46,40 idi. Tek günlük
# bozuk tik. Koruma olmasaydı onarım o çöpü kalıcı kayda yazacaktı ve
# "düzeltme" sanılan şey, sistemin doğru tuttuğu bir kaydı bozmak
# olacaktı.
#
# Ders: onarım kaynağa körü körüne güvenmez. Ambar da yanılabilir, Yahoo
# da; ikisi çeliştiğinde İMKÂNSIZ olanı eleriz.
AZAMI_GUNLUK_HAREKET = 0.25


def _yahoo_kapanislar(semboller: list[str], baslangic: str,
                      bitis: str) -> dict[tuple[str, str], float]:
    """{(sembol, tarih): kapanış} — tek toplu indirme."""
    import yfinance as yf
    warnings.filterwarnings("ignore")
    kodlar = [s + ".IS" for s in semboller]
    # auto_adjust=True ŞART ve bu satır pahalıya mal oldu: veri.py
    # DÜZELTİLMİŞ fiyat saklıyor (bölünme/temettü için ayarlanmış).
    # Onarım ham fiyatla yapılırsa sermaye artırımı geçirmiş hisselerde
    # kayıtlar birbirini tutmaz — DOAS'ta %8,4, KTLEV'de %238 sapma
    # üretti ve düzeltme sanılan şey bozma oldu.
    d = yf.download(kodlar, start=baslangic, end=bitis, progress=False,
                    auto_adjust=True, group_by="column")
    if d is None or d.empty:
        return {}
    cikti: dict[tuple[str, str], float] = {}
    kapanis = d["Close"] if "Close" in d else d
    for s in semboller:
        kod = s + ".IS"
        if kod not in kapanis:
            continue
        seri = kapanis[kod].dropna()
        for t, v in seri.items():
            cikti[(s, t.strftime("%Y-%m-%d"))] = float(v)
    return cikti


def zinciri_yeniden_kur(yol=None) -> dict:
    """`onceki` ve `degisim` alanlarını kayıtlı kapanışlardan yeniden kurar.

    NEDEN GEREKLİ: `onceki` o gün yazılmış bir ANLIK GÖRÜNTÜ. Hisse
    sonradan bölünürse (ya da temettü düzeltmesi olursa) kapanışlar
    yeniden ayarlanır ama `onceki` olduğu gibi kalır ve satır kendi
    içinde tutarsızlaşır: bölünme öncesi fiyatla bölünme sonrası fiyat
    kıyaslanınca %60'lık sahte bir düşüş çıkar.

    CVKMD'de tam bu oldu: 3 Ağustos'ta -%61,88 görünüyordu, oysa fiyat
    düşmemişti, hisse bölünmüştü.

    Zinciri kayıtlı kapanışlardan kurmak tabloyu kendi içinde tutarlı
    yapıyor: her satırın `onceki`si bir önceki işlem gününün kapanışı.
    """
    with ambar.baglan(yol) as c:
        semboller = [r["sembol"] for r in c.execute(
            "SELECT DISTINCT sembol FROM gunluk_fiyat").fetchall()]
        guncellenen = 0
        for sem in semboller:
            satirlar = c.execute(
                "SELECT tarih, kapanis, onceki, degisim FROM gunluk_fiyat "
                "WHERE sembol=? ORDER BY tarih", (sem,)).fetchall()
            onceki_kapanis = None
            for r in satirlar:
                k = r["kapanis"]
                if k is None:
                    onceki_kapanis = None
                    continue
                if onceki_kapanis is not None and float(onceki_kapanis) > 0:
                    ham = float(k) / float(onceki_kapanis) - 1
                    yeni_onceki = round(float(onceki_kapanis), 4)
                    # BIST günlük tavanı ~%20. Bunu aşan bir "getiri",
                    # kaynağın DÜZELTMEDİĞİ bir sermaye olayıdır (CVKMD
                    # 3 Ağustos: 37,82 → 14,42, Yahoo'da kayıtlı bölünme
                    # yok). Gerçek getiriyi buradan kurtaramayız.
                    #
                    # BİLİNMİYOR yazmak, uydurmaktan iyidir: -%62'lik
                    # sahte bir getiri ortalamalara, Sharpe'a ve sinyal
                    # sicilinde o güne denk gelen her ölçüme sızar.
                    # NULL ise okuyan taraf zaten atlıyor.
                    yeni_degisim = (None if abs(ham) > AZAMI_GUNLUK_HAREKET
                                    else round(ham * 100, 4))
                    mevcut = r["degisim"]
                    farkli = (
                        r["onceki"] is None
                        or abs(float(r["onceki"]) - yeni_onceki) > ESIK
                        or (mevcut is None) != (yeni_degisim is None)
                        or (mevcut is not None and yeni_degisim is not None
                            and abs(float(mevcut) - yeni_degisim) > 0.01))
                    if farkli:
                        c.execute(
                            "UPDATE gunluk_fiyat SET onceki=?, degisim=? "
                            "WHERE tarih=? AND sembol=?",
                            (yeni_onceki, yeni_degisim, r["tarih"], sem))
                        guncellenen += 1
                onceki_kapanis = k
    return {"sembol": len(semboller), "guncellenen": guncellenen}


def imkansiz_kayitlari_onar(yol=None) -> dict:
    """Borsa limitinin dışında değişim taşıyan kayıtları düzeltir.

    NEDEN AYRI BİR ONARIM: bu kayıtlar dış kaynaktan gelen bozuk tiklerle
    oluşuyor (ya da onarımın kendisi koruma yokken çalıştırılmışsa).
    BIST ana pazar günlük tavanı ~%20; %25 üstü bir değişim fiyat değil
    veri hatasıdır ve hiçbir hesaba girmemelidir.

    DÜZELTMENİN KAYNAĞI: bir sonraki günün `onceki` alanı. O alan ayrı
    yazıldığı için bozuk tikten etkilenmemiş oluyor ve gerçek kapanışı
    taşıyor. Dışarıdan yeniden çekmek yerine kendi kaydımızın tutarlı
    kısmını kullanmak daha güvenli: kaynak zaten yanılmış durumda.
    """
    with ambar.baglan(yol) as c:
        bozuk = c.execute(
            "SELECT tarih, sembol, kapanis, onceki, degisim FROM gunluk_fiyat "
            "WHERE degisim IS NOT NULL AND ABS(degisim) > ?",
            (AZAMI_GUNLUK_HAREKET * 100,)).fetchall()

        duzeltilen, cozulemeyen = [], []
        for r in bozuk:
            sonraki = c.execute(
                "SELECT tarih, onceki FROM gunluk_fiyat WHERE sembol=? "
                "AND tarih > ? ORDER BY tarih LIMIT 1",
                (r["sembol"], r["tarih"])).fetchone()
            gercek = sonraki["onceki"] if sonraki else None
            if not gercek or float(gercek) <= 0:
                cozulemeyen.append({"tarih": r["tarih"], "sembol": r["sembol"]})
                continue
            onc = r["onceki"]
            degisim = ((float(gercek) / float(onc) - 1) * 100
                       if onc and float(onc) > 0 else None)
            c.execute("UPDATE gunluk_fiyat SET kapanis=?, degisim=? "
                      "WHERE tarih=? AND sembol=?",
                      (round(float(gercek), 4),
                       round(degisim, 4) if degisim is not None else None,
                       r["tarih"], r["sembol"]))
            duzeltilen.append({"tarih": r["tarih"], "sembol": r["sembol"],
                               "eski": round(float(r["kapanis"]), 2),
                               "yeni": round(float(gercek), 4),
                               "eski_degisim": r["degisim"]})

    return {"bozuk": len(bozuk), "duzeltilen": len(duzeltilen),
            "cozulemeyen": len(cozulemeyen), "ornekler": duzeltilen[:5]}


def denetle(gun: int = 30, yol=None) -> dict:
    """Kaç kayıt yanlış? HİÇBİR ŞEY DEĞİŞTİRMEZ.

    Önce ölçüp sonra düzeltmek bilinçli: kaç kaydın değişeceğini görmeden
    toplu güncelleme çalıştırmak, sessizce veri bozma riskidir.
    """
    return _calis(gun, yol=yol, yaz=False)


def onar(gun: int = 30, yol=None) -> dict:
    """Yanlış kapanışları düzeltir ve değişimi yeniden hesaplar."""
    return _calis(gun, yol=yol, yaz=True)


def _calis(gun: int, yol=None, yaz: bool = False) -> dict:
    bitis = date.today()
    baslangic = bitis - timedelta(days=gun)

    with ambar.baglan(yol) as c:
        satirlar = c.execute(
            "SELECT tarih, sembol, kapanis, onceki FROM gunluk_fiyat "
            "WHERE tarih >= ? ORDER BY tarih",
            (baslangic.isoformat(),)).fetchall()
    if not satirlar:
        return {"bakilan": 0, "yanlis": 0, "duzeltilen": 0, "not": "kayıt yok"}

    semboller = sorted({r["sembol"] for r in satirlar})
    try:
        gercek = _yahoo_kapanislar(semboller, baslangic.isoformat(),
                                   (bitis + timedelta(days=1)).isoformat())
    except Exception as e:
        return {"bakilan": len(satirlar), "yanlis": 0, "duzeltilen": 0,
                "hata": str(e)[:150]}
    if not gercek:
        return {"bakilan": len(satirlar), "yanlis": 0, "duzeltilen": 0,
                "not": "yahoo verisi gelmedi"}

    yanlis, supheli, ornekler = [], [], []
    for r in satirlar:
        y = gercek.get((r["sembol"], r["tarih"]))
        if y is None or r["kapanis"] is None:
            continue
        if abs(y - float(r["kapanis"])) <= ESIK:
            continue

        # İmkânsız hareket testi: önerilen kapanış, önceki günün
        # kapanışına göre borsa limitinin dışında bir sıçrama ima
        # ediyorsa bu düzeltme değil veri hatasıdır.
        onc = r["onceki"]
        if onc and float(onc) > 0:
            if abs(y / float(onc) - 1) > AZAMI_GUNLUK_HAREKET:
                supheli.append({"tarih": r["tarih"], "sembol": r["sembol"],
                                "kayitli": round(float(r["kapanis"]), 4),
                                "onerilen": round(y, 4),
                                "ima_edilen_hareket_yuzde":
                                    round((y / float(onc) - 1) * 100, 2)})
                continue

        yanlis.append((r["tarih"], r["sembol"], float(r["kapanis"]), y))

    yanlis.sort(key=lambda x: -abs(x[3] / x[2] - 1) if x[2] else 0)
    for t, s, a, y in yanlis[:5]:
        ornekler.append({"tarih": t, "sembol": s, "eski": round(a, 4),
                         "yeni": round(y, 4),
                         "fark_yuzde": round((y / a - 1) * 100, 3) if a else 0})

    duzeltilen = 0
    if yaz and yanlis:
        with ambar.baglan(yol) as c:
            for t, s, _eski, y in yanlis:
                # Değişim yüzdesi de yeniden hesaplanmalı: kapanışı
                # düzeltip değişimi eski bırakmak, tabloyu kendi içinde
                # tutarsız yapar ve sonraki okumalar hangisine güveneceğini
                # bilemez.
                onceki = c.execute(
                    "SELECT onceki FROM gunluk_fiyat WHERE tarih=? AND sembol=?",
                    (t, s)).fetchone()
                onc = onceki["onceki"] if onceki else None
                degisim = ((y / float(onc) - 1) * 100
                           if onc and float(onc) > 0 else None)
                c.execute(
                    "UPDATE gunluk_fiyat SET kapanis=?, degisim=? "
                    "WHERE tarih=? AND sembol=?",
                    (round(y, 4),
                     round(degisim, 4) if degisim is not None else None, t, s))
                duzeltilen += 1

    return {"bakilan": len(satirlar), "yanlis": len(yanlis),
            "duzeltilen": duzeltilen, "sembol": len(semboller),
            "supheli": len(supheli), "supheli_ornek": supheli[:5],
            "ornekler": ornekler}
