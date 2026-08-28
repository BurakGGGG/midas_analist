"""Bildirim katmanı — AĞ ERİŞİMİ GEREKTİRMEZ.

Bu katmanın işi sunucunun kullanıcıya ULAŞMASI. İki hata pahalı:

  SESSİZ KALMA  — gerçekten önemli bir şey olduğunda haber vermemek.
                  Stop geçildi ve kimse söylemedi: doğrudan para.
  GÜRÜLTÜ       — her turda mesaj atmak. Kullanıcı botu susturur ve
                  bir daha hiçbir uyarıyı görmez. Susturulmuş bot,
                  olmayan bottan kötüdür.

Ayrıca: bildirim ÇÖKERSE günlük iş başarılı sayılmalı. Bildirim işin
kendisi değil.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import json
from datetime import date, timedelta

import pytest

from cekirdek import bildirim, izleme, telegram


OZET = {
    "tarih": "2026-08-25", "endeks_degisim": -0.44,
    "yukselen": 28, "dusen": 69, "bist_reel_1y": -5.65,
    "rejim": {"ad": "ılımlı"}, "kap_bildirim": 41,
    "sinyal_veren": [
        {"sembol": "EUPWR", "skor": 74.9, "fiyat": 95.3,
         "sinyaller": ["trend"], "karantina": ["trend"], "onerilir": False},
    ],
}


@pytest.fixture
def defter(monkeypatch, tmp_path):
    """İzleme defterini geçici dosyaya alır."""
    monkeypatch.setattr(izleme, "DOSYA", tmp_path / "izleme.json")
    return tmp_path


# ── günlük özet ────────────────────────────────────────────────────────────

def test_ozet_temel_rakamlari_tasir():
    m = bildirim.gunluk_ozet(OZET)
    assert "2026-08-25" in m
    assert "28 yükselen" in m and "69 düşen" in m


def test_reel_getiri_negatifse_uyarir():
    """Nominal rakama sevinmek en sık tuzak; reel negatifse yazılmalı."""
    assert "reel" in bildirim.gunluk_ozet(OZET)


def test_reel_pozitifse_uyari_yok():
    m = bildirim.gunluk_ozet({**OZET, "bist_reel_1y": 4.2})
    assert "reel" not in m


def test_karantinali_sinyal_gizlenmez():
    """'Sinyal yok' ile 'sinyal var ama önerilmiyor' farklı şeyler."""
    m = bildirim.gunluk_ozet(OZET, {"trend": {"onerilir": False}})
    assert "karantina" in m.lower()
    assert "Önerilen sinyal yok" in m


def test_onerilen_sinyal_listelenir():
    o = {**OZET, "sinyal_veren": [
        {"sembol": "THYAO", "skor": 71, "fiyat": 250.0,
         "sinyaller": ["tepki"], "karantina": [], "onerilir": True}]}
    m = bildirim.gunluk_ozet(o)
    assert "THYAO" in m and "1 sinyal" in m


def test_hic_sinyal_yoksa_nakit_hatirlatilir():
    m = bildirim.gunluk_ozet({**OZET, "sinyal_veren": []})
    assert "Nakitte beklemek" in m


def test_bozuk_ozet_cokme_uretmez():
    assert "çıkarılamadı" in bildirim.gunluk_ozet({"hata": "yok"})
    assert bildirim.gunluk_ozet({})


def test_ozet_telegram_sinirinin_altinda():
    """4096 karakteri aşan mesaj bölünür; özet tek parça kalmalı."""
    o = {**OZET, "sinyal_veren": [
        {"sembol": f"HISSE{i}", "skor": 70, "fiyat": 10.0,
         "sinyaller": ["tepki"], "onerilir": True} for i in range(40)]}
    assert len(bildirim.gunluk_ozet(o)) < telegram.AZAMI_UZUNLUK


def test_sirket_adindaki_isaretler_kacirilir():
    """& ve < HTML kipini bozar, mesaj hiç gitmez."""
    m = bildirim.gunluk_ozet({**OZET, "rejim": {"ad": "risk <açık> & sıcak"}})
    assert "&lt;" in m and "&amp;" in m


# ── stop uyarısı ───────────────────────────────────────────────────────────

POZ = {"sembol": "THYAO", "stop": 250.0, "hedef": 300.0, "giris": 260.0}


def test_stop_gecti_mesaji_rakamlari_tasir():
    m = bildirim.stop_uyarisi(POZ, 248.0, "stop_gecti")
    assert "THYAO" in m and "248" in m and "250" in m


def test_stop_mesaji_emir_vermedigini_soyler():
    """Sistem emir göndermez; mesaj bunu açıkça söylemeli."""
    assert "emir göndermez" in bildirim.stop_uyarisi(POZ, 248.0, "stop_gecti")


def test_hedef_mesaji_kar_yuzdesini_hesaplar():
    m = bildirim.stop_uyarisi(POZ, 300.0, "hedef_gecti")
    assert "+15.4%" in m


# ── izleme defteri ─────────────────────────────────────────────────────────

def test_pozisyon_eklenir_ve_listelenir(defter):
    izleme.ekle("THYAO", 250, 300, 260)
    assert [p["sembol"] for p in izleme.liste()] == ["THYAO"]


def test_ayni_sembol_iki_kez_eklenmez(defter):
    izleme.ekle("THYAO", 250, 300)
    izleme.ekle("THYAO", 255, 310)
    assert len(izleme.liste()) == 1
    assert izleme.liste()[0]["stop"] == 255


def test_is_uzantisi_temizlenir(defter):
    izleme.ekle("THYAO.IS", 250)
    assert izleme.liste()[0]["sembol"] == "THYAO"


def test_silinen_pozisyon_izlenmez(defter):
    izleme.ekle("THYAO", 250)
    assert izleme.sil("thyao") is True
    assert izleme.liste() == []


# ── alarm mantığı ──────────────────────────────────────────────────────────

def test_stop_gecilince_uyarir(defter):
    izleme.ekle("THYAO", 250, 300)
    u = izleme.kontrol(lambda s: 245.0)
    assert [t for _, _, t in u] == ["stop_gecti"]


def test_hedef_gecilince_uyarir(defter):
    izleme.ekle("THYAO", 250, 300)
    assert [t for _, _, t in izleme.kontrol(lambda s: 305.0)] == ["hedef_gecti"]


def test_stopa_yaklasinca_onceden_uyarir(defter):
    izleme.ekle("THYAO", 250, 300)
    assert [t for _, _, t in izleme.kontrol(lambda s: 253.0)] == ["stop_yakin"]


def test_guvenli_bolgede_uyari_yok(defter):
    izleme.ekle("THYAO", 250, 300)
    assert izleme.kontrol(lambda s: 275.0) == []


def test_ayni_uyari_gunde_bir_kez(defter):
    """İş 5 dakikada bir çalışıyor. Her turda mesaj atmak botu
    susturulmaya götürür — susturulmuş bot hiç uyarı vermez."""
    izleme.ekle("THYAO", 250, 300)
    assert len(izleme.kontrol(lambda s: 245.0)) == 1
    assert izleme.kontrol(lambda s: 245.0) == []
    assert izleme.kontrol(lambda s: 240.0) == []


def test_yeni_gunde_tekrar_uyarir(defter):
    izleme.ekle("THYAO", 250, 300)
    izleme.kontrol(lambda s: 245.0)
    d = json.loads(izleme.DOSYA.read_text(encoding="utf-8"))
    dun = (date.today() - timedelta(days=1)).isoformat()
    d["pozisyonlar"][0]["uyarildi"]["stop_gecti"] = dun
    izleme.DOSYA.write_text(json.dumps(d), encoding="utf-8")
    assert len(izleme.kontrol(lambda s: 245.0)) == 1


def test_fiyat_gelmezse_sessiz(defter):
    """Veri yokluğu alarm sebebi değildir — yanlış alarm gerçek alarmı
    değersizleştirir."""
    izleme.ekle("THYAO", 250, 300)
    assert izleme.kontrol(lambda s: None) == []


def test_fiyat_getirici_patlarsa_diger_pozisyonlar_kontrol_edilir(defter):
    izleme.ekle("BOZUK", 100)
    izleme.ekle("THYAO", 250, 300)

    def getir(s):
        if s == "BOZUK":
            raise RuntimeError("veri yok")
        return 245.0

    assert [p["sembol"] for p, _, _ in izleme.kontrol(getir)] == ["THYAO"]


# ── yapılandırma yoksa ─────────────────────────────────────────────────────

def test_yapilandirma_yoksa_sessizce_kapali(monkeypatch):
    monkeypatch.delenv("MIDAS_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("MIDAS_TELEGRAM_SOHBET", raising=False)
    assert telegram.kurulu_mu() is False
    assert telegram.gonder("deneme") is False


def test_uzun_mesaj_bolunur(monkeypatch):
    """Kesmek yerine bölmek: kesilen yerde önemli bilgi kalabilir."""
    monkeypatch.setenv("MIDAS_TELEGRAM_TOKEN", "sahte")
    monkeypatch.setenv("MIDAS_TELEGRAM_SOHBET", "1")
    gonderilen = []
    monkeypatch.setattr(telegram, "_cagir",
                        lambda y, v, **k: gonderilen.append(v["text"]) or {"ok": True})
    telegram.gonder("satır\n" * 2000)
    assert len(gonderilen) > 1
    assert all(len(x) <= telegram.AZAMI_UZUNLUK for x in gonderilen)


# ── bot komutları ──────────────────────────────────────────────────────────

@pytest.fixture
def komut(defter, monkeypatch):
    """Komut işleyiciyi sahte fiyatla çalıştırır."""
    from cekirdek import bot_calistir
    monkeypatch.setattr(bot_calistir, "_fiyat_getir", lambda s: 260.0)
    return bot_calistir._komut_isle


def test_izle_komutu_pozisyon_ekler(komut):
    c = komut("/izle THYAO 250 300")
    assert "THYAO" in c and "izlemeye alındı" in c
    assert izleme.liste()[0]["stop"] == 250.0


def test_izle_virgullu_sayi_kabul_eder(komut):
    """Türkçe klavyede ondalık ayırıcı virgül."""
    komut("/izle THYAO 250,5 300")
    assert izleme.liste()[0]["stop"] == 250.5


def test_izle_eksik_parametrede_kullanim_gosterir(komut):
    assert "Kullanım" in komut("/izle THYAO")


def test_izle_bozuk_sayida_cokmez(komut):
    assert "okunamadı" in komut("/izle THYAO abc")


def test_bilinmeyen_kod_eklenmez(defter, monkeypatch):
    """Yanlış yazılan kod sessizce eklenirse hiç uyarı gelmez."""
    from cekirdek import bot_calistir
    monkeypatch.setattr(bot_calistir, "_fiyat_getir", lambda s: None)
    assert "bulunamadı" in bot_calistir._komut_isle("/izle XYZQ 10")
    assert izleme.liste() == []


def test_liste_komutu(komut):
    assert "yok" in komut("/liste")
    komut("/izle THYAO 250 300")
    assert "THYAO" in komut("/liste")


def test_birak_komutu(komut):
    komut("/izle THYAO 250")
    assert "Bırakıldı" in komut("/birak THYAO")


def test_yardim_komutlari_listeler(komut):
    y = komut("/yardim")
    for k in ("/izle", "/birak", "/liste", "/durum"):
        assert k in y


def test_bot_emir_vermedigini_soyler(komut):
    assert "emir göndermez" in komut("/yardim")


def test_grup_soneki_temizlenir(komut):
    """Gruplarda komutlar /izle@botadi biçiminde gelir."""
    assert "Kullanım" in komut("/izle@midas_bot")


def test_bilinmeyen_komut_yonlendirir(komut):
    assert "/yardim" in komut("/olmayan")


# ── genişletilmiş komutlar ─────────────────────────────────────────────────

def test_menu_ve_yardim_ayni_kaynaktan(komut):
    """Menü ile yardım metni ayrışırsa kullanıcı olmayan komutu dener."""
    y = komut("/yardim")
    for k, _ in bildirim.KOMUTLAR:
        assert f"/{k}" in y, f"{k} yardımda yok"


def test_duz_hisse_kodu_analiz_edilir(defter, monkeypatch):
    """'/hisse THYAO' yerine sadece 'THYAO' yazmak daha doğal."""
    from cekirdek import bot_calistir
    monkeypatch.setattr(bot_calistir, "_hisse_ozeti", lambda k: f"ANALIZ:{k}")
    assert bot_calistir._komut_isle("THYAO") == "ANALIZ:THYAO"
    assert bot_calistir._komut_isle("thyao") == "ANALIZ:THYAO"


def test_duz_metin_hisse_sanilmaz(defter, monkeypatch):
    """Rastgele yazı hisse kodu sanılıp boşuna analiz edilmemeli."""
    from cekirdek import bot_calistir
    monkeypatch.setattr(bot_calistir, "_hisse_ozeti",
                        lambda k: pytest.fail("analiz çağrılmamalıydı"))
    assert "Anlamadım" in bot_calistir._komut_isle("merhaba nasılsın")
    assert "Anlamadım" in bot_calistir._komut_isle("AB")


def test_hisse_komutu_eksik_parametrede_kullanim(komut):
    assert "Kullanım" in komut("/hisse")


def test_uzun_yoklama_zaman_asimini_buyutur(monkeypatch):
    """urlopen zaman aşımı Telegram'ınkinden büyük olmalı, yoksa
    bağlantı sunucu cevap vermeden kopar."""
    monkeypatch.setenv("MIDAS_TELEGRAM_TOKEN", "sahte")
    monkeypatch.setenv("MIDAS_TELEGRAM_SOHBET", "1")
    yakalanan = {}

    def sahte(yontem, veri, zaman_asimi=20.0):
        yakalanan["telegram"] = veri.get("timeout")
        yakalanan["urlopen"] = zaman_asimi
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram, "_cagir", sahte)
    telegram.komutlari_oku(0, bekle=45)
    assert yakalanan["urlopen"] > yakalanan["telegram"]


# ═══════════════════════════════════════════════ vade ve yaklaşanlar
# "Bugün al" ile "hiçbir şey yok" arasındaki alanı anlatan iki ekleme:
# sinyalin tipik tutma süresi ve tek koşulu eksik hisseler.

def _ozet_yaklasanli(sinyal_var: bool = False) -> dict:
    return {
        "tarih": "2026-08-28", "endeks_degisim": -0.4,
        "yukselen": 38, "dusen": 55,
        "sinyal_veren": ([{"sembol": "EUPWR", "sinyaller": ["trend"],
                           "skor": 71, "fiyat": 12.4, "onerilir": True,
                           "vade": "1-2 hafta"}] if sinyal_var else []),
        "yaklasanlar": [
            {"sembol": "SOKM", "strateji": "trend", "karsilanan": 3,
             "toplam": 4, "mesaj": "EMA20'ye %0,8 gerilemesi gerekiyor"},
            {"sembol": "ENERY", "strateji": "kirilim", "karsilanan": 3,
             "toplam": 4, "mesaj": "tek eksik: hacim teyidi"},
        ],
    }


def test_vade_sinyal_satirinda_gorunur():
    m = bildirim.gunluk_ozet(_ozet_yaklasanli(sinyal_var=True), {})
    assert "tipik tutma: 1-2 hafta" in m


def test_yaklasanlar_mesaja_giriyor():
    m = bildirim.gunluk_ozet(_ozet_yaklasanli(), {})
    assert "2 hisse sinyale yakın" in m
    assert "SOKM" in m and "ENERY" in m


def test_yaklasan_sinyal_sanilmamali():
    """En pahalı yanılgı: izleme listesini alım listesi sanmak."""
    m = bildirim.gunluk_ozet(_ozet_yaklasanli(), {})
    assert "sinyal DEĞİL" in m


def test_yaklasanlar_bos_ise_blok_hic_cikmaz():
    o = _ozet_yaklasanli()
    o["yaklasanlar"] = []
    m = bildirim.gunluk_ozet(o, {})
    assert "sinyale yakın" not in m
    assert "Bugün sinyal yok" in m


def test_push_sinyal_yokken_yaklasanlari_soyler():
    bas, govde = bildirim.gunluk_push(_ozet_yaklasanli())
    assert "SOKM" in govde and "yakın 2" in govde


def test_push_sinyal_varken_yaklasanlari_one_cikarmaz():
    """Sinyal varken push'un konusu sinyaldir; yaklaşan gürültü olur."""
    _, govde = bildirim.gunluk_push(_ozet_yaklasanli(sinyal_var=True))
    assert "EUPWR" in govde and "SOKM" not in govde


def test_eski_ozet_yeni_alanlarsiz_calisir():
    """Sunucudaki eski kayıtlarda `yaklasanlar` ve `vade` yok."""
    eski = {"tarih": "2026-01-02", "endeks_degisim": 0.3,
            "yukselen": 50, "dusen": 40,
            "sinyal_veren": [{"sembol": "THYAO", "sinyaller": ["tepki"],
                              "skor": 60, "fiyat": 300.0, "onerilir": True}]}
    m = bildirim.gunluk_ozet(eski, {})
    assert "THYAO" in m and "tipik tutma" not in m
    assert bildirim.gunluk_push(eski)[1]
