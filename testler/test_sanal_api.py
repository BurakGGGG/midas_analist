"""Sanal İşlem uçları — HTTP SÖZLEŞMESİ.

Bu dosya mantığı değil, sözleşmeyi sınıyor: çekirdek doğru hesaplarken uç
yanlış durum kodu döndürebilir, alan adını değiştirebilir ya da istemcinin
gönderdiği durumu hiç okumayabilir. İkisi ayrışabilir.

TASARIM KURALI — DURUMSUZLUK: bakiye, pozisyonlar ve özkaynak geçmişi
telefonda yaşıyor; sunucu her istekte onları alıyor ve hiçbir şey
saklamıyor. Aşağıdaki testler bu kuralı da koruyor: aynı istek iki kez
gönderildiğinde aynı cevap gelmeli.

Çalıştır:  .venv/bin/python -m pytest testler/test_sanal_api.py -q
"""
import importlib

import pytest
from fastapi.testclient import TestClient

from cekirdek import ortam  # noqa: F401  (.env yükler)

TARIH = "2024-06-12"


def _modul():
    """api.main'i ÇAĞRI ANINDA çöz.

    test_api_anahtar.py modülü importlib.reload ile yeniden yüklüyor
    (anahtar modül yüklenirken okunuyor). İçe aktarma anında kopyalanan
    `app` ve `_ANAHTAR`, yeniden yüklemeden sonra bayat kalıyor ve bütün
    istekler 401 dönüyordu — testler tek başına geçip takımla kırılıyordu.
    """
    return importlib.import_module("api.main")


@pytest.fixture
def istemci():
    return TestClient(_modul().app)


@pytest.fixture
def baslik():
    return {"X-API-Anahtar": _modul()._ANAHTAR}


def _al(istemci, baslik, sembol="THYAO", adet=4, nakit=10_000.0, tarih=TARIH):
    return istemci.post("/alistirma/al", headers=baslik, json={
        "sembol": sembol, "tarih": tarih, "adet": adet, "nakit": nakit})


# ── aralık ────────────────────────────────────────────────────────────────

def test_aralik_secilebilir_gunleri_verir(istemci, baslik):
    r = istemci.get("/alistirma/aralik", headers=baslik)
    assert r.status_code == 200
    d = r.json()
    assert d["en_erken"] < d["en_gec"]
    assert d["gun_sayisi"] > 100


# ── alım ──────────────────────────────────────────────────────────────────

def test_alim_kayma_ile_fiyat_dondurur(istemci, baslik):
    r = _al(istemci, baslik)
    assert r.status_code == 200
    d = r.json()
    assert d["gecti"] is True
    assert d["fiyat"] > d["ham_fiyat"], "alışta kayma yukarı olmalı"
    assert d["maliyet"] == pytest.approx(4 * d["fiyat"], abs=0.01)
    assert "bar" in d, "istemci ATR'yi bardan okuyor"


def test_bakiye_yetmezse_gecmez_ama_200_doner(istemci, baslik):
    """400 DEĞİL 200: bu bir istemci hatası değil, iş kuralı sonucu.
    Hata kodu dönseydi ekran kırmızı hata gösterirdi; oysa kullanıcı
    yalnızca daha az adet almalı."""
    r = _al(istemci, baslik, adet=500, nakit=1_000)
    assert r.status_code == 200
    assert r.json()["gecti"] is False
    assert "Bakiye" in r.json()["sebep"]


def test_veri_olmayan_tarih_404(istemci, baslik):
    r = _al(istemci, baslik, tarih="1990-01-02")
    assert r.status_code == 404


def test_bilinmeyen_sembol_404(istemci, baslik):
    r = _al(istemci, baslik, sembol="YOKBOYLEBIRSEY")
    assert r.status_code == 404


# ── değerleme ─────────────────────────────────────────────────────────────

def test_deger_ozkaynagi_nakit_arti_piyasa_verir(istemci, baslik):
    poz = [{"sembol": "THYAO", "adet": 4, "giris": 300.0,
            "stop": 280.0, "hedef": 340.0, "tarih": TARIH}]
    r = istemci.post("/alistirma/deger", headers=baslik,
                     json={"tarih": TARIH, "nakit": 8_800.0,
                           "pozisyonlar": poz})
    assert r.status_code == 200
    d = r.json()
    assert d["ozkaynak"] == pytest.approx(d["nakit"] + d["piyasa"], abs=0.02)
    s = d["satirlar"][0]
    assert s["sembol"] == "THYAO" and s["veri_var"] is True
    assert s["stop_uzaklik"] is not None


def test_bos_portfoy_degeri_nakite_esit(istemci, baslik):
    r = istemci.post("/alistirma/deger", headers=baslik,
                     json={"tarih": TARIH, "nakit": 10_000.0,
                           "pozisyonlar": []})
    assert r.json()["ozkaynak"] == 10_000.0


# ── adım ──────────────────────────────────────────────────────────────────

def test_pozisyonsuz_adim_400_DONMEZ(istemci, baslik):
    """Eski /alistirma/ilerlet sembol listesi boşsa 400 dönüyordu.
    Kullanıcı tarih seçip 'yarına bakayım' dediğinde hata alıyordu."""
    r = istemci.post("/alistirma/adim", headers=baslik,
                     json={"tarih": TARIH, "nakit": 10_000.0, "adim": 1,
                           "pozisyonlar": []})
    assert r.status_code == 200
    assert r.json()["tarih"] > TARIH


