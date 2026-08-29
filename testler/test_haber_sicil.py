"""Haber sicili — haber fiyatı gerçekten hareket ettiriyor mu?

Haberleri hisseye eşleştiriyorduk ama SONUCUNU hiç ölçmüyorduk.
Bu dosya ölçümün iki temel özelliğini koruyor:

  1. PİYASADAN ARINDIRMA. Haber günü bütün borsa yükseldiyse hissenin
     yükselmesi habere bağlanamaz. Arındırma olmadan boğa piyasasında
     her haber "iyi" çıkardı.

  2. ASGARİ ÖRNEK. Üç haberden ortalama çıkarmak, gürültüyü bulgu diye
     sunmak olur. Az örnekli kategori hiç raporlanmıyor.
"""
from datetime import date, timedelta

import pytest

from cekirdek import ambar, haber_sicil as hs


# ── kategori ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin,beklenen", [
    ("Şirketimiz ihaleyi kazandı", "sözleşme"),
    ("Kâr Payı Dağıtım İşlemleri", "temettü"),
    ("2. çeyrek finansal rapor", "bilanço"),
    ("Bedelsiz sermaye artırımı", "sermaye"),
    ("Genel müdür istifa etti", "yönetim"),
    ("Kredi derecelendirme notu güncellendi", "derecelendirme"),
    ("Aleyhine soruşturma başlatıldı", "hukuk"),
    ("Kapasite artırım yatırımı", "yatırım"),
    ("Hava bugün güzel", "diğer"),
    ("", "diğer"),
])
def test_kategori(metin, beklenen):
    assert hs.kategori(metin) == beklenen


# ── ölçüm ─────────────────────────────────────────────────────────────────

def _kur(tmp_path, hisse_getiri, piyasa_getiri, haber_sayisi=12):
    """Sentetik ambar: hisse günde `hisse_getiri`%, piyasa
    `piyasa_getiri`% yükseliyor. Haberler ilk günlere dağıtılmış."""
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    bugun = date.today()
    gunler = [(bugun - timedelta(days=60 - i)).isoformat() for i in range(60)]

    fiyat, hisse_f, piyasa_f = [], 100.0, 100.0
    for g in gunler:
        hisse_f *= 1 + hisse_getiri / 100
        piyasa_f *= 1 + piyasa_getiri / 100
        fiyat.append({"tarih": g, "sembol": "AAA", "kapanis": hisse_f,
                      "acilis": hisse_f, "yuksek": hisse_f, "dusuk": hisse_f,
                      "hacim": 1e6, "onceki": hisse_f, "degisim": hisse_getiri,
                      "tl_hacim": 1e7, "rsi": 50, "adx": 20, "atr_yuzde": 2,
                      "sma200_ustu": 1, "skor": 60})
        # Piyasa medyanı için en az 5 hisse gerekiyor
        for i, kod in enumerate(("BBB", "CCC", "DDD", "EEE", "FFF")):
            fiyat.append({"tarih": g, "sembol": kod, "kapanis": piyasa_f,
                          "acilis": piyasa_f, "yuksek": piyasa_f,
                          "dusuk": piyasa_f, "hacim": 1e6, "onceki": piyasa_f,
                          "degisim": piyasa_getiri, "tl_hacim": 1e7,
                          "rsi": 50, "adx": 20, "atr_yuzde": 2,
                          "sma200_ustu": 1, "skor": 60})
    ambar.fiyat_yaz(fiyat, yol=yol)

    haberler, esles = [], []
    for i in range(haber_sayisi):
        hid = f"h{i}"
        haberler.append({"id": hid, "tarih": gunler[i], "kaynak": "KAP",
                         "baslik": "AAA ihaleyi kazandı", "ozet": "",
                         "url": f"u{i}", "yayin": gunler[i]})
        esles.append({"haber_id": hid, "sembol": "AAA", "ifade": "AAA"})
    ambar.haber_yaz(haberler, esles, yol=yol)
    return yol


def test_haber_kategorisi_olculuyor(tmp_path):
    yol = _kur(tmp_path, hisse_getiri=1.0, piyasa_getiri=0.0)
    r = hs.olc(gun=90, yol=yol)
    assert r["yeterli_mi"] is True
    assert "sözleşme" in r["kategoriler"]
    v = r["kategoriler"]["sözleşme"]["vadeler"]
    assert 1 in v and 5 in v
    assert v[1]["ortalama"] == pytest.approx(1.0, abs=0.05)


def test_PIYASADAN_ARINDIRILIYOR(tmp_path):
    """Hisse de piyasa da aynı oranda yükseliyorsa habere bağlanacak
    bir hareket YOKTUR. Arındırma olmadan boğa piyasasında her haber
    'iyi' çıkardı."""
    yol = _kur(tmp_path, hisse_getiri=1.0, piyasa_getiri=1.0)
    r = hs.olc(gun=90, yol=yol)
    v = r["kategoriler"]["sözleşme"]["vadeler"]
    assert r["piyasadan_arindirildi"] is True
    assert abs(v[1]["ortalama"]) < 0.05, "piyasa hareketi habere yazılmış"
    assert abs(v[5]["ortalama"]) < 0.2


def test_piyasanin_ALTINDA_kalan_haber_NEGATIF(tmp_path):
    """Hisse yükselse bile piyasanın gerisindeyse haber iyi değildir."""
    yol = _kur(tmp_path, hisse_getiri=0.5, piyasa_getiri=1.5)
    r = hs.olc(gun=90, yol=yol)
    assert r["kategoriler"]["sözleşme"]["vadeler"][1]["ortalama"] < 0


