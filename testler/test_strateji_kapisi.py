"""Strateji kapıları ve kapatılan strateji.

Bu dosya 29 Ağustos 2026'da yapılan iki kararı koruyor. İkisi de
1250 günlük veri üzerinde, GELİŞTİRME ve DOKUNULMAZ dönem ayrı ayrı
ölçülerek verildi — tek dönemde iyi görünen bir eşik reddedilirdi.

  1. Kırılıma göreceli güç kapısı (GG60 >= 10)
       geliştirme  PF 1,60 -> 2,43 · getiri  %58 -> %112
       DOKUNULMAZ  PF 1,26 -> 1,90 · getiri  %19 -> %57

  2. `tepki` kapatıldı — iki dönemde de para kaybetti
       geliştirme  PF 0,89 · getiri  -%8,3
       DOKUNULMAZ  PF 0,66 · getiri -%21,5

Buradaki testlerin işi, bu kararların sessizce geri alınmasını
engellemek: biri kapıyı kaldırırsa ya da kapalı stratejiyi yeniden
sinyal üretir hale getirirse test kırılır.
"""
import numpy as np
import pandas as pd
import pytest

from cekirdek import strateji as st
from cekirdek.strateji import STRATEJILER, aktif_stratejiler, skorla


def _cerceve(n=300, gg60=50.0, kirilim_var=True):
    """Kırılım koşullarını sağlayan yapay seri."""
    kapanis = np.linspace(100, 160, n)
    g = pd.DataFrame({
        "Open": kapanis * 0.99, "High": kapanis * 1.01,
        "Low": kapanis * 0.98, "Close": kapanis,
        "Volume": np.full(n, 1e6),
        "SMA200": kapanis * 0.85,
        "EMA10": kapanis * 0.99, "EMA20": kapanis * 0.98,
        "EMA50": kapanis * 0.95,
        "ADX14": np.full(n, 30.0), "RSI14": np.full(n, 55.0),
        "RSI2": np.full(n, 50.0), "BB_konum": np.full(n, 0.5),
        "ATR14": kapanis * 0.02, "ATR_yuzde": np.full(n, 2.5),
        "Hacim_orani": np.full(n, 2.0),
        "TL_hacim_ort20": np.full(n, 5e7),
        "GG60": np.full(n, gg60), "GG20": np.full(n, 5.0),
        "Getiri_20g": np.full(n, 5.0),
        "DON_ust": kapanis * (0.99 if kirilim_var else 1.05),
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))
    return g


# ── kırılım: göreceli güç kapısı ──────────────────────────────────────────

def test_kirilim_endeksi_gecmeyen_hisseyi_ALMAZ():
    """Zirveyi kıran ama endeksin gerisinde kalan hisse, kırılımını
    çoğunlukla geri veriyor."""
    zayif = _cerceve(gg60=st.KIRILIM_ASGARI_GG60 - 1)
    assert not bool(STRATEJILER["kirilim"].giris(zayif).iloc[-1])


def test_kirilim_endeksi_gecen_hisseyi_ALIR():
    guclu = _cerceve(gg60=st.KIRILIM_ASGARI_GG60 + 1)
    assert bool(STRATEJILER["kirilim"].giris(guclu).iloc[-1])


def test_kirilim_esigi_TAM_sinirda_gecer():
    tam = _cerceve(gg60=st.KIRILIM_ASGARI_GG60)
    assert bool(STRATEJILER["kirilim"].giris(tam).iloc[-1])


def test_gucluyken_bile_kirilim_yoksa_sinyal_yok():
    """Kapı bir EK koşul; tek başına sinyal üretmemeli."""
    g = _cerceve(gg60=99.0, kirilim_var=False)
    assert not bool(STRATEJILER["kirilim"].giris(g).iloc[-1])


def test_esik_makul_araligta():
    """Eşiği 0'a indirmek kapıyı kaldırmak, 30'a çıkarmak sinyalleri
    tüketmek olur. Ölçülen değer 10."""
    assert 5 <= st.KIRILIM_ASGARI_GG60 <= 20


# ── kapatılan strateji ────────────────────────────────────────────────────

def test_tepki_KAPALI():
    assert STRATEJILER["tepki"].aktif is False


def test_kapali_strateji_YENI_SINYAL_URETMEZ():
    g = _cerceve(gg60=50.0)
    # tepki'nin giriş koşullarını sağlayacak hale getir
    g["RSI2"] = 5.0
    g["BB_konum"] = 0.1
    assert bool(STRATEJILER["tepki"].giris(g).iloc[-1]), "senaryo kurulamadı"
    assert "tepki" not in skorla(g)["sinyaller"], "kapalı strateji sızıyor"


def test_kapali_strateji_SILINMEDI():
    """Kod, testler ve geçmiş sicil duruyor: karar geri alınabilmeli ve
    'neden kapatıldı' sorusu cevaplanabilmeli."""
    assert "tepki" in STRATEJILER
    assert STRATEJILER["tepki"].giris is not None
    assert "KAPALI" in STRATEJILER["tepki"].aciklama


def test_aktif_stratejiler_kapaliyi_disarida_birakir():
    a = aktif_stratejiler()
    assert "tepki" not in a
    assert "trend" in a and "kirilim" in a
    assert all(s.aktif for s in a.values())


def test_gecmis_pozisyonun_kurallari_hala_okunabilir():
    """Portföyde tepki ile açılmış bir pozisyon varsa, onun çıkış
    kuralları hâlâ bulunabilmeli."""
    assert STRATEJILER.get("tepki") is not None
    assert STRATEJILER["tepki"].azami_tutma > 0


def test_en_az_iki_aktif_strateji_var():
    """Tek stratejiye düşmek yoğunlaşma riski demek."""
    assert len(aktif_stratejiler()) >= 2
