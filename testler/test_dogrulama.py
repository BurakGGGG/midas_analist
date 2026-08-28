"""İkinci kaynak ve çapraz doğrulama — AĞ ERİŞİMİ GEREKTİRMEZ.

Bu katmanın işi uyarı üretmek. İki yönlü hata da pahalı:

  YANLIŞ ALARM  — her gün "veri şüpheli" diyen bir sistem okunmaz olur;
                  ağ arızası veri arızası sayılmamalı.
  KAÇIRMA       — sahte bir uçurumu görmezse katmanın hiç olmaması gibi.

Testler bu iki ucu da kilitler.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import dogrulama as d


# 2026-08-25'te CVKMD'de gerçekten görülen desen: yfinance bir bedelsizi
# kaçırmış, 03-08'de sahte bir uçurum bırakmış. İş Yatırım geçmişi düzeltmiş.
YF_BOZUK = {"2026-07-29": 36.28, "2026-07-30": 37.14, "2026-07-31": 37.82,
            "2026-08-03": 14.42, "2026-08-04": 14.89, "2026-08-05": 15.21}
IY_DOGRU = {"2026-07-29": 14.03, "2026-07-30": 14.36, "2026-07-31": 14.63,
            "2026-08-03": 14.42, "2026-08-04": 14.89, "2026-08-05": 15.21}

TEMIZ = {"2026-08-03": 66.0, "2026-08-04": 66.4, "2026-08-05": 67.1,
         "2026-08-06": 66.8, "2026-08-07": 67.5}


def _iy(monkeypatch, veri_):
    """isyatirim_fiyat'ı sabit veriyle değiştirir."""
    monkeypatch.setattr(d, "isyatirim_fiyat",
                        lambda kod, gun=60: {t: {"kapanis": v} for t, v in veri_.items()})


# ── kaçırmama ──────────────────────────────────────────────────────────────

def test_sahte_ucurum_yakalanir(monkeypatch):
    _iy(monkeypatch, IY_DOGRU)
    u = d.capraz_kontrol(["CVKMD.IS"], lambda s: YF_BOZUK, gun=30)
    assert len(u) == 1
    assert u[0]["azami_fark_yuzde"] > 50
    assert u[0]["gun"] in ("2026-07-29", "2026-07-30", "2026-07-31")


def test_sapan_gun_ve_degerler_raporlanir(monkeypatch):
    """Uyarı tek başına işe yaramaz; hangi gün, hangi değerler belli olmalı."""
    _iy(monkeypatch, IY_DOGRU)
    u = d.capraz_kontrol(["CVKMD.IS"], lambda s: YF_BOZUK, gun=30)[0]
    assert u["yfinance"] != u["isyatirim"]
    assert u["karsilastirilan_gun"] == len(IY_DOGRU)


# ── yanlış alarm vermeme ───────────────────────────────────────────────────

def test_ortusen_kaynaklar_uyari_uretmez(monkeypatch):
    _iy(monkeypatch, TEMIZ)
    assert d.capraz_kontrol(["AKBNK.IS"], lambda s: TEMIZ, gun=30) == []


def test_esigin_altindaki_fark_uyari_degil(monkeypatch):
    """Ölçülen normal sapma %0,23; %0,5'lik fark gürültüdür."""
    hafif = {t: v * 1.005 for t, v in TEMIZ.items()}
    _iy(monkeypatch, hafif)
    assert d.capraz_kontrol(["AKBNK.IS"], lambda s: TEMIZ, gun=30) == []


def test_ikinci_kaynak_ulasilamazsa_sessiz(monkeypatch):
    """Ağ arızası veri arızası değildir — uyarı üretilmemeli."""
    monkeypatch.setattr(d, "isyatirim_fiyat", lambda kod, gun=60: {})
    assert d.capraz_kontrol(["AKBNK.IS"], lambda s: TEMIZ, gun=30) == []


def test_birinci_kaynak_bossa_sessiz(monkeypatch):
    _iy(monkeypatch, TEMIZ)
    assert d.capraz_kontrol(["AKBNK.IS"], lambda s: {}, gun=30) == []


