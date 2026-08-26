"""Uygulama sözlüğü — AĞ GEREKTİRMEZ.

Sözlüğün tek gerçek riski sessizce geride kalmaktır: koda yeni bir gösterge
ya da strateji eklenir, sözlüğe eklenmez, kullanıcı bakar ve bulamaz. Bir
kez bulamayan bir daha bakmaz.

Bu yüzden testlerin çoğu KAPSAM testidir: kodda üretilen her sütunun, her
stratejinin ve her rejim adının sözlükte karşılığı olmak zorunda.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import numpy as np
import pandas as pd
import pytest

from cekirdek import sozluk as sz
from cekirdek.egitmen_dersler import DERS_HARITA
from cekirdek.strateji import STRATEJILER


def _gosterge_kolonlari() -> list[str]:
    """gosterge_seti'nin ÜRETTİĞİ sütunlar — elle yazılmış bir liste değil.

    Elle yazılsaydı test, korumaya çalıştığı driftin aynısına uğrardı.
    """
    from cekirdek.gostergeler import gosterge_seti
    n = 300
    i = pd.date_range("2024-01-01", periods=n, freq="B")
    k = pd.Series(np.linspace(100, 140, n), index=i)
    df = pd.DataFrame({"Open": k, "High": k * 1.01, "Low": k * 0.99,
                       "Close": k, "Volume": 1e6}, index=i)
    endeks = pd.Series(np.linspace(100, 120, n), index=i)
    out = gosterge_seti(df, endeks)
    return [c for c in out.columns if c not in df.columns]


# ── kapsam ─────────────────────────────────────────────────────────────────

def test_her_gosterge_sutununun_karsiligi_var():
    eksik = [c for c in _gosterge_kolonlari() if c not in sz.KOLON_HARITA]
    assert not eksik, f"sözlükte karşılığı olmayan sütun: {eksik}"


def test_sozlukteki_kolonlar_gercekten_uretiliyor():
    """Ters yön: kaldırılmış bir sütunu açıklamaya devam etmek de drift."""
    uretilen = set(_gosterge_kolonlari())
    fazla = [k for k in sz.KOLON_HARITA if k not in uretilen]
    assert not fazla, f"artık üretilmeyen sütun açıklanıyor: {fazla}"


def test_her_stratejinin_karsiligi_var():
    for ad in STRATEJILER:
        assert sz.terim_getir(ad) is not None, f"{ad} sözlükte yok"


def test_rejim_adlarinin_hepsi_aciklanmis():
    """makro.rejim() dört ad üretir; dördü de sözlükte geçmeli."""
    t = sz.terim_getir("rejim")
    assert t is not None
    for ad in ("RİSK AÇIK", "ılımlı", "temkinli", "SAVUNMA"):
        assert ad in t.aciklama, f"rejim '{ad}' sözlükte anlatılmamış"


def test_karantina_siniflarinin_hepsi_aciklanmis():
    """ogrenme.strateji_siniflari() dört sınıf üretir."""
    t = sz.terim_getir("karantina")
    for sinif in ("normal", "izlemede", "karantina", "hüküm_yok"):
        assert sinif in t.aciklama, f"'{sinif}' sınıfı anlatılmamış"


# ── sözleşme ───────────────────────────────────────────────────────────────

def test_terim_adlari_benzersiz():
    adlar = [t.terim.lower() for t in sz.TUM_TERIMLER]
    assert len(adlar) == len(set(adlar))


def test_bir_kolon_tek_terime_ait():
    """Aynı sütunu iki terim sahiplenirse hangisinin gösterileceği
    yazılış sırasına kalır — sessiz ve keyfi."""
    sahipli = [k for t in sz.TUM_TERIMLER for k in t.kolonlar]
    assert len(sahipli) == len(set(sahipli))


@pytest.mark.parametrize("t", sz.TUM_TERIMLER, ids=lambda t: t.terim)
def test_kisa_karsilik_gercekten_kisa(t):
    """Sözlüğün varlık sebebi 30 saniyede cevap vermek. Uzarsa ders olur
    ve ikisi de bozulur."""
    assert 0 < len(t.kisa) <= 110, f"{t.terim}: {len(t.kisa)} karakter"


@pytest.mark.parametrize("t", sz.TUM_TERIMLER, ids=lambda t: t.terim)
def test_terimin_adi_ve_karsiligi_dolu(t):
    assert t.terim.strip() and t.kisa.strip()


def test_ders_baglantilari_gercek():
    """Sözlük merak uyandırır, ders cevaplar. Kırık bağ, kullanıcıyı
    olmayan bir derse yollar."""
    for t in sz.TUM_TERIMLER:
        if t.ders:
            assert t.ders in DERS_HARITA or t.ders.startswith(("t", "o", "u")), \
                f"{t.terim} -> {t.ders} diye bir ders yok"


def test_bolum_kodlari_benzersiz():
    kodlar = [b.kod for b in sz.BOLUMLER]
    assert len(kodlar) == len(set(kodlar))


def test_her_bolumde_terim_var():
    for b in sz.BOLUMLER:
        assert b.terimler, f"{b.kod} boş"


# ── arama ──────────────────────────────────────────────────────────────────

def test_kolon_adiyla_bulunur():
    assert sz.terim_getir("ATR_yuzde").terim == "ATR"
    assert sz.terim_getir("GG60").terim == "Göreli güç (GG)"


def test_buyuk_kucuk_harf_duyarsiz():
    assert sz.terim_getir("atr_yuzde") is sz.terim_getir("ATR_YUZDE")


def test_olmayan_terim_cokme_uretmez():
    assert sz.terim_getir("boyle_bir_sey_yok") is None
    assert sz.terim_getir("") is None
    assert sz.terim_getir(None) is None


def test_arama_terim_adinda_bulur():
    assert any(t.terim == "Hacim oranı" for t in sz.ara("hacim"))


def test_arama_govdede_aramaz():
    """'stop' onlarca terimin gövdesinde geçiyor; hepsini döndürmek arama
    değil gürültüdür."""
    sonuc = sz.ara("stop")
    assert all("stop" in t.terim.lower() or "stop" in t.kisa.lower()
               for t in sonuc)


def test_bos_arama_bos_doner():
    assert sz.ara("") == [] and sz.ara(None) == []
