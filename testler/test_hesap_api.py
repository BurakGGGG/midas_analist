"""Hesap uçları — AĞ GEREKTİRMEZ, gerçek veritabanına DOKUNMAZ.

Bu dosyanın ayrı olmasının sebebi: cekirdek/test_hesap.py mantığı sınıyor,
burası HTTP sözleşmesini. İkisi ayrışabilir — çekirdek doğru çalışırken uç
yanlış durum kodu döndürebilir ya da jetonu hiç okumayabilir.

En kritik test `test_api_anahtari_hesap_uclarini_da_koruyor`: kayıt ucu
anahtar kapısının dışında kalsaydı, sunucunun adresini bilen herkes hesap
açabilirdi.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import importlib

import pytest
from fastapi.testclient import TestClient


ANAHTAR = "test-anahtari-123"


@pytest.fixture
def gecici_db(tmp_path, monkeypatch):
    """Hesap tabloları gerçek ambar.db'ye yazılmasın."""
    from cekirdek import ambar
    monkeypatch.setattr(ambar, "VERITABANI", tmp_path / "test_ambar.db")


@pytest.fixture
def istemci(gecici_db, monkeypatch):
    import api.main as m
    monkeypatch.setattr(m, "_ANAHTAR", "")
    monkeypatch.setattr(m.onbellek, "arka_planda_isit", lambda *a, **k: None)
    monkeypatch.setattr(m.onbellek, "periyodik", lambda *a, **k: None)
    with TestClient(m.app) as c:
        yield c


def _kayit(c, eposta="burak@ornek.com", parola="parola1234"):
    r = c.post("/hesap/kayit",
               json={"eposta": eposta, "parola": parola, "cihaz": "test"})
    assert r.status_code == 200, r.text
    return r.json()


def _bas(jeton: str) -> dict:
    return {"Authorization": f"Bearer {jeton}"}


# ── kayıt ve giriş ─────────────────────────────────────────────────────────

def test_kayit_jeton_doner(istemci):
    o = _kayit(istemci)
    assert o["jeton"] and o["eposta"] == "burak@ornek.com"


def test_ayni_eposta_ikinci_kez_400(istemci):
    _kayit(istemci)
    r = istemci.post("/hesap/kayit",
                     json={"eposta": "burak@ornek.com", "parola": "parola1234"})
    assert r.status_code == 400


def test_kisa_parola_400(istemci):
    r = istemci.post("/hesap/kayit",
                     json={"eposta": "a@b.com", "parola": "kisa"})
    assert r.status_code == 400


def test_yanlis_parolayla_giris_400(istemci):
    _kayit(istemci)
    r = istemci.post("/hesap/giris",
                     json={"eposta": "burak@ornek.com", "parola": "yanlis"})
    assert r.status_code == 400


def test_dogru_parolayla_giris_gecer(istemci):
    _kayit(istemci)
    r = istemci.post("/hesap/giris",
                     json={"eposta": "burak@ornek.com", "parola": "parola1234"})
    assert r.status_code == 200 and r.json()["jeton"]


# ── jeton kapısı ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("yol", ["/hesap", "/yedek"])
def test_jetonsuz_istek_401(istemci, yol):
    assert istemci.get(yol).status_code == 401


@pytest.mark.parametrize("baslik", [
    {"Authorization": "Bearer uydurma-jeton"},
    {"Authorization": "jetonsuz"},
    {"Authorization": "Bearer "},
])
def test_bozuk_jeton_401(istemci, baslik):
    assert istemci.get("/hesap", headers=baslik).status_code == 401


def test_cikistan_sonra_jeton_gecersiz(istemci):
    o = _kayit(istemci)
    assert istemci.post("/hesap/cikis", headers=_bas(o["jeton"])).json()["dustu"]
    assert istemci.get("/hesap", headers=_bas(o["jeton"])).status_code == 401


def test_hesap_bilgisi_parola_sizdirmaz(istemci):
    o = _kayit(istemci)
    g = istemci.get("/hesap", headers=_bas(o["jeton"])).json()
    assert "parola" not in str(g) and "tuz" not in str(g)


# ── yedek ──────────────────────────────────────────────────────────────────

def test_yedek_gidip_geliyor(istemci):
    o = _kayit(istemci)
    veri = {"pozisyonlar": [{"sembol": "THYAO", "adet": 3}],
            "ayarlar": {"sermaye": 1000}}
    r = istemci.put("/yedek", headers=_bas(o["jeton"]),
                    json={"icerik": veri, "cihaz": "telefon"})
    assert r.json()["yazildi"] and r.json()["surum"] == 1

    g = istemci.get("/yedek", headers=_bas(o["jeton"])).json()
    assert g["var"] is True and g["icerik"] == veri


def test_yedek_yokken_var_false(istemci):
    o = _kayit(istemci)
    assert istemci.get("/yedek", headers=_bas(o["jeton"])).json() == {"var": False}


def test_eski_surum_yeniyi_ezemez(istemci):
    o = _kayit(istemci)
    h = _bas(o["jeton"])
    istemci.put("/yedek", headers=h, json={"icerik": {"n": 1}})
    istemci.put("/yedek", headers=h, json={"icerik": {"n": 2}})

    r = istemci.put("/yedek", headers=h,
                    json={"icerik": {"n": "eski"}, "beklenen_surum": 1}).json()
    assert r["yazildi"] is False and r["cakisma"] is True
    assert r["sunucudaki"]["icerik"] == {"n": 2}
    assert istemci.get("/yedek", headers=h).json()["icerik"] == {"n": 2}


def test_kullanicilar_birbirinin_yedegini_gormez(istemci):
    a = _kayit(istemci, "a@ornek.com")
    b = _kayit(istemci, "b@ornek.com")
    istemci.put("/yedek", headers=_bas(a["jeton"]), json={"icerik": {"kim": "a"}})
    assert istemci.get("/yedek", headers=_bas(b["jeton"])).json()["var"] is False


# ── parola değiştirme ──────────────────────────────────────────────────────

def test_parola_degisince_jeton_duser(istemci):
    o = _kayit(istemci)
    r = istemci.post("/hesap/parola", headers=_bas(o["jeton"]),
                     json={"eski": "parola1234", "yeni": "yeniparola99"})
    assert r.json()["yeniden_giris_gerekli"] is True
    assert istemci.get("/hesap", headers=_bas(o["jeton"])).status_code == 401


# ── API anahtarı kapısı ────────────────────────────────────────────────────

def test_api_anahtari_hesap_uclarini_da_koruyor(gecici_db, monkeypatch):
    """Kayıt ucu kapının dışında kalsaydı, sunucu adresini bilen herkes
    hesap açabilirdi."""
    monkeypatch.setenv("MIDAS_API_ANAHTARI", ANAHTAR)
    import api.main as m
    importlib.reload(m)
    monkeypatch.setattr(m.onbellek, "arka_planda_isit", lambda *a, **k: None)
    monkeypatch.setattr(m.onbellek, "periyodik", lambda *a, **k: None)
    with TestClient(m.app) as c:
        govde = {"eposta": "sizinti@ornek.com", "parola": "parola1234"}
        assert c.post("/hesap/kayit", json=govde).status_code == 401
        assert c.get("/yedek").status_code == 401
        r = c.post("/hesap/kayit", json=govde,
                   headers={"X-API-Anahtar": ANAHTAR})
        assert r.status_code == 200
    importlib.reload(m)          # sonraki testler anahtarsız sunucu görsün
