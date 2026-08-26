"""API anahtar kapısı — AĞ ve SUNUCU GEREKTİRMEZ.

Kapı iki şeyi aynı anda yapmak zorunda:

  KORUMA  — anahtarsız istek uçlara ulaşmamalı; bulutta açık bir API'nin
            bütün uçları herkese açıktır.
  GEÇİRME — tarayıcının CORS ön kontrolü (OPTIONS) tanım gereği özel başlık
            TAŞIMAZ. Onu 401'lersek tarayıcı asıl isteği hiç yapmaz ve web
            istemcisi "sunucuya bağlanılamıyor" der. 2026-08-25'te tam bu
            yaşandı: curl çalışıyordu, tarayıcı çalışmıyordu.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

ANAHTAR = "test-anahtari-123"


@pytest.fixture
def istemci(monkeypatch):
    """Anahtar ZORUNLU bir sunucu örneği kurar."""
    monkeypatch.setenv("MIDAS_API_ANAHTARI", ANAHTAR)
    import api.main as m
    importlib.reload(m)          # _ANAHTAR modül yüklenirken okunuyor
    # Açılışta 100 hisse indirmesin.
    monkeypatch.setattr(m.onbellek, "arka_planda_isit", lambda *a, **k: None)
    monkeypatch.setattr(m.onbellek, "periyodik", lambda *a, **k: None)
    with TestClient(m.app) as c:
        yield c


# ── geçirme: tarayıcı ön kontrolü ──────────────────────────────────────────

def test_cors_on_kontrolu_401_almaz(istemci):
    """Ön kontrol reddedilirse tarayıcı asıl isteği HİÇ yapmaz."""
    c = istemci.options("/tarama", headers={
        "Origin": "http://localhost:8899",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-api-anahtar",
    })
    assert c.status_code != 401, "ön kontrol 401 aldı — web istemcisi bağlanamaz"
    assert c.status_code < 400


def test_on_kontrol_izin_basligi_doner(istemci):
    c = istemci.options("/tarama", headers={
        "Origin": "http://localhost:8899",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-api-anahtar",
    })
    assert "access-control-allow-origin" in {k.lower() for k in c.headers}


# ── koruma: anahtarsız gerçek istek geçmemeli ──────────────────────────────

def test_anahtarsiz_istek_reddedilir(istemci):
    assert istemci.get("/risk?sermaye=1000").status_code == 401


def test_yanlis_anahtar_reddedilir(istemci):
    r = istemci.get("/risk?sermaye=1000", headers={"X-API-Anahtar": "yanlis"})
    assert r.status_code == 401


def test_dogru_anahtar_gecer(istemci):
    r = istemci.get("/risk?sermaye=1000", headers={"X-API-Anahtar": ANAHTAR})
    assert r.status_code == 200


def test_saglik_anahtarsiz_acik(istemci):
    """Sağlık ucu açık kalmalı: izleme ve dağıtım betiği anahtarsız sorar."""
    r = istemci.get("/saglik")
    assert r.status_code == 200
    assert r.json()["anahtar_gerekli"] is True


def test_on_kontrol_gecse_de_asil_istek_korunur(istemci):
    """Ön kontrolü geçirmek kapıyı açmak değildir."""
    istemci.options("/risk", headers={
        "Origin": "http://localhost:8899",
        "Access-Control-Request-Method": "GET"})
    assert istemci.get("/risk?sermaye=1000").status_code == 401
