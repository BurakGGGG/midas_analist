"""Bilanço, temettü ve ekonomi takvimi.

İKİ TÜR KAYIT ve ayrımı gizlemek yanlış olurdu:
  duyurulan — KAP bildiriminde tarih YAZILI, kaynağı belli
  beklenen  — mevzuattan HESAPLANAN son tarih

"12 Eylül'de bilanço var" demek yanlış olurdu; "9 Kasım'a kadar
açıklanmalı" doğru. Kullanıcı birine göre gün planlar, ötekine göre
yalnızca dikkatli olur.
"""
from datetime import date

import pytest

from cekirdek import takvim as t


# ── tarih çıkarma ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin,beklenen", [
    ("Kâr payı 12.09.2026 tarihinde ödenecek", [date(2026, 9, 12)]),
    ("Genel Kurul 15 Ekim 2026 tarihinde", [date(2026, 10, 15)]),
    ("Toplantı 05/11/2026 günü", [date(2026, 11, 5)]),
    ("1 Aralık 2026 ve 15.12.2026",
     [date(2026, 12, 1), date(2026, 12, 15)]),
])
def test_tarih_cikariliyor(metin, beklenen):
    assert t.tarih_cikar(metin, en_erken=date(2026, 8, 29)) == beklenen


def test_gecmis_tarihler_ATILIYOR():
    """Bildirim metni geçmiş dönemlere atıf yapıyor ('2025 yılı
    kârından'); onları takvime koymak takvimi çöpe çevirirdi."""
    m = "2025 yılı kârından 01.01.2025 döneminde 12.09.2026'da ödenecek"
    assert t.tarih_cikar(m, en_erken=date(2026, 8, 29)) == [date(2026, 9, 12)]


def test_gecersiz_tarih_cokmez():
    assert t.tarih_cikar("32.13.2026 ve 99 Zilzil 2026") == []
    assert t.tarih_cikar("") == []
    assert t.tarih_cikar(None) == []


def test_turkce_ay_adlari_kapsandi():
    aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    for i, ay in enumerate(aylar, start=1):
        r = t.tarih_cikar(f"15 {ay} 2027", en_erken=date(2026, 1, 1))
        assert r == [date(2027, i, 15)], ay


# ── bilanço penceresi ─────────────────────────────────────────────────────

def test_bilanco_son_tarihleri_mevzuata_uyuyor():
    """SPK II-14.1: ara dönem konsolide 40 gün, yıllık 70 gün."""
    r = t.bilanco_penceresi(date(2026, 9, 1), ileri_gun=400)
    tarihler = {x["baslik"]: x["tarih"] for x in r}
    assert tarihler["2026 3. çeyrek bilanço son tarihi"] == "2026-11-09"
    assert tarihler["2026 yıllık bilanço son tarihi"] == "2027-03-11"


def test_bilanco_kaydi_BEKLENEN_diye_isaretli():
    """Şirket kesin günü ayrıca duyuruyor. 'Bugün bilanço var' demek
    yanlış olurdu."""
    r = t.bilanco_penceresi(date(2026, 9, 1), ileri_gun=200)
    assert r and all(x["kaynak"] == "beklenen" for x in r)
    assert "kadar açıklanmalı" in r[0]["aciklama"]


def test_gecmis_donem_takvime_girmez():
    r = t.bilanco_penceresi(date(2026, 9, 1), ileri_gun=200)
    assert all(x["tarih"] >= "2026-09-01" for x in r)


def test_ileri_gun_siniri_uygulaniyor():
    assert t.bilanco_penceresi(date(2026, 9, 1), ileri_gun=10) == []


# ── ekonomi ───────────────────────────────────────────────────────────────

def test_enflasyon_ayin_ucunde():
    r = t.enflasyon_gunleri(date(2026, 8, 29), ileri_gun=40)
    assert r and r[0]["tarih"] == "2026-09-03"


def test_enflasyon_hafta_sonuna_denk_gelirse_KAYAR():
    # 3 Ekim 2026 cumartesi → 5 Ekim pazartesi
    r = t.enflasyon_gunleri(date(2026, 9, 20), ileri_gun=30)
    assert any(x["tarih"] == "2026-10-05" for x in r)
    for x in r:
        assert date.fromisoformat(x["tarih"]).weekday() < 5


