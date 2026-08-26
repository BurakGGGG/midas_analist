"""Hesap ve bulut yedeği — AĞ GEREKTİRMEZ.

Kimlik doğrulama, sessizce yanlış çalıştığında en pahalı katmandır: kilit
tutmazsa kaba kuvvet açılır, çakışma yakalanmazsa bir telefon diğerinin
yedeğini ezer, jeton düz saklanırsa veritabanı sızıntısı oturum sızıntısı
olur. Bu testler o üçünü ayrı ayrı kilitliyor.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
from datetime import datetime, timedelta, timezone

import pytest

from cekirdek import ambar, hesap


@pytest.fixture
def db(tmp_path):
    """Her test kendi veritabanında; hesaplar birbirine karışmasın."""
    y = tmp_path / "hesap_test.db"
    hesap.kur(y)
    return y


def _kayit(db, eposta="burak@ornek.com", parola="parola1234"):
    return hesap.kayit(eposta, parola, "test", yol=db)


# ── kayıt doğrulaması ──────────────────────────────────────────────────────

@pytest.mark.parametrize("eposta", ["", "burak", "burak@", "@ornek.com",
                                    "bo şluk@ornek.com", "a@b"])
def test_gecersiz_eposta_reddedilir(db, eposta):
    with pytest.raises(hesap.HesapHata):
        hesap.kayit(eposta, "parola1234", yol=db)


@pytest.mark.parametrize("parola", ["", "kisa", "1234567"])
def test_kisa_parola_reddedilir(db, parola):
    with pytest.raises(hesap.HesapHata):
        hesap.kayit("burak@ornek.com", parola, yol=db)


def test_ayni_eposta_iki_kez_kaydedilemez(db):
    _kayit(db)
    with pytest.raises(hesap.HesapHata):
        _kayit(db)


def test_eposta_buyuk_kucuk_ve_bosluk_duyarsiz(db):
    _kayit(db, "  Burak@Ornek.COM ")
    g = hesap.giris("burak@ornek.com", "parola1234", yol=db)
    assert g["eposta"] == "burak@ornek.com"


# ── giriş ──────────────────────────────────────────────────────────────────

def test_dogru_parola_jeton_verir(db):
    _kayit(db)
    g = hesap.giris("burak@ornek.com", "parola1234", yol=db)
    assert hesap.jeton_dogrula(g["jeton"], yol=db) == g["kullanici_id"]


def test_yanlis_parola_reddedilir(db):
    _kayit(db)
    with pytest.raises(hesap.HesapHata):
        hesap.giris("burak@ornek.com", "yanlisparola", yol=db)


def test_olmayan_kullanici_ayni_hatayi_verir(db):
    """Farklı mesaj verseydi 'bu e-posta kayıtlı mı' sorusu dışarıdan
    cevaplanabilirdi."""
    _kayit(db)
    with pytest.raises(hesap.HesapHata) as a:
        hesap.giris("burak@ornek.com", "yanlisparola", yol=db)
    with pytest.raises(hesap.HesapHata) as b:
        hesap.giris("yokboyle@ornek.com", "yanlisparola", yol=db)
    assert str(a.value) == str(b.value)


# ── kaba kuvvet ────────────────────────────────────────────────────────────

def test_bes_hatali_denemeden_sonra_kilitlenir(db):
    _kayit(db)
    for _ in range(hesap.AZAMI_DENEME):
        with pytest.raises(hesap.HesapHata):
            hesap.giris("burak@ornek.com", "yanlis", yol=db)
    # Artık DOĞRU parola bile girmemeli.
    with pytest.raises(hesap.HesapHata) as e:
        hesap.giris("burak@ornek.com", "parola1234", yol=db)
    assert "dakika" in str(e.value)


def test_basarisiz_deneme_gercekten_kaydedilir(db):
    """Sayaç `ambar.baglan()` commit etmeden fırlatılan bir istisnayla geri
    alınırsa kilit hiç kurulmaz — her şey doğru görünür, koruma yoktur."""
    _kayit(db)
    with pytest.raises(hesap.HesapHata):
        hesap.giris("burak@ornek.com", "yanlis", yol=db)
    with ambar.baglan(db) as c:
        assert c.execute("SELECT basarisiz FROM kullanici").fetchone()[0] == 1


def test_basarili_giris_sayaci_sifirlar(db):
    _kayit(db)
    for _ in range(hesap.AZAMI_DENEME - 1):
        with pytest.raises(hesap.HesapHata):
            hesap.giris("burak@ornek.com", "yanlis", yol=db)
    hesap.giris("burak@ornek.com", "parola1234", yol=db)
    with ambar.baglan(db) as c:
        k = c.execute("SELECT basarisiz, kilit_bitis FROM kullanici").fetchone()
    assert k["basarisiz"] == 0 and k["kilit_bitis"] is None


def test_kilit_suresi_dolunca_acilir(db):
    _kayit(db)
    for _ in range(hesap.AZAMI_DENEME):
        with pytest.raises(hesap.HesapHata):
            hesap.giris("burak@ornek.com", "yanlis", yol=db)
    gecmis = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with ambar.baglan(db) as c:
        c.execute("UPDATE kullanici SET kilit_bitis=?", (gecmis,))
    assert hesap.giris("burak@ornek.com", "parola1234", yol=db)["jeton"]


# ── jeton ──────────────────────────────────────────────────────────────────

def test_jeton_duz_saklanmaz(db):
    """Veritabanı sızarsa oturumlar ele geçmemeli."""
    o = _kayit(db)
    with ambar.baglan(db) as c:
        satir = c.execute("SELECT jeton_ozet FROM oturum").fetchone()
    assert o["jeton"] not in satir["jeton_ozet"]
    assert len(satir["jeton_ozet"]) == 64          # sha256 onaltılık


def test_suresi_gecmis_jeton_gecersiz(db):
    o = _kayit(db)
    gecmis = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with ambar.baglan(db) as c:
        c.execute("UPDATE oturum SET bitis=?", (gecmis,))
    assert hesap.jeton_dogrula(o["jeton"], yol=db) is None


def test_cikis_jetonu_dusurur(db):
    o = _kayit(db)
    assert hesap.cikis(o["jeton"], yol=db) is True
    assert hesap.jeton_dogrula(o["jeton"], yol=db) is None


def test_bozuk_jeton_cokme_uretmez(db):
    for j in ("", None, "abc", "x" * 500):
        assert hesap.jeton_dogrula(j, yol=db) is None


# ── yedek ──────────────────────────────────────────────────────────────────

def test_yedek_yazilir_ve_okunur(db):
    o = _kayit(db)
    veri = {"pozisyonlar": [{"sembol": "THYAO"}], "ayarlar": {"sermaye": 1000}}
    r = hesap.yedek_yaz(o["kullanici_id"], veri, yol=db)
    assert r["yazildi"] and r["surum"] == 1
    assert hesap.yedek_oku(o["kullanici_id"], yol=db)["icerik"] == veri


def test_her_yazma_surumu_artirir(db):
    o = _kayit(db)
    for beklenen in (1, 2, 3):
        r = hesap.yedek_yaz(o["kullanici_id"], {"n": beklenen}, yol=db)
        assert r["surum"] == beklenen


def test_eski_surum_yeniyi_ezemez(db):
    """İkinci telefon bir hafta açılmamışsa, açıldığı anda güncel yedeği
    sessizce ezmemeli."""
    o = _kayit(db)
    kid = o["kullanici_id"]
    hesap.yedek_yaz(kid, {"kaynak": "telefon-1"}, yol=db)            # surum 1
    hesap.yedek_yaz(kid, {"kaynak": "telefon-1b"}, yol=db)           # surum 2

    r = hesap.yedek_yaz(kid, {"kaynak": "eski-telefon"},
                        beklenen_surum=1, yol=db)
    assert r["yazildi"] is False and r["cakisma"] is True
    assert r["sunucudaki"]["icerik"] == {"kaynak": "telefon-1b"}
    assert hesap.yedek_oku(kid, yol=db)["icerik"] == {"kaynak": "telefon-1b"}


def test_guncel_surumle_yazma_gecer(db):
    o = _kayit(db)
    kid = o["kullanici_id"]
    hesap.yedek_yaz(kid, {"a": 1}, yol=db)
    r = hesap.yedek_yaz(kid, {"a": 2}, beklenen_surum=1, yol=db)
    assert r["yazildi"] is True and r["surum"] == 2


def test_ilk_yedekte_cakisma_olmaz(db):
    o = _kayit(db)
    r = hesap.yedek_yaz(o["kullanici_id"], {"a": 1}, beklenen_surum=0, yol=db)
    assert r["yazildi"] is True


def test_cok_buyuk_yedek_reddedilir(db):
    o = _kayit(db)
    with pytest.raises(hesap.HesapHata):
        hesap.yedek_yaz(o["kullanici_id"],
                        {"golge": "x" * (hesap.AZAMI_YEDEK_BAYT + 10)}, yol=db)


def test_yedek_yokken_okuma_none_doner(db):
    o = _kayit(db)
    assert hesap.yedek_oku(o["kullanici_id"], yol=db) is None


def test_kullanicilar_birbirinin_yedegini_gormez(db):
    a = _kayit(db, "a@ornek.com")
    b = _kayit(db, "b@ornek.com")
    hesap.yedek_yaz(a["kullanici_id"], {"kim": "a"}, yol=db)
    assert hesap.yedek_oku(b["kullanici_id"], yol=db) is None


# ── parola değiştirme ──────────────────────────────────────────────────────

def test_parola_degisince_oturumlar_duser(db):
    """Parola değiştirmenin sebebi genelde 'başkası girmiş olabilir'dir."""
    o = _kayit(db)
    hesap.parola_degistir(o["kullanici_id"], "parola1234", "yeniparola99", yol=db)
    assert hesap.jeton_dogrula(o["jeton"], yol=db) is None
    assert hesap.giris("burak@ornek.com", "yeniparola99", yol=db)["jeton"]


def test_yanlis_eski_parolayla_degistirilemez(db):
    o = _kayit(db)
    with pytest.raises(hesap.HesapHata):
        hesap.parola_degistir(o["kullanici_id"], "yanlis", "yeniparola99", yol=db)


# ── bilgi ──────────────────────────────────────────────────────────────────

def test_bilgi_parola_sizdirmaz(db):
    o = _kayit(db)
    b = hesap.bilgi(o["kullanici_id"], yol=db)
    düz = str(b)
    assert "parola" not in düz and "tuz" not in düz
    assert b["eposta"] == "burak@ornek.com"
