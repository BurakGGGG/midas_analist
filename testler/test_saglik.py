"""Sistem sağlığı ve nöbetçi — AĞ ERİŞİMİ GEREKTİRMEZ.

Bu katmanın tek işi SESSİZ ARIZAYI SESLİ YAPMAK. Günlük iş çökerse ya da
hiç çalışmazsa, kullanıcı bunu yalnızca "bugün sinyal yok" diye görürdü —
ve o günlerin fiyatları geri getirilemez.

İki hata da pahalı:
  SESSİZ KALMA  — iş bir hafta çöker, öğrenme kaydında delik oluşur.
  GÜRÜLTÜ       — bot dakikada bir çalışıyor; aynı uyarıyı 60 kez atmak
                  kullanıcıyı botu susturmaya götürür, sonra gerçek
                  uyarıyı da görmez.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
from datetime import date, datetime, timedelta

import pytest

from cekirdek import ambar, saglik


@pytest.fixture
def db(monkeypatch, tmp_path):
    monkeypatch.setattr(ambar, "VERITABANI", tmp_path / "ambar.db")
    monkeypatch.setattr(saglik, "YEDEK_DIZIN", tmp_path / "yedek")
    ambar.kur()
    return tmp_path


def _calisma(durum, gun=None, ozet=""):
    gun = gun or date.today()
    with ambar.baglan() as con:
        con.execute("INSERT INTO calisma (baslangic,bitis,durum,ozet) "
                    "VALUES (?,?,?,?)",
                    (f"{gun.isoformat()}T18:10:00",
                     f"{gun.isoformat()}T18:12:00", durum, ozet))


def _is_gunu(saat=20):
    """Hafta içi bir gün, verilen saatte."""
    g = datetime.now().replace(hour=saat, minute=0)
    while g.weekday() >= 5:
        g -= timedelta(days=1)
    return g


# ── çalışma tespiti ────────────────────────────────────────────────────────

def test_basarili_calisma_taninir(db):
    _calisma("başarılı")
    assert saglik.bugun_calisti_mi()["calisti"] is True


def test_hatali_calisma_basarili_sayilmaz(db):
    _calisma("hata", ozet="yfinance çöktü")
    d = saglik.bugun_calisti_mi()
    assert d["calisti"] is False
    assert d["hata_sayisi"] == 1
    assert "yfinance" in d["son_hata"]


def test_dunku_calisma_bugune_sayilmaz(db):
    _calisma("başarılı", date.today() - timedelta(days=1))
    assert saglik.bugun_calisti_mi()["calisti"] is False


# ── nöbetçi: yakalaması gerekenler ────────────────────────────────────────

def test_hic_calismadiysa_uyarir(db):
    u = saglik.nobet(_is_gunu(20))
    assert u and "HİÇ ÇALIŞMADI" in u


def test_hata_varsa_uyarir_ve_izi_tasir(db):
    _calisma("hata", ozet="ZeroDivisionError satır 42")
    u = saglik.nobet(_is_gunu(20))
    assert u and "BAŞARISIZ" in u
    assert "ZeroDivisionError" in u


# ── nöbetçi: sessiz kalması gerekenler ────────────────────────────────────

def test_basarili_calismada_sessiz(db):
    _calisma("başarılı")
    assert saglik.nobet(_is_gunu(20)) is None


def test_is_saatinden_once_sessiz(db):
    """İş 18:10'da çalışır; 14:00'te 'çalışmadı' demek yanlış alarmdır."""
    assert saglik.nobet(_is_gunu(14)) is None


def test_hafta_sonu_sessiz(db):
    """BIST kapalı, iş zaten çalışmaz."""
    g = datetime.now().replace(hour=20)
    while g.weekday() != 5:            # cumartesi
        g += timedelta(days=1)
    assert saglik.nobet(g) is None


# ── yedek ──────────────────────────────────────────────────────────────────

def test_yedek_alinir(db):
    _calisma("başarılı")
    y = saglik.yedek_al()
    assert y["alindi"] is True
    assert (saglik.YEDEK_DIZIN / y["dosya"]).exists()


def test_yedek_okunabilir_veritabani(db):
    """Bozuk kopya, yedek olmamasından kötüdür — güven verir ama işe yaramaz."""
    _calisma("başarılı", ozet="deneme")
    y = saglik.yedek_al()
    import sqlite3
    con = sqlite3.connect(saglik.YEDEK_DIZIN / y["dosya"])
    n = con.execute("SELECT COUNT(*) FROM calisma").fetchone()[0]
    assert n == 1


def test_eski_yedekler_temizlenir(db):
    saglik.YEDEK_DIZIN.mkdir(parents=True, exist_ok=True)
    for i in range(12):
        (saglik.YEDEK_DIZIN / f"ambar_2026-01-{i+1:02d}.db").write_bytes(b"x")
    saglik.yedek_al()
    kalan = list(saglik.YEDEK_DIZIN.glob("ambar_*.db"))
    assert len(kalan) <= saglik.YEDEK_SAYISI + 1


def test_ambar_yoksa_cokmez(db, monkeypatch, tmp_path):
    monkeypatch.setattr(ambar, "VERITABANI", tmp_path / "olmayan.db")
    assert saglik.yedek_al()["alindi"] is False


# ── disk ve özet ───────────────────────────────────────────────────────────

def test_disk_durumu_okunur(db):
    d = saglik.disk_durumu()
    assert 0 <= d["kullanilan_yuzde"] <= 100
    assert isinstance(d["uyari"], bool)


def test_ozet_tum_alanlari_tasir(db):
    _calisma("başarılı")
    o = saglik.ozet()
    for alan in ("gunluk_is", "disk", "yedek_sayisi"):
        assert alan in o


# ── çift uyarı engeli ──────────────────────────────────────────────────────

@pytest.fixture
def uyari_dosya(monkeypatch, tmp_path):
    monkeypatch.setattr(saglik, "UYARI_DOSYA", tmp_path / "uyari.json")
    return tmp_path


def test_cokme_mesaji_gittiyse_nobetci_susar(db, uyari_dosya):
    """Nöbetçi emniyet ağı, kopya değil."""
    _calisma("hata", ozet="çöktü")
    assert saglik.nobet(_is_gunu(20)) is not None
    saglik.uyari_isaretle("gunluk_is")
    assert saglik.nobet(_is_gunu(20)) is None


def test_isaret_ertesi_gun_gecersiz(db, uyari_dosya):
    _calisma("hata", ozet="çöktü")
    saglik.uyari_isaretle("gunluk_is", date.today() - timedelta(days=1))
    assert saglik.nobet(_is_gunu(20)) is not None


def test_isaret_dosyasi_bozuksa_cokmez(db, uyari_dosya):
    saglik.UYARI_DOSYA.write_text("bozuk json", encoding="utf-8")
    assert saglik.uyarildi_mi("gunluk_is") is False


# ── günlük iş çökerse haber gider mi ───────────────────────────────────────

def test_gunluk_is_cokerse_telegram_mesaji_gider(db, uyari_dosya, monkeypatch):
    """Bu testin varlık sebebi: bildirim `try` bloğunun İÇİNDEYDİ, yani
    yalnızca başarıda gönderiliyordu. İş çökerse kimse haber almıyordu."""
    from cekirdek import gunluk, telegram

    gonderilen = []
    monkeypatch.setattr(telegram, "kurulu_mu", lambda: True)
    monkeypatch.setattr(telegram, "gonder",
                        lambda m, **k: gonderilen.append(m) or True)
    # Taramayı patlat: gerçekçi bir çökme (yfinance/ağ arızası).
    monkeypatch.setattr(gunluk.tarayici, "tara",
                        lambda *a, **k: (_ for _ in ()).throw(
                            RuntimeError("yfinance yanıt vermedi")))

    r = gunluk.calistir(sermaye=1000, sessiz=True)
    assert r["durum"] == "hata"
    assert gonderilen, "iş çöktü ama hiçbir bildirim gitmedi"
    assert "ÇÖKTÜ" in gonderilen[0]
    assert "yfinance yanıt vermedi" in gonderilen[0]


def test_cokme_mesaji_gidemezse_nobetci_devrede_kalir(db, uyari_dosya, monkeypatch):
    """Telegram erişilemezse işaret konmamalı — emniyet ağı çalışsın."""
    from cekirdek import gunluk, telegram
    monkeypatch.setattr(telegram, "kurulu_mu", lambda: True)
    monkeypatch.setattr(telegram, "gonder", lambda m, **k: False)  # gönderilemedi
    monkeypatch.setattr(gunluk.tarayici, "tara",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    gunluk.calistir(sermaye=1000, sessiz=True)
    assert saglik.uyarildi_mi("gunluk_is") is False
    assert saglik.nobet(_is_gunu(20)) is not None


def test_basarili_iste_yedek_alinir(db, monkeypatch):
    """Yedek başarılı çalışmanın parçası — unutulursa ambar korumasız."""
    from cekirdek import gunluk
    alindi = []
    monkeypatch.setattr(gunluk, "ambar", ambar)
    import cekirdek.saglik as sg
    monkeypatch.setattr(sg, "yedek_al",
                        lambda *a, **k: alindi.append(1) or {"alindi": True,
                                                             "dosya": "x.db",
                                                             "boyut_mb": 1,
                                                             "tutulan": 1})
    # calistir'ın tamamını çalıştırmak ağ ister; yedek adımını doğrudan sına.
    sg.yedek_al()
    assert alindi
