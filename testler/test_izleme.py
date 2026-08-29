"""İzleme listesi — pozisyon izleme ve kullanıcı izleme listesi.

İKİ TÜR KAYIT AYNI DOSYADA:
  pozisyon — karar defterine alım yazılınca kendiliğinden ekleniyor.
             Stopa değmesi KÖTÜ haber.
  izleme   — sahip olmadığın, beklediğin hisse. Alta inmesi çoğu zaman
             İYİ haber: beklediğin fiyat gelmiş oluyor.

İkisini aynı yerde tutmak bilinçli: iki paralel sistem kurmak, birinde
düzeltilen hatanın ötekinde kalması demekti. Ama karışmamaları gerekiyor
ve bu dosyanın asıl işi onu korumak.
"""
import json
from datetime import date, timedelta

import pytest

from cekirdek import izleme


@pytest.fixture
def dosya(tmp_path, monkeypatch):
    yol = tmp_path / "izleme.json"
    monkeypatch.setattr(izleme, "DOSYA", yol)
    return yol


# ── izleme listesi ────────────────────────────────────────────────────────

def test_izlemeye_alma(dosya):
    k = izleme.izle("thyao", alt=250, ust=400, not_="bilanço sonrası")
    assert k["sembol"] == "THYAO"
    assert k["tur"] == "izleme"
    assert k["alt"] == 250 and k["ust"] == 400
    assert izleme.liste("izleme") == [k]


def test_seviyesiz_kayit_REDDEDILIR(dosya):
    """Seviyesiz izleme kaydı hiç uyarı üretmez ve kullanıcı
    'ekledim ama haber gelmiyor' der."""
    with pytest.raises(ValueError):
        izleme.izle("THYAO")


def test_alt_ustun_altinda_olmali(dosya):
    with pytest.raises(ValueError):
        izleme.izle("THYAO", alt=400, ust=250)


def test_tek_seviye_yeter(dosya):
    assert izleme.izle("THYAO", alt=250)["alt"] == 250
    assert izleme.izle("EREGL", ust=60)["ust"] == 60


def test_ayni_sembol_guncellenir(dosya):
    izleme.izle("THYAO", alt=250)
    izleme.izle("THYAO", alt=260, ust=380)
    liste = izleme.liste("izleme")
    assert len(liste) == 1 and liste[0]["alt"] == 260


def test_silme(dosya):
    izleme.izle("THYAO", alt=250)
    assert izleme.izleme_sil("thyao") is True
    assert izleme.liste("izleme") == []
    assert izleme.izleme_sil("THYAO") is False


# ── iki tür karışmasın ────────────────────────────────────────────────────

def test_ayni_hisse_hem_POZISYON_hem_IZLEME_olabilir(dosya):
    """Tuttuğun hisseyi ayrı bir seviyeden de izleyebilmelisin:
    'elimde var ama 200'e düşerse ekleme yaparım'."""
    izleme.ekle("THYAO", stop=280, hedef=350, giris=300)
    izleme.izle("THYAO", alt=200)
    assert len(izleme.liste("pozisyon")) == 1
    assert len(izleme.liste("izleme")) == 1


def test_pozisyon_silmek_izlemeyi_SILMEZ(dosya):
    izleme.ekle("THYAO", stop=280, hedef=350)
    izleme.izle("THYAO", alt=200)
    izleme.sil("THYAO")
    assert izleme.liste("pozisyon") == []
    assert len(izleme.liste("izleme")) == 1


def test_izleme_silmek_pozisyonu_SILMEZ(dosya):
    izleme.ekle("THYAO", stop=280, hedef=350)
    izleme.izle("THYAO", alt=200)
    izleme.izleme_sil("THYAO")
    assert len(izleme.liste("pozisyon")) == 1
    assert izleme.liste("izleme") == []


def test_eski_kayitlar_pozisyon_sayilir(dosya):
    """Sürüm yükselten kurulumda kayıtlarda `tur` alanı yok."""
    dosya.write_text(json.dumps({
        "pozisyonlar": [{"sembol": "THYAO", "stop": 280.0, "hedef": 350.0,
                         "giris": 300.0, "tarih": "2026-01-01",
                         "uyarildi": {}}],
        "son_guncelleme_id": 0,
    }), encoding="utf-8")
    assert izleme.liste("pozisyon")[0]["sembol"] == "THYAO"
    assert izleme.liste("izleme") == []


