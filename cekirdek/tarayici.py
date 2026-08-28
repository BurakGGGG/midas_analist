"""Günlük tarayıcı: tüm evreni tarar, sıralar, uygulanabilir işlem önerir.

Çıktı bir EMİR değil, bir GÜNDEM'dir. Kararı sen verirsin, emri Midas'ta
sen girersin (Midas'ın API'si yok - hiçbir yazılım senin yerine emir veremez).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import veri, gostergeler, evren
from .risk import RiskAyarlari, pozisyon_hesapla, Pozisyon
from .strateji import Filtreler, skorla, STRATEJILER


def _yakinlik_ozeti(g) -> dict | None:
    """Sinyale yakınlık. Hesap patlarsa None — tarama çökmemeli."""
    try:
        from . import yakinlik as _y
        return _y.ozet(g)
    except Exception:
        return None


def _vade(sinyaller: list) -> str:
    """Sinyal veren stratejinin ölçülmüş tipik tutma süresi.

    Birden çok sinyal varsa EN UZUNU yazılır: kullanıcı pozisyonu ne
    kadar taşıyacağını planlarken kısa olana göre planlarsa erken çıkar.
    """
    from .strateji import STRATEJILER
    vadeler = [STRATEJILER[a].tipik_tutma for a in (sinyaller or [])
               if a in STRATEJILER]
    if not vadeler:
        return ""
    en_uzun = max(vadeler)
    for st in STRATEJILER.values():
        if st.tipik_tutma == en_uzun:
            return st.vade
    return ""


@dataclass
class Aday:
    sembol: str
    skor: float
    fiyat: float
    gunluk_degisim: float
    rsi: float
    adx: float
    atr_yuzde: float
    gg60: float | None
    sinyaller: list
    sma200_ustu: bool | None
    tl_hacim: float
    trend: float
    momentum: float
    zamanlama: float
    kalite: float
    pozisyon: Pozisyon | None = None
    elendi: str = ""
    # Sinyal YOKSA bile "ne kadar uzakta" bilgisi. Sistem her gün ya
    # "AL" diyordu ya susuyordu; arada koca bir alan var ve kullanıcı
    # orada yaşıyor (bkz. cekirdek/yakinlik.py).
    yakinlik: dict | None = None
    # Sinyal VARSA ölçülmüş tipik tutma süresi — "bu hafta mı, bu ay mı".
    vade: str = ""

    def sozluk(self) -> dict:
        d = asdict(self)
        d["pozisyon"] = asdict(self.pozisyon) if self.pozisyon else None
        return d


def tara(
    evren_adi: str = "bist100",
    risk_ayar: RiskAyarlari | None = None,
    filtre: Filtreler | None = None,
    gun: int = 500,
    onbellek_saat: float = 6.0,
    nakit: float | None = None,
    sadece_sinyalli: bool = False,
) -> tuple[list[Aday], list[Aday]]:
    """(gecenler, elenenler) döndürür. Gecenler skora göre sıralı."""
    risk_ayar = risk_ayar or RiskAyarlari()
    filtre = filtre or Filtreler()

    semboller = evren.evren_getir(evren_adi)
    print(f"» {len(semboller)} hisse taranıyor ({evren_adi})...")
    ham = veri.toplu_cek(semboller, gun=gun, onbellek_saat=onbellek_saat)
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=gun, onbellek_saat=onbellek_saat)
    endeks_kapanis = endeks["Close"] if not endeks.empty else None

    gecenler: list[Aday] = []
    elenenler: list[Aday] = []

    for sem, df in sorted(ham.items()):
        if df is None or len(df) < 60:
            continue
        try:
            g = gostergeler.gosterge_seti(df, endeks_kapanis)
            r = skorla(g)
        except Exception:
            continue

        aday = Aday(
            sembol=sem, skor=r["skor"], fiyat=r["fiyat"],
            gunluk_degisim=r["gunluk_degisim"], rsi=r["rsi"], adx=r["adx"],
            atr_yuzde=r["atr_yuzde"], gg60=r["gg60"], sinyaller=r["sinyaller"],
            sma200_ustu=r["sma200_ustu"], tl_hacim=r["tl_hacim"],
            trend=r["trend"], momentum=r["momentum"],
            zamanlama=r["zamanlama"], kalite=r["kalite"],
            yakinlik=_yakinlik_ozeti(g),
            vade=_vade(r["sinyaller"]),
        )

        uygun, sebep = filtre.gecer_mi(g)
        if not uygun:
            aday.elendi = sebep
            elenenler.append(aday)
            continue

        # Birden çok sinyal varsa en dar stop'u kullan (en temkinli olan)
        sk = hk = None
        if r["sinyaller"]:
            aktif = [STRATEJILER[a] for a in r["sinyaller"] if a in STRATEJILER]
            if aktif:
                en_dar = min(aktif, key=lambda st: st.atr_stop_kat)
                sk, hk = en_dar.atr_stop_kat, en_dar.atr_hedef_kat
        aday.pozisyon = pozisyon_hesapla(
            sem, r["fiyat"], r["atr"], risk_ayar, kullanilabilir_nakit=nakit,
            stop_kat=sk, hedef_kat=hk,
        )
        if sadece_sinyalli and not r["sinyaller"]:
            continue
        gecenler.append(aday)

    gecenler.sort(key=lambda a: (len(a.sinyaller) > 0, a.skor), reverse=True)
    elenenler.sort(key=lambda a: a.skor, reverse=True)
    return gecenler, elenenler


def tek_hisse(sembol: str, risk_ayar: RiskAyarlari | None = None, gun: int = 500) -> dict | None:
    """Tek bir hisse için ayrıntılı analiz."""
    risk_ayar = risk_ayar or RiskAyarlari()
    df = veri.fiyat_cek(sembol, gun=gun)
    if df.empty:
        return None
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=gun)
    g = gostergeler.gosterge_seti(df, endeks["Close"] if not endeks.empty else None)
    r = skorla(g)
    uygun, sebep = Filtreler().gecer_mi(g)
    sk = hk = None
    if r["sinyaller"]:
        aktif = [STRATEJILER[a] for a in r["sinyaller"] if a in STRATEJILER]
        if aktif:
            en_dar = min(aktif, key=lambda st: st.atr_stop_kat)
            sk, hk = en_dar.atr_stop_kat, en_dar.atr_hedef_kat
    poz = pozisyon_hesapla(evren.sade_kod(sembol), r["fiyat"], r["atr"], risk_ayar,
                           stop_kat=sk, hedef_kat=hk)
    s = g.iloc[-1]
    return {
        "sembol": evren.sade_kod(sembol), "skor": r, "filtre": (uygun, sebep),
        "pozisyon": poz, "gostergeler": g,
        "seviyeler": {
            "EMA20": float(s["EMA20"]) if np.isfinite(s["EMA20"]) else None,
            "EMA50": float(s["EMA50"]) if np.isfinite(s["EMA50"]) else None,
            "SMA200": float(s["SMA200"]) if np.isfinite(s["SMA200"]) else None,
            "BB_alt": float(s["BB_alt"]) if np.isfinite(s["BB_alt"]) else None,
            "BB_ust": float(s["BB_ust"]) if np.isfinite(s["BB_ust"]) else None,
            "DON_ust": float(s["DON_ust"]) if np.isfinite(s["DON_ust"]) else None,
            "52h_zirve": float(g["High"].tail(252).max()),
            "52h_dip": float(g["Low"].tail(252).min()),
        },
    }
