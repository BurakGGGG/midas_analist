"""Bedelsiz ve sermaye artırımı uyarısı.

BU ÖZELLİĞİN VARLIK SEBEBİ TEK: bedelsizden sonra fiyat MEKANİK olarak
düşer. Hisse ucuzlamaz, adet artar, toplam para aynı kalır. Bunu
bilmeyen kullanıcı aracı kurum ekranında -%50 görüp panik satar —
hiçbir şey olmadığı bir günde hayatının en pahalı kararını verir.

TESPİT KESİN, ORAN "ÇIKARABİLİRSEM": hangi hissede işlem olduğu KAP'ın
konu başlığından geliyor. Oran serbest metinde ve her şirket aynı
cümleyi kurmuyor — çıkaramadığımızda oran yazılmıyor, uyarı yine
veriliyor. Yanlış oran yazmak hiç yazmamaktan kötüdür.
"""
import pytest

from cekirdek import sermaye_islemi as si


# ── tespit ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin,beklenen", [
    ("Bedelsiz Sermaye Artırımı Hk.", "bedelsiz sermaye artırımı"),
    ("Sermaye Artırımına İlişkin Bildirim", "sermaye artırımı"),
    # Türkçe çekim tuzağı: aynı olay, farklı kelime. Kök eşleştirmesi
    # olmadan canlı KAP'ta bu satır sessizce kaçıyordu.
    ("Kayıtlı Sermaye Tavanının ve Çıkarılmış Sermayenin Artırılmasına "
     "İlişkin Esas Sözleşme Değişikliği", "sermaye artırımı"),
    ("Sermayenin artırılması kararı", "sermaye artırımı"),
    ("Sermaye Azaltımı Hakkında", "sermaye azaltımı"),
    ("Şirket Bölünme İşlemi", "bölünme"),
    ("Pay Birleştirme İşlemi", "pay birleştirme"),
])
def test_sermaye_islemi_taniniyor(metin, beklenen):
    assert si.ilgili_mi(metin) == beklenen


@pytest.mark.parametrize("metin", [
    "Kayıtlı Sermaye Tavanı Süre Uzatımı",
    "Şirket Genel Bilgi Formu",
    "Yeni İş İlişkisi",
    "Sürdürülebilirlik Raporu",
    "Transfer Görüşmeleri",
    "",
])
def test_ilgisiz_bildirim_uyari_uretmez(metin):
    """Rutin bildirimi uyarıya çevirmek her ay boşuna panik yaratırdı.
    'Kayıtlı sermaye TAVANI süre uzatımı' sermaye artırımı DEĞİL —
    yalnızca iznin uzatılması."""
    assert si.ilgili_mi(metin) == ""


def test_fiyati_bolen_islemler_ayirt_ediliyor():
    """Bedelsiz fiyatı böler, sermaye artırımı bildirimi her zaman
    bölmez. İkisini aynı tonda uyarmak yanlış alarm olurdu."""
    assert si.fiyat_bolunur_mu("bedelsiz sermaye artırımı") is True
    assert si.fiyat_bolunur_mu("bölünme") is True
    assert si.fiyat_bolunur_mu("sermaye artırımı") is False
    assert si.fiyat_bolunur_mu("sermaye azaltımı") is False


# ── oran ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin,oran", [
    ("Bedelsiz Sermaye Artırımı - %100 oranında bedelsiz", 100.0),
    ("Şirketimizin %250 oranında bedelsiz sermaye artırımı", 250.0),
    ("bedelsiz sermaye artırım oranı 50", 50.0),
    ("%12,5 oranında bedelsiz", 12.5),
])
def test_oran_cikariliyor(metin, oran):
    assert si.oran_cikar(metin) == oran


