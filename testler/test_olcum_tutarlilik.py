"""Ölçüm ↔ ders metni tutarlılığı — AĞ ERİŞİMİ GEREKTİRMEZ.

Müfredat birçok yerde "sistemin ölçtüğü rakam" diye sayı aktarıyor. Bu
sayılar metnin içine gömülü sabitlerdi; ölçüm yenilendiğinde metni
güncellemek kimsenin hatırlamasına kalıyordu.

Bir eğitim sisteminde yanlış rakam, yanlış koddan daha zararlıdır: kod
hatası bir gün patlar ve fark edilir, yanlış rakam sessizce öğretilir.
2026-08-26'da tam bu yaşandı — dersler Sharpe 1,93 diye aktarıyordu,
doğrusu −0,71'di (backtest risksiz getiriyi çıkarmıyordu).

Bu testler `cekirdek/olcumler.py` ile ders metnini bağlar: ölçüm
yenilenip sabitler güncellenirse, metin de güncellenene kadar test düşer.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import re

import pytest

from cekirdek import backtest, istatistik, olcumler as o
from cekirdek.egitmen_dersler import TUM_DERSLER


METIN = "\n".join(
    f"{d.icerik}\n{d.bist}\n{d.tuzak}\n{d.ornek}" for d in TUM_DERSLER)


def _tr(sayi: float, basamak: int = 1) -> str:
    """Ders metinleri Türkçe ondalık ayırıcı kullanır: 117,7"""
    return f"{sayi:.{basamak}f}".replace(".", ",")


# ── Sharpe: risksiz getiri çıkarılıyor mu ─────────────────────────────────

def test_backtest_sharpe_risksiz_getiriyi_cikarir():
    """Bu satır olmadan mevduatın altında kalan strateji 1,9 skor alır."""
    import numpy as np
    import pandas as pd

    class SahteSonuc:
        islemler: list = []
        kacirilan = 0
        ayarlar: dict = {}

    s = SahteSonuc()
    # Yıllık ~%20 getiren, oynaklığı düşük bir seri: risksiz %40'ın ALTINDA
    gunluk = 0.20 / 252
    s.ozkaynak = pd.Series(
        1000 * np.cumprod(np.full(600, 1 + gunluk)),
        index=pd.bdate_range("2024-01-01", periods=600))
    m = backtest.metrik_hesapla(s)
    assert m["sharpe"] < 0, (
        f"yıllık %20 getiri risksiz %40 karşısında pozitif Sharpe aldı: "
        f"{m['sharpe']}")


def test_iki_sharpe_hesabi_ayni_sonucu_verir():
    """backtest ve istatistik iki farklı sayı üretirse hangisinin doğru
    olduğu bilinmez — 2026-08-26'ya kadar öyleydi."""
    import numpy as np
    import pandas as pd

    class SahteSonuc:
        islemler: list = []
        kacirilan = 0
        ayarlar: dict = {}

    rng = np.random.default_rng(7)
    ozk = pd.Series(
        1000 * np.cumprod(1 + rng.normal(0.0015, 0.012, 600)),
        index=pd.bdate_range("2024-01-01", periods=600))
    s = SahteSonuc(); s.ozkaynak = ozk
    assert backtest.metrik_hesapla(s)["sharpe"] == pytest.approx(
        istatistik.performans(ozk)["sharpe"], abs=0.02)


def test_risksiz_oran_iki_modulde_ayni():
    assert backtest.RISKSIZ_YILLIK == o.RISKSIZ_YILLIK


# ── ders metni ölçümlerle uyuşuyor mu ─────────────────────────────────────

@pytest.mark.parametrize("strateji", sorted(o.PORTFOY_BACKTEST))
def test_ders_metni_getiriyi_dogru_aktarir(strateji):
    g = o.PORTFOY_BACKTEST[strateji]["getiri"]
    assert _tr(abs(g)) in METIN, (
        f"{strateji} getirisi %{_tr(abs(g))} hiçbir derste geçmiyor — "
        f"ölçüm güncellendi ama ders metni eski kalmış olabilir")


def test_ders_metni_sharpe_degerlerini_dogru_aktarir():
    for st in ("kirilim", "trend"):
        s = o.PORTFOY_BACKTEST[st]["sharpe"]
        assert _tr(abs(s), 2) in METIN, f"{st} Sharpe {s} derslerde yok"


def test_eski_yanlis_sharpe_metinlerde_kalmadi():
    """Regresyon: düzeltmeden önceki değerler geri sızmamalı."""
    for yanlis in ("Sharpe 1,93", "Sharpe 1,53", "Sharpe 1,27"):
        assert yanlis not in METIN, f"eski yanlış değer geri gelmiş: {yanlis}"


def test_endeks_rakamlari_aktariliyor():
    assert _tr(o.ENDEKS["getiri"]) in METIN
    assert _tr(abs(o.ENDEKS["sharpe"]), 2) in METIN


def test_canli_sicil_rakamlari_aktariliyor():
    assert str(o.CANLI_SICIL["sinyal"]) in METIN
    assert _tr(o.CANLI_SICIL["kazanma_20g"]) in METIN


def test_piyasa_rakamlari_aktariliyor():
    assert str(o.PIYASA["xu100_tl_3y"]) in METIN
    assert _tr(abs(o.PIYASA["bist_reel_1y"])) in METIN


# ── ölçümün kendisi tutarlı mı ────────────────────────────────────────────

def test_negatif_sharpe_dusuk_getiriyle_tutarli():
    """Yıllık getirisi risksiz oranın altında olan her stratejinin Sharpe'ı
    negatif olmalı — aksi bir hesap hatasıdır."""
    for ad, d in o.PORTFOY_BACKTEST.items():
        if d["yillik"] < o.RISKSIZ_YILLIK:
            assert d["sharpe"] < 0, (
                f"{ad}: yıllık %{d['yillik']} < risksiz %{o.RISKSIZ_YILLIK} "
                f"ama Sharpe {d['sharpe']}")


def test_olcum_tarihi_var():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", o.OLCUM_TARIHI)
    assert o.OLCUM_TARIHI in METIN, (
        "ölçüm tarihi hiçbir derste geçmiyor — tarihsiz rakam, bayatladığında "
        "sessizce yanlış olur")
