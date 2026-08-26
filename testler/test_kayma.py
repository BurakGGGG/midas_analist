"""Canlı sicil ↔ backtest kıyası — AĞ ve VERİTABANI GEREKTİRMEZ.

Bu kıyasın işi hüküm vermek değil, HÜKÜM VERİLEBİLİR Mİ onu söylemek.
İki hata da pahalı:

  YANLIŞ ALARM  — "kenar aşınıyor" diyen bir sistem, her seferinde haksız
                  çıkarsa okunmaz olur ve gerçek bozulmayı da kaçırırsın.
  SAHTE GÜVEN   — 4 aylık veriyle "strateji çalışıyor" demek, gürültüyü
                  kanıt sanmaktır.

Eski kod sabit ±8 puanlık eşik kullanıyordu. Ölçüm: aylık kazanma oranı
%16,9 ile %81,2 arasında savruluyor — yani 8 puan, gürültünün çok altında
bir eşik ve neredeyse her ay alarm üretir.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import ogrenme as o


# ── beklenen aralık ────────────────────────────────────────────────────────

def test_kisa_pencere_genis_aralik_verir():
    """4 aylık pencere çok belirsizdir; aralık dar çıkarsa mantık bozuktur."""
    a = o.beklenen_aralik("trend", 4)
    assert a["yeterli_mi"]
    assert a["ust"] - a["alt"] > 20, f"aralık şüpheli dar: {a}"


def test_uzun_pencere_daralir():
    """Veri biriktikçe belirsizlik azalmalı."""
    kisa = o.beklenen_aralik("trend", 3)
    uzun = o.beklenen_aralik("trend", 12)
    assert (uzun["ust"] - uzun["alt"]) < (kisa["ust"] - kisa["alt"])


def test_ayni_girdi_ayni_cikti():
    """Tohum sabit olmalı: uyarı bir gün çıkıp ertesi gün kaybolmamalı."""
    assert o.beklenen_aralik("tepki", 5) == o.beklenen_aralik("tepki", 5)


def test_medyan_tarihsel_ortalamaya_yakin():
    a = o.beklenen_aralik("trend", 6)
    tarihsel = sum(o.BACKTEST_AYLIK["trend"]) / len(o.BACKTEST_AYLIK["trend"])
    assert abs(a["medyan"] - tarihsel) < 5


def test_bilinmeyen_strateji_hukum_vermez():
    assert o.beklenen_aralik("olmayan", 4)["yeterli_mi"] is False


def test_tarihsel_veriden_fazla_ay_istenirse_kirpilir():
    a = o.beklenen_aralik("trend", 999)
    assert a["ay"] == len(o.BACKTEST_AYLIK["trend"])


# ── karar mantığı ──────────────────────────────────────────────────────────

@pytest.fixture
def karar(monkeypatch):
    """kayma_analizi'ni sahte canlı sicil ile çalıştırır."""
    def kur(kazanma, ay, strateji="trend", sinyal=200):
        monkeypatch.setattr(o.ambar, "sinyal_karnesi",
                            lambda *a, **k: {"sinyal": sinyal,
                                             "kazanma_orani": kazanma,
                                             "ort_kazanc": 5.0, "ort_kayip": -4.0})
        monkeypatch.setattr(o, "_canli_ay_sayisi", lambda *a, **k: ay)
        return [x for x in o.kayma_analizi() if x["strateji"] == strateji][0]
    return kur


def test_normal_sonuc_alarm_uretmez(karar):
    """Tarihsel medyana yakın bir sonuç 'kenar aşınıyor' dememeli."""
    r = karar(kazanma=50.0, ay=4)
    assert "beklenen aralıkta" in r["durum"]


def test_gercekten_kotu_sonuc_yakalanir(karar):
    r = karar(kazanma=15.0, ay=4)
    assert "KÖTÜ" in r["durum"]


def test_gercekten_iyi_sonuc_yakalanir(karar):
    r = karar(kazanma=85.0, ay=4)
    assert "İYİ" in r["durum"]


def test_tek_ay_ile_hukum_verilmez(karar):
    """Bir ay, sinyal sayısı ne olursa olsun tek gözlemdir."""
    r = karar(kazanma=15.0, ay=1, sinyal=500)
    assert r["durum"] == "hüküm verilemez"
    assert "AY" in r["not"]


def test_eski_sabit_esik_artik_alarm_uretmiyor(karar):
    """Regresyon: eski mantık 8 puanlık farkı 'kenar aşınıyor' sayardı.

    trend referansı %48; %39 (9 puan altı) eskiden alarm üretirdi ama
    4 aylık pencerenin tarihsel aralığı bunu rahatça kapsıyor.
    """
    r = karar(kazanma=39.0, ay=4)
    assert r["kazanma_farki"] < -8          # eski eşiği aşıyor
    assert "beklenen aralıkta" in r["durum"]  # ama artık alarm yok


def test_aralik_cikti_ile_birlikte_donuyor(karar):
    """Kullanıcı hükmü değil, gerekçeyi de görmeli."""
    r = karar(kazanma=50.0, ay=4)
    assert r["aralik"]["yeterli_mi"]
    assert "beklenen aralık" in r["not"]


# ── referans tutarlılığı ───────────────────────────────────────────────────

def test_iki_referans_ayni_olcumden_gelmeli():
    """BACKTEST_REFERANS ile BACKTEST_AYLIK aynı koşudan türetilir.

    Biri güncellenip diğeri unutulursa kıyas sessizce tutarsızlaşır:
    'durum' bir referansa, 'kazanma_farki' başkasına bakar. Aylık serinin
    ortalaması, genel kazanma oranına yakın olmalı.
    """
    for st, ref in o.BACKTEST_REFERANS.items():
        aylik = o.BACKTEST_AYLIK.get(st)
        assert aylik, f"{st} için aylık seri yok"
        ort = sum(aylik) / len(aylik)
        assert abs(ort - ref["kazanma_orani"]) < 6, (
            f"{st}: aylık ortalama %{ort:.1f} ile genel oran "
            f"%{ref['kazanma_orani']} ayrışmış — referanslar farklı koşudan mı?")


def test_her_stratejinin_aylik_serisi_var():
    assert set(o.BACKTEST_AYLIK) == set(o.BACKTEST_REFERANS)


def test_aylik_seri_yeterli_uzunlukta():
    """Kısa seri, güven aralığını anlamsız kılar."""
    for st, aylik in o.BACKTEST_AYLIK.items():
        assert len(aylik) >= 12, f"{st}: {len(aylik)} ay — en az 12 gerekir"


def test_aylik_degerler_yuzde_araliginda():
    for st, aylik in o.BACKTEST_AYLIK.items():
        assert all(0 <= x <= 100 for x in aylik), st
