"""Karar günlüğü — AĞ ERİŞİMİ GEREKTİRMEZ.

Sistem 769 sinyalini ölçüyor; bu defter KULLANICININ kararlarını ölçer.
Ölçülmek istenen şey aradaki fark: sistem 7 sinyal üretiyor, kullanıcı
2'sini alıyor — beceri o seçimde.

Üç şey kilitlenir:

  DEĞİŞTİRİLEMEZLİK  — satış alımı silmez, günlük yalnızca büyür.
                       "Ben zaten biliyordum" demeyi imkânsız kılan şey.
  KARAR ANI          — sistemin ne dediği alım anında donar, sonradan
                       sorgulanmaz. Sonradan bakınca sistem hep haklı
                       görünür.
  TAZELİK            — aylar önceki bir sinyal bugünkü alımı "sinyalli"
                       yapmaz; yoksa takip oranı ölçümü çöpe döner.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
from datetime import date, timedelta

import pytest

from cekirdek import ambar, defter


@pytest.fixture
def db(monkeypatch, tmp_path):
    """Temiz ambar — üretim veritabanına dokunulmaz."""
    yol = tmp_path / "ambar.db"
    monkeypatch.setattr(ambar, "VERITABANI", yol)
    ambar.kur()
    return yol


def _sinyal(db, sembol, gun=None, strateji="trend", skor=70.0,
            stop=90.0, hedef=120.0):
    gun = gun or date.today().isoformat()
    with ambar.baglan() as con:
        con.execute("""INSERT OR REPLACE INTO sinyal
            (tarih,sembol,strateji,skor,fiyat,stop,hedef,alinabilir)
            VALUES (?,?,?,?,?,?,?,1)""",
            (gun, sembol, strateji, skor, 100.0, stop, hedef))


# ── temel akış ─────────────────────────────────────────────────────────────

def test_alim_kaydedilir(db):
    defter.alim("THYAO", 100.0, 2)
    p = defter.acik_pozisyonlar()
    assert len(p) == 1 and p[0]["adet"] == 2


def test_satim_pozisyonu_kapatir(db):
    defter.alim("THYAO", 100.0, 2)
    defter.satim("THYAO", 110.0)
    assert defter.acik_pozisyonlar() == []


def test_kismi_satim_kalani_birakir(db):
    defter.alim("THYAO", 100.0, 5)
    defter.satim("THYAO", 110.0, 2)
    assert defter.acik_pozisyonlar()[0]["adet"] == 3


def test_getiri_dogru_hesaplanir(db):
    defter.alim("THYAO", 100.0, 1)
    assert defter.satim("THYAO", 115.0)["getiri"] == pytest.approx(15.0)


def test_acik_pozisyon_yokken_satilamaz(db):
    assert "hata" in defter.satim("THYAO", 100.0)


def test_fifo_ile_eslesir(db):
    """Önce alınan önce satılır — ortalama maliyet değil FIFO."""
    defter.alim("THYAO", 100.0, 1)
    defter.alim("THYAO", 200.0, 1)
    defter.satim("THYAO", 110.0, 1)
    k = defter.kapali_islemler()
    assert len(k) == 1 and k[0]["giris"] == 100.0
    assert defter.acik_pozisyonlar()[0]["giris"] == 200.0


# ── değiştirilemezlik ──────────────────────────────────────────────────────

def test_satis_alimi_silmez(db):
    """Günlük yalnızca büyür; geçmiş yeniden yazılamaz."""
    defter.alim("THYAO", 100.0, 1)
    defter.satim("THYAO", 110.0)
    with ambar.baglan() as con:
        n = con.execute("SELECT COUNT(*) n FROM karar").fetchone()["n"]
    assert n == 2


def test_kapanan_islem_kayitli_kalir(db):
    defter.alim("THYAO", 100.0, 1)
    defter.satim("THYAO", 90.0)
    k = defter.kapali_islemler()
    assert len(k) == 1 and k[0]["getiri"] == pytest.approx(-10.0)


# ── karar anı dondurulur ───────────────────────────────────────────────────

def test_sinyalli_alim_isaretlenir(db):
    _sinyal(db, "THYAO")
    defter.alim("THYAO", 100.0)
    assert defter.karne()["sinyalli_alim"] == 1


def test_sinyalsiz_alim_kendi_fikri_sayilir(db):
    defter.alim("THYAO", 100.0)
    d = defter.karne()
    assert d["sinyalli_alim"] == 0
    assert d["sistem_takip_orani"] == 0.0


def test_eski_sinyal_taze_sayilmaz(db):
    """Aylar önceki sinyal bugünkü alımı 'sinyalli' yapmamalı — yoksa
    her hisse bir gün sinyal verdiği için takip oranı hep %100 çıkar."""
    eski = (date.today() - timedelta(days=60)).isoformat()
    _sinyal(db, "THYAO", gun=eski)
    defter.alim("THYAO", 100.0)
    assert defter.karne()["sinyalli_alim"] == 0


def test_taze_pencere_icindeki_sinyal_sayilir(db):
    dun = (date.today() - timedelta(days=1)).isoformat()
    _sinyal(db, "THYAO", gun=dun)
    defter.alim("THYAO", 100.0)
    assert defter.karne()["sinyalli_alim"] == 1


def test_karantinali_strateji_kaydedilir(db, monkeypatch):
    from cekirdek import ogrenme
    _sinyal(db, "THYAO", strateji="kirilim")
    monkeypatch.setattr(ogrenme, "strateji_siniflari",
                        lambda *a, **k: {"kirilim": {"onerilir": False}})
    defter.alim("THYAO", 100.0)
    assert defter.karne()["karantinali_alim"] == 1


# ── karne ──────────────────────────────────────────────────────────────────

def test_bos_defter_yonlendirir(db):
    assert "not" in defter.karne()


def test_kazanma_orani_hesaplanir(db):
    for f, c in ((100, 110), (100, 90), (100, 120)):
        defter.alim("A", f, 1); defter.satim("A", c)
    d = defter.karne()
    assert d["kapanan"] == 3
    assert d["kazanma_orani"] == pytest.approx(66.7, abs=0.1)


def test_sinyalli_ve_kendi_fikri_ayri_olculur(db):
    """Seçim becerisi buradan görünür: sistemi takip ettiğinde mi yoksa
    kendi fikrinle mi daha iyisin?"""
    _sinyal(db, "SINYALLI")
    defter.alim("SINYALLI", 100.0); defter.satim("SINYALLI", 120.0)
    defter.alim("KENDI", 100.0); defter.satim("KENDI", 80.0)
    d = defter.karne()
    assert d["sinyalli"]["ortalama"] == pytest.approx(20.0)
    assert d["kendi_fikrin"]["ortalama"] == pytest.approx(-20.0)


def test_az_ornekte_uyari_verilir(db):
    """Sistemin sicilinde uygulanan dürüstlük burada da geçerli."""
    defter.alim("A", 100.0); defter.satim("A", 110.0)
    assert "uyari" in defter.karne()


def test_stop_disiplini_olculur(db):
    """Stopun altında kapanan işlem, stopa uyulmadığını gösterir."""
    _sinyal(db, "THYAO", stop=95.0)
    defter.alim("THYAO", 100.0, stop=95.0)
    defter.satim("THYAO", 90.0)          # stopun ALTINDA çıkış
    sd = defter.karne()["stop_disiplini"]
    assert sd["stopun_altinda_kapanan"] == 1


def test_stopa_uyulunca_disiplin_temiz(db):
    defter.alim("THYAO", 100.0, stop=95.0)
    defter.satim("THYAO", 95.0)
    assert defter.karne()["stop_disiplini"]["stopun_altinda_kapanan"] == 0


# ── kağıt / gerçek ayrımı ──────────────────────────────────────────────────

def test_varsayilan_kagit_uzerinde(db):
    """Gerçek para açıkça belirtilmeli; kaza ile gerçek kayıt olmasın."""
    defter.alim("THYAO", 100.0)
    assert defter.acik_pozisyonlar()[0]["kagit"] == 1


def test_gercek_para_ayri_suzulebilir(db):
    defter.alim("KAGIT", 100.0, kagit=True)
    defter.alim("GERCEK", 100.0, kagit=False)
    assert len(defter.acik_pozisyonlar(kagit=False)) == 1
    assert defter.acik_pozisyonlar(kagit=False)[0]["sembol"] == "GERCEK"


# ── API yazma uçları ───────────────────────────────────────────────────────

@pytest.fixture
def istemci(db, monkeypatch):
    """Defter uçlarını gerçek HTTP üzerinden sınar."""
    import importlib
    monkeypatch.setenv("MIDAS_API_ANAHTARI", "")
    from fastapi.testclient import TestClient
    import api.main as m
    importlib.reload(m)
    monkeypatch.setattr(m.onbellek, "arka_planda_isit", lambda *a, **k: None)
    monkeypatch.setattr(m.onbellek, "periyodik", lambda *a, **k: None)
    monkeypatch.setattr(m, "guvenli", m.guvenli)
    with TestClient(m.app) as c:
        yield c


def test_api_alim_kaydeder(istemci):
    r = istemci.post("/defter/alim",
                     json={"sembol": "THYAO", "fiyat": 100.0, "adet": 2})
    assert r.status_code == 200
    assert r.json()["acik"][0]["adet"] == 2


def test_api_satim_getiri_doner(istemci):
    istemci.post("/defter/alim", json={"sembol": "THYAO", "fiyat": 100.0})
    r = istemci.post("/defter/satim", json={"sembol": "THYAO", "fiyat": 110.0})
    assert r.json()["karar"]["getiri"] == pytest.approx(10.0)


def test_api_olmayan_pozisyon_satilamaz(istemci):
    """Sessizce başarılı dönerse telefon pozisyonu kapattığını sanır."""
    assert istemci.post("/defter/satim",
                        json={"sembol": "XXXX", "fiyat": 10.0}).status_code == 400


def test_api_stopla_alim_izlemeyi_baslatir(istemci, monkeypatch, tmp_path):
    from cekirdek import izleme
    monkeypatch.setattr(izleme, "DOSYA", tmp_path / "izleme.json")
    istemci.post("/defter/alim",
                 json={"sembol": "THYAO", "fiyat": 100.0, "stop": 95.0})
    assert [p["sembol"] for p in izleme.liste()] == ["THYAO"]


def test_api_satim_izlemeyi_kapatir(istemci, monkeypatch, tmp_path):
    from cekirdek import izleme
    monkeypatch.setattr(izleme, "DOSYA", tmp_path / "izleme.json")
    istemci.post("/defter/alim",
                 json={"sembol": "THYAO", "fiyat": 100.0, "stop": 95.0})
    istemci.post("/defter/satim", json={"sembol": "THYAO", "fiyat": 110.0})
    assert izleme.liste() == []


def test_api_defter_okur(istemci):
    istemci.post("/defter/alim", json={"sembol": "THYAO", "fiyat": 100.0})
    d = istemci.get("/defter").json()
    assert d["karne"]["alim_sayisi"] == 1
    assert len(d["acik"]) == 1
