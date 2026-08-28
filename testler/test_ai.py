"""AI katmanının güvenlik kuralları — API anahtarı GEREKTİRMEZ.

Buradaki testlerin tamamı sahte yanıtlarla çalışır. Sebebi tek: bu katmanın
riski modelin ne kadar iyi düşündüğü değil, KÖTÜ ÇIKTIYI nasıl karşıladığımız.
Model uydurma bir hisse kodu döndürdüğünde onu kaydedersek kullanıcı olmayan
bir gerekçeye dayanıp işlem yapar.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import os
from types import SimpleNamespace as N

import pytest

from cekirdek import ai, haber_ai

B = haber_ai.HaberBagi
S = haber_ai.HaberSonuc

HABERLER = [
    {"id": "h0", "baslik": "Gıda devinde yönetim değişikliği", "ozet": ""},
    {"id": "h1", "baslik": "Enflasyon beklentinin altında geldi", "ozet": ""},
    {"id": "h2", "baslik": "THYAO yeni uçak siparişi verdi", "ozet": ""},
]


@pytest.fixture
def sahte(monkeypatch):
    """ai._cagir'i sabit bir model çıktısıyla değiştirir."""
    def kur(cikti, hata=None):
        def f(is_adi, sistem, mesaj, azami=2000, sema=None):
            return (None, hata) if hata else (N(parsed_output=cikti), None)
        monkeypatch.setattr(ai, "_cagir", f)
    return kur


# ── uydurma çıktıya karşı savunma ───────────────────────────────────────

@pytest.mark.parametrize("ad,bag", [
    ("uydurma kod", B(sira=0, sembol="ZZZZZ", tur="yonetim", onemli=True, gerekce="x")),
    ("evren dışı", B(sira=0, sembol="AAPL", tur="yonetim", onemli=True, gerekce="x")),
    ("sıra taşkını", B(sira=99, sembol="ULKER", tur="yonetim", onemli=True, gerekce="x")),
    ("negatif sıra", B(sira=-1, sembol="ULKER", tur="yonetim", onemli=True, gerekce="x")),
])
def test_gecersiz_bag_atilir(sahte, ad, bag):
    sahte(S(baglar=[bag]))
    sonuc, hata = haber_ai.sinifla(HABERLER)
    assert sonuc == [], f"{ad}: geçersiz bağ kaydedildi"
    assert hata is None


def test_gecerli_bag_gecer(sahte):
    sahte(S(baglar=[B(sira=2, sembol="THYAO", tur="sozlesme",
                      onemli=True, gerekce="uçak siparişi")]))
    sonuc, hata = haber_ai.sinifla(HABERLER)
    assert hata is None
    assert len(sonuc) == 1
    assert sonuc[0]["sembol"] == "THYAO"
    assert sonuc[0]["haber_id"] == "h2"
    assert sonuc[0]["onemli"] is True


def test_kucuk_harf_kod_normallesir(sahte):
    sahte(S(baglar=[B(sira=0, sembol="ulker", tur="yonetim",
                      onemli=True, gerekce="x")]))
    sonuc, _ = haber_ai.sinifla(HABERLER)
    assert sonuc[0]["sembol"] == "ULKER"


def test_bilinmeyen_tur_digere_duser(sahte):
    """Serbest etiket kabul edersek her gün başka bir tür üretir, sayamayız."""
    sahte(S(baglar=[B(sira=0, sembol="ULKER", tur="uyduruk",
                      onemli=True, gerekce="x")]))
    sonuc, _ = haber_ai.sinifla(HABERLER)
    assert sonuc[0]["tur"] == "diger"


def test_bos_liste_gecerli_cevap(sahte):
    sahte(S(baglar=[]))
    assert haber_ai.sinifla(HABERLER) == ([], None)


# ── hata yolları: sistem çalışmaya devam etmeli ─────────────────────────

def test_model_hatasinda_bos_doner(sahte):
    sahte(None, hata="AI hatası: bağlantı yok")
    sonuc, hata = haber_ai.sinifla(HABERLER)
    assert sonuc == []
    assert "bağlantı" in hata


def test_bos_cikti_hata_sayilir(sahte):
    sahte(None)          # parsed_output = None
    sonuc, hata = haber_ai.sinifla(HABERLER)
    assert sonuc == [] and hata


