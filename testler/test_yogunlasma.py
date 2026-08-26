"""Sinyal yoğunlaşması — AĞ ERİŞİMİ GEREKTİRMEZ.

Ekranda "3 sinyal" görüp üç ayrı fırsat sanmak, bu sistemdeki en pahalı
yanılgı: bütün sinyaller UZUN yönlü ve aynı anda açık. Ölçüldü — aylık
kazanma oranı %17 ile %81 arasında savruluyor, çünkü bir ayın sinyalleri
aynı kaderi paylaşıyor.

Bu katman karar üretmez, ÖLÇER: n korelasyonlu bahis kaç bağımsız bahse denk?

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import numpy as np
import pandas as pd
import pytest

from cekirdek import istatistik as st


def _seri(getiriler, baslangic=100.0):
    k = baslangic * np.cumprod(1 + np.array(getiriler))
    i = pd.bdate_range("2026-01-01", periods=len(k))
    return pd.DataFrame({"Close": k}, index=i)


@pytest.fixture
def rng():
    return np.random.default_rng(42)


# ── bağımsız bahis formülü ─────────────────────────────────────────────────

def test_korelasyonsuz_bahisler_tam_sayilir():
    assert st.bagimsiz_bahis_sayisi(0.0, 4) == pytest.approx(4.0)


def test_tam_korelasyon_tek_bahise_iner():
    """Dört özdeş bahis, dört değil BİR bahistir."""
    assert st.bagimsiz_bahis_sayisi(1.0, 4) == pytest.approx(1.0)


def test_yuksek_korelasyon_cesitlendirmeyi_yok_eder():
    assert st.bagimsiz_bahis_sayisi(0.8, 4) < 1.5


def test_tek_sinyal_bir_bahistir():
    assert st.bagimsiz_bahis_sayisi(0.5, 1) == 1.0


def test_negatif_korelasyon_sifira_kirpilir():
    """Formül ρ<0'da patlar; kırpma olmazsa saçma sayı üretir."""
    assert st.bagimsiz_bahis_sayisi(-0.5, 4) == pytest.approx(4.0)


# ── yoğunlaşma ölçümü ──────────────────────────────────────────────────────

def test_ayni_yonde_hareket_edenler_tek_bahis(rng):
    """Aynı seriyi paylaşan üç hisse çeşitlendirme sağlamaz."""
    ortak = rng.normal(0, 0.02, 200)
    f = {f"X{i}.IS": _seri(ortak + rng.normal(0, 0.0005, 200)) for i in range(3)}
    r = st.sinyal_yogunlasmasi(list(f), f)
    assert r["yeterli_mi"]
    assert r["ortalama_korelasyon"] > 0.9
    assert r["bagimsiz_bahis"] < 1.5
    assert "tek bir bahis" in r["yorum"]


def test_bagimsiz_hisseler_cesitlendirme_sayilir(rng):
    f = {f"Y{i}.IS": _seri(rng.normal(0, 0.02, 200)) for i in range(4)}
    r = st.sinyal_yogunlasmasi(list(f), f)
    assert r["bagimsiz_bahis"] > 2.5


def test_en_yakin_cift_bildirilir(rng):
    """Soyut bir sayı yetmez; hangi ikisinin aynı bahis olduğu söylenmeli."""
    ortak = rng.normal(0, 0.02, 200)
    f = {"A.IS": _seri(ortak), "B.IS": _seri(ortak + rng.normal(0, 1e-6, 200)),
         "C.IS": _seri(rng.normal(0, 0.02, 200))}
    r = st.sinyal_yogunlasmasi(list(f), f)
    assert set(r["en_yakin_cift"]) == {"A.IS", "B.IS"}


def test_sektor_yogunlasmasi_raporlanir(rng):
    f = {f"B{i}.IS": _seri(rng.normal(0, 0.02, 200)) for i in range(4)}
    sek = {"B0.IS": "banka", "B1.IS": "banka", "B2.IS": "banka", "B3.IS": "gıda"}
    r = st.sinyal_yogunlasmasi(list(f), f, sek)
    assert r["baskin_sektor"]["sektor"] == "banka"
    assert r["baskin_sektor"]["oran"] == 75


# ── yetersiz veri ──────────────────────────────────────────────────────────

def test_tek_sinyalde_hukum_verilmez(rng):
    f = {"A.IS": _seri(rng.normal(0, 0.02, 200))}
    assert st.sinyal_yogunlasmasi(["A.IS"], f)["yeterli_mi"] is False


def test_kisa_gecmis_sessizce_atlanir(rng):
    f = {f"A{i}.IS": _seri(rng.normal(0, 0.02, 10)) for i in range(3)}
    assert st.sinyal_yogunlasmasi(list(f), f)["yeterli_mi"] is False


def test_eksik_fiyat_cokme_uretmez(rng):
    f = {"A.IS": _seri(rng.normal(0, 0.02, 200))}
    r = st.sinyal_yogunlasmasi(["A.IS", "YOK.IS", "HIC.IS"], f)
    assert r["yeterli_mi"] is False


def test_sektor_yogunlasmasi_yoruma_girer(rng):
    """Kart kendi kendiyle çelişmemeli: korelasyon düşük ama sektör aynıysa
    'makul çeşitlendirme' demek yanıltıcıdır."""
    f = {f"S{i}.IS": _seri(rng.normal(0, 0.02, 200)) for i in range(3)}
    sek = {k: "enerji" for k in f}
    r = st.sinyal_yogunlasmasi(list(f), f, sek)
    assert r.get("sektor_uyarisi") is True
    assert "tek sektörde" in r["yorum"]


def test_dagilmis_sektorde_uyari_yok(rng):
    f = {f"D{i}.IS": _seri(rng.normal(0, 0.02, 200)) for i in range(3)}
    sek = {"D0.IS": "banka", "D1.IS": "gıda", "D2.IS": "enerji"}
    r = st.sinyal_yogunlasmasi(list(f), f, sek)
    assert r.get("sektor_uyarisi") is not True