def test_ppk_tarihi_UYDURULMUYOR():
    """TCMB faiz kararı takvimi elimizde yok. Uydurmak, olmayan bir
    günü 'faiz kararı var' diye göstermek olurdu."""
    r = t.takvim(ileri_gun=200, bugun=date(2026, 8, 29))
    assert not any("faiz" in x["baslik"].lower() for x in r)


# ── KAP olayları ──────────────────────────────────────────────────────────

def _ambar_kur(tmp_path, baslik, ozet=""):
    from cekirdek import ambar
    yol = tmp_path / "a.db"
    ambar.kur(yol)
    bugun = date.today().isoformat()
    ambar.haber_yaz(
        [{"id": "k1", "tarih": bugun, "kaynak": "KAP", "baslik": baslik,
          "ozet": ozet, "url": "u1", "yayin": bugun}],
        [{"haber_id": "k1", "sembol": "THYAO", "ifade": "THYAO"}], yol=yol)
    return yol


def test_temettu_bildiriminden_olay_cikiyor(tmp_path):
    yol = _ambar_kur(tmp_path, "THYAO Kar Payı Dağıtım İşlemlerine İlişkin",
                     "Kâr payı 12.09.2099 tarihinde ödenecektir")
    r = t.kap_olaylari(["THYAO"], ileri_gun=40000,
                       bugun=date.today(), yol=yol)
    assert len(r) == 1
    assert r[0]["tur"] == "temettü"
    assert r[0]["kaynak"] == "duyurulan"
    assert r[0]["sembol"] == "THYAO"


def test_genel_kurul_taniniyor(tmp_path):
    yol = _ambar_kur(tmp_path, "THYAO Genel Kurul Toplantısı",
                     "Toplantı 15 Ekim 2099 tarihinde yapılacaktır")
    r = t.kap_olaylari(["THYAO"], ileri_gun=40000,
                       bugun=date.today(), yol=yol)
    assert r and r[0]["tur"] == "genel_kurul"


def test_ilgisiz_bildirim_takvime_girmez(tmp_path):
    yol = _ambar_kur(tmp_path, "THYAO Yeni İş İlişkisi",
                     "Sözleşme 12.09.2099 tarihinde imzalandı")
    assert t.kap_olaylari(["THYAO"], ileri_gun=40000,
                          bugun=date.today(), yol=yol) == []


def test_tarihsiz_bildirim_takvime_girmez(tmp_path):
    yol = _ambar_kur(tmp_path, "THYAO Kar Payı Dağıtım", "tarih yok")
    assert t.kap_olaylari(["THYAO"], ileri_gun=40000,
                          bugun=date.today(), yol=yol) == []


def test_ayni_olay_iki_kez_girmez(tmp_path):
    yol = _ambar_kur(tmp_path, "THYAO Kar Payı Dağıtım",
                     "12.09.2099 ve tekrar 12.09.2099")
    assert len(t.kap_olaylari(["THYAO"], ileri_gun=40000,
                              bugun=date.today(), yol=yol)) == 1


# ── birleşik takvim ───────────────────────────────────────────────────────

def test_takvim_tarihe_gore_sirali():
    r = t.takvim(ileri_gun=300, bugun=date(2026, 8, 29))
    assert r == sorted(r, key=lambda x: (x["tarih"], x["sembol"]))


def test_kalan_gun_hesaplaniyor():
    r = t.takvim(ileri_gun=120, bugun=date(2026, 8, 29))
    for x in r:
        assert x["kalan_gun"] >= 0
        beklenen = (date.fromisoformat(x["tarih"]) - date(2026, 8, 29)).days
        assert x["kalan_gun"] == beklenen


def test_sembolsuz_takvim_genel_olaylari_verir():
    r = t.takvim(None, ileri_gun=120, bugun=date(2026, 8, 29))
    assert r and all(x["sembol"] == "" for x in r)


def test_her_olayin_kaynagi_isaretli():
    for x in t.takvim(ileri_gun=200, bugun=date(2026, 8, 29)):
        assert x["kaynak"] in ("duyurulan", "beklenen"), x
