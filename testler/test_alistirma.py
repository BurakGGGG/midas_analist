"""Alıştırma kum havuzu — AĞ GEREKTİRMEZ (bar üretimi hariç).

Bu katmanın tek işi kullanıcıyı gerçeğe hazırlamak. O yüzden en pahalı
arıza YANLIŞ ÖĞRETMEK olur: alıştırmada stop backtest'ten farklı
çalışırsa, kullanıcı öğrendiği şeyi gerçek işlemde uygulayıp şaşırır.

Bu yüzden testlerin çoğu "backtest ile aynı mı" sorusunu soruyor.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import alistirma as al


def _bar(acilis, yuksek, dusuk, kapanis, onceki=100.0, tarih="2026-03-12"):
    return al.Bar(tarih=tarih, acilis=acilis, yuksek=yuksek, dusuk=dusuk,
                  kapanis=kapanis, onceki_kapanis=onceki, atr=3.0)


POZ = {"sembol": "THYAO", "stop": 95.0, "hedef": 110.0}


# ── çıkış kuralları: backtest ile birebir ─────────────────────────────────

def test_stop_gun_ici_calisir():
    c = al.cikis_kontrol(POZ, _bar(100, 101, 94, 96))
    assert c and c.sebep == "stop" and c.fiyat == 95.0


def test_hedef_gun_ici_calisir():
    c = al.cikis_kontrol(POZ, _bar(100, 112, 99, 111))
    assert c and c.sebep == "hedef" and c.fiyat == 110.0


def test_bosluklu_acilista_stop_ACILISTAN_calisir():
    """'Stopum 95'ti' desen de hisse 88'den açtıysa 88'den çıkarsın.
    Bunu modellemeyen alıştırma, stopu olduğundan güvenli gösterir."""
    c = al.cikis_kontrol(POZ, _bar(88, 92, 86, 90))
    assert c and c.sebep == "stop"
    assert c.fiyat == 88.0, "stop fiyatından değil AÇILIŞTAN çıkmalı"


def test_bosluklu_acilista_hedef_ACILISTAN_calisir():
    c = al.cikis_kontrol(POZ, _bar(115, 118, 114, 117))
    assert c and c.sebep == "hedef" and c.fiyat == 115.0


def test_ayni_gun_ikisi_de_gorulduyse_STOP_sayilir():
    """Günlük barla hangisinin önce olduğunu bilemeyiz. İyimser varsaymak
    sonuçları sistematik olarak güzelleştirirdi — backtest de kötümser
    varsayıyor, alıştırma da varsaymalı."""
    c = al.cikis_kontrol(POZ, _bar(100, 112, 94, 105))
    assert c and c.sebep == "stop"


def test_ne_stop_ne_hedef_cikis_yok():
    assert al.cikis_kontrol(POZ, _bar(100, 105, 97, 103)) is None


def test_stopsuz_pozisyon_stopla_cikmaz():
    poz = {"sembol": "X", "stop": 0, "hedef": 110.0}
    assert al.cikis_kontrol(poz, _bar(50, 60, 40, 55)) is None


def test_hedefsiz_pozisyon_hedefle_cikmaz():
    poz = {"sembol": "X", "stop": 95.0, "hedef": 0}
    assert al.cikis_kontrol(poz, _bar(200, 210, 199, 205)) is None


# ── tavan kuralı ───────────────────────────────────────────────────────────

def test_tavanda_acan_bar_isaretlenir():
    """Backtest de tavanda açan hisseyi alınamaz sayıyor; gerçekte de
    tavanda satıcı yoktur."""
    assert _bar(120, 121, 119, 120, onceki=100).tavan_mi is True
    assert _bar(119, 121, 118, 120, onceki=100).tavan_mi is False


def test_onceki_kapanis_sifirsa_tavan_hesaplanmaz():
    assert _bar(120, 121, 119, 120, onceki=0).tavan_mi is False


# ── pozisyon boyutu (d802'nin uygulaması) ─────────────────────────────────

def test_adedi_stop_mesafesi_belirler():
    """Alıştırmanın öğretmesi gereken ana fikir: adet 'içine sinen miktar'
    değil, stop mesafesinin sonucudur."""
    yakin = al.adet_oner(10_000, 100.0, 98.0)["adet"]
    uzak = al.adet_oner(10_000, 100.0, 90.0)["adet"]
    assert yakin > uzak, "stop yakınsa daha çok adet alınır"


def test_risk_butcesi_asilmaz():
    r = al.adet_oner(10_000, 100.0, 90.0, risk_yuzde=1.5)
    assert r["adet"] * r["hisse_basi_risk"] <= r["risk_butcesi"] + 0.01


def test_tek_hisse_tavani_baglayici_olabilir():
    """Küçük sermayede genelde bu tavan bağlar."""
    r = al.adet_oner(1_000, 400.0, 399.0)
    assert r["baglayici"] == "tek hisse tavanı"
    assert r["adet"] * 400.0 <= 1_000 * 0.35 + 400.0


def test_stop_giristen_yuksekse_reddedilir():
    assert al.adet_oner(10_000, 100.0, 105.0)["adet"] == 0
    assert al.adet_oner(10_000, 100.0, 100.0)["adet"] == 0


def test_stopsuz_adet_hesaplanmaz():
    """Stop koymadan pozisyon boyutu hesaplanamaz — alıştırma bunu
    kullanıcıya öğretmeli, sessizce bir sayı uydurmamalı."""
    assert al.adet_oner(10_000, 100.0, 0)["adet"] == 0


def test_gecersiz_fiyat_cokme_uretmez():
    assert al.adet_oner(10_000, 0, 0)["adet"] == 0
    assert al.adet_oner(0, 100.0, 90.0)["adet"] == 0


# ── bar üretimi (ağ ister) ────────────────────────────────────────────────

@pytest.mark.parametrize("tarih", ["2026-03-12"])
def test_gecmis_bar_gercek_veriden_gelir(tarih):
    b = al.gun("THYAO", tarih)
    if b is None:
        pytest.skip("fiyat verisi yok (ağ ya da önbellek)")
    assert b.tarih <= tarih
    assert b.yuksek >= b.dusuk
    assert b.dusuk <= b.acilis <= b.yuksek
    assert b.dusuk <= b.kapanis <= b.yuksek


def test_sonraki_gun_ileri_gider():
    b = al.sonraki_gun("THYAO", "2026-03-12")
    if b is None:
        pytest.skip("fiyat verisi yok")
    assert b.tarih > "2026-03-12"


def test_olmayan_sembol_cokme_uretmez():
    assert al.gun("YOKBOYLEBIRHISSE", "2026-03-12") is None
    assert al.sonraki_gun("YOKBOYLEBIRHISSE", "2026-03-12") is None


def test_bozuk_tarih_cokme_uretmez():
    assert al.gun("THYAO", "bozuk-tarih") is None
    assert al.sonraki_gun("THYAO", "bozuk-tarih") is None


# ── görevler ───────────────────────────────────────────────────────────────

from cekirdek import alistirma_gorevler as ag


def test_gorev_kodlari_benzersiz():
    kodlar = [g.kod for g in ag.GOREVLER]
    assert len(kodlar) == len(set(kodlar))


@pytest.mark.parametrize("g", ag.GOREVLER, ids=lambda g: g.kod)
def test_gorev_sozlesmesi(g):
    assert g.baslik and g.amac and g.anlatim
    assert g.tur in ("secim", "sayi", "islem", "ilerlet")
    assert g.aciklama, "cevaptan sonra NEDEN açıklanmalı"


@pytest.mark.parametrize("g", [x for x in ag.GOREVLER if x.tur == "secim"],
                         ids=lambda g: g.kod)
def test_secim_gorevi_gecerli(g):
    assert len(g.secenekler) >= 2
    assert isinstance(g.dogru, int) and 0 <= g.dogru < len(g.secenekler)


@pytest.mark.parametrize("g", [x for x in ag.GOREVLER if x.tur == "sayi"],
                         ids=lambda g: g.kod)
def test_sayi_gorevi_gecerli(g):
    assert isinstance(g.dogru, (int, float))
    assert g.tolerans > 0, "sıfır tolerans, kuruş farkını yanlış sayar"
    assert g.ipucu, "sayı görevi ipuçsuz bırakılmamalı"


def test_ders_baglantilari_gercek():
    from cekirdek.egitmen_dersler import DERS_HARITA
    for g in ag.GOREVLER:
        if g.ders:
            assert g.ders in DERS_HARITA, f"{g.kod} -> {g.ders} diye ders yok"


def test_virgullu_sayi_kabul_edilir():
    """Türkçe klavyede ondalık ayırıcı virgül. Reddetseydik doğru cevap
    veren kullanıcı yanlış yapmış sayılırdı."""
    assert ag.kontrol("g03", "84,80")["dogru"] is True


def test_sayisal_olmayan_cevap_cokme_uretmez():
    r = ag.kontrol("g03", "abc")
    assert r["dogru"] is False and "not" in r


def test_olmayan_gorev_cokme_uretmez():
    assert ag.kontrol("gYOK", 1)["dogru"] is False


def test_islem_gorevleri_kum_havuzunda_dogrulanir():
    """islem/ilerlet türünün kontrolü, işlemin gerçekleşmiş olması."""
    for kod in ("g06", "g07"):
        assert ag.kontrol(kod, None)["dogru"] is True


# ── görev cevapları motorla tutarlı mı ────────────────────────────────────

def test_adet_gorevi_motorun_hesabiyla_ayni():
    """g05'in beklediği cevap ile alistirma.adet_oner ayrışırsa alıştırma
    yanlış öğretir: kullanıcı 'doğru' cevabı verir, uygulama başka adet
    hesaplar."""
    g = ag.gorev_getir("g05")
    s = g.senaryo
    motor = al.adet_oner(s["bakiye"], s["fiyat"], s["stop"],
                         risk_yuzde=s["risk_yuzde"])
    assert abs(motor["adet"] - float(g.dogru)) <= g.tolerans


def test_stop_gorevi_sistemin_atr_katiyla_ayni():
    """g03, stopu 2 ATR altına koyduruyor. Stratejilerin atr_stop_kat
    değeri değişirse görev de değişmeli."""
    from cekirdek.strateji import STRATEJILER
    g = ag.gorev_getir("g03")
    s = g.senaryo
    assert abs((s["fiyat"] - s["kat"] * s["atr"]) - float(g.dogru)) <= g.tolerans
    katlar = {st.atr_stop_kat for st in STRATEJILER.values()}
    assert s["kat"] in katlar, "görevdeki ATR katı hiçbir stratejide yok"


def test_odul_risk_gorevi_aritmetigi_dogru():
    g = ag.gorev_getir("g04")
    s = g.senaryo
    oran = (s["hedef"] - s["giris"]) / (s["giris"] - s["stop"])
    assert abs(oran - float(g.dogru)) <= g.tolerans


def test_tutar_gorevi_aritmetigi_dogru():
    g = ag.gorev_getir("g02")
    s = g.senaryo
    assert abs(s["adet"] * s["fiyat"] - float(g.dogru)) <= g.tolerans
