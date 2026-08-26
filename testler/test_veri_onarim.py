"""Fiyat onarımı bayrağı — AĞ ERİŞİMİ GEREKTİRMEZ.

yfinance'in repair=True'su kaçırılmış bedelsiz/bölünmeleri düzeltir ve
scikit-learn ister. Tehlike, bayrağın YANLIŞ sebeple kapanmasıdır:

  Boş sonuç == sklearn yok  DEĞİLDİR.
  Boş sonuç çoğu zaman hissenin borsadan çıkmış olması demektir.

BIST 100 listesinde borsadan çıkmış kodlar bulunuyor. Eski kod bunlardan
birini görünce onarımı TÜM çalıştırma için kapatıyordu; geri kalan ~96 hisse
onarımsız iniyor ve düzeltilmiş sayılan sahte çöküşler geri geliyordu.
Sessiz olduğu için de kimse fark etmiyordu.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import importlib

import pandas as pd
import pytest

from cekirdek import veri


BOS = pd.DataFrame()
DOLU = pd.DataFrame({
    "Open": [10.0, 11.0], "High": [11.0, 12.0], "Low": [9.0, 10.0],
    "Close": [10.5, 11.5], "Volume": [1000, 1100]},
    index=pd.to_datetime(["2026-08-24", "2026-08-25"]))


def test_sklearn_varsa_onarim_acik():
    """Ortamda sklearn var; bayrak açık başlamalı."""
    assert veri._onarim_mumkun_mu() is True
    assert veri._ONARIM is True


def test_bayrak_sklearn_varligindan_turetilir(monkeypatch):
    """Tespit tahminle değil, doğrudan sorguyla yapılmalı."""
    import importlib.util
    monkeypatch.setattr(importlib.util, "find_spec", lambda ad: None)
    assert veri._onarim_mumkun_mu() is False


def test_bos_sonuc_onarimi_kapatmaz(monkeypatch, tmp_path):
    """Borsadan çıkmış kod, onarımı diğer hisseler için kapatmamalı."""
    monkeypatch.setattr(veri, "ONBELLEK", tmp_path)

    class SahteTicker:
        def __init__(self, kod): self.kod = kod
        def history(self, **kw): return BOS

    monkeypatch.setattr(veri.yf, "Ticker", SahteTicker)
    onceki = veri._ONARIM
    veri.fiyat_cek("BORSADAN_CIKMIS.IS", gun=30, onbellek_saat=0)
    assert veri._ONARIM == onceki, "boş sonuç onarım bayrağını kapattı"


def test_bos_sonucta_onarimsiz_tekrar_denenir(monkeypatch, tmp_path):
    """Onarımlı çağrı boş dönerse, o çağrı için onarımsız denenmeli."""
    monkeypatch.setattr(veri, "ONBELLEK", tmp_path)
    cagrilar = []

    class SahteTicker:
        def __init__(self, kod): pass
        def history(self, **kw):
            cagrilar.append(kw.get("repair"))
            return BOS if kw.get("repair") else DOLU

    monkeypatch.setattr(veri.yf, "Ticker", SahteTicker)
    d = veri.fiyat_cek("XYZ.IS", gun=30, onbellek_saat=0)
    assert True in cagrilar and False in cagrilar, f"denenen: {cagrilar}"
    assert not d.empty


def test_onarim_bayragi_modul_yuklenirken_belirlenir():
    """Bayrak çalışma sırasında değil, yüklenirken saptanmalı —
    böylece bir hissenin durumu diğerlerini etkilemez."""
    kaynak = importlib.import_module("cekirdek.veri")
    assert isinstance(kaynak._ONARIM, bool)