def test_ortak_gun_azsa_karsilastirma_yapilmaz(monkeypatch):
    """3 günlük örtüşmeden hüküm çıkmaz."""
    _iy(monkeypatch, {"2026-08-03": 1.0, "2026-08-04": 99.0})
    u = d.capraz_kontrol(["AKBNK.IS"], lambda s: TEMIZ, gun=30, asgari_ortak_gun=5)
    assert u == []


def test_sifir_fiyat_bolme_hatasi_vermez(monkeypatch):
    _iy(monkeypatch, TEMIZ)
    bozuk = dict.fromkeys(TEMIZ, 0.0)
    assert d.capraz_kontrol(["AKBNK.IS"], lambda s: bozuk, gun=30) == []


def test_bir_hissenin_sorunu_digerlerini_durdurmaz(monkeypatch):
    def sahte(kod, gun=60):
        if kod == "BOZUK":
            raise RuntimeError("uç çöktü")
        return {t: {"kapanis": v} for t, v in IY_DOGRU.items()}
    monkeypatch.setattr(d, "isyatirim_fiyat", sahte)
    with pytest.raises(RuntimeError):
        d.capraz_kontrol(["BOZUK"], lambda s: YF_BOZUK)
    # Sağlam sembol tek başına çalışmalı
    assert len(d.capraz_kontrol(["CVKMD.IS"], lambda s: YF_BOZUK)) == 1


# ── İş Yatırım ayrıştırma ──────────────────────────────────────────────────

YANIT = {"ok": True, "value": [
    {"HGDG_HS_KODU": "AKBNK", "HGDG_TARIH": "24-08-2026", "HGDG_KAPANIS": 72.1,
     "HGDG_MIN": 71.35, "HGDG_MAX": 73.35, "HGDG_HACIM": 1.3e10,
     "DOLAR_BAZLI_FIYAT": 1.4996, "PD": 3.749e11, "PD_USD": 7.8e9}]}


def test_isyatirim_tarihi_iso_yapar(monkeypatch):
    import json
    monkeypatch.setattr(d, "_cek", lambda *a, **k: json.dumps(YANIT).encode())
    f = d.isyatirim_fiyat("AKBNK")
    assert "2026-08-24" in f
    assert f["2026-08-24"]["kapanis"] == 72.1
    assert f["2026-08-24"]["usd_fiyat"] == 1.4996


def test_isyatirim_ulasilamazsa_bos(monkeypatch):
    monkeypatch.setattr(d, "_cek", lambda *a, **k: None)
    assert d.isyatirim_fiyat("AKBNK") == {}


def test_isyatirim_json_disi_yanitta_bos(monkeypatch):
    monkeypatch.setattr(d, "_cek", lambda *a, **k: b"<html>hata</html>")
    assert d.isyatirim_fiyat("AKBNK") == {}


def test_isyatirim_ok_false_ise_bos(monkeypatch):
    import json
    monkeypatch.setattr(d, "_cek",
                        lambda *a, **k: json.dumps({"ok": False, "value": []}).encode())
    assert d.isyatirim_fiyat("AKBNK") == {}


# ── TCMB ───────────────────────────────────────────────────────────────────

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="25.08.2026">
  <Currency Kod="USD"><Unit>1</Unit><ForexBuying>48.0117</ForexBuying></Currency>
  <Currency Kod="EUR"><Unit>1</Unit><ForexBuying>55.9892</ForexBuying></Currency>
  <Currency Kod="JPY"><Unit>100</Unit><ForexBuying>32.5000</ForexBuying></Currency>
