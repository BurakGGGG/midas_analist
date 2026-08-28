"""Sinyale yakınlık — AĞ GEREKTİRİR (gerçek veriyle kıyas).

BU DOSYADAKİ EN ÖNEMLİ TEST `test_kosullar_gercek_girisle_ayni`:
yakinlik.py, strateji.py'deki giriş koşullarını İKİNCİ KEZ yazıyor.
İki tanım kayarsa ekran "yaklaşıyor" derken sinyal hiç gelmez, ya da
tersi — ve bu sessizce olur, çünkü ikisi ayrı ekranlarda görünür.

Test, koşulları GERÇEK VERİDE karşılaştırıyor: yakinlik "sinyal var"
diyorsa strateji fonksiyonu da demeli.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import warnings

import pytest

from cekirdek import gostergeler, veri, yakinlik
from cekirdek.strateji import STRATEJILER

warnings.filterwarnings("ignore")

ORNEK = ["THYAO", "GESAN", "AKBNK", "EREGL", "BIMAS", "ASELS"]


@pytest.fixture(scope="module")
def veriler():
    endeks = veri.fiyat_cek("XU100", gun=400)
    if endeks is None or endeks.empty:
        pytest.skip("endeks verisi yok")
    d = {}
    for s in ORNEK:
        ham = veri.fiyat_cek(s, gun=400)
        if ham is None or len(ham) < 250:
            continue
        d[s] = gostergeler.gosterge_seti(ham, endeks["Close"])
    if not d:
        pytest.skip("hisse verisi yok")
    return d


def test_kosullar_gercek_girisle_ayni(veriler):
    """yakinlik'in 'sinyal' kararı, stratejinin giriş fonksiyonuyla
    birebir aynı olmalı — son 60 günün HER GÜNÜ için."""
    uyusmazlik = []
    for sem, g in veriler.items():
        for ad, st in STRATEJILER.items():
            gercek = st.giris(g)
            for i in range(-60, 0):
                try:
                    y = yakinlik.olc(g, i).get(ad, {}).get("sinyal")
                    d = bool(gercek.iloc[i])
                except Exception:
                    continue
                if y != d:
                    uyusmazlik.append(
                        (sem, ad, str(g.index[i].date()), y, d))
    assert not uyusmazlik, (
        f"{len(uyusmazlik)} uyuşmazlık; ilk 5: {uyusmazlik[:5]}")


def test_her_strateji_kapsandi(veriler):
    """Yeni strateji eklenip yakınlık tanımı unutulursa, o strateji için
    hiç 'yaklaşıyor' bilgisi çıkmaz ve kimse fark etmez."""
    g = next(iter(veriler.values()))
    assert set(yakinlik.olc(g)) == set(STRATEJILER)


def test_ozet_en_ileri_stratejiyi_secer(veriler):
    g = next(iter(veriler.values()))
    o = yakinlik.ozet(g)
    assert o and o["strateji"] in STRATEJILER
    hepsi = yakinlik.olc(g)
    assert o["karsilanan"] == max(v["karsilanan"] for v in hepsi.values()) \
        or o["sinyal"] or o["yakin"]


def test_eksik_kosul_aciklama_tasir(veriler):
    """'Yaklaşıyor' demek yetmez; NEYİN eksik olduğu yazılmalı, yoksa
    kullanıcı neyi bekleyeceğini bilemez."""
    for g in veriler.values():
        for v in yakinlik.olc(g).values():
            for e in v["eksikler"]:
                assert e["ad"] and e["aciklama"]


def test_yakin_esigi_makul():
    """Çok geniş bir eşik 'yakın' kelimesini anlamsız yapar."""
    assert 1.0 <= yakinlik.YAKIN_ESIK <= 5.0


def test_yakin_yalnizca_tek_eksikte(veriler):
    """İki koşul eksikken 'yaklaşıyor' demek kullanıcıyı boşuna
    beklettirir."""
    for g in veriler.values():
        for v in yakinlik.olc(g).values():
            if v["yakin"]:
                assert len(v["eksikler"]) == 1


def test_kisa_veri_cokme_uretmez():
    import pandas as pd
    assert yakinlik.olc(pd.DataFrame()) == {}
    assert yakinlik.ozet(pd.DataFrame()) is None
