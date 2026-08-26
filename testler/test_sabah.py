"""Sabah emir hatırlatıcısı — AĞ GEREKTİRMEZ.

Bu işin iki yönlü sessiz arıza riski var:

  KONUŞMAMASI GEREKİRKEN KONUŞUR — hafta sonu, tatil, bayat kayıt ya da
  karantinadaki stratejinin sinyali için "bugün şunu al" demek. En
  tehlikelisi bayat kayıt: uzun tatil sonrası bir haftalık listeyle emir
  vermek, hiç hatırlatmamaktan kötüdür.

  KONUŞMASI GEREKİRKEN SUSAR — sinyal var, emir rakamları var, ama mesaj
  gitmez. Bu sessizce olur; kimse fark etmez, sadece işlem yapılmaz.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
from datetime import date

import pytest

from cekirdek import ambar, bildirim, sabah


def _sinyal(sembol="THYAO", onerilir=True, alinabilir=True, adet=3):
    return {"sembol": sembol, "skor": 78.4, "sinyaller": ["kirilim"],
            "fiyat": 300.5, "alinabilir": alinabilir, "adet": adet,
            "stop": 287.2, "hedef": 326.1, "maliyet": 901.5,
            "risk_tl": 39.9, "uyari": "", "karantina": [],
            "onerilir": onerilir}


@pytest.fixture
def db(tmp_path):
    y = tmp_path / "sabah_test.db"
    ambar.kur(y)
    return y


def _ozet_yaz(db, tarih, sinyaller, rejim="ılımlı"):
    ambar.ozet_yaz(tarih, {"tarih": tarih, "sinyal_veren": sinyaller,
                           "rejim": {"ad": rejim}}, yol=db)


# ── susması gereken durumlar ───────────────────────────────────────────────

def test_hafta_sonu_susar(db):
    _ozet_yaz(db, "2026-08-28", [_sinyal()])          # cuma
    r = sabah.hazirla(date(2026, 8, 29), yol=db)      # cumartesi
    assert r["gonder"] is False and "hafta sonu" in r["sebep"]


def test_resmi_tatil_susar(db):
    from cekirdek.gunluk import TATILLER_2026
    tatil = date.fromisoformat(sorted(TATILLER_2026)[0])
    _ozet_yaz(db, "2026-01-01", [_sinyal()])
    assert sabah.hazirla(tatil, yol=db)["gonder"] is False


def test_bayat_kayit_susar(db):
    """Uzun tatil sonrası bir haftalık listeyle emir vermek, hiç
    hatırlatmamaktan kötüdür."""
    _ozet_yaz(db, "2026-08-10", [_sinyal()])
    r = sabah.hazirla(date(2026, 8, 26), yol=db)
    assert r["gonder"] is False and "eski" in r["sebep"]


def test_ambar_bossa_susar(db):
    r = sabah.hazirla(date(2026, 8, 26), yol=db)
    assert r["gonder"] is False and "özet yok" in r["sebep"]


def test_kurulmamis_ambar_cokme_uretmez(tmp_path):
    """Taze kurulumda tablolar ilk 18:10 işinden ÖNCE yok. Hatırlatıcının
    çökmesi, sessizce susmasından kötü: nöbetçi katmanı boşuna alarm
    verir ve gerçek arızalar gürültüde kaybolur."""
    r = sabah.hazirla(date(2026, 8, 26), yol=tmp_path / "hic_yok.db")
    assert r["gonder"] is False and r["sebep"]


def test_karantinali_sinyal_hatirlatilmaz(db):
    """Akşam 'önerilmez' işareti konmuşsa sabah 'şunu al' denmez."""
    _ozet_yaz(db, "2026-08-25", [_sinyal(onerilir=False)])
    assert sabah.hazirla(date(2026, 8, 26), yol=db)["gonder"] is False


def test_alinamayan_sinyal_hatirlatilmaz(db):
    """Sermayeye sığmayan hisseyi hatırlatmak boş bildirimdir."""
    _ozet_yaz(db, "2026-08-25", [_sinyal(alinabilir=False)])
    assert sabah.hazirla(date(2026, 8, 26), yol=db)["gonder"] is False


def test_adet_sifirsa_hatirlatilmaz(db):
    _ozet_yaz(db, "2026-08-25", [_sinyal(adet=0)])
    assert sabah.hazirla(date(2026, 8, 26), yol=db)["gonder"] is False


def test_eski_bicimli_kayit_cokme_uretmez(db):
    """adet/stop/hedef alanları sonradan eklendi; eski kayıtlar onlarsız."""
    _ozet_yaz(db, "2026-08-25", [{"sembol": "THYAO", "skor": 70,
                                  "sinyaller": ["trend"], "fiyat": 300.0,
                                  "alinabilir": True, "onerilir": True}])
    assert sabah.hazirla(date(2026, 8, 26), yol=db)["gonder"] is False


# ── konuşması gereken durum ────────────────────────────────────────────────

def test_gecerli_sinyal_hatirlatilir(db):
    _ozet_yaz(db, "2026-08-25", [_sinyal()])
    r = sabah.hazirla(date(2026, 8, 26), yol=db)
    assert r["gonder"] is True
    assert len(r["emirler"]) == 1
    assert r["emirler"][0]["sembol"] == "THYAO"


def test_pazartesi_cuma_kaydini_bulur(db):
    """Hafta sonu araya girince önceki İŞLEM gününe bakılmalı."""
    _ozet_yaz(db, "2026-08-28", [_sinyal()])          # cuma
    r = sabah.hazirla(date(2026, 8, 31), yol=db)      # pazartesi
    assert r["gonder"] is True and r["tarih"] == "2026-08-28"


def test_yalnizca_onerilenler_gecer(db):
    _ozet_yaz(db, "2026-08-25", [
        _sinyal("THYAO"),
        _sinyal("EUREN", onerilir=False),
        _sinyal("GESAN", alinabilir=False),
    ])
    r = sabah.hazirla(date(2026, 8, 26), yol=db)
    assert [e["sembol"] for e in r["emirler"]] == ["THYAO"]


def test_tavan_fiyati_hesaplanir(db):
    """Backtest, önceki kapanışın %19,5 üstünde AÇAN hisseyi alınamaz
    sayıyor. Mesaj aynı eşiği söylemezse sicil ile gerçek ayrışır."""
    _ozet_yaz(db, "2026-08-25", [_sinyal()])
    e = sabah.hazirla(date(2026, 8, 26), yol=db)["emirler"][0]
    assert e["tavan_fiyat"] == pytest.approx(300.5 * 1.195, abs=0.01)


# ── mesaj ──────────────────────────────────────────────────────────────────

def test_mesaj_emir_rakamlarini_tasir():
    """Bu işin varlık sebebi: akşamki mesajda adet/stop/hedef YOK."""
    plan = {"emirler": [{**_sinyal(), "tavan_fiyat": 359.1}], "rejim": "ılımlı"}
    m = bildirim.sabah_hatirlatici(plan)
    assert "THYAO" in m
    assert "3 adet" in m
    assert "287.20" in m and "326.10" in m
    assert "359.10" in m and "tavan" in m.lower()


def test_mesaj_bosluk_uyarisini_tasir():
    """Rakamlar dünkü kapanışa göre; bunu söylememek yanlış güven verir."""
    plan = {"emirler": [{**_sinyal(), "tavan_fiyat": 359.1}]}
    assert "kapanış" in bildirim.sabah_hatirlatici(plan).lower()


def test_bos_plan_bos_mesaj():
    assert bildirim.sabah_hatirlatici({"emirler": []}) == ""
    assert bildirim.sabah_hatirlatici({}) == ""


def test_mesaj_aksamkinden_farkli():
    """İkisi aynı olsaydı sabah işi gereksizdi."""
    ozet = {"tarih": "2026-08-25", "sinyal_veren": [_sinyal()]}
    aksam = bildirim.gunluk_ozet(ozet)
    plan = {"emirler": [{**_sinyal(), "tavan_fiyat": 359.1}]}
    sabah_m = bildirim.sabah_hatirlatici(plan)
    assert "adet" not in aksam.lower()
    assert "adet" in sabah_m.lower()
