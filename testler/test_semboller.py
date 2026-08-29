"""Sembol arama — "thy" yazınca THYAO çıkmalı.

Bu dosyanın iki işi var:
  1. Gösterim adının KAP unvanından doğru türetildiğini kilitlemek
     (Türkçe büyük/küçük harf, hukuki sonekler).
  2. Sıralama kurallarını kilitlemek. AYNI KURALLAR MOBİLDE DE VAR
     (mobil/lib/servis/semboller.dart); ikisi ayrışırsa aynı sorgu iki
     yerde farklı sonuç verir. mobil/test/semboller_test.dart aynı
     örnekleri kullanıyor.
"""
import pytest

from cekirdek import semboller as s


# ── gösterim adı ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("unvan,beklenen", [
    ("TÜRK HAVA YOLLARI A.O.", "Türk Hava Yolları"),
    ("TÜRKİYE İŞ BANKASI A.Ş.", "Türkiye İş Bankası"),
    ("ALARKO HOLDİNG A.Ş.", "Alarko Holding"),
    ("ŞEKERBANK T.A.Ş.", "Şekerbank"),
    ("ASELSAN ELEKTRONİK SANAYİ VE TİCARET A.Ş.", "Aselsan Elektronik"),
    ("KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.",
     "Kardemir Karabük Demir Çelik"),
])
def test_gosterim_adi(unvan, beklenen):
    assert s.gosterim_adi(unvan) == beklenen


def test_holding_atilmaz():
    """'Alarko' tek başına şirketi tanıtmıyor; HOLDİNG adın parçası."""
    assert "Holding" in s.gosterim_adi("ALARKO HOLDİNG A.Ş.")


def test_baglaclar_kucuk_kalir():
    assert s.gosterim_adi("ANADOLU EFES BİRACILIK VE MALT SANAYİİ A.Ş.") \
        == "Anadolu Efes Biracılık ve Malt Sanayii"


def test_turkce_i_harfi_dogru_donusur():
    """Python'un .title()'ı 'İŞ' → 'İş' yerine 'Iş' yapar."""
    assert s.gosterim_adi("İŞ YATIRIM MENKUL DEĞERLER A.Ş.") \
        .startswith("İş Yatırım")


def test_bos_unvan_cokmez():
    assert s.gosterim_adi("") == ""


def test_yalnizca_hukuki_sonekten_ibaret_unvan_korunur():
    assert s.gosterim_adi("A.Ş.") == "A.Ş."


# ── arama ─────────────────────────────────────────────────────────────────

# Mobil testi de bu listeyi kullanıyor. Değiştirirsen ikisini birlikte
# değiştir, yoksa iki tarafta farklı sonuç çıkar.
ORNEK = [
    {"k": "THYAO", "a": "Türk Hava Yolları", "i": 1,
     "n": ["THYAO", "TURK HAVA YOLLARI", "THY"]},
    {"k": "TSKB", "a": "Türkiye Sınai Kalkınma Bankası", "i": 1,
     "n": ["TSKB", "TURKIYE SINAI KALKINMA BANKASI"]},
    {"k": "ISCTR", "a": "Türkiye İş Bankası", "i": 1,
     "n": ["ISCTR", "TURKIYE IS BANKASI"]},
    {"k": "ISATR", "a": "Türkiye İş Bankası", "i": 0,
     "n": ["ISATR", "TURKIYE IS BANKASI"]},
    {"k": "KCHOL", "a": "Koç Holding", "i": 1,
     "n": ["KCHOL", "KOC HOLDING"]},
    {"k": "KOCFN", "a": "Koç Finansman", "i": 0,
     "n": ["KOCFN", "KOC FINANSMAN"]},
    {"k": "EREGL", "a": "Ereğli Demir ve Çelik", "i": 1,
     "n": ["EREGL", "EREGLI DEMIR VE CELIK", "ERDEMIR"]},
]


def _ilk(sorgu):
    r = s.ara(sorgu, ORNEK, azami=5)
    return r[0]["k"] if r else None


@pytest.mark.parametrize("sorgu,beklenen", [
    ("thy", "THYAO"),            # kod ön eki
    ("THYAO", "THYAO"),          # tam kod
    ("türk hava", "THYAO"),      # ad, Türkçe karakterli
    ("turk hava", "THYAO"),      # ad, sadeleştirilmiş
    ("erdemir", "EREGL"),        # takma ad
    ("koç", "KCHOL"),            # takip edilen, kod ön ekini yener
    ("KOCFN", "KOCFN"),          # tam kod her şeyi yener
    ("iş bankası", "ISCTR"),     # doğru Türkçe
    ("is bankasi", "ISCTR"),     # ASCII
    ("ıs bankası", "ISCTR"),     # noktasız ı
    ("İŞ BANKASI", "ISCTR"),     # tümü büyük
])
def test_arama_sirasi(sorgu, beklenen):
    assert _ilk(sorgu) == beklenen