def test_habersiz_cagri_api_ye_gitmez(monkeypatch):
    """Boş listede API'ye gidilirse boşuna para harcanır."""
    def patlat(*a, **k):
        raise AssertionError("boş haber listesinde API çağrıldı")
    monkeypatch.setattr(ai, "_cagir", patlat)
    assert haber_ai.sinifla([]) == ([], None)


# ── kelime eşlemesi taban kalmalı ───────────────────────────────────────

def test_kelime_eslemesi_cakismada_kazanir():
    kel = [{"haber_id": "h1", "sembol": "ULKER", "ifade": "ULKER"}]
    aies = [
        {"haber_id": "h1", "sembol": "ULKER", "ifade": "ai:yonetim", "onemli": True},
        {"haber_id": "h2", "sembol": "THYAO", "ifade": "ai:sozlesme", "onemli": True},
        {"haber_id": "h3", "sembol": "GARAN", "ifade": "ai:diger?", "onemli": False},
    ]
    birlesik, bilgi = haber_ai.birlestir(kel, aies)
    assert bilgi == {"kelime": 1, "ai_yeni": 2, "ai_onemli": 1}
    # Elle yazılmış takma ad listesi modelden daha güvenilir.
    assert birlesik[0]["ifade"] == "ULKER"
    assert len(birlesik) == 3


def test_ai_bos_olsa_da_kelime_korunur():
    kel = [{"haber_id": "h1", "sembol": "ULKER", "ifade": "ULKER"}]
    birlesik, bilgi = haber_ai.birlestir(kel, [])
    assert birlesik == kel
    assert bilgi["ai_yeni"] == 0


# ── maliyet hesabı ──────────────────────────────────────────────────────

def test_maliyet_gercek_fiyatlarla():
    kul = N(input_tokens=4200, output_tokens=800,
            cache_creation_input_tokens=0, cache_read_input_tokens=0)
    usd, tl = ai._maliyet_tl("claude-haiku-4-5", kul, 48.0)
    # 4200*1 + 800*5 = 8200 / 1e6 = $0.0082
    assert usd == pytest.approx(0.0082, rel=1e-6)
    assert tl == pytest.approx(0.0082 * 48.0, rel=1e-6)


def test_onbellek_okuma_ucuzdur():
    onb = N(input_tokens=200, output_tokens=500,
            cache_creation_input_tokens=0, cache_read_input_tokens=1300)
    tam = N(input_tokens=1500, output_tokens=500,
            cache_creation_input_tokens=0, cache_read_input_tokens=0)
    a = ai._maliyet_tl("claude-sonnet-5", onb, 48.0)[0]
    b = ai._maliyet_tl("claude-sonnet-5", tam, 48.0)[0]
    assert a < b, "önbellek okuma indirimi uygulanmıyor"


def test_eksik_usage_alani_cokertmez():
    """SDK alanı hiç döndürmezse çökmemeli — para gitmiş sayılmalı."""
    bos = N(input_tokens=10, output_tokens=5)
    usd, tl = ai._maliyet_tl("claude-haiku-4-5", bos, 48.0)
    assert usd > 0 and tl > 0


def test_bilinmeyen_model_varsayilana_duser():
    kul = N(input_tokens=1000, output_tokens=100,
            cache_creation_input_tokens=0, cache_read_input_tokens=0)
    a = ai._maliyet_tl("uydurma-model", kul, 48.0)
    b = ai._maliyet_tl(ai.VARSAYILAN_MODEL, kul, 48.0)
    assert a == b


def test_her_isin_modeli_fiyat_tablosunda_var():
    """Fiyatı bilinmeyen modele iş atarsak bütçe yanlış sayar."""
    for isim, model in ai.MODELLER.items():
        assert model in ai.FIYAT, f"{isim} -> {model} fiyat tablosunda yok"


# ── bütçe tavanı ────────────────────────────────────────────────────────

