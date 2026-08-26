"""Öğretici şemalar — AĞ ve VERİ GEREKTİRMEZ.

Şema, canlı veri grafiğinden farklı bir şeydir: kavramı gerçek fiyatın
gürültüsü içinde değil, temiz bir çizimde gösterir. "Destek nedir"
sorusunun cevabı gerçek bir grafikte kaybolur.

Sözleşme istemciyle paylaşıldığı için testler ONU kilitler: alan adları
değişirse ressam sessizce boş çizer, kimse fark etmez.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import egitmen_sema as es
from cekirdek import egitmen_gorsel as gg
from cekirdek.egitmen_dersler import DERS_HARITA, MODUL_HARITA


ALANLAR = {"tur", "en", "boy", "cizgiler", "mumlar", "seviyeler",
           "etiketler", "oklar", "baslik", "aciklama", "sonuc"}


# ── sözleşme ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_sozlesmeye_uyar(ad):
    s = es.sema_getir(ad)
    assert s["tur"] == "sema"
    eksik = {"en", "boy", "cizgiler", "mumlar", "seviyeler", "etiketler"} - set(s)
    assert not eksik, f"{ad}: eksik alan {eksik}"
    assert set(s) <= ALANLAR, f"{ad}: bilinmeyen alan {set(s) - ALANLAR}"


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_bos_degil(ad):
    """Hiçbir şey çizmeyen şema, şema olmamasından kötüdür."""
    s = es.sema_getir(ad)
    assert (len(s["cizgiler"]) + len(s["mumlar"]) + len(s["seviyeler"])) > 0


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_sema_aciklama_ve_sonuc_tasir(ad):
    """Çizim tek başına yorumlanmaz; ne anlattığı yazılmalı."""
    s = es.sema_getir(ad)
    assert len(s.get("aciklama", "")) > 30
    assert len(s.get("sonuc", "")) > 30


@pytest.mark.parametrize("ad", sorted(es.SEMALAR))
def test_koordinatlar_uzayin_icinde(ad):
    """Uzayın dışına taşan nokta, ressamda kırpılır ve sessizce kaybolur."""
    s = es.sema_getir(ad)
    en, boy = s["en"], s["boy"]
    for c in s["cizgiler"]:
        for x, y in c["nokta"]:
            assert -1 <= x <= en + 1, f"{ad}: x={x} uzay dışı"
            assert -1 <= y <= boy + 1, f"{ad}: y={y} uzay dışı"
    for m in s["mumlar"]:
        assert 0 <= m["x"] <= en
        assert m["d"] <= m["a"] <= m["y"] or m["d"] <= m["k"] <= m["y"]


# ── mum tutarlılığı ────────────────────────────────────────────────────────

def test_mumlarda_yuksek_dusukten_buyuk():
    for ad in es.SEMALAR:
        for m in es.sema_getir(ad)["mumlar"]:
            assert m["y"] > m["d"], f"{ad}: en yüksek <= en düşük"


def test_mum_anatomisinde_bir_yukselen_bir_dusen_var():
    """Ders ikisini karşılaştırıyor; ikisi de olmalı."""
    m = es.sema_getir("mum_anatomisi")["mumlar"]
    assert any(x["k"] > x["a"] for x in m), "yükselen mum yok"
    assert any(x["k"] < x["a"] for x in m), "düşen mum yok"


def test_cekic_uzun_alt_fitilli():
    """Çekicin tanımı: alt fitil gövdenin en az iki katı."""
    m = es.sema_getir("mum_formasyonlari")["mumlar"][0]
    govde = abs(m["k"] - m["a"])
    alt_fitil = min(m["a"], m["k"]) - m["d"]
    assert alt_fitil >= govde * 2, f"gövde {govde}, alt fitil {alt_fitil}"


def test_doji_govdesi_neredeyse_yok():
    m = es.sema_getir("mum_formasyonlari")["mumlar"][1]
    assert abs(m["k"] - m["a"]) < (m["y"] - m["d"]) * 0.1


def test_yutan_boga_ikinci_mum_birinciyi_kapsar():
    m = es.sema_getir("mum_formasyonlari")["mumlar"]
    kucuk, buyuk = m[2], m[3]
    assert min(buyuk["a"], buyuk["k"]) <= min(kucuk["a"], kucuk["k"])
    assert max(buyuk["a"], buyuk["k"]) >= max(kucuk["a"], kucuk["k"])


def test_boslukta_gercekten_bosluk_var():
    """Şema boşluğu anlatıyor; mumlar arasında gerçekten boşluk olmalı."""
    m = es.sema_getir("bosluk")["mumlar"]
    onceki_en_yuksek = max(x["y"] for x in m[:2])
    sonraki_en_dusuk = min(x["d"] for x in m[2:])
    assert sonraki_en_dusuk > onceki_en_yuksek, "boşluk yok"


# ── derslere bağlanma ──────────────────────────────────────────────────────

def test_m13_dersleri_semaya_bagli():
    m13 = MODUL_HARITA["m13"]
    for d in m13.dersler:
        assert d.kod in gg.DERS_GORSEL, f"{d.kod} görselsiz"


def test_sema_onekli_esleme_gecerli():
    for kod, tur in gg.DERS_GORSEL.items():
        if tur.startswith("sema:"):
            assert tur.split(":", 1)[1] in es.SEMALAR, f"{kod} -> {tur} yok"


def test_ders_gorseli_semayi_dondurur():
    assert gg.ders_gorseli("d1303")["tur"] == "sema"


def test_olmayan_sema_cokme_uretmez():
    assert es.sema_getir("olmayan")["yok"] is True


def test_m13_dersleri_mufredatta():
    for kod in ("d1301", "d1302", "d1303", "d1304", "d1305", "d1306", "d1307",
                "d1308", "d1309", "d1310", "d1311"):
        assert kod in DERS_HARITA


# ── retest: rol değişimi ───────────────────────────────────────────────────

def test_retest_seviyesi_rol_degistirir():
    """Dersin tek iddiası bu: aynı seviye önce direnç, sonra destek."""
    sv = es.sema_getir("retest")["seviyeler"]
    assert len({x["y"] for x in sv}) == 1, "rol değişimi aynı seviyede olmalı"
    renkler = {x["renk"] for x in sv}
    assert "eksi" in renkler and "arti" in renkler


def test_retest_fiyati_seviyeyi_asip_geri_geliyor():
    s = es.sema_getir("retest")
    y_seviye = s["seviyeler"][0]["y"]
    nokta = s["cizgiler"][0]["nokta"]
    ust = [i for i, (_, y) in enumerate(nokta) if y > y_seviye]
    assert ust, "kırılım yok"
    # kırılımdan sonra seviyeye geri yaklaşan bir nokta olmalı
    sonra = [y for _, y in nokta[ust[0]:]]
    assert min(sonra) - y_seviye < 4, "retest yok — geri dönüş görünmüyor"
    assert sonra[-1] > y_seviye, "retest sonrası devam yok"


# ── mum sözlüğü: aynı şekil, zıt anlam ────────────────────────────────────

def test_mum_sozlugunde_iki_mum_ayni_sekilde():
    """Şemanın tamamı bu eşitliğe dayanıyor: şekil aynı, anlam farklı."""
    a, b = es.sema_getir("mum_sozlugu")["mumlar"]

    def olcu(m):
        return (round(abs(m["k"] - m["a"]), 6),
                round(min(m["a"], m["k"]) - m["d"], 6),
                round(m["y"] - max(m["a"], m["k"]), 6))

    assert olcu(a) == olcu(b), f"şekiller farklı: {olcu(a)} vs {olcu(b)}"


def test_mum_sozlugunde_uzun_alt_fitil_var():
    for m in es.sema_getir("mum_sozlugu")["mumlar"]:
        govde = abs(m["k"] - m["a"])
        assert min(m["a"], m["k"]) - m["d"] >= govde * 2


def test_mum_sozlugunde_biri_dususte_biri_yukseliste():
    """Konum farkı yoksa şema hiçbir şey anlatmıyor demektir."""
    s = es.sema_getir("mum_sozlugu")
    dusus, yukselis = s["cizgiler"][0]["nokta"], s["cizgiler"][1]["nokta"]
    assert dusus[0][1] > dusus[-1][1], "sol taraf düşen trend değil"
    assert yukselis[0][1] < yukselis[-1][1], "sağ taraf yükselen trend değil"


# ── formasyon sicili: yazı tura çizgisi ───────────────────────────────────

def test_formasyon_sicili_yazi_tura_cizgisi_tam_ortada():
    """Çubuklar ancak bir taban orana göre okunur; çizgi kalkarsa şema yalan
    söyler — %60'lık bir çubuk tek başına 'iyi' görünür."""
    s = es.sema_getir("formasyon_sicili")
    dikey = s["cizgiler"][0]["nokta"]
    x = {p[0] for p in dikey}
    assert len(x) == 1, "yazı tura çizgisi dikey değil"
    assert s["cizgiler"][0].get("kesik") is True


