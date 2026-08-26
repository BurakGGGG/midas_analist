"""Bağlamsal ders seçimi — AĞ ve VERİTABANI GEREKTİRMEZ.

65 derslik müfredat ayrı bir iş gibi durduğu için açılmıyordu: ölçüldü,
65 dersten 1'i okunmuştu. Sebep içerik değil AKIŞ — kullanıcı "eğitim"
için ayrı zaman ayırmıyor.

Bu katmanın işi dersi o günün gerçek olayına bağlamak. İki hata pahalı:

  ALAKASIZ DERS  — bağlam kurulmazsa müfredat yine ayrı bir iş olarak kalır.
  SESSİZ KALMA   — hiç ders önermemek, katmanın hiç olmaması demektir.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import egitmen as e
from cekirdek.egitmen_dersler import DERS_HARITA


# ── eşleme ─────────────────────────────────────────────────────────────────

def test_karantina_backtest_dersini_getirir():
    assert e.baglamsal_ders({"karantina": True})["kod"] == "d1202"


def test_yogunlasma_korelasyon_dersini_getirir():
    assert e.baglamsal_ders({"yogunlasma": True})["kod"] == "d804"


def test_reel_negatif_enflasyon_dersini_getirir():
    assert e.baglamsal_ders({"reel_negatif": True})["kod"] == "d601"


def test_sinyalsiz_gun_asiri_islem_dersini_getirir():
    """Boş günde işlem üretme dürtüsü en pahalı alışkanlık."""
    assert e.baglamsal_ders({"sinyal_yok": True})["kod"] == "d1004"


def test_eslesen_ders_gercekten_var():
    """Kural tablosundaki her kod müfredatta bulunmalı."""
    for _, kod, _ in e._BAGLAM_KURALLARI:
        assert kod in DERS_HARITA, f"{kod} müfredatta yok"


def test_kirilim_sinyali_retest_dersini_getirir():
    """Kırılım sinyali olan gün, sorulacak soru 'ne zaman alacağım'dır."""
    assert e.baglamsal_ders({"kirilim_sinyali": True})["kod"] == "d1308"


def test_derslerin_sorulari_gercekten_var():
    """Ders var olmayan bir soru koduna işaret ederse CLI kullanıcıya
    bulunmayan bir kod gösterir ve o kod okunmuş sayılır."""
    from cekirdek.egitmen_sorular import TUM_SORULAR
    kodlar = {q.kod for q in TUM_SORULAR}
    for d in DERS_HARITA.values():
        for k in d.sorular:
            assert k in kodlar, f"{d.kod} -> {k} soru bankasında yok"


# ── her zaman bir cevap ────────────────────────────────────────────────────

def test_ozel_durum_yoksa_mufredattan_devam():
    r = e.baglamsal_ders({})
    assert r is not None
    assert r["tetikleyen"] is None


def test_bos_durumda_bile_ders_doner():
    assert e.baglamsal_ders({"karantina": False, "yogunlasma": False}) is not None


# ── öncelik ────────────────────────────────────────────────────────────────

def test_birden_cok_durumda_en_ozgul_kazanir():
    """Sıra tablodaki sıradır: karantina, reel getiriden önce gelir."""
    r = e.baglamsal_ders({"karantina": True, "reel_negatif": True})
    assert r["kod"] == "d1202"


def test_neden_alani_bos_olmaz():
    """Ders tek başına yetmez; bugün NEDEN bu ders, söylenmeli."""
    for d in ({"karantina": True}, {"yogunlasma": True}, {}):
        assert len(e.baglamsal_ders(d)["neden"]) > 20


# ── okunmuş ders ───────────────────────────────────────────────────────────

def test_okunmus_ders_tekrar_isaretlenir():
    okundu = {"d1202": e.DersKaydi(kod="d1202", okundu=True)}
    r = e.baglamsal_ders({"karantina": True}, okundu)
    assert r["kod"] == "d1202"
    assert r["tekrar"] is True


def test_okunmamis_ders_tekrar_degil():
    assert e.baglamsal_ders({"karantina": True})["tekrar"] is False


# ── durum çıkarımı ─────────────────────────────────────────────────────────

def test_karantinali_strateji_durumu_tetikler():
    d = e.gunun_durumu(tarama={"strateji_durumlari": {
        "trend": {"onerilir": False}, "tepki": {"onerilir": True}}})
    assert d["karantina"] is True


def test_hepsi_onerilirse_karantina_yok():
    d = e.gunun_durumu(tarama={"strateji_durumlari": {
        "trend": {"onerilir": True}, "tepki": {"onerilir": True}}})
    assert d["karantina"] is False


def test_zayif_cesitlendirme_tetikler():
    d = e.gunun_durumu(tarama={"yogunlasma": {
        "yeterli_mi": True, "adet": 4, "bagimsiz_bahis": 1.2}})
    assert d["yogunlasma"] is True


def test_iyi_cesitlendirme_tetiklemez():
    d = e.gunun_durumu(tarama={"yogunlasma": {
        "yeterli_mi": True, "adet": 4, "bagimsiz_bahis": 3.5}})
    assert d["yogunlasma"] is False


def test_kirilim_sinyali_ozetten_okunur():
    """Strateji adı `cekirdek/strateji.py` ile aynı yazılmalı; sessizce
    kayarsa ders hiç tetiklenmez ve kimse fark etmez."""
    ozet = {"sinyal_veren": [{"sembol": "X", "sinyaller": ["tepki"]},
                             {"sembol": "Y", "sinyaller": ["kirilim"]}]}
    assert e.gunun_durumu(ozet=ozet)["kirilim_sinyali"] is True


def test_kirilim_yoksa_tetiklenmez():
    ozet = {"sinyal_veren": [{"sembol": "X", "sinyaller": ["trend"]}]}
    assert e.gunun_durumu(ozet=ozet)["kirilim_sinyali"] is False


def test_sinyalsiz_gunde_kirilim_yok():
    assert e.gunun_durumu(ozet={})["kirilim_sinyali"] is False


def test_reel_getiri_ozetten_okunur():
    assert e.gunun_durumu(ozet={"bist_reel_1y": -5.65})["reel_negatif"] is True
    assert e.gunun_durumu(ozet={"bist_reel_1y": 3.2})["reel_negatif"] is False


def test_eksik_veri_cokme_uretmez():
    d = e.gunun_durumu()
    assert isinstance(d, dict) and "karantina" in d