@pytest.mark.parametrize("metin", [
    "Sermaye Artırımına İlişkin Bildirim",
    "bedelsiz sermaye artırımı yapılacaktır",
    "",
    "%0 oranında bedelsiz",          # ayrıştırma hatası
    "%99999 oranında bedelsiz",      # ayrıştırma hatası
])
def test_emin_degilse_oran_YAZILMAZ(metin):
    """Yanlış oran, hiç oran olmamasından kötü: kullanıcı ona göre
    hesap yapar."""
    assert si.oran_cikar(metin) is None


# ── açıklama ──────────────────────────────────────────────────────────────

def test_bedelsiz_aciklamasi_PANIK_ONLUYOR():
    m = si.aciklama("THYAO", "bedelsiz sermaye artırımı", 100.0)
    assert "MEKANİK" in m
    assert "ucuzlamıyor" in m
    assert "kayıp değil" in m
    assert "%100" in m


def test_oran_yoksa_aciklama_yine_calisiyor():
    m = si.aciklama("THYAO", "bedelsiz sermaye artırımı", None)
    assert "MEKANİK" in m
    assert "%" not in m.split("\n")[0], "olmayan oran yazılmamalı"


def test_azaltim_aciklamasi_ters_yonu_anlatiyor():
    m = si.aciklama("THYAO", "sermaye azaltımı")
    assert "azalacak" in m and "yükselecek" in m


def test_bilinmeyen_islem_temkinli_konusuyor():
    m = si.aciklama("THYAO", "birleşme")
    assert "pozisyon kararı" in m


# ── bildirim metinleri ────────────────────────────────────────────────────

def test_push_bedelsizde_orani_tasiyor():
    from cekirdek import bildirim
    bas, gov = bildirim.sermaye_islemi_push(
        {"sembol": "THYAO", "fiyat_bolunur": True, "oran": 100.0})
    assert "THYAO" in bas
    assert "%100" in gov and "kayıp değil" in gov


def test_telegram_mesaji_kap_baglantisi_veriyor():
    from cekirdek import bildirim
    m = bildirim.sermaye_islemi_mesaji({
        "sembol": "THYAO", "fiyat_bolunur": True, "oran": 100.0,
        "aciklama": si.aciklama("THYAO", "bedelsiz sermaye artırımı", 100.0),
        "url": "https://www.kap.org.tr/tr/Bildirim/123"})
    assert "KAP bildirimi" in m
    assert "MEKANİK" in m


def test_urlsiz_mesaj_cokmez():
    from cekirdek import bildirim
    m = bildirim.sermaye_islemi_mesaji(
        {"sembol": "X", "aciklama": "bir şey", "url": ""})
    assert "X" in m and "href" not in m


# ── ambar sorgusu ─────────────────────────────────────────────────────────

def test_bul_ilgisiz_haberi_ELEMEZ_haberi_getirmez(tmp_path):
    from cekirdek import ambar
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    bugun = __import__("datetime").date.today().isoformat()
    ambar.haber_yaz(
        [{"id": "k1", "tarih": bugun, "kaynak": "KAP",
          "baslik": "THYAO Bedelsiz Sermaye Artırımı",
          "ozet": "%100 oranında bedelsiz", "url": "u1", "yayin": bugun},
         {"id": "k2", "tarih": bugun, "kaynak": "KAP",
          "baslik": "THYAO Şirket Genel Bilgi Formu",
          "ozet": "", "url": "u2", "yayin": bugun}],
        [{"haber_id": "k1", "sembol": "THYAO", "ifade": "THYAO"},
         {"haber_id": "k2", "sembol": "THYAO", "ifade": "THYAO"}],
        yol=yol)

    r = si.bul(["THYAO"], gun=30, yol=yol)
    assert len(r) == 1, "rutin bildirim de uyarıya girdi"
    assert r[0]["oran"] == 100.0
    assert r[0]["fiyat_bolunur"] is True


def test_bul_bos_liste_ile_cokmez():
    assert si.bul([], gun=30) == []


def test_bul_bilinmeyen_sembolde_cokmez(tmp_path):
    from cekirdek import ambar
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    assert si.bul(["YOKBOYLE"], gun=30, yol=yol) == []
