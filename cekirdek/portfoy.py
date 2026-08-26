"""Açık pozisyon takibi.

Midas'ta emri sen giriyorsun; bu modül girdiğin işlemi kaydeder ve her gün
"stop'a değdi mi, hedefe ulaştı mı, çıkış sinyali var mı" diye kontrol eder.
Sistemin disiplin tarafı burada: karar anında değil, ÖNCEDEN yazılmış kural.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from pathlib import Path

import numpy as np

from . import veri, gostergeler, evren
from .strateji import STRATEJILER

DOSYA = Path(__file__).resolve().parent.parent / "portfoy.json"


@dataclass
class AcikPozisyon:
    sembol: str
    adet: int
    giris: float
    stop: float
    hedef: float
    tarih: str
    strateji: str = "kirilim"
    not_: str = ""

    @property
    def maliyet(self) -> float:
        return self.adet * self.giris


def yukle() -> list[AcikPozisyon]:
    if not DOSYA.exists():
        return []
    try:
        return [AcikPozisyon(**p) for p in json.loads(DOSYA.read_text(encoding="utf-8"))]
    except Exception:
        return []


def kaydet(pozisyonlar: list[AcikPozisyon]) -> None:
    DOSYA.write_text(
        json.dumps([asdict(p) for p in pozisyonlar], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ekle(sembol: str, adet: int, giris: float, stop: float, hedef: float,
         strateji: str = "kirilim", not_: str = "") -> AcikPozisyon:
    poz = yukle()
    sem = evren.sade_kod(sembol)
    poz = [p for p in poz if p.sembol != sem]      # aynı hisse tekrar eklenirse üzerine yaz
    yeni = AcikPozisyon(sem, adet, giris, stop, hedef,
                        date.today().isoformat(), strateji, not_)
    poz.append(yeni)
    kaydet(poz)
    return yeni


def cikar(sembol: str) -> bool:
    poz = yukle()
    sem = evren.sade_kod(sembol)
    kalan = [p for p in poz if p.sembol != sem]
    if len(kalan) == len(poz):
        return False
    kaydet(kalan)
    return True


def kontrol(gun: int = 400) -> list[dict]:
    """Her açık pozisyon için güncel durum ve AKSİYON önerisi."""
    pozlar = yukle()
    if not pozlar:
        return []
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=gun)
    ek = endeks["Close"] if not endeks.empty else None

    sonuc = []
    for p in pozlar:
        df = veri.fiyat_cek(p.sembol, gun=gun, onbellek_saat=2.0)
        if df.empty:
            sonuc.append({"poz": p, "hata": "veri alınamadı"})
            continue
        g = gostergeler.gosterge_seti(df, ek)
        s = g.iloc[-1]
        fiyat = float(s["Close"])
        kar = (fiyat - p.giris) * p.adet
        kar_y = (fiyat / p.giris - 1) * 100

        # çıkış sinyali var mı?
        st = STRATEJILER.get(p.strateji, STRATEJILER["kirilim"])
        try:
            cikis_sinyali = bool(st.cikis(g).iloc[-1])
        except Exception:
            cikis_sinyali = False

        gun_sayisi = int(np.busday_count(
            datetime.fromisoformat(p.tarih).date(), date.today()))

        if fiyat <= p.stop:
            aksiyon, aciklama = "SAT", f"STOP tetiklendi ({fiyat:.2f} ≤ {p.stop:.2f})"
        elif fiyat >= p.hedef:
            aksiyon, aciklama = "SAT", f"HEDEF geldi ({fiyat:.2f} ≥ {p.hedef:.2f})"
        elif cikis_sinyali:
            aksiyon, aciklama = "SAT", "strateji çıkış sinyali verdi"
        elif gun_sayisi >= st.azami_tutma:
            aksiyon, aciklama = "SAT", f"azami tutma süresi doldu ({gun_sayisi} iş günü)"
        else:
            aksiyon = "TUT"
            mesafe = (fiyat - p.stop) / fiyat * 100
            aciklama = f"stop'a %{mesafe:.1f}, hedefe %{(p.hedef - fiyat) / fiyat * 100:.1f}"

        # kâr varsa stop'u başabaşa çekme önerisi (risksiz hale getirme)
        oneri = ""
        atr = float(s["ATR14"]) if np.isfinite(s["ATR14"]) else 0
        if aksiyon == "TUT" and kar_y > 0 and atr > 0:
            yeni_stop = max(p.stop, fiyat - st.atr_stop_kat * atr)
            if yeni_stop > p.stop * 1.005:
                oneri = f"stop'u {p.stop:.2f} → {yeni_stop:.2f} yukarı çek (iz süren stop)"

        sonuc.append({
            "poz": p, "fiyat": fiyat, "kar": kar, "kar_yuzde": kar_y,
            "aksiyon": aksiyon, "aciklama": aciklama, "oneri": oneri,
            "gun": gun_sayisi, "rsi": float(s["RSI14"]),
            "gunluk_degisim": float(s["Close"] / g["Close"].iloc[-2] - 1) * 100,
        })
    return sonuc