def test_bir_hafta_TEK_TURDA(istemci, baslik):
    """Eskiden 5 ayrı HTTP turu gerekiyordu."""
    r = istemci.post("/alistirma/adim", headers=baslik,
                     json={"tarih": TARIH, "nakit": 10_000.0, "adim": 5,
                           "pozisyonlar": []})
    d = r.json()
    assert len(d["gunler"]) == 5
    assert len(d["ozkaynak_noktalari"]) == 5


def test_kapanana_kadar_pozisyonu_kapatir(istemci, baslik):
    poz = [{"sembol": "THYAO", "adet": 1, "giris": 300.0,
            "stop": 297.0, "hedef": 303.0, "tarih": TARIH}]
    r = istemci.post("/alistirma/adim", headers=baslik,
                     json={"tarih": TARIH, "nakit": 0.0, "adim": 0,
                           "pozisyonlar": poz})
    d = r.json()
    assert d["pozisyonlar"] == []
    assert len(d["cikislar"]) == 1
    assert d["cikislar"][0]["sebep"] in ("stop", "hedef")
    assert d["nakit"] > 0, "çıkış hasılatı nakde eklenmedi"


def test_adim_DURUMSUZ_ayni_istek_ayni_cevap(istemci, baslik):
    """Sunucu hiçbir şey saklamıyor: aynı gövde iki kez aynı sonucu
    vermeli. Aksi halde telefondaki durum ile sunucudaki ayrışırdı."""
    govde = {"tarih": TARIH, "nakit": 10_000.0, "adim": 3,
             "pozisyonlar": []}
    a = istemci.post("/alistirma/adim", headers=baslik, json=govde).json()
    b = istemci.post("/alistirma/adim", headers=baslik, json=govde).json()
    assert a["tarih"] == b["tarih"]
    assert a["ozkaynak_noktalari"] == b["ozkaynak_noktalari"]


# ── satış ─────────────────────────────────────────────────────────────────

def test_kismi_satis_kalani_bildirir(istemci, baslik):
    r = istemci.post("/alistirma/sat", headers=baslik, json={
        "tarih": TARIH, "adet": 2,
        "pozisyon": {"sembol": "THYAO", "adet": 5, "giris": 300.0}})
    d = r.json()
    assert d["adet"] == 2 and d["kalan_adet"] == 3
    assert d["fiyat"] < d["ham_fiyat"], "satışta kayma aşağı olmalı"


def test_satista_adet_sifir_tamami_satar(istemci, baslik):
    r = istemci.post("/alistirma/sat", headers=baslik, json={
        "tarih": TARIH, "adet": 0,
        "pozisyon": {"sembol": "THYAO", "adet": 5, "giris": 300.0}})
    assert r.json()["adet"] == 5 and r.json()["kalan_adet"] == 0


# ── seri ──────────────────────────────────────────────────────────────────

def test_seri_gecmis_kesiti_verir(istemci, baslik):
    """Hisse ekranı bunu veremiyor: oradaki seri hep BUGÜNE kadar."""
    r = istemci.get("/alistirma/seri", headers=baslik,
                    params={"sembol": "THYAO", "baslangic": "2024-06-01",
                            "bitis": "2024-07-31"})
    assert r.status_code == 200
    n = r.json()["kapanis"]
    assert n and n[0]["t"] >= "2024-06-01"
    assert n[-1]["t"] <= "2024-07-31"


# ── sinyaller ─────────────────────────────────────────────────────────────

def test_sinyaller_o_gunun_kararlarini_verir(istemci, baslik):
    r = istemci.get("/alistirma/sinyaller", headers=baslik,
                    params={"tarih": TARIH, "sermaye": 10_000})
    assert r.status_code == 200
    d = r.json()
    assert d["tarih"] <= TARIH, "geleceğe bakmamalı"
    for s in d["sinyaller"]:
        assert s["stop"] < s["fiyat"] < s["hedef"]
        assert s["strateji"] in ("trend", "tepki", "kirilim")


def test_sinyaller_sermayeye_gore_adet_verir(istemci, baslik):
    """Aynı gün, farklı sermaye → farklı adet. Adedi stop mesafesi ve
    sermaye birlikte belirliyor."""
    def adetler(sermaye):
        d = istemci.get("/alistirma/sinyaller", headers=baslik,
                        params={"tarih": TARIH, "sermaye": sermaye}).json()
        return {s["sembol"]: s["adet"] for s in d["sinyaller"]}

    kucuk, buyuk = adetler(5_000), adetler(50_000)
    ortak = set(kucuk) & set(buyuk)
    assert ortak, "karşılaştırılacak ortak sinyal yok"
    assert any(buyuk[s] > kucuk[s] for s in ortak)


def test_anahtarsiz_istek_reddedilir(istemci):
    if not _modul()._ANAHTAR:
        pytest.skip("API anahtarı tanımlı değil")
    r = istemci.get("/alistirma/aralik")
    assert r.status_code == 401
