"""Push bildirimi ve cihaz kaydı — AĞ GEREKTİRMEZ.

Bu katmanın en pahalı arızası SESSİZ OLANI: bildirim gitmez ve kimse fark
etmez. İki ana kaynağı var ve ikisi de burada kilitli:

  ÖLÜ JETON BİRİKMESİ — kullanıcı uygulamayı silince jeton ölür. Silinmezse
  her bildirimde boşuna istek atılır, hata sayısı şişer ve gerçek arıza
  gürültüde kaybolur.

  KANAL BAĞIMLILIĞI — bot eskiden Telegram kurulu değilse tümüyle
  çıkıyordu, yani Telegram kaldırılınca stop alarmı da ölürdü.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import ambar, bildirim, cihaz, haberci, push


@pytest.fixture
def db(tmp_path, monkeypatch):
    y = tmp_path / "push_test.db"
    monkeypatch.setattr(ambar, "VERITABANI", y)
    ambar.kur(y)
    cihaz.kur(y)
    return y


# ── yapılandırma yokken ────────────────────────────────────────────────────

def test_anahtarsiz_push_sessizce_devre_disi(monkeypatch):
    """Anahtar yokken çökmek değil susmak doğrusu: bildirim işin kendisi
    değil, üstüne eklenen katman."""
    monkeypatch.delenv("MIDAS_FCM_ANAHTAR", raising=False)
    assert push.kurulu_mu() is False
    assert push.dogrula()["tamam"] is False
    r = push.gonder("Başlık", "Gövde", ["jeton"])
    assert r == {"gonderildi": 0, "basarisiz": 0, "gecersiz": []}


def test_olmayan_anahtar_dosyasi_cokme_uretmez(monkeypatch, tmp_path):
    monkeypatch.setenv("MIDAS_FCM_ANAHTAR", str(tmp_path / "yok.json"))
    assert push.kurulu_mu() is False
    assert "bulunamadı" in push.dogrula()["not"]


def test_bos_jeton_listesi_istek_atmaz(monkeypatch, tmp_path):
    sahte = tmp_path / "a.json"
    sahte.write_text('{"project_id":"x"}', encoding="utf-8")
    monkeypatch.setenv("MIDAS_FCM_ANAHTAR", str(sahte))
    assert push.gonder("b", "g", [])["gonderildi"] == 0


# ── cihaz kaydı ────────────────────────────────────────────────────────────

def test_jeton_kaydedilir_ve_okunur(db):
    assert cihaz.kaydet(1, "jeton-a", "android", yol=db)["kayitli"]
    assert cihaz.jetonlar(1, yol=db) == ["jeton-a"]


def test_ayni_jeton_iki_kez_kaydedilmez(db):
    """İstemci her açılışta gönderiyor; her seferinde yeni satır açsaydı
    aynı telefona onlarca bildirim giderdi."""
    cihaz.kaydet(1, "jeton-a", "android", yol=db)
    cihaz.kaydet(1, "jeton-a", "android", yol=db)
    assert cihaz.jetonlar(1, yol=db) == ["jeton-a"]


def test_jeton_kullanici_degistirebilir(db):
    """Telefonda çıkış yapıp başka hesapla girilince jeton YENİ sahibine
    geçmeli; yoksa bildirim eski kullanıcıya gitmeye devam ederdi."""
    cihaz.kaydet(1, "jeton-a", yol=db)
    cihaz.kaydet(2, "jeton-a", yol=db)
    assert cihaz.jetonlar(1, yol=db) == []
    assert cihaz.jetonlar(2, yol=db) == ["jeton-a"]


def test_bos_jeton_reddedilir(db):
    assert cihaz.kaydet(1, "", yol=db)["kayitli"] is False
    assert cihaz.kaydet(1, "   ", yol=db)["kayitli"] is False


def test_gecersiz_jetonlar_temizlenir(db):
    cihaz.kaydet(1, "iyi", yol=db)
    cihaz.kaydet(1, "olu", yol=db)
    assert cihaz.temizle(["olu"], yol=db) == 1
    assert cihaz.jetonlar(1, yol=db) == ["iyi"]


def test_temizle_bos_liste_ile_cagirilabilir(db):
    assert cihaz.temizle([], yol=db) == 0
    assert cihaz.temizle(None, yol=db) == 0


def test_kullanicilar_birbirinin_cihazini_gormez(db):
    cihaz.kaydet(1, "a", yol=db)
    cihaz.kaydet(2, "b", yol=db)
    assert cihaz.jetonlar(1, yol=db) == ["a"]
    assert cihaz.jetonlar(2, yol=db) == ["b"]


def test_kurulmamis_ambar_bos_liste_doner(tmp_path):
    """Push yüzünden günlük iş çökmemeli."""
    assert cihaz.jetonlar(1, yol=tmp_path / "hic.db") == []
    assert cihaz.liste(1, yol=tmp_path / "hic.db") == []


# ── dağıtıcı ───────────────────────────────────────────────────────────────

def test_kanal_yokken_yolla_cokmez(monkeypatch):
    monkeypatch.delenv("MIDAS_FCM_ANAHTAR", raising=False)
    monkeypatch.delenv("MIDAS_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("MIDAS_TELEGRAM_SOHBET", raising=False)
    r = haberci.yolla("metin", "başlık", "gövde")
    assert r["telegram"] is False
    assert r["push"]["gonderildi"] == 0


def test_acik_kanallar_sozluk_doner(monkeypatch):
    monkeypatch.delenv("MIDAS_FCM_ANAHTAR", raising=False)
    k = haberci.acik_kanallar()
    assert set(k) == {"telegram", "push"} and k["push"] is False


# ── içerik: iki biçim ──────────────────────────────────────────────────────

def test_push_metni_telegramdan_kisa():
    """Push kilit ekranında iki satır gösteriyor; aynı metni vermek
    birinde etiket kalabalığı diğerinde yarım cümle demekti."""
    plan = {"emirler": [{"sembol": "GESAN", "sinyaller": ["kirilim"],
                         "skor": 73, "fiyat": 92.2, "adet": 3, "stop": 82.95,
                         "hedef": 110.7, "maliyet": 276.6, "risk_tl": 27.7,
                         "tavan_fiyat": 110.18}]}
    uzun = bildirim.sabah_hatirlatici(plan)
    bas, gov = bildirim.sabah_push(plan)
    assert len(bas) < 45 and len(gov) < 120
    assert len(gov) < len(uzun)
    assert "<b>" not in bas and "<b>" not in gov


def test_push_basligi_emir_sayisini_tasir():
    plan = {"emirler": [{"sembol": "A", "adet": 1}, {"sembol": "B", "adet": 2}]}
    bas, gov = bildirim.sabah_push(plan)
    assert "2" in bas and "A" in gov and "B" in gov


def test_cok_emirde_govde_kirpilir():
    plan = {"emirler": [{"sembol": f"H{i}", "adet": 1} for i in range(6)]}
    bas, gov = bildirim.sabah_push(plan)
    assert "+3" in gov and len(gov) < 120


def test_bos_planda_push_bos():
    assert bildirim.sabah_push({"emirler": []}) == ("", "")


def test_stop_push_uc_turu_de_karsilar():
    poz = {"sembol": "THYAO", "stop": 296.4, "hedef": 351.0}
    for tur in ("stop_gecti", "hedef_gecti", "stop_yakin"):
        bas, gov = bildirim.stop_push(poz, 300.0, tur)
        assert bas and gov and "THYAO" in bas
    assert bildirim.stop_push(poz, 300.0, "bilinmeyen") == ("", "")


def test_gunluk_push_sinyalsiz_gunu_anlatir():
    bas, gov = bildirim.gunluk_push({"endeks_degisim": -1.2, "sinyal_veren": []})
    assert "sinyal yok" in gov.lower()
