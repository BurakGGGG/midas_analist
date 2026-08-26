"""JSON'a güvenli dönüşüm.

Çekirdek modüller dataclass, pandas Series/DataFrame ve numpy tipleri döndürür.
Bunlar doğrudan JSON'a çevrilemez; NaN ise geçerli JSON değildir (null olmalı).
Bu katman olmadan API sessizce bozuk JSON üretir.
"""
from __future__ import annotations

import dataclasses
import math
from datetime import date, datetime

import numpy as np
import pandas as pd


def guvenli(x):
    """Her şeyi JSON'a çevrilebilir hale getirir. NaN/Inf -> None."""
    if x is None:
        return None
    if isinstance(x, (str, bool)):
        return x
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (datetime, pd.Timestamp)):
        return x.isoformat()
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): guvenli(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set, np.ndarray)):
        return [guvenli(v) for v in x]
    if isinstance(x, pd.Series):
        return {str(k): guvenli(v) for k, v in x.items()}
    if isinstance(x, pd.DataFrame):
        return [guvenli(r) for r in x.to_dict("records")]
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {k: guvenli(v) for k, v in dataclasses.asdict(x).items()}
    if hasattr(x, "__dict__"):
        return {k: guvenli(v) for k, v in vars(x).items() if not k.startswith("_")}
    return str(x)


def _kasitli_son(satir: str, genislik: int = 62) -> bool:
    t = satir.rstrip()
    if not t:
        return False
    if t[-1] in '.:!?"\u201d)':
        return True
    return len(t) < genislik


def metin_akit(metin: str, genislik: int = 62) -> str:
    """Sabit sarılmış metni akışkan hale getirir, KASITLI satır sonlarını korur.

    Kaynak metinler dosyada okunabilir olsun diye ~78 karakterde elle sarılmış.
    Telefonda bu satır sonları olduğu gibi görünür ve metin garip kırılır.
    Ama ders içeriğindeki tanım satırları ve etiketler kasıtlı kısadır — onlar
    korunmalı. Ayrım: cümle sonu noktalaması veya belirgin kısa satır = kasıtlı.
    """
    if not metin:
        return metin

    def madde_mi(t: str) -> bool:
        return (t[:2] in ("\u00b7 ", "- ", "\u2022 ")
                or (len(t) > 2 and t[0].isdigit() and t[1] in (")", ".")))

    cikti = []
    for p in metin.split("\n\n"):
        birlesik, o = [], ""
        for sat in p.split("\n"):
            t = sat.strip()
            if not t:
                continue
            if o and madde_mi(t):
                birlesik.append(o)
                o = t
            else:
                o = f"{o} {t}".strip() if o else t
            if _kasitli_son(t, genislik) and o:
                birlesik.append(o)
                o = ""
        if o:
            birlesik.append(o)
        cikti.append("\n".join(birlesik))
    return "\n\n".join(cikti)


def seri_noktalari(s: pd.Series, azami: int = 120) -> list[dict]:
    """Grafik için seri, mobil yükü düşük tutacak şekilde.

    İki tasarruf: (1) nokta sayısı seyreltilir — telefon ekranında 800 nokta
    zaten 3 piksele düşer, (2) günlük veride tam ISO damgası yerine sadece
    tarih yazılır. İkisi birlikte yükü yarıya indiriyor.
    """
    if s is None or len(s) == 0:
        return []
    s = s.dropna()
    adim = max(1, len(s) // azami)
    cikti = []
    for i, v in s.iloc[::adim].items():
        if isinstance(i, (pd.Timestamp,)):
            t = i.strftime("%Y-%m-%d") if (i.hour == 0 and i.minute == 0) else i.isoformat()
        else:
            t = str(i)
        cikti.append({"t": t, "d": guvenli(v)})
    return cikti
