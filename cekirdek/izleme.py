"""Pozisyon izleme — stop/hedef alarmı.

NEDEN AYRI BİR DEFTER: API durumsuzdur, pozisyonlar telefonda yaşar
(bkz. mobil/lib/servis/modeller.dart). Sunucu onları bilmez ve bilmemeli
— durumsuzluk bilinçli bir tasarım kararıydı.

Ama alarm için sunucunun neyi izleyeceğini bilmesi gerekiyor. Çözüm:
telefonun portföyünü sunucuya taşımak DEĞİL, botun kendi küçük izleme
listesini tutması. Kullanıcı Telegram'dan `/izle THYAO 250 300` der,
liste burada yaşar. Portföyün kaynağı hâlâ telefon; bu sadece "şu
seviyeleri gözet" listesi.

TEKRAR UYARI ENGELİ: iş 5 dakikada bir çalışıyor. Stop bir kez geçildiğinde
her turda mesaj atmak, bildirimi çöpe çevirir ve kullanıcı hepsini
susturur. Her uyarı türü pozisyon başına GÜNDE BİR kez gönderilir.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DOSYA = Path(__file__).resolve().parent.parent / "veri" / "izleme.json"

# Stopa bu kadar yaklaşınca önceden haber ver (yüzde).
YAKIN_ESIK = 2.0


def _oku() -> dict:
    if not DOSYA.exists():
        return {"pozisyonlar": [], "son_guncelleme_id": 0}
    try:
        d = json.loads(DOSYA.read_text(encoding="utf-8"))
        d.setdefault("pozisyonlar", [])
        d.setdefault("son_guncelleme_id", 0)
        return d
    except Exception:
        return {"pozisyonlar": [], "son_guncelleme_id": 0}


def _yaz(d: dict) -> None:
    DOSYA.parent.mkdir(parents=True, exist_ok=True)
    DOSYA.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def liste() -> list[dict]:
    return _oku()["pozisyonlar"]


def ekle(sembol: str, stop: float, hedef: float = 0.0,
         giris: float = 0.0) -> dict:
    """Pozisyonu izlemeye alır. Aynı sembol varsa günceller."""
    sembol = sembol.upper().replace(".IS", "").strip()
    d = _oku()
    d["pozisyonlar"] = [p for p in d["pozisyonlar"] if p["sembol"] != sembol]
    kayit = {"sembol": sembol, "stop": float(stop), "hedef": float(hedef),
             "giris": float(giris or 0), "tarih": date.today().isoformat(),
             "uyarildi": {}}
    d["pozisyonlar"].append(kayit)
    _yaz(d)
    return kayit


def sil(sembol: str) -> bool:
    sembol = sembol.upper().replace(".IS", "").strip()
    d = _oku()
    once = len(d["pozisyonlar"])
    d["pozisyonlar"] = [p for p in d["pozisyonlar"] if p["sembol"] != sembol]
    _yaz(d)
    return len(d["pozisyonlar"]) < once


def son_id(yeni: int | None = None) -> int:
    """İşlenen son Telegram güncelleme kimliği — aynı komutu iki kez
    çalıştırmamak için."""
    d = _oku()
    if yeni is not None:
        d["son_guncelleme_id"] = int(yeni)
        _yaz(d)
    return int(d.get("son_guncelleme_id", 0))


def _uyarildi_mi(p: dict, tur: str) -> bool:
    return (p.get("uyarildi") or {}).get(tur) == date.today().isoformat()


def _uyarildi_isaretle(p: dict, tur: str) -> None:
    p.setdefault("uyarildi", {})[tur] = date.today().isoformat()


def kontrol(fiyat_getir) -> list[tuple[dict, float, str]]:
    """İzlenen pozisyonları güncel fiyatla karşılaştırır.

    fiyat_getir: sembol -> son fiyat (float) veya None. Dışarıdan
    geçiliyor ki test ağ gerektirmesin.

    [(pozisyon, fiyat, tur)] döner; tur: stop_gecti | hedef_gecti |
    stop_yakin. Her tür pozisyon başına günde bir kez üretilir.
    """
    d = _oku()
    cikti = []
    degisti = False

    for p in d["pozisyonlar"]:
        try:
            fiyat = fiyat_getir(p["sembol"])
        except Exception:
            fiyat = None
        if fiyat is None or fiyat <= 0:
            continue

        stop = float(p.get("stop") or 0)
        hedef = float(p.get("hedef") or 0)

        if stop > 0 and fiyat <= stop:
            if not _uyarildi_mi(p, "stop_gecti"):
                cikti.append((dict(p), fiyat, "stop_gecti"))
                _uyarildi_isaretle(p, "stop_gecti")
                degisti = True
        elif stop > 0 and fiyat <= stop * (1 + YAKIN_ESIK / 100):
            if not _uyarildi_mi(p, "stop_yakin"):
                cikti.append((dict(p), fiyat, "stop_yakin"))
                _uyarildi_isaretle(p, "stop_yakin")
                degisti = True

        if hedef > 0 and fiyat >= hedef:
            if not _uyarildi_mi(p, "hedef_gecti"):
                cikti.append((dict(p), fiyat, "hedef_gecti"))
                _uyarildi_isaretle(p, "hedef_gecti")
                degisti = True

    if degisti:
        _yaz(d)
    return cikti