def test_formasyon_sicili_cubuklari_orana_gore_uzuyor():
    sv = es.sema_getir("formasyon_sicili")["seviyeler"]
    uzunluk = [x["x2"] - x["x1"] for x in sv]
    oran = [float(x["ad"].split("%")[1]) for x in sv]
    assert sorted(zip(oran, uzunluk)) == sorted(zip(oran, sorted(uzunluk)))


def test_formasyon_sicili_hepsi_yazi_turanin_ustunde():
    s = es.sema_getir("formasyon_sicili")
    esik = s["cizgiler"][0]["nokta"][0][0]
    assert all(x["x2"] > esik for x in s["seviyeler"])


# ── zaman serisi: trend ve gürültü ────────────────────────────────────────

def test_zaman_serisinde_gurultu_trendin_etrafinda_salinir():
    """Gürültü hep tek tarafta kalırsa çizilen şey gürültü değil, ikinci
    bir trenddir."""
    s = es.sema_getir("zaman_serisi")
    trend, fiyat = s["cizgiler"][0]["nokta"], s["cizgiler"][1]["nokta"]

    def trend_y(x):
        for (x1, y1), (x2, y2) in zip(trend, trend[1:]):
            if x1 <= x <= x2:
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
        return trend[-1][1]

    fark = [y - trend_y(x) for x, y in fiyat]
    assert any(f > 0 for f in fark) and any(f < 0 for f in fark)


def test_zaman_serisinde_trend_yukselir():
    trend = es.sema_getir("zaman_serisi")["cizgiler"][0]["nokta"]
    assert all(trend[i][1] < trend[i + 1][1] for i in range(len(trend) - 1))