# ── alarm ─────────────────────────────────────────────────────────────────

def _fiyat(deger):
    return lambda sem: deger


def test_alt_seviye_uyarisi(dosya):
    izleme.izle("THYAO", alt=250)
    u = izleme.kontrol(_fiyat(248))
    assert len(u) == 1 and u[0][2] == "alt_gecti"


def test_ust_seviye_uyarisi(dosya):
    izleme.izle("THYAO", ust=400)
    u = izleme.kontrol(_fiyat(405))
    assert len(u) == 1 and u[0][2] == "ust_gecti"


def test_seviye_arasinda_uyari_yok(dosya):
    izleme.izle("THYAO", alt=250, ust=400)
    assert izleme.kontrol(_fiyat(300)) == []


def test_uyari_GUNDE_BIR(dosya):
    """İş 5 dakikada bir çalışıyor; her turda mesaj atmak bildirimi
    çöpe çevirir ve kullanıcı hepsini susturur."""
    izleme.izle("THYAO", alt=250)
    assert len(izleme.kontrol(_fiyat(248))) == 1
    assert izleme.kontrol(_fiyat(248)) == []
    assert izleme.kontrol(_fiyat(240)) == []


def test_alt_ve_ust_ayri_sayilir(dosya):
    """İkisi ayrı uyarı türü: biri gönderildi diye öteki susmamalı."""
    izleme.izle("THYAO", alt=250, ust=400)
    assert izleme.kontrol(_fiyat(240))[0][2] == "alt_gecti"
    assert izleme.kontrol(_fiyat(410))[0][2] == "ust_gecti"


def test_pozisyon_ve_izleme_alarmlari_karismaz(dosya):
    izleme.ekle("THYAO", stop=280, hedef=350, giris=300)
    izleme.izle("THYAO", alt=200)
    turler = {t for _, _, t in izleme.kontrol(_fiyat(190))}
    assert turler == {"stop_gecti", "alt_gecti"}


def test_fiyat_alinamazsa_cokmez(dosya):
    izleme.izle("THYAO", alt=250)

    def patlat(sem):
        raise RuntimeError("ağ yok")

    assert izleme.kontrol(patlat) == []


# ── bildirim metinleri ────────────────────────────────────────────────────

def test_izleme_uyarisi_SINYAL_SANILMASIN():
    """Kullanıcının koyduğu seviye, sistemin sinyali değil. Aynı tonda
    verilirse kullanıcı bunu bir alım tavsiyesi sanır."""
    from cekirdek import bildirim
    m = bildirim.stop_uyarisi(
        {"sembol": "THYAO", "alt": 250.0, "tur": "izleme"}, 248.0,
        "alt_gecti")
    assert "sinyal DEĞİL" in m
    assert "THYAO" in m


def test_izleme_notu_mesaja_giriyor():
    from cekirdek import bildirim
    m = bildirim.stop_uyarisi(
        {"sembol": "THYAO", "alt": 250.0, "not": "bilanço sonrası bak"},
        248.0, "alt_gecti")
    assert "bilanço sonrası bak" in m


def test_push_metinleri_var():
    from cekirdek import bildirim
    for tur in ("alt_gecti", "ust_gecti"):
        bas, gov = bildirim.stop_push({"sembol": "X", "alt": 1, "ust": 2},
                                      1.5, tur)
        assert bas and gov, tur


def test_izleme_ve_stop_TONU_AYRI():
    """Alta inmek izlemede iyi haber, pozisyonda kötü. Aynı emoji ve
    dil ikisini karıştırırdı."""
    from cekirdek import bildirim
    stop = bildirim.stop_push({"sembol": "X", "stop": 100}, 99, "stop_gecti")
    izle = bildirim.stop_push({"sembol": "X", "alt": 100}, 99, "alt_gecti")
    assert stop[0] != izle[0]
    assert "🛑" in stop[0] and "🛑" not in izle[0]
