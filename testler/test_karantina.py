"""Strateji karantinası — AĞ ve VERİTABANI GEREKTİRMEZ.

Karantinanın amacı stratejiyi KAPATMAK değil, ÖNERMEYİ durdurmaktır.
Fark önemli: kapatılan strateji hakkında yeni kanıt birikmez, karantina
kalıcı hapse dönüşür ve strateji düzelse bile bunu kimse göremez.

İki hata da pahalı:
  ERKEN HÜKÜM  — 1-2 aylık veriyle strateji damgalamak gürültüyü kanıt saymak.
  GEÇ HÜKÜM    — bozulmuş bir stratejiyi önermeye devam etmek gerçek para.

Eşik strateji ADINA değil VERİYE bağlı olmalı: bozulan kendiliğinden girer,
düzelen kendiliğinden çıkar.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import ogrenme as o


@pytest.fixture
def sinifla(monkeypatch):
    """Sahte canlı sicille strateji_siniflari çalıştırır."""
    def kur(kazanma, ay=4, sinyal=200, strateji="trend"):
        monkeypatch.setattr(o.ambar, "sinyal_karnesi",
                            lambda gun, strateji=None, yol=None: {
                                "sinyal": sinyal, "kazanma_orani": kazanma,
                                "ort_kazanc": 5.0, "ort_kayip": -4.0})
        monkeypatch.setattr(o, "_canli_ay_sayisi", lambda *a, **k: ay)
        return o.strateji_siniflari()[strateji]
    return kur


# ── sınıflandırma ──────────────────────────────────────────────────────────

def test_alt_sinirin_altinda_karantina(sinifla):
    r = sinifla(kazanma=20.0)
    assert r["sinif"] == "karantina"
    assert r["onerilir"] is False


def test_normal_sonuc_onerilir(sinifla):
    r = sinifla(kazanma=55.0)
    assert r["sinif"] == "normal"
    assert r["onerilir"] is True


def test_alt_ceyrekle_alt_sinir_arasi_izlemede(sinifla):
    """Zayıf ama karantinalık değil — önerilir, ama işaretli."""
    aralik = o.beklenen_aralik("trend", 4)
    orta = (aralik["alt"] + aralik["dusuk_ceyrek"]) / 2
    r = sinifla(kazanma=orta)
    assert r["sinif"] == "izlemede"
    assert r["onerilir"] is True


# ── erken hüküm vermeme ────────────────────────────────────────────────────

def test_tek_ay_ile_karantina_verilmez(sinifla):
    """Bir ay tek gözlemdir; sinyal sayısı ne olursa olsun."""
    r = sinifla(kazanma=5.0, ay=1, sinyal=900)
    assert r["sinif"] == "hüküm_yok"
    assert r["onerilir"] is True


def test_az_sinyalle_karantina_verilmez(sinifla):
    r = sinifla(kazanma=5.0, ay=4, sinyal=10)
    assert r["sinif"] == "hüküm_yok"
    assert r["onerilir"] is True


def test_hukum_yok_durumunda_oneri_engellenmez(sinifla):
    """Veri yokluğu suç değildir — yeni strateji baştan cezalandırılmamalı."""
    assert sinifla(kazanma=None, ay=0, sinyal=0)["onerilir"] is True


# ── karantina kalıcı olmamalı ──────────────────────────────────────────────

def test_duzelen_strateji_karantinadan_cikar(sinifla):
    """Kural veriye bağlı: aynı strateji, iyi sicille normale döner."""
    assert sinifla(kazanma=20.0)["sinif"] == "karantina"
    assert sinifla(kazanma=55.0)["sinif"] == "normal"


def test_karantina_strateji_adina_bagli_degil(sinifla):
    """Karantina kararı VERİYE bağlı; hiçbir AÇIK strateji ismen yasaklı
    olmamalı.

    Kapatılan stratejiler bunun dışında: kapatma karantina mekanizması
    değil, ölçüme dayanan ayrı ve kalıcı bir karar (bkz.
    test_strateji_kapisi.py). İkisini karıştırmamak önemli — karantina
    kendiliğinden girilip çıkılan geçici bir hâl."""
    from cekirdek.strateji import aktif_stratejiler
    acik = set(aktif_stratejiler())
    for st in o.BACKTEST_AYLIK:
        if st not in acik:
            continue
        assert sinifla(kazanma=60.0, strateji=st)["sinif"] == "normal"


def test_kapali_strateji_KAPALI_diye_isaretlenir(sinifla):
    """Kapalı stratejiyi "karantina" diye göstermek yanıltıcı olurdu:
    karantina geçici ve veriye bağlı, kapatma kalıcı bir karar."""
    from cekirdek.strateji import STRATEJILER
    kapali = [a for a, x in STRATEJILER.items() if not x.aktif]
    if not kapali:
        pytest.skip("kapalı strateji yok")
    for st in kapali:
        if st not in o.BACKTEST_AYLIK:
            continue
        r = sinifla(kazanma=90.0, strateji=st)
        assert r["sinif"] == "kapalı"
        assert r["onerilir"] is False
        assert r["aktif"] is False
        assert "KAPATILDI" in r["gerekce"]


def test_kapatma_yuksek_canli_oranla_bile_degismez(sinifla):
    """Kapatma kararı 1250 günlük ölçüme dayanıyor; birkaç iyi canlı
    sinyal onu geri almamalı. Geri alma bilinçli bir karar olmalı."""
    from cekirdek.strateji import STRATEJILER
    kapali = [a for a, x in STRATEJILER.items()
              if not x.aktif and a in o.BACKTEST_AYLIK]
    if not kapali:
        pytest.skip("kapalı strateji yok")
    assert sinifla(kazanma=95.0, strateji=kapali[0])["sinif"] == "kapalı"


def test_gerekce_sayilarla_aciklanir(sinifla):
    """Hüküm tek başına yetmez; kullanıcı neden olduğunu görmeli."""
    r = sinifla(kazanma=20.0)
    assert "%" in r["gerekce"]
    assert r["aralik"]["yeterli_mi"]


def test_tum_stratejiler_siniflanir():
    """Gerçek ambarla çalışırken hiçbir strateji listeden düşmemeli."""
    s = o.strateji_siniflari()
    assert set(s) == set(o.BACKTEST_AYLIK)
    for d in s.values():
        assert d["sinif"] in ("normal", "izlemede", "karantina",
                              "hüküm_yok", "kapalı")
        assert isinstance(d["onerilir"], bool)
