"""Önbellek ısıtma ve periyodik tazeleme.

Ölçüm: önbellek sıcakken 100 hisselik tarama 1,65 sn, soğukken dakikalar.
Bu yüzden sunucu açılışta veriyi arka planda indirir; ilk istek beklemez,
'hazırlanıyor' cevabı alır.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime

from cekirdek import veri, evren, makro, sektor

DURUM = {
    "hazir": False,
    "isiniyor": False,
    "son_tazeleme": None,
    "hisse_sayisi": 0,
    "hata": None,
}
_kilit = threading.Lock()


def isit(gun: int = 800, sessiz: bool = True) -> None:
    with _kilit:
        if DURUM["isiniyor"]:
            return
        DURUM["isiniyor"] = True
    try:
        semboller = evren.evren_getir("bist100")
        d = veri.toplu_cek(semboller, gun=gun, onbellek_saat=6.0, sessiz=sessiz)
        veri.fiyat_cek(evren.ENDEKS, gun=gun)
        for _anahtar, (kod, _ad, _grup) in makro.GOSTERGELER.items():
            veri.fiyat_cek(kod, gun=400, ham=not kod.endswith(".IS"))
        try:
            sektor.sektor_haritasi()
        except Exception:
            pass
        DURUM.update(hazir=True, hisse_sayisi=len(d),
                     son_tazeleme=datetime.now().isoformat(), hata=None)
    except Exception as e:
        DURUM["hata"] = str(e)[:300]
    finally:
        DURUM["isiniyor"] = False


def arka_planda_isit(gun: int = 800) -> None:
    threading.Thread(target=isit, args=(gun,), daemon=True).start()


def periyodik(saat: float = 4.0) -> None:
    """BIST 10:00-18:00 açık; 4 saatte bir tazeleme yeterli."""
    def dongu():
        while True:
            time.sleep(saat * 3600)
            isit()
    threading.Thread(target=dongu, daemon=True).start()
