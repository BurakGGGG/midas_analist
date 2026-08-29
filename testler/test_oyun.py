"""Sanal İşlem oyunu — üretilmiş piyasa.

Bu dosyanın koruduğu üç şey:

1. AYNI TOHUM AYNI OYUN. Telefon yalnızca tohumu saklıyor; oyun
   gerektiğinde yeniden üretiliyor. Üretim tohumdan sapsa kullanıcının
   yarısına kadar geldiği oyun bir daha açılmaz.

2. FARKLI TOHUM FARKLI OYUN. "Her girdiğim oyun bir öncekinden farklı
   olsun" isteğinin karşılığı bu.

3. ZORLUK GERÇEKTEN FARK YARATIYOR. Etiket koyup aynı piyasayı üretmek
   en kolay ve en yanıltıcı hata olurdu.
"""
import numpy as np
import pytest

from cekirdek import oyun


@pytest.fixture(scope="module")
def normal():
    return oyun.uret(4242, "normal")


# ── belirlenimcilik ───────────────────────────────────────────────────────

def test_ayni_tohum_ayni_oyun():
    a = oyun.uret(999, "normal")
    b = oyun.uret(999, "normal")
    assert a["hisseler"] == b["hisseler"]
    assert a["sinyaller"] == b["sinyaller"]
    assert a["haberler"] == b["haberler"]
    assert a["endeks"] == b["endeks"]


def test_farkli_tohum_farkli_oyun():
    a = oyun.uret(1, "normal")
    b = oyun.uret(2, "normal")
    assert a["hisseler"] != b["hisseler"]
    assert [h["kod"] for h in a["hisseler"]] != [h["kod"] for h in b["hisseler"]]


def test_ayni_tohum_farkli_zorluk_farkli_oyun():
    a = oyun.uret(555, "kolay")
    b = oyun.uret(555, "zor")
    assert len(a["hisseler"]) != len(b["hisseler"])


def test_uretilen_tohumlar_tekrar_etmiyor():
    tohumlar = {oyun.tohum_uret() for _ in range(200)}
    assert len(tohumlar) == 200


def test_bilinmeyen_zorluk_reddedilir():
    with pytest.raises(ValueError):
        oyun.uret(1, "imkansiz")


# ── fiyat serisi sağlamlığı ───────────────────────────────────────────────

def _barlar(o):
    for h in o["hisseler"]:
        for b in h["barlar"]:
            yield h["kod"], b


def test_fiyatlar_pozitif(normal):
    for kod, (a, y, d, k, hac) in _barlar(normal):
        assert a > 0 and y > 0 and d > 0 and k > 0, kod
        assert hac >= 0


def test_ohlc_tutarli(normal):
    """Yüksek en yüksek, düşük en düşük olmalı. Bozuksa stop kontrolü
    saçmalar: hisse hiç değmediği fiyattan stop yemiş görünür."""
    for kod, (a, y, d, k, _) in _barlar(normal):
        assert y >= max(a, k) - 1e-9, f"{kod}: yüksek < açılış/kapanış"
        assert d <= min(a, k) + 1e-9, f"{kod}: düşük > açılış/kapanış"
        assert y >= d


def test_gunluk_hareket_makul(normal):
    """Üretilmiş piyasa da BIST gibi davranmalı: günde %20'yi aşan
    hareketler kural dışı ve oyunu inandırıcılıktan çıkarır."""
    asiri = 0
    toplam = 0
    for h in normal["hisseler"]:
        b = h["barlar"]
        for i in range(1, len(b)):
            toplam += 1
            d = abs(b[i][3] / b[i - 1][3] - 1)
            if d > 0.20:
                asiri += 1
    assert asiri / toplam < 0.002, f"{asiri}/{toplam} bar %20'den fazla oynadı"


def test_bar_sayisi_gecmis_arti_oyun(normal):
    beklenen = oyun.GOSTERILEN_GECMIS + normal["gun_sayisi"]
    for h in normal["hisseler"]:
        assert len(h["barlar"]) == beklenen
    assert len(normal["endeks"]) == beklenen


# ── zorluk gerçekten fark yaratıyor mu ────────────────────────────────────

def _verimlilik(o) -> float:
    """Trend netliğinin ölçüsü: kat edilen NET yol / TOPLAM yol.

    1'e yakınsa fiyat düz gidiyor (temiz trend), 0'a yakınsa aynı yerde
    testere çiziyor. Ölçmeden "zorluk trendi bozuyor" demek, etiket
    koyup aynı piyasayı üretmekten farksız olurdu.
    """
    oranlar = []
    for h in o["hisseler"]:
        k = np.array([b[3] for b in h["barlar"]])[-o["gun_sayisi"]:]
        yol = np.abs(np.diff(k)).sum()
        if yol > 0:
            oranlar.append(abs(k[-1] - k[0]) / yol)
    return float(np.mean(oranlar))


def test_kolay_mod_ZOR_moddan_daha_temiz_trend():
    kolay = np.mean([_verimlilik(oyun.uret(t, "kolay")) for t in range(20, 32)])
    zor = np.mean([_verimlilik(oyun.uret(t, "zor")) for t in range(20, 32)])
    assert kolay > zor * 1.25, (
        f"kolay {kolay:.3f} · zor {zor:.3f} — zorluk trend netliğini "
        f"yeterince değiştirmiyor")


