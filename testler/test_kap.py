"""KAP bildirim katmanı — AĞ ERİŞİMİ GEREKTİRMEZ.

Testlerin tamamı sabit örneklerle çalışır. Sebebi tek: bu katmanın riski
KAP'ın o an ne döndürdüğü değil, BELGELENMEMİŞ BİR UCUN kırıldığında ne
yaptığımız. Uç sessizce şekil değiştirirse sistem yanlış hisseye bildirim
bağlamamalı, hiç bildirim bağlamamalı.

Örnek veri 2026-08-25'te canlı uçtan alındı.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import json

import pytest

from cekirdek import kap


# Canlı yanıttan alınmış gerçek kayıtlar (kısaltıldı).
YANIT = [
    {"subject": "Özel Durum Açıklaması (Genel)", "summary": None,
     "title": "EMLAK KONUT GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
     "publishDate": "25.08.2026 15:12:40", "disclosureIndex": 1654684},
    {"subject": "Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin "
                "Bildirim (Faiz İçeren)", "summary": None,
     "title": "OTOKAR OTOMOTİV VE SAVUNMA SANAYİ A.Ş.",
     "publishDate": "25.08.2026 14:02:11", "disclosureIndex": 1654600},
    # Fon: hisse kodu yok, elenmeli.
    {"subject": "Fon Sürekli Bilgilendirme Formu", "summary": None,
     "title": "AK PORTFÖY ALTINCI SERBEST (DÖVİZ) FON",
     "publishDate": "25.08.2026 13:00:00", "disclosureIndex": 1654500},
    # Borsanın kendi duyurusu: şirket değil, elenmeli.
    {"subject": "Pay Bazında Devre Kesici Bildirimi", "summary": None,
     "title": "BORSA İSTANBUL BISTECH DEVRE KESİCİ UYGULAMASI",
     "publishDate": "25.08.2026 12:00:00", "disclosureIndex": 1654400},
]

HARITA = {
    "EMLAK KONUT GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.": "EKGYO",
    "OTOKAR OTOMOTİV VE SAVUNMA SANAYİ A.Ş.": "OTKAR",
}


@pytest.fixture
def sahte(monkeypatch):
    """Ağ çağrılarını sabit veriyle değiştirir."""
    def kur(yanit=YANIT, harita=HARITA):
        monkeypatch.setattr(kap, "_istek",
                            lambda *a, **k: json.dumps(yanit) if yanit is not None else None)
        monkeypatch.setattr(kap, "sirket_haritasi", lambda **k: harita)
    return kur


# ── önem derecelendirmesi ──────────────────────────────────────────────────

def test_ozel_durum_yuksek_onem():
    assert kap.onem("Özel Durum Açıklaması (Genel)") == 3


def test_rutin_ihrac_dusuk_onem():
    assert kap.onem("Pay Dışında Sermaye Piyasası Aracı İşlemlerine "
                    "İlişkin Bildirim (Faiz İçeren)") == 1


def test_taninmayan_konu_elenmiyor():
    """Yeni bir konu türü çıkarsa sessizce kaybolmamalı.

    onem() bilinmeyene 1 dönseydi varsayılan asgari_onem=2 eşiği onu atardı
    ve KAP yeni bir bildirim türü eklediğinde bunu kimse fark etmezdi.
    """
    assert kap.onem("Bugüne Kadar Görülmemiş Yeni Bildirim Türü") == 2


# ── eşleme ve eleme ────────────────────────────────────────────────────────

def test_yalnizca_kodu_olan_sirketler_alinir(sahte):
    sahte()
    kayitlar, eslesmeler = kap.topla(asgari_onem=1)
    kodlar = {e["sembol"] for e in eslesmeler}
    assert kodlar == {"EKGYO", "OTKAR"}          # fon ve borsa duyurusu elendi
    assert len(kayitlar) == 2


def test_onem_esigi_rutini_eler(sahte):
    sahte()
    kayitlar, eslesmeler = kap.topla(asgari_onem=2)
    assert {e["sembol"] for e in eslesmeler} == {"EKGYO"}
    assert kayitlar[0]["_onem"] == 3


def test_evren_disi_hisse_alinmaz(sahte):
    sahte()
    kayitlar, _ = kap.topla(evren_kodlari={"OTKAR"}, asgari_onem=1)
    assert len(kayitlar) == 1
    assert kayitlar[0]["baslik"].startswith("OTOKAR")


# ── kayıt biçimi ───────────────────────────────────────────────────────────

def test_kayit_ambar_bicimine_uyar(sahte):
    """haber tablosunun beklediği alanlar eksiksiz olmalı."""
    sahte()
    kayitlar, _ = kap.topla(asgari_onem=1)
    for alan in ("id", "tarih", "kaynak", "baslik", "ozet", "url", "yayin"):
        assert alan in kayitlar[0], alan
    assert kayitlar[0]["kaynak"] == "KAP"


def test_baslik_sirket_adini_tasir(sahte):
    """Konu tek başına ('Özel Durum Açıklaması') kime ait belli etmez."""
    sahte()
    kayitlar, _ = kap.topla(asgari_onem=2)
    assert "EMLAK KONUT" in kayitlar[0]["baslik"]
    assert "Özel Durum" in kayitlar[0]["baslik"]


def test_kimlik_bildirim_indeksinden_gelir(sahte):
    """Aynı bildirim iki kez yazılırsa ambar'da kopya oluşmamalı."""
    sahte()
    kayitlar, _ = kap.topla(asgari_onem=1)
    assert kayitlar[0]["id"] == "kap-1654684"