def test_takip_edilen_kod_on_ekini_YENER():
    """"koç" yazan kullanıcı Koç Holding'i arıyor. Ama KOCFN'nin KODU
    da 'KOC' ile başlıyor ve kod ön eki normalde ad eşleşmesinden
    güçlü — bu kural 'thy' için doğru, 'koç' için yanlıştı."""
    assert [x["k"] for x in s.ara("koç", ORNEK)][:2] == ["KCHOL", "KOCFN"]


def test_tam_kod_takip_edilmeyeni_de_one_alir():
    assert _ilk("KOCFN") == "KOCFN"


def test_ayni_unvanda_takip_edilen_once():
    r = [x["k"] for x in s.ara("is bankasi", ORNEK)]
    assert r.index("ISCTR") < r.index("ISATR")


def test_bos_sorgu_bos_sonuc():
    assert s.ara("", ORNEK) == []
    assert s.ara("   ", ORNEK) == []


def test_eslesmeyen_sorgu_bos_sonuc():
    assert s.ara("zzzqqq", ORNEK) == []


def test_azami_sinira_uyar():
    assert len(s.ara("t", ORNEK, azami=2)) <= 2


# ── gerçek liste ──────────────────────────────────────────────────────────

def test_gercek_liste_evreni_kapsiyor():
    from cekirdek import evren
    L = s.liste()
    kodlar = {x["k"] for x in L}
    eksik = [x for x in evren.evren_getir("hepsi") if x not in kodlar]
    assert not eksik, f"evrende olup listede olmayan: {eksik}"


def test_gercek_listede_thyao_adi_var():
    L = {x["k"]: x for x in s.liste()}
    assert L["THYAO"]["a"] == "Türk Hava Yolları"
    assert L["THYAO"]["i"] == 1


def test_kisa_kodlar_ayiklanir():
    """3 harfli KAP üyeleri borsada işlem görmüyor — arama gürültüsü."""
    L = s.liste()
    kisa = [x["k"] for x in L if len(x["k"]) < 4 and not x["i"]]
    assert kisa == []


def test_liste_makul_boyutta():
    """Telefona indirilecek: büyürse arama gecikir."""
    import json
    ham = json.dumps(s.liste(), ensure_ascii=False).encode()
    assert len(ham) < 250_000, f"{len(ham)} bayt — fazla büyük"


# ── iki dilli normalize kilidi ─────────────────────────────────────────────
#
# mobil/lib/servis/semboller.dart aynı sadeleştirmeyi Dart'ta yeniden
# yazıyor (zorunlu: sorgu telefonda normalize ediliyor). İkisi ayrışırsa
# aynı arama iki yerde farklı sonuç verir.
#
# Ortak örnek dosyası bunu yakalıyor — ama dosya bayatlarsa yakalayamaz.
# Aşağıdaki testler dosyanın güncel ve iki tarafta AYNI olduğunu
# garantiliyor.

_ORNEK_YOL = "testler/normalize_ornekleri.json"
_MOBIL_YOL = "mobil/test/veri/normalize_ornekleri.json"


def _ornekler(yol):
    import json
    from pathlib import Path
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def test_normalize_ornekleri_GUNCEL():
    """Dosya, normalize'ın BUGÜNKÜ çıktısını yansıtmalı.

    Kırılırsa: normalize değişmiş demektir. Dosyayı yeniden üret ve
    mobil kopyasını da güncelle — yoksa Dart tarafı eski davranışı
    doğru sanmaya devam eder.
    """
    from cekirdek.haber_esleme import normalize
    bozuk = [o for o in _ornekler(_ORNEK_YOL)
             if normalize(o["girdi"]) != o["cikti"]]
    assert not bozuk, (
        f"{len(bozuk)} örnek bayat, ilki: {bozuk[0]} — "
        f"dosyayı yeniden üret ve {_MOBIL_YOL} kopyasını da güncelle")


def test_mobil_kopyasi_AYNI():
    """Dart testi kendi kopyasını okuyor; ikisi ayrışırsa mobil taraf
    olmayan bir davranışı doğruluyor olur."""
    assert _ornekler(_ORNEK_YOL) == _ornekler(_MOBIL_YOL), (
        f"{_MOBIL_YOL} güncel değil")


def test_ornekler_turkcenin_tuzaklarini_kapsiyor():
    """Örnek dosyası zayıflarsa test bir şey kanıtlamaz."""
    girdiler = " ".join(o["girdi"] for o in _ornekler(_ORNEK_YOL))
    for harf in "İıŞşĞğÜüÖöÇçÂâ":
        assert harf in girdiler, f"'{harf}' örneklerde yok"