def test_tavan_asilinca_cagri_durur(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sahte")
    monkeypatch.setattr(ai, "AYLIK_TAVAN_TL", 100.0)
    monkeypatch.setattr(ai.ambar, "ai_ay_toplami", lambda *a, **k: 100.01)
    ok, sebep = ai.kullanilabilir()
    assert ok is False
    assert "bütçe" in sebep


def test_tavan_altinda_calisir(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sahte")
    monkeypatch.setattr(ai, "AYLIK_TAVAN_TL", 100.0)
    monkeypatch.setattr(ai.ambar, "ai_ay_toplami", lambda *a, **k: 99.99)
    assert ai.kullanilabilir()[0] is True


def test_tavan_sifir_sinirsiz_demek(monkeypatch):
    monkeypatch.setattr(ai, "AYLIK_TAVAN_TL", 0.0)
    monkeypatch.setattr(ai.ambar, "ai_ay_toplami", lambda *a, **k: 5000.0)
    b = ai.butce_durumu()
    assert b["asildi"] is False
    assert b["tavan_tl"] is None


def test_anahtarsiz_calismaz(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ok, sebep = ai.kullanilabilir()
    assert ok is False and "ANTHROPIC_API_KEY" in sebep


# ── .env yükleyici ──────────────────────────────────────────────────────
# Yük taşıyan bir parça: anahtar buradan gelmezse akşamki zamanlanmış iş
# AI katmanını sessizce atlar ve kimse fark etmez.

from cekirdek import ortam   # noqa: E402


@pytest.fixture
def env_dosyasi(tmp_path):
    def yaz(icerik):
        y = tmp_path / "t.env"
        y.write_text(icerik, encoding="utf-8")
        return y
    return yaz


def test_temel_okuma(env_dosyasi, monkeypatch):
    monkeypatch.delenv("BIR_DEGISKEN", raising=False)
    ortam.yukle(env_dosyasi("BIR_DEGISKEN=deger\n"))
    assert os.environ["BIR_DEGISKEN"] == "deger"


@pytest.mark.parametrize("satir,beklenen", [
    ('export A_X="tirnakli"', "tirnakli"),
    ("A_X='tek tirnak'", "tek tirnak"),
    ("  A_X = bosluklu  ", "bosluklu"),
    ("A_X=sk-ant-api03-abc_DEF-123", "sk-ant-api03-abc_DEF-123"),
    ("A_X=deger=icinde=esittir", "deger=icinde=esittir"),
])
def test_bicimler(env_dosyasi, monkeypatch, satir, beklenen):
    monkeypatch.delenv("A_X", raising=False)
    ortam.yukle(env_dosyasi(satir + "\n"))
    assert os.environ.get("A_X") == beklenen


def test_yorum_ve_bozuk_satir_atlanir(env_dosyasi, monkeypatch):
    monkeypatch.delenv("A_Y", raising=False)
    n = ortam.yukle(env_dosyasi("# yorum\n\nBOZUKSATIR\nA_Y=1\n"))
    assert n == 1 and os.environ["A_Y"] == "1"


def test_bos_deger_tanimlamaz(env_dosyasi, monkeypatch):
    """`ANTHROPIC_API_KEY=` yazan şablon, anahtarı 'tanımlı' saymamalı —
    yoksa kullanilabilir() yalan söyler ve çağrı 401 ile patlar."""
    monkeypatch.delenv("A_Z", raising=False)
    ortam.yukle(env_dosyasi("A_Z=\n"))
    assert "A_Z" not in os.environ


def test_mevcut_deger_ezilmez(env_dosyasi, monkeypatch):
    """Tek seferlik deneme dosyayı geçersiz kılabilmeli."""
    monkeypatch.setenv("A_W", "elle")
    ortam.yukle(env_dosyasi("A_W=dosyadan\n"))
    assert os.environ["A_W"] == "elle"


def test_ez_bayragi_calisir(env_dosyasi, monkeypatch):
    monkeypatch.setenv("A_V", "elle")
    ortam.yukle(env_dosyasi("A_V=dosyadan\n"), ez=True)
    assert os.environ["A_V"] == "dosyadan"


def test_dosya_yoksa_hata_degil(tmp_path):
    assert ortam.yukle(tmp_path / "yok.env") == 0


def test_durum_deger_sizdirmaz(monkeypatch):
    """durum() ekrana/loga basılıyor; anahtarın kendisi ASLA çıkmamalı."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-gizli-deger-123")
    d = ortam.durum()
    assert d["anthropic"] is True
    assert "gizli" not in repr(d)