def test_AZ_ORNEKLI_kategori_raporlanmaz(tmp_path):
    """Üç haberden ortalama çıkarmak, gürültüyü bulgu diye sunmaktır."""
    yol = _kur(tmp_path, 1.0, 0.0, haber_sayisi=3)
    r = hs.olc(gun=90, asgari_ornek=8, yol=yol)
    assert r["yeterli_mi"] is False
    assert r["kategoriler"] == {}
    assert "gürültü" in r["not"]


def test_pozitif_oran_hesaplaniyor(tmp_path):
    yol = _kur(tmp_path, hisse_getiri=1.0, piyasa_getiri=0.0)
    v = hs.olc(gun=90, yol=yol)["kategoriler"]["sözleşme"]["vadeler"]
    assert v[1]["pozitif_oran"] == 100.0


def test_medyan_da_veriliyor(tmp_path):
    """Ortalama birkaç uç değerle sürüklenir; medyan onu dengeliyor."""
    yol = _kur(tmp_path, hisse_getiri=1.0, piyasa_getiri=0.0)
    v = hs.olc(gun=90, yol=yol)["kategoriler"]["sözleşme"]["vadeler"]
    assert "medyan" in v[1] and "ornek" in v[1]


def test_bos_ambar_cokmez(tmp_path):
    yol = tmp_path / "bos.db"
    ambar.kur(yol)
    r = hs.olc(gun=90, yol=yol)
    assert r["yeterli_mi"] is False
    assert r["kategoriler"] == {}


def test_fiyati_olmayan_haber_atlanir(tmp_path):
    """Haber gününde fiyat yoksa o haber ÖLÇÜLEMEZ. Tahmin etmek,
    olmayan bir hareketi ölçmek olurdu."""
    yol = _kur(tmp_path, 1.0, 0.0)
    ambar.haber_yaz(
        [{"id": "yok", "tarih": "2000-01-01", "kaynak": "KAP",
          "baslik": "AAA ihale", "ozet": "", "url": "uy",
          "yayin": "2000-01-01"}],
        [{"haber_id": "yok", "sembol": "AAA", "ifade": "AAA"}], yol=yol)
    r = hs.olc(gun=90, yol=yol)
    assert r["olculen"] <= r["haber"]


# ── piyasa serisi ─────────────────────────────────────────────────────────

def test_piyasa_serisi_MEDYANLA_kuruluyor(tmp_path):
    """Ortalama yerine medyan: birkaç hissenin tavan yapması ortalamayı
    sürükler ve o gün piyasa yükselmiş gibi görünür."""
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    bugun = date.today().isoformat()
    satirlar = []
    # Beş hisse %0, bir hisse %20 (tavan). Medyan 0 olmalı.
    for kod, d in (("A", 0.0), ("B", 0.0), ("C", 0.0), ("D", 0.0),
                   ("E", 0.0), ("F", 20.0)):
        satirlar.append({"tarih": bugun, "sembol": kod, "kapanis": 100,
                         "acilis": 100, "yuksek": 100, "dusuk": 100,
                         "hacim": 1e6, "onceki": 100, "degisim": d,
                         "tl_hacim": 1e7, "rsi": 50, "adx": 20,
                         "atr_yuzde": 2, "sma200_ustu": 1, "skor": 60})
    ambar.fiyat_yaz(satirlar, yol=yol)
    seri = hs._piyasa_serisi(30, yol=yol)
    assert len(seri) == 1
    assert seri[0]["kapanis"] == pytest.approx(100.0, abs=0.01)


def test_az_hisseli_gun_piyasa_serisine_girmez(tmp_path):
    """Üç hisseden piyasa medyanı çıkarmak anlamsız."""
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    bugun = date.today().isoformat()
    ambar.fiyat_yaz([
        {"tarih": bugun, "sembol": k, "kapanis": 100, "acilis": 100,
         "yuksek": 100, "dusuk": 100, "hacim": 1e6, "onceki": 100,
         "degisim": 1.0, "tl_hacim": 1e7, "rsi": 50, "adx": 20,
         "atr_yuzde": 2, "sma200_ustu": 1, "skor": 60}
        for k in ("A", "B", "C")], yol=yol)
    assert hs._piyasa_serisi(30, yol=yol) == []


def test_kapsam_notu_neden_az_olculdugunu_soyler(tmp_path):
    """Sunucuda 229 haber varken 23'ü ölçülebiliyordu ve sebebi
    görünmüyordu: fiyat kaydı haberden kısa. Kullanıcı "neden bu kadar
    az" diye sormamalı."""
    yol = _kur(tmp_path, 1.0, 0.0)
    # Fiyat geçmişinden ÇOK ESKİ bir haber ekle
    ambar.haber_yaz(
        [{"id": "eski", "tarih": "2020-01-02", "kaynak": "KAP",
          "baslik": "AAA ihale", "ozet": "", "url": "ue",
          "yayin": "2020-01-02"}],
        [{"haber_id": "eski", "sembol": "AAA", "ifade": "AAA"}], yol=yol)
    r = hs.olc(gun=5000, yol=yol)
    assert r["kapsam_notu"], "kapsam farkı söylenmiyor"
    assert "ölçülemiyor" in r["kapsam_notu"]


def test_kapsam_tamsa_not_bos(tmp_path):
    yol = _kur(tmp_path, 1.0, 0.0)
    assert hs.olc(gun=90, yol=yol)["kapsam_notu"] == ""