</Tarih_Date>"""


def test_tcmb_kuru_ayristirir(monkeypatch):
    monkeypatch.setattr(d, "_cek", lambda *a, **k: XML)
    k = d.tcmb_kur()
    assert k["USD"] == 48.0117


def test_tcmb_100_birimlik_kuru_bolerek_normalize_eder(monkeypatch):
    """JPY 100 birim üzerinden yayınlanır; bölünmezse kur 100 kat şişer."""
    monkeypatch.setattr(d, "_cek", lambda *a, **k: XML)
    assert d.tcmb_kur()["JPY"] == pytest.approx(0.325)


def test_tcmb_tatilde_geriye_yurur(monkeypatch):
    """Hafta sonu kur yayınlanmaz; betik geriye yürüyüp son kuru bulmalı."""
    cagri = {"n": 0}
    def sahte(*a, **k):
        cagri["n"] += 1
        return XML if cagri["n"] >= 3 else None
    monkeypatch.setattr(d, "_cek", sahte)
    assert d.tcmb_kur()["USD"] == 48.0117
    assert cagri["n"] == 3


def test_tcmb_hic_ulasilamazsa_bos(monkeypatch):
    monkeypatch.setattr(d, "_cek", lambda *a, **k: None)
    assert d.tcmb_kur() == {}


# ── sayı biçimi ────────────────────────────────────────────────────────────
#
# Rejim notları doğrudan kullanıcıya gidiyor: Makro ekranı, Bugün kartı,
# Telegram ve push. Uygulamanın geri kalanı Türkçe virgül kullanırken bu
# notlardan nokta çıkıyordu ve aynı ekranda "VIX 14.6" ile "14,63" yan
# yana duruyordu.

def test_rejim_notlari_turkce_ondalik_kullanir():
    from cekirdek.makro import _sayi
    assert _sayi(14.63) == "14,6"
    assert _sayi(1.75, 2) == "1,75"
    assert _sayi(12.4, 0) == "12"
    assert "." not in _sayi(1234.5)


def test_sayi_bozuk_girdide_cokmez():
    from cekirdek.makro import _sayi
    for v in (None, "abc", float("nan")):
        assert isinstance(_sayi(v), str)


def test_rejim_notlarinda_nokta_ondalik_yok():
    """Not şablonlarında ':.1f' kalırsa nokta geri gelir ve kimse fark
    etmez — metinler ekranda küçük ve seyrek okunuyor."""
    from pathlib import Path
    kaynak = Path(__file__).resolve().parent.parent / "cekirdek" / "makro.py"
    for satir in kaynak.read_text(encoding="utf-8").splitlines():
        if "notlar.append" in satir:
            assert ":.0f}" not in satir and ":.1f}" not in satir, satir.strip()


# ── seansa duyarlı önbellek ────────────────────────────────────────────────
#
# Sabit 6 saatlik önbellek, seans içinde saatlerce eski fiyat göstermek
# demekti: kullanıcı öğlen bakıp sabah 10'un fiyatını görüyordu.

from datetime import datetime as _dt


def test_seans_saatleri_dogru():
    from cekirdek.veri import seans_ici_mi
    ac = [("2026-08-28 10:00", True),   # açılış
          ("2026-08-28 13:45", True),
          ("2026-08-28 17:59", True),
          ("2026-08-28 18:05", True),   # kapanış seansı
          ("2026-08-28 18:30", False),  # açık artırma bitti
          ("2026-08-28 09:30", False),  # açılış öncesi
          ("2026-08-29 12:00", False),  # cumartesi
          ("2026-08-30 12:00", False)]  # pazar
    for t, beklenen in ac:
        assert seans_ici_mi(_dt.fromisoformat(t)) is beklenen, t


def test_seans_disinda_uzun_onbellek():
    """Piyasa kapalıyken fiyat değişmiyor; sık çekmek boşuna istek."""
    from cekirdek import veri
    import unittest.mock as m
    with m.patch.object(veri, "seans_ici_mi", return_value=False):
        assert veri.seans_onbellegi(6.0, 0.08) == 6.0


def test_seans_icinde_kisa_onbellek():
    from cekirdek import veri
    import unittest.mock as m
    with m.patch.object(veri, "seans_ici_mi", return_value=True):
        assert veri.seans_onbellegi(6.0, 0.08) == 0.08


def test_kisa_omur_makul_aralikta():
    """Çok kısası Yahoo'nun görünmez kısıtlamasına takılma riski; çok
    uzunu zaten çözmeye çalıştığımız sorun."""
    from cekirdek.veri import seans_onbellegi
    import unittest.mock as m
    from cekirdek import veri
    with m.patch.object(veri, "seans_ici_mi", return_value=True):
        sure = seans_onbellegi()
        assert 0.03 <= sure <= 0.25, f"{sure*60:.0f} dakika"


def test_tarama_seans_omrunu_kullanmaz():
    """100 hisseyi 5 dakikada bir çekmek saatte 1200 istek eder ve
    engellenirsek günlük iş dahil her şey durur. Tazelik yalnızca az
    sayıda sembol için: kendi pozisyonların ve baktığın hisse."""
    import inspect
    from cekirdek import tarayici
    assert "seans_onbellegi" not in inspect.getsource(tarayici)
