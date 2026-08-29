"""Alıştırma kum havuzu — AĞ GEREKTİRMEZ (bar üretimi hariç).

Bu katmanın tek işi kullanıcıyı gerçeğe hazırlamak. O yüzden en pahalı
arıza YANLIŞ ÖĞRETMEK olur: alıştırmada stop backtest'ten farklı
çalışırsa, kullanıcı öğrendiği şeyi gerçek işlemde uygulayıp şaşırır.

Bu yüzden testlerin çoğu "backtest ile aynı mı" sorusunu soruyor.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pandas as pd
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


def test_hedefin_ustunde_acan_hisse_HEDEFTEN_cikar():
    """Gerçekte limit satışın 115'te dolardı ve daha çok kazanırdın.
    Ama backtest hedef fiyatından çıkarıyor (backtest.py:194) ve iki
    yerin farklı davranması simülatörü backtest'ten sistematik olarak
    daha iyi gösterirdi. Kötümserlik iki yönde de tutarlı: boşluk
    aşağıysa açılıştan çıkıyoruz, yukarıysa hedeften."""
    c = al.cikis_kontrol(POZ, _bar(115, 118, 114, 117))
    assert c and c.sebep == "hedef"
    assert c.fiyat == 110.0, "açılıştan değil HEDEFTEN çıkmalı"


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


# ═══════════════════════════════════ backtest ile denklik (asıl sınama)
#
# Modül "çıkış kuralları backtest ile birebir aynı" diyor. Bu iddia bir
# kez yanlıştı: hedefin üstünde açan hisse burada AÇILIŞTAN çıkıyordu,
# backtest'te HEDEFTEN. Fark küçük ama tek yönlü — simülatör backtest'ten
# sistematik olarak daha kârlı görünüyordu.
#
# Bu test iddiayı koda bağlıyor: GERÇEK backtest koşuluyor ve her
# işlemin çıkışı `cikis_kontrol` ile yeniden üretiliyor.

import pytest


@pytest.fixture(scope="module")
def gercek_veri():
    from cekirdek import veri, evren, gostergeler
    ek = veri.fiyat_cek(evren.ENDEKS, gun=900)
    ek_s = ek["Close"] if ek is not None and not ek.empty else None
    d = {}
    for sem in ["THYAO", "EREGL", "ASELS", "SISE", "KCHOL", "TUPRS"]:
        g = veri.fiyat_cek(sem, gun=900)
        if g is not None and not g.empty:
            d[sem] = gostergeler.gosterge_seti(g, ek_s)
    if len(d) < 4:
        pytest.skip("yeterli fiyat verisi yok")
    return d


def test_cikislar_backtest_ile_KURUSUNA_KADAR_ayni(gercek_veri):
    """Backtest'in kapattığı her işlem, aynı barlarda `cikis_kontrol`
    ile aynı fiyattan ve aynı günde kapanmalı."""
    from cekirdek import backtest
    from cekirdek.strateji import STRATEJILER
    from cekirdek.risk import RiskAyarlari

    kayma = 15.0 / 10_000.0
    karsilastirilan = 0

    for ad in ("trend", "tepki", "kirilim"):
        sonuc = backtest.calistir(gercek_veri, STRATEJILER[ad],
                                  RiskAyarlari(sermaye=100_000), kayma_bp=15.0)
        for islem in sonuc.islemler:
            # Süre-doldu ve sinyal çıkışları simülatörde YOK (bilinçli):
            # orada stopu kullanıcı koyuyor, arkasında strateji olmayabilir.
            if islem.sebep not in ("stop", "hedef", "boşluklu stop"):
                continue
            if islem.cikis_tarih is None:
                continue

            poz = {"sembol": islem.sembol, "stop": islem.stop,
                   "hedef": islem.hedef}
            d = gercek_veri[islem.sembol]
            # Giriş günü DAHİL: backtest o gün de gün içi çıkışa bakıyor.
            dilim = d.loc[islem.giris_tarih:islem.cikis_tarih]

            bulunan = None
            for t, satir in dilim.iterrows():
                bar = al.Bar(
                    tarih=t.strftime("%Y-%m-%d"),
                    acilis=float(satir["Open"]), yuksek=float(satir["High"]),
                    dusuk=float(satir["Low"]), kapanis=float(satir["Close"]),
                    onceki_kapanis=0.0, atr=0.0)
                c = al.cikis_kontrol(poz, bar)
                if c:
                    bulunan = (t, c)
                    break

            assert bulunan is not None, (
                f"{ad}/{islem.sembol}: backtest {islem.sebep} ile çıktı, "
                f"simülatör hiç çıkmadı")
            t, c = bulunan
            assert t == islem.cikis_tarih, (
                f"{ad}/{islem.sembol}: çıkış GÜNÜ farklı — "
                f"backtest {islem.cikis_tarih.date()}, simülatör {t.date()}")
            # 4 basamak: backtest boşluk dalında round(fiyat, 4) yapıyor,
            # gün içi dalında yapmıyor. Kuruşun on binde biri.
            bizim = round(c.fiyat * (1 - kayma), 4)
            assert bizim == pytest.approx(round(islem.cikis, 4), abs=1e-4), (
                f"{ad}/{islem.sembol} {t.date()}: çıkış FİYATI farklı — "
                f"backtest {islem.cikis:.4f}, simülatör {bizim:.4f}")
            karsilastirilan += 1

    assert karsilastirilan >= 20, (
        f"yalnızca {karsilastirilan} işlem karşılaştırıldı — test bir şey "
        f"kanıtlamıyor")


# ═══════════════════════════════════════════════ simülasyon motoru

def _sahte_bar(kapanis, acilis=None, onceki=None, tarih="2024-06-12"):
    a = acilis if acilis is not None else kapanis
    return al.Bar(tarih=tarih, acilis=a, yuksek=max(a, kapanis),
                  dusuk=min(a, kapanis), kapanis=kapanis,
                  onceki_kapanis=onceki if onceki is not None else kapanis,
                  atr=kapanis * 0.02)


# ── kayma yönü ─────────────────────────────────────────────────────────────

def test_alista_kayma_YUKARI_satista_ASAGI():
    """Kaymanın yönü hep kullanıcının aleyhine. Ters yön, simülatörü
    gerçekten daha kârlı gösterirdi."""
    b = _sahte_bar(100.0)
    alis = al.al_kontrol(b, 1, 10_000)
    assert alis["gecti"] and alis["fiyat"] > 100.0

    satis = al.sat({"sembol": "X", "adet": 1}, b)
    assert satis["gecti"] and satis["fiyat"] < 100.0


def test_kayma_backtest_ile_ayni_oran():
    assert al.KAYMA_BP == 15.0


def test_kaymasiz_istenirse_ham_fiyat():
    b = _sahte_bar(100.0)
    assert al.al_kontrol(b, 1, 10_000, kayma_bp=0)["fiyat"] == 100.0


# ── alım kapıları ──────────────────────────────────────────────────────────

def test_tavanda_acan_hisse_ALINAMAZ():
    """Eskiden yalnızca bayrak dönüyordu ve telefon uyarı gösterip
    alıma izin veriyordu. Backtest bu emri hiç doldurmuyor."""
    b = _sahte_bar(120.0, acilis=120.0, onceki=100.0)
    assert b.tavan_mi is True
    r = al.al_kontrol(b, 1, 10_000)
    assert r["gecti"] is False and "tavan" in r["sebep"].lower()


def test_bakiye_yetmezse_alinamaz():
    r = al.al_kontrol(_sahte_bar(100.0), 50, 1_000)
    assert r["gecti"] is False and "Bakiye" in r["sebep"]


def test_sifir_adet_alinamaz():
    assert al.al_kontrol(_sahte_bar(100.0), 0, 10_000)["gecti"] is False


def test_veri_yoksa_alinamaz():
    assert al.al_kontrol(None, 1, 10_000)["gecti"] is False


# ── satış ──────────────────────────────────────────────────────────────────

def test_kismi_satis_kalani_birakir():
    r = al.sat({"sembol": "X", "adet": 10}, _sahte_bar(100.0), adet=4)
    assert r["adet"] == 4 and r["kalan_adet"] == 6


def test_adet_sifirsa_tamami_satilir():
    r = al.sat({"sembol": "X", "adet": 10}, _sahte_bar(100.0), adet=0)
    assert r["adet"] == 10 and r["kalan_adet"] == 0


def test_acikta_olandan_fazlasi_satilamaz():
    r = al.sat({"sembol": "X", "adet": 3}, _sahte_bar(100.0), adet=99)
    assert r["adet"] == 3 and r["kalan_adet"] == 0


# ── değerleme ──────────────────────────────────────────────────────────────

def test_deger_nakit_ve_piyasayi_toplar(monkeypatch):
    monkeypatch.setattr(al, "gun", lambda s, t=None: _sahte_bar(110.0))
    d = al.deger([{"sembol": "X", "adet": 10, "giris": 100.0,
                   "stop": 90.0, "hedef": 130.0}], 5_000, "2024-06-12")
    assert d["piyasa"] == 1100.0
    assert d["ozkaynak"] == 6100.0
    assert d["acik_kar"] == 100.0
    s = d["satirlar"][0]
    assert s["stop_uzaklik"] == pytest.approx(18.18, abs=0.01)
    assert s["hedef_uzaklik"] == pytest.approx(18.18, abs=0.01)


def test_fiyat_bulunamazsa_SON_BILINEN_korunur(monkeypatch):
    """Sıfır saymak özkaynak eğrisinde sahte bir çöküş çizerdi ve
    kullanıcı olmayan bir kaybı öğrenirdi."""
    monkeypatch.setattr(al, "gun", lambda s, t=None: None)
    d = al.deger([{"sembol": "X", "adet": 10, "giris": 100.0}],
                 0, "2024-06-12")
    assert d["piyasa"] == 1000.0
    assert d["satirlar"][0]["veri_var"] is False


def test_bos_portfoy_nakite_esit():
    d = al.deger([], 10_000, "2024-06-12")
    assert d["ozkaynak"] == 10_000 and d["satirlar"] == []


# ── motor: adım ────────────────────────────────────────────────────────────

def test_pozisyon_YOKKEN_de_gun_ilerler():
    """Kullanıcı tarih seçip 'yarına bakayım' dediğinde eskiden uç 400
    dönüyordu. Takvim referans sembolden okunuyor."""
    r = al.adim([], 10_000, "2024-06-12", adim_sayisi=1)
    assert r["bitti"] is False
    assert r["tarih"] > "2024-06-12"
    assert r["nakit"] == 10_000


def test_bir_hafta_tek_turda_bes_gun_ilerler():
    r = al.adim([], 10_000, "2024-06-12", adim_sayisi=5)
    assert len(r["gunler"]) == 5
    assert r["tarih"] == r["gunler"][-1]


def test_her_gun_icin_ozkaynak_noktasi_uretilir():
    r = al.adim([], 10_000, "2024-06-12", adim_sayisi=5)
    assert len(r["ozkaynak_noktalari"]) == 5
    assert all(n["d"] == 10_000 for n in r["ozkaynak_noktalari"])
    assert [n["t"] for n in r["ozkaynak_noktalari"]] == r["gunler"]


def test_takvim_hafta_sonlarini_atlar():
    g = al.takvim("2024-06-12", "2024-06-25")
    assert g, "takvim boş"
    import datetime as _dt
    for t in g:
        assert _dt.date.fromisoformat(t).weekday() < 5


def test_veri_bitince_bitti_isareti():
    son = al.aralik()["en_gec"]
    r = al.adim([], 10_000, son, adim_sayisi=50)
    # Son günden sonra en fazla bir gün var (aralik son günü dışarıda bırakır)
    assert r["bitti"] or len(r["gunler"]) <= 2


def test_kapanana_kadar_pozisyon_kapaninca_durur():
    """adim_sayisi=0 → hepsi kapanana kadar."""
    b = al.gun("THYAO", "2024-06-12")
    poz = [{"sembol": "THYAO", "adet": 1, "giris": b.kapanis,
            "stop": b.kapanis * 0.98,     # yakın stop: hızlı kapanmalı
            "hedef": b.kapanis * 1.02, "tarih": b.tarih}]
    r = al.adim(poz, 1_000, "2024-06-12", adim_sayisi=0)
    assert r["pozisyonlar"] == [], "pozisyon kapanmadı"
    assert len(r["cikislar"]) == 1
    assert r["cikislar"][0]["sebep"] in ("stop", "hedef")


def test_cikista_da_kayma_uygulanir():
    b = al.gun("THYAO", "2024-06-12")
    poz = [{"sembol": "THYAO", "adet": 1, "giris": b.kapanis,
            "stop": b.kapanis * 0.98, "hedef": b.kapanis * 1.02,
            "tarih": b.tarih}]
    r = al.adim(poz, 0, "2024-06-12", adim_sayisi=0)
    c = r["cikislar"][0]
    assert c["fiyat"] < c["ham_fiyat"], "çıkışta kayma aşağı olmalı"


def test_azami_adim_sonsuz_dongu_engeller():
    r = al.adim([], 10_000, "2024-06-12", adim_sayisi=0, azami_adim=3)
    assert len(r["gunler"]) <= 3


def test_aralik_son_gunu_disarida_birakir():
    """Kullanıcı son güne başlarsa simülasyon başlar başlamaz biterdi."""
    a = al.aralik()
    assert a["en_erken"] < a["en_gec"] < "2030-01-01"
    t = al.takvim(a["en_gec"])
    assert len(t) >= 2, "en_gec'ten sonra ilerlenecek gün kalmalı"


# ══════════════════════════════ geçmiş sinyaller ("o gün ne diyordu")

def test_sinyal_dilimi_TAM_SERIYLE_ayni_sonuc_verir():
    """Hız için göstergeler 400 satırlık dilimde hesaplanıyor.

    Bu, sonucu değiştirmediği sürece geçerli bir iyileştirme. SMA200
    kayan pencere olduğu için son değerler aynı çıkmalı — ama bunu
    varsaymak yetmez, ölçmek gerekir. Tam seride 33 saniye süren hesap
    dilimle 1 saniye; fark sonuca yansırsa kullanıcıya o gün var
    olmayan bir sinyal gösterilirdi.
    """
    from cekirdek import gostergeler, evren, veri
    from cekirdek.strateji import skorla, Filtreler

    ek_ham = veri.fiyat_cek(evren.ENDEKS, gun=1300)
    ek = ek_ham["Close"] if not ek_ham.empty else None
    filtre = Filtreler()
    karsilastirilan = 0

    for sem in ["THYAO", "EREGL", "ASELS", "SISE", "KCHOL", "TUPRS"]:
        ham = veri.fiyat_cek(sem, gun=1300)
        if ham is None or len(ham) < 600:
            continue
        for tarih in ("2024-11-04", "2025-03-14", "2025-09-22", "2026-02-10"):
            sinir = pd.Timestamp(tarih)
            kesik = ham[ham.index <= sinir]
            if len(kesik) < 260:
                continue

            tam = gostergeler.gosterge_seti(ham, ek)
            tam = tam[tam.index <= sinir]
            dilim = gostergeler.gosterge_seti(
                kesik.tail(al.ISINMA_SATIRI), ek)

            r_tam, r_dilim = skorla(tam), skorla(dilim)
            assert r_tam["sinyaller"] == r_dilim["sinyaller"], (
                f"{sem} {tarih}: sinyaller farklı — "
                f"tam {r_tam['sinyaller']} · dilim {r_dilim['sinyaller']}")
            assert r_tam["skor"] == pytest.approx(r_dilim["skor"], abs=0.5), (
                f"{sem} {tarih}: skor farklı — "
                f"{r_tam['skor']} vs {r_dilim['skor']}")
            assert filtre.gecer_mi(tam)[0] == filtre.gecer_mi(dilim)[0], (
                f"{sem} {tarih}: filtre kararı farklı")
            karsilastirilan += 1

    assert karsilastirilan >= 15, f"yalnızca {karsilastirilan} karşılaştırma"


def test_sinyaller_gelecege_bakmaz():
    """T günü sorulduğunda T+1'in verisi hesaba girmemeli."""
    r = al.sinyaller("2024-11-04")
    assert r["tarih"] <= "2024-11-04"
    for s in r["sinyaller"]:
        b = al.gun(s["sembol"], "2024-11-04")
        assert b is not None
        # Sinyal fiyatı O GÜNÜN kapanışı olmalı, ertesi günün değil
        assert s["fiyat"] == pytest.approx(b.kapanis, rel=0.001), (
            f"{s['sembol']}: sinyal fiyatı o günün kapanışı değil")


def test_sinyaller_skora_gore_sirali():
    r = al.sinyaller("2024-11-04")
    skorlar = [s["skor"] for s in r["sinyaller"]]
    assert skorlar == sorted(skorlar, reverse=True)


def test_hafta_sonu_sorulursa_onceki_islem_gunu():
    r = al.sinyaller("2024-11-09")      # cumartesi
    assert r["tarih"] < "2024-11-09"


def test_bozuk_tarih_cokmez():
    r = al.sinyaller("bu bir tarih değil")
    assert r["sinyaller"] == []
