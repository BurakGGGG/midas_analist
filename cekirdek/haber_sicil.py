"""Haber sicili — haber fiyatı gerçekten hareket ettiriyor mu?

NEDEN VAR: haberleri hisseye eşleştiriyoruz ama SONUCUNU hiç
ölçmüyorduk. "İhale kazandı" haberinden sonra hisse ortalama ne yaptı?
Bu ölçülünce haber okumak bir HİS olmaktan çıkıp bir SAYI oluyor.

Muhtemel cevap şu: çoğu haber hiçbir şey yapmıyor. Ve bunu görmek,
habere göre alım yapma dürtüsünü kesiyor — sistemin bütün mimarisi
zaten bunun üstüne kurulu (karar defteri "sistemi mi takip ettin,
kendi fikrin miydi" diye soruyor).

YÖNTEM SİNYAL SİCİLİYLE AYNI: haber gününden sonraki 1/5/20 iş günü
getirisi ölçülüyor. Sistem kendi sinyallerini böyle ölçüyor, haberi
başka türlü ölçmek iki farklı ölçüt üretirdi.

ENDEKSTEN ARINDIRILIYOR: haber günü bütün piyasa yükseldiyse hissenin
yükselmesi habere bağlanamaz. Ölçülen şey, hissenin ENDEKSE GÖRE
farkı — yoksa boğa piyasasında her haber "iyi" çıkardı.
"""
from __future__ import annotations

import re
from collections import defaultdict

# Haber kategorileri. Anahtar kelimeler KAP konu başlıklarından ve
# haber metinlerinden; her biri farklı bir "olay tipi".
KATEGORILER: list[tuple[str, tuple[str, ...]]] = [
    ("bilanço", ("finansal rapor", "bilanço", "faaliyet raporu",
                 "kâr açıkla", "kar açıkla", "çeyrek")),
    ("temettü", ("kar payı", "kâr payı", "temettü")),
    ("sermaye", ("sermaye artırım", "bedelsiz", "sermaye azaltım")),
    ("sözleşme", ("ihale", "sözleşme", "yeni iş ilişkisi", "anlaşma")),
    ("yatırım", ("yatırım", "kapasite", "tesis", "fabrika")),
    ("ortaklık", ("birleşme", "devralma", "pay alım", "pay satım",
                  "hisse geri alım")),
    ("yönetim", ("genel müdür", "yönetim kurulu", "istifa", "atama")),
    ("hukuk", ("soruşturma", "dava", "ceza", "denetim")),
    ("derecelendirme", ("kredi derecelendirme", "not artır", "not indir")),
    ("genel_kurul", ("genel kurul",)),
]


def kategori(metin: str) -> str:
    """Haberi bir olay tipine yerleştirir. Bulamazsa 'diğer'."""
    d = (metin or "").lower()
    for ad, anahtarlar in KATEGORILER:
        if any(a in d for a in anahtarlar):
            return ad
    return "diğer"


def _sonraki_getiriler(fiyatlar: list[dict], tarih: str,
                       vadeler: tuple[int, ...]) -> dict[int, float]:
    """Haber gününden sonraki N iş günü getirisi.

    `fiyatlar` tarihe göre ARTAN sıralı olmalı. Haber gününde fiyat
    yoksa (tatil, veri eksiği) o haber ölçülemez ve atlanır — tahmin
    etmek, olmayan bir hareketi ölçmek olurdu.
    """
    endeks = {f["tarih"]: i for i, f in enumerate(fiyatlar)}
    i = endeks.get(tarih)
    if i is None:
        return {}
    try:
        temel = float(fiyatlar[i]["kapanis"])
    except Exception:
        return {}
    if temel <= 0:
        return {}
    cikti = {}
    for v in vadeler:
        j = i + v
        if j >= len(fiyatlar):
            continue
        try:
            son = float(fiyatlar[j]["kapanis"])
        except Exception:
            continue
        if son > 0:
            cikti[v] = (son / temel - 1) * 100
    return cikti


def _piyasa_serisi(gun: int, yol=None) -> list[dict]:
    """Günlük piyasa "endeksi" — o günün hisselerinin medyan değişimi
    üzerinden kurulmuş bir seri.

    `_sonraki_getiriler` ile aynı biçimde ({tarih, kapanis}) dönüyor ki
    hisse getirisiyle aynı fonksiyondan geçsin: iki ayrı hesap yazmak,
    birinde düzeltilen hatanın ötekinde kalması demekti.
    """
    from . import ambar
    import statistics as ist

    with ambar.baglan(yol) as con:
        satirlar = con.execute("""
            SELECT tarih, degisim FROM gunluk_fiyat
            WHERE tarih >= date('now', ?) AND degisim IS NOT NULL
            ORDER BY tarih
        """, (f"-{gun} days",)).fetchall()
    if not satirlar:
        return []

    gunluk: dict[str, list[float]] = defaultdict(list)
    for r in satirlar:
        try:
            gunluk[r["tarih"]].append(float(r["degisim"]))
        except Exception:
            pass

    seri, seviye = [], 100.0
    for tarih in sorted(gunluk):
        degerler = gunluk[tarih]
        if len(degerler) < 5:
            continue
        seviye *= 1 + ist.median(degerler) / 100
        seri.append({"tarih": tarih, "kapanis": seviye})
    return seri