def _gunluk_oynaklik(o) -> float:
    ler = []
    for h in o["hisseler"]:
        k = np.array([b[3] for b in h["barlar"]])
        ler.append(float(np.std(np.diff(np.log(k)))))
    return float(np.mean(ler))


def test_zor_mod_daha_oynak():
    kolay = np.mean([_gunluk_oynaklik(oyun.uret(t, "kolay")) for t in range(5, 13)])
    zor = np.mean([_gunluk_oynaklik(oyun.uret(t, "zor")) for t in range(5, 13)])
    assert zor > kolay * 1.3, f"kolay {kolay:.4f} · zor {zor:.4f}"


@pytest.mark.parametrize("zorluk", ["kolay", "normal", "zor"])
def test_zorluk_ayarlari_ciktiya_yansiyor(zorluk):
    z = oyun.ZORLUKLAR[zorluk]
    o = oyun.uret(31, zorluk)
    assert len(o["hisseler"]) == z.hisse_sayisi
    assert o["gun_sayisi"] == z.gun
    assert o["ayar"]["sermaye"] == z.sermaye
    assert o["ayar"]["kayma_bp"] == z.kayma_bp


def test_haber_guvenilirligi_zorlukla_dusuyor():
    def oran(zorluk):
        h = []
        for t in range(40, 52):
            o = oyun.uret(t, zorluk)
            h += [x["guvenilir"] for x in o["haberler"]]
        return sum(h) / len(h)

    assert oran("kolay") == 1.0, "kolayda haber hep dürüst olmalı"
    assert oran("zor") < 0.75, "zorda haberlerin bir kısmı yanıltıcı olmalı"


# ── sinyaller ─────────────────────────────────────────────────────────────

def test_sinyaller_oyun_gunlerinde(normal):
    for s in normal["sinyaller"]:
        assert 0 <= s["gun"] < normal["gun_sayisi"]


def test_sinyal_stop_hedef_tutarli(normal):
    for s in normal["sinyaller"]:
        assert s["stop"] < s["fiyat"] < s["hedef"], s


def test_sinyal_fiyati_O_GUNUN_kapanisi(normal):
    """Sinyal ertesi günün fiyatıyla üretilseydi oyun kullanıcıya
    bilinmesi imkânsız bir bilgi verirdi."""
    kod_bar = {h["kod"]: h["barlar"] for h in normal["hisseler"]}
    for s in normal["sinyaller"][:40]:
        i = oyun.GOSTERILEN_GECMIS + s["gun"]
        kapanis = kod_bar[s["sembol"]][i][3]
        assert abs(s["fiyat"] - kapanis) < 0.02, (
            f"{s['sembol']} gün {s['gun']}: sinyal {s['fiyat']} "
            f"kapanış {kapanis}")


def test_sinyal_stratejileri_gercek(normal):
    from cekirdek.strateji import STRATEJILER
    for s in normal["sinyaller"]:
        assert s["strateji"] in STRATEJILER


def test_kolay_modda_da_sinyal_uretilir():
    """Piyasa fazla düzgün üretilirse hiçbir giriş koşulu tetiklenmez
    ve analist bölümü boş kalır."""
    toplam = sum(len(oyun.uret(t, "kolay")["sinyaller"]) for t in range(60, 66))
    assert toplam > 20, f"6 kolay oyunda yalnızca {toplam} sinyal"


# ── haberler ──────────────────────────────────────────────────────────────

def test_haberler_oyun_gunlerinde(normal):
    for h in normal["haberler"]:
        assert 0 <= h["gun"] < normal["gun_sayisi"]


def test_haber_sembolleri_oyundaki_hisseler(normal):
    kodlar = {h["kod"] for h in normal["hisseler"]}
    for h in normal["haberler"]:
        assert not h["sembol"] or h["sembol"] in kodlar


def test_ayni_baslik_arka_arkaya_cikmaz(normal):
    """Aynı cümlenin üst üste çıkması haberi anlamsızlaştırıyor ve
    üretilmiş olduğunu ele veriyor."""
    son = []
    for h in normal["haberler"]:
        assert h["baslik"] not in son, h["baslik"]
        son.append(h["baslik"])
        if len(son) > 12:
            son.pop(0)


def test_haber_basliklari_sirket_adi_tasiyor(normal):
    kisa = {oyun._kisa_ad(h["ad"]) for h in normal["hisseler"]}
    sirket = [h for h in normal["haberler"] if h["sembol"]]
    assert sirket, "hiç şirket haberi yok"
    for h in sirket[:20]:
        assert any(k in h["baslik"] for k in kisa), h["baslik"]


def test_kisa_ad_uzun_unvani_kirpiyor():
    assert oyun._kisa_ad("Anadolu Efes Biracılık ve Malt Sanayii") \
        == "Anadolu Efes"
    assert oyun._kisa_ad("Akbank") == "Akbank"


# ── boyut ─────────────────────────────────────────────────────────────────

def test_oyun_yuku_telefona_makul():
    """Tek seferde iniyor ve sonrası çevrimdışı. Büyürse ilk açılış
    mobil şebekede uzar."""
    import json
    for zorluk in ("kolay", "normal", "zor"):
        kb = len(json.dumps(oyun.uret(7, zorluk)).encode()) / 1024
        assert kb < 400, f"{zorluk}: {kb:.0f} KB"
