"""Ders görselleri — AĞ ERİŞİMİ GEREKTİRMEZ (canlı üreticiler hariç tutulur).

Görsellerin işi dersi somutlaştırmak. İki hata pahalı:

  BOŞ KUTU   — veri gelmediğinde yine de bir grafik çerçevesi çizmek,
               grafik hiç olmamasından kötüdür.
  ÇÖKME      — bir hisse verisi eksik diye ders ekranı açılmamalı.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import pytest

from cekirdek import egitmen_gorsel as g
from cekirdek.egitmen_dersler import DERS_HARITA


# ── eşleme ─────────────────────────────────────────────────────────────────

def test_eslenen_dersler_gercekten_var():
    for kod in g.DERS_GORSEL:
        assert kod in DERS_HARITA, f"{kod} müfredatta yok"


def test_her_gorsel_turunun_ureticisi_var():
    """Canlı görsellerin üreticisi URETICILER'de, şemalarınki SEMALAR'da.

    İkisi ayrı: canlı görsel veriden üretilir ve boş dönebilir; şema
    saf çizimdir, hep aynı şeyi verir.
    """
    from cekirdek.egitmen_sema import SEMALAR
    for kod, tur in g.DERS_GORSEL.items():
        if tur.startswith("sema:"):
            assert tur.split(":", 1)[1] in SEMALAR, f"{kod} -> {tur} şeması yok"
        else:
            assert tur in g.URETICILER, f"{kod} -> {tur} üreticisi yok"


def test_gorseli_olmayan_ders_bos_doner():
    assert g.ders_gorseli("d101")["yok"] is True


def test_olmayan_ders_cokme_uretmez():
    assert g.ders_gorseli("dYOK")["yok"] is True


# ── veri gelmezse ──────────────────────────────────────────────────────────

def test_uretici_patlarsa_sessizce_yok_doner(monkeypatch):
    """Ders ekranı grafik yüzünden açılmaz hâle gelmemeli."""
    monkeypatch.setitem(g.URETICILER, "kayip_asimetrisi",
                        lambda: (_ for _ in ()).throw(RuntimeError("çöktü")))
    r = g.ders_gorseli("d801")
    assert r["yok"] is True
    assert "çöktü" in r.get("hata", "")


def test_veri_yoksa_bos_kutu_cizilmez(monkeypatch):
    monkeypatch.setitem(g.URETICILER, "rsi", lambda: {"yok": True})
    assert g.ders_gorseli("d704") == {"yok": True}


# ── kayıp asimetrisi (saf matematik, veri gerekmez) ───────────────────────

def test_kayip_asimetrisi_dogru_hesaplanir():
    r = g.kayip_asimetrisi()
    i = r["etiketler"].index("-%50")
    assert r["degerler"][i] == pytest.approx(100.0)


def test_kayip_asimetrisi_artan_egri():
    """Kayıp büyüdükçe gereken kazanç HIZLANARAK artmalı."""
    d = g.kayip_asimetrisi()["degerler"]
    assert all(d[i] < d[i + 1] for i in range(len(d) - 1))
    assert d[-1] > d[0] * 20


def test_kayip_asimetrisi_sonuc_cumlesi_var():
    """Grafik tek başına yorumlanmaz; ne göreceğini söylemek şart."""
    r = g.kayip_asimetrisi()
    assert "%100" in r["sonuc"]


# ── seri biçimi ────────────────────────────────────────────────────────────

def test_seri_mobil_bicimini_uretir():
    s = g._seri([1.0, 2.0, 3.0])
    assert all(set(x) == {"t", "d"} for x in s)
    assert [x["d"] for x in s] == [1.0, 2.0, 3.0]


def test_seri_gecersiz_degerleri_atar():
    import numpy as np
    assert len(g._seri([1.0, np.nan, 3.0, None])) == 2


def test_seri_uzun_veriyi_seyreltir():
    """Telefonda 500 nokta birkaç piksele düşer ama yükü beşe katlar."""
    assert len(g._seri(list(range(1000)), azami=120)) <= 130


def test_pandas_serisi_tarih_tasir():
    import pandas as pd
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-08-24", "2026-08-25"]))
    out = g._seri(s)
    assert out[0]["t"] == "2026-08-24"
