"""Öğretici şemalar — AĞ ve VERİ GEREKTİRMEZ.

Şema, canlı veri grafiğinden farklı bir şeydir: kavramı gerçek fiyatın
gürültüsü içinde değil, temiz bir çizimde gösterir. "Destek nedir"
sorusunun cevabı gerçek bir grafikte kaybolur.

Sözleşme istemciyle paylaşıldığı için testler ONU kilitler: alan adları
değişirse ressam sessizce boş çizer, kimse fark etmez.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import egitmen_sema as es
from cekirdek import egitmen_gorsel as gg
from cekirdek.egitmen_dersler import DERS_HARITA, MODUL_HARITA


ALANLAR = {"tur", "en", "boy", "cizgiler", "mumlar", "seviyeler",
           "etiketler", "oklar", "baslik", "aciklama", "sonuc"}


# ── sözleşme ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_sozlesmeye_uyar(ad):
    s = es.sema_getir(ad)
    assert s["tur"] == "sema"
    eksik = {"en", "boy", "cizgiler", "mumlar", "seviyeler", "etiketler"} - set(s)
    assert not eksik, f"{ad}: eksik alan {eksik}"
    assert set(s) <= ALANLAR, f"{ad}: bilinmeyen alan {set(s) - ALANLAR}"


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_bos_degil(ad):
    """Hiçbir şey çizmeyen şema, şema olmamasından kötüdür."""
    s = es.sema_getir(ad)
    assert (len(s["cizgiler"]) + len(s["mumlar"]) + len(s["seviyeler"])) > 0


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_aciklama_ve_sonuc_tasir(ad):
    """Çizim tek başına yorumlanmaz; ne anlattığı yazılmalı."""
    s = es.sema_getir(ad)
    assert len(s.get("aciklama", "")) > 30
    assert len(s.get("sonuc", "")) > 30


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_koordinatlar_uzayin_icinde(ad):
    """Uzayın dışına taşan nokta, ressamda kırpılır ve sessizce kaybolur."""
    s = es.sema_getir(ad)
    en, boy = s["en"], s["boy"]
    for c in s["cizgiler"]:
        for x, y in c["nokta"]:
            assert -1 <= x <= en + 1, f"{ad}: x={x} uzay dışı"
            assert -1 <= y <= boy + 1, f"{ad}: y={y} uzay dışı"
    for m in s["mumlar"]:
        assert 0 <= m["x"] <= en
        assert m["d"] <= m["a"] <= m["y"] or m["d"] <= m["k"] <= m["y"]


# ── mum tutarlılığı ────────────────────────────────────────────────────────

def test_mumlarda_yuksek_dusukten_buyuk():
    for ad in es.SEMALAR:
        for m in es.sema_getir(ad)["mumlar"]:
            assert m["y"] > m["d"], f"{ad}: en yüksek <= en düşük"


def test_mum_anatomisinde_bir_yukselen_bir_dusen_var():
    """Ders ikisini karşılaştırıyor; ikisi de olmalı."""
    m = es.sema_getir("mum_anatomisi")["mumlar"]
    assert any(x["k"] > x["a"] for x in m), "yükselen mum yok"
    assert any(x["k"] < x["a"] for x in m), "düşen mum yok"


def test_cekic_uzun_alt_fitilli():
    """Çekicin tanımı: alt fitil gövdenin en az iki katı."""
    m = es.sema_getir("mum_formasyonlari")["mumlar"][0]
    govde = abs(m["k"] - m["a"])
    alt_fitil = min(m["a"], m["k"]) - m["d"]
    assert alt_fitil >= govde * 2, f"gövde {govde}, alt fitil {alt_fitil}"


def test_doji_govdesi_neredeyse_yok():
    m = es.sema_getir("mum_formasyonlari")["mumlar"][1]
    assert abs(m["k"] - m["a"]) < (m["y"] - m["d"]) * 0.1


def test_yutan_boga_ikinci_mum_birinciyi_kapsar():
    m = es.sema_getir("mum_formasyonlari")["mumlar"]
    kucuk, buyuk = m[2], m[3]
    assert min(buyuk["a"], buyuk["k"]) <= min(kucuk["a"], kucuk["k"])
    assert max(buyuk["a"], buyuk["k"]) >= max(kucuk["a"], kucuk["k"])


def test_boslukta_gercekten_bosluk_var():
    """Şema boşluğu anlatıyor; mumlar arasında gerçekten boşluk olmalı."""
    m = es.sema_getir("bosluk")["mumlar"]
    onceki_en_yuksek = max(x["y"] for x in m[:2])
    sonraki_en_dusuk = min(x["d"] for x in m[2:])
    assert sonraki_en_dusuk > onceki_en_yuksek, "boşluk yok"


# ── derslere bağlanma ──────────────────────────────────────────────────────

def test_m13_dersleri_semaya_bagli():
    m13 = MODUL_HARITA["m13"]
    for d in m13.dersler:
        assert d.kod in gg.DERS_GORSEL, f"{d.kod} görselsiz"


def test_sema_onekli_esleme_gecerli():
    for kod, tur in gg.DERS_GORSEL.items():
        if tur.startswith("sema:"):
            assert tur.split(":", 1)[1] in es.SEMALAR, f"{kod} -> {tur} yok"


def test_ders_gorseli_semayi_dondurur():
    assert gg.ders_gorseli("d1303")["tur"] == "sema"


def test_olmayan_sema_cokme_uretmez():
    assert es.sema_getir("olmayan")["yok"] is True


def test_m13_dersleri_mufredatta():
    for kod in ("d1301", "d1302", "d1303", "d1304", "d1305", "d1306", "d1307"):
        assert kod in DERS_HARITA