def test_url_bildirime_gider(sahte):
    sahte()
    kayitlar, _ = kap.topla(asgari_onem=1)
    assert kayitlar[0]["url"] == "https://www.kap.org.tr/tr/Bildirim/1654684"


def test_tarih_ayristirilir(sahte):
    sahte()
    kayitlar, _ = kap.topla(asgari_onem=1)
    assert kayitlar[0]["tarih"] == "2026-08-25"
    assert kayitlar[0]["yayin"].startswith("2026-08-25T15:12:40")


# ── uç kırıldığında ────────────────────────────────────────────────────────

def test_uc_cevap_vermezse_bos_doner(sahte, monkeypatch):
    sahte()
    monkeypatch.setattr(kap, "_istek", lambda *a, **k: None)
    assert kap.topla() == ([], [])


def test_uc_json_disi_donerse_bos_doner(sahte, monkeypatch):
    """KAP bir hata sayfası (HTML) dönerse çökmemeli."""
    sahte()
    monkeypatch.setattr(kap, "_istek", lambda *a, **k: "<html>404</html>")
    assert kap.topla() == ([], [])


def test_alanlar_degisirse_sessizce_atlanir(sahte, monkeypatch):
    """Uç alan adlarını değiştirirse yanlış veri üretmektense hiç üretme."""
    bozuk = [{"konu": "Özel Durum", "sirket": "EMLAK KONUT", "no": 1}]
    monkeypatch.setattr(kap, "_istek", lambda *a, **k: json.dumps(bozuk))
    monkeypatch.setattr(kap, "sirket_haritasi", lambda **k: HARITA)
    assert kap.topla() == ([], [])


def test_sirket_haritasi_bossa_bildirim_baglanmaz(sahte, monkeypatch):
    """Eşleme yoksa bildirimi rastgele bir hisseye bağlamaktansa hiç bağlama."""
    sahte(harita={})
    assert kap.topla() == ([], [])


def test_bozuk_kayit_digerlerini_dusurmez(monkeypatch):
    karisik = [{"subject": None, "title": None, "publishDate": None,
                "disclosureIndex": None}] + YANIT
    monkeypatch.setattr(kap, "_istek", lambda *a, **k: json.dumps(karisik))
    monkeypatch.setattr(kap, "sirket_haritasi", lambda **k: HARITA)
    kayitlar, _ = kap.topla(asgari_onem=1)
    assert len(kayitlar) == 2