def olc(gun: int = 180, vadeler: tuple[int, ...] = (1, 5, 20),
        asgari_ornek: int = 8, yol=None) -> dict:
    """Kategori bazlı haber sicili.

    `asgari_ornek`: bu sayıdan az örneği olan kategori RAPORLANMAZ.
    Üç haberden ortalama çıkarmak, gürültüyü bulgu diye sunmak olurdu.
    """
    from . import ambar, evren

    with ambar.baglan(yol) as con:
        satirlar = con.execute("""
            SELECT h.tarih, h.baslik, h.ozet, hh.sembol
            FROM haber h JOIN haber_hisse hh ON hh.haber_id = h.id
            WHERE h.tarih >= date('now', ?)
            ORDER BY h.tarih
        """, (f"-{gun} days",)).fetchall()

    if not satirlar:
        return {"yeterli_mi": False, "not": "ölçülecek haber yok",
                "kategoriler": {}, "haber": 0}

    # PİYASA GETİRİSİ elimizdeki veriden hesaplanıyor: o günün bütün
    # hisselerinin ortalama değişimi. Endeksin kendisi `gunluk_fiyat`ta
    # saklanmıyor (iş 100 hisseyi yazıyor, endeksi değil) ve ona
    # bağımlı olmak bu ölçümü kırılgan yapardı.
    #
    # Ortalama yerine MEDYAN: birkaç hissenin tavan yapması ortalamayı
    # sürüklüyor ve o gün piyasa yükselmiş gibi görünüyor.
    piyasa = _piyasa_serisi(gun + 40, yol)

    fiyat_onbellek: dict[str, list[dict]] = {}
    toplam: dict[tuple[str, int], list[float]] = defaultdict(list)
    olculen = 0

    for r in satirlar:
        sem = (r["sembol"] or "").upper()
        if not sem:
            continue
        if sem not in fiyat_onbellek:
            fiyat_onbellek[sem] = ambar.fiyat_gecmis(sem, gun=gun + 40,
                                                     yol=yol)[::-1]
        g = _sonraki_getiriler(fiyat_onbellek[sem], r["tarih"], vadeler)
        if not g:
            continue
        e = _sonraki_getiriler(piyasa, r["tarih"], vadeler) if piyasa else {}
        kat = kategori(f"{r['baslik']} {r['ozet'] or ''}")
        for v, deger in g.items():
            toplam[(kat, v)].append(deger - e.get(v, 0.0))
        olculen += 1

    import statistics as ist

    kategoriler: dict[str, dict] = {}
    for (kat, v), degerler in sorted(toplam.items()):
        if len(degerler) < asgari_ornek:
            continue
        k = kategoriler.setdefault(kat, {"vadeler": {}})
        k["vadeler"][v] = {
            "ornek": len(degerler),
            "ortalama": round(float(ist.mean(degerler)), 2),
            "medyan": round(float(ist.median(degerler)), 2),
            "pozitif_oran": round(
                sum(1 for x in degerler if x > 0) / len(degerler) * 100, 1),
        }

    # NEDEN BU KADAR AZ ÖLÇÜLDÜ sorusu havada kalmamalı. Fiyat geçmişi
    # haber geçmişinden kısaysa eski haberler ölçülemez: sunucuda 229
    # haber varken 23'ü ölçülebiliyordu ve sebebi görünmüyordu.
    fiyat_bas = piyasa[0]["tarih"] if piyasa else ""
    haber_bas = satirlar[0]["tarih"] if satirlar else ""
    kapsam_notu = ""
    if fiyat_bas and haber_bas and fiyat_bas > haber_bas:
        kapsam_notu = (
            f"Fiyat kaydı {fiyat_bas} tarihinde başlıyor, haberler "
            f"{haber_bas}'de. Daha eski haberler ölçülemiyor — ölçüm "
            f"penceresi fiyat geçmişi büyüdükçe genişleyecek.")

    return {
        "yeterli_mi": bool(kategoriler),
        "haber": len(satirlar),
        "olculen": olculen,
        "gun": gun,
        "fiyat_baslangic": fiyat_bas,
        "haber_baslangic": haber_bas,
        "kapsam_notu": kapsam_notu,
        "piyasadan_arindirildi": bool(piyasa),
        "kategoriler": kategoriler,
        "not": ("" if kategoriler else
                f"{olculen} haber ölçüldü ama hiçbir kategoride "
                f"{asgari_ornek} örnek birikmedi. Üç haberden ortalama "
                f"çıkarmak, gürültüyü bulgu diye sunmak olurdu."),
    }
