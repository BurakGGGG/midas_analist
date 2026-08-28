"""Kapanış onarımı — AĞ GEREKTİRMEZ (denetim testleri hariç).

BULUNAN ARIZA: günlük iş 18:10'da çalışıyordu, BIST'in kapanış seansı da
18:00-18:10'da bitiyor. İş kesinleşmemiş fiyatı yakalayıp ambara
yazıyordu. Ölçüldü: 8524 kaydın 858'i yanlıştı.

BU DOSYADAKİ EN ÖNEMLİ TEST `test_onarim_duzeltilmis_fiyat_kullanir`:
onarımı yazarken auto_adjust=False kullandım ve 775 kaydın DÜZELTİLMİŞ
fiyatını HAM fiyatla ezdim. Sermaye artırımı geçirmiş hisselerde sapma
%238'e çıktı — düzeltme sanılan şey bozma oldu. Yedekten dönülüp doğru
kuralla tekrarlandı.

İki fiyat kuralının karışması sessiz bir arızadır: sayılar makul görünür,
yalnızca sermaye olayı geçirmiş hisselerde ve aylar sonra fark edilir.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import inspect

from cekirdek import kapanis_onarim, veri


def test_onarim_duzeltilmis_fiyat_kullanir():
    """veri.py auto_adjust=True saklıyor; onarım da öyle okumalı.

    İkisi ayrışırsa ambar kendi içinde iki farklı fiyat kuralı taşır ve
    hangi kaydın hangi kurala göre yazıldığı bilinemez."""
    kaynak = inspect.getsource(kapanis_onarim._yahoo_kapanislar)
    assert "auto_adjust=True" in kaynak
    assert "auto_adjust=False" not in kaynak


def test_veri_katmani_hala_duzeltilmis_fiyat_cekiyor():
    """Onarımın dayandığı varsayım bu. veri.py bir gün ham fiyata
    geçerse onarım sessizce yanlış tarafa çeker."""
    kaynak = inspect.getsource(veri)
    assert "auto_adjust=True" in kaynak


def test_esik_yuvarlama_gurultusunu_eler():
    """Kuruş altı sapma için kayıt güncellemek, gereksiz yazma ve
    gereksiz 'düzeltildi' sayısı üretir."""
    assert 0 < kapanis_onarim.ESIK < 0.01


def test_denetle_yazmaz():
    """Önce ölçüp sonra düzeltmek bilinçli: kaç kaydın değişeceğini
    görmeden toplu güncelleme, sessizce veri bozma riskidir."""
    kaynak = inspect.getsource(kapanis_onarim.denetle)
    assert "yaz=False" in kaynak


def test_onar_degisimi_de_yeniden_hesaplar():
    """Kapanışı düzeltip değişim yüzdesini eski bırakmak, tabloyu kendi
    içinde tutarsız yapar."""
    kaynak = inspect.getsource(kapanis_onarim._calis)
    assert "degisim" in kaynak and "UPDATE gunluk_fiyat SET kapanis=?, degisim=?" in kaynak


def test_bos_ambar_cokme_uretmez(tmp_path):
    from cekirdek import ambar
    y = tmp_path / "bos.db"
    ambar.kur(y)
    r = kapanis_onarim.denetle(gun=5, yol=y)
    assert r["yanlis"] == 0 and r["duzeltilen"] == 0


# ── imkânsız hareket koruması ──────────────────────────────────────────────

def test_imkansiz_hareket_esigi_borsa_limitinin_ustunde():
    """BIST ana pazar tavanı ~%20. Eşik onun altına inerse gerçek limit
    hareketleri veri hatası sanılıp elenir."""
    assert 0.20 < kapanis_onarim.AZAMI_GUNLUK_HAREKET < 0.50


def test_onarim_imkansiz_oneriyi_reddeder():
    """KTLEV 29 Temmuz: Yahoo 156,00 veriyordu, komşu günler 46,5 ve 46,4.
    Koruma olmasaydı o çöp kalıcı kayda yazılırdı."""
    kaynak = inspect.getsource(kapanis_onarim._calis)
    assert "AZAMI_GUNLUK_HAREKET" in kaynak
    assert "supheli" in kaynak


def test_zincir_imkansiz_getiriyi_bilinmiyor_yapar():
    """Kaynağın düzeltmediği sermaye olayında gerçek getiri kurtarılamaz.
    NULL yazmak uydurmaktan iyidir: sahte getiri ortalamalara, Sharpe'a
    ve sinyal siciline sızar."""
    kaynak = inspect.getsource(kapanis_onarim.zinciri_yeniden_kur)
    assert "None if abs(ham) > AZAMI_GUNLUK_HAREKET" in kaynak


def test_zincir_onceki_alanini_kapanislardan_kurar():
    """`onceki` o gün yazılmış anlık görüntü; bölünmeden sonra eskir ve
    satırı kendi içinde tutarsız yapar."""
    kaynak = inspect.getsource(kapanis_onarim.zinciri_yeniden_kur)
    assert "onceki_kapanis" in kaynak and "UPDATE gunluk_fiyat SET onceki=?" in kaynak


def test_gunluk_is_onarimi_calistiriyor():
    """Onarım elle çalıştırılan bir bakım işi olarak kalırsa unutulur."""
    from cekirdek import gunluk
    kaynak = inspect.getsource(gunluk.calistir)
    assert "kapanis_onarim" in kaynak and "zinciri_yeniden_kur" in kaynak
