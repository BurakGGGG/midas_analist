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

İKİ TÜR KAYIT:
  pozisyon — sahip olunan hisse. Karar defterine alım yazılınca
             kendiliğinden ekleniyor, satılınca siliniyor. Stop ve hedef
             POZİSYONUN kuralları; stopa değmesi kötü haber.
  izleme   — sahip OLMADIĞIN, sadece beklediğin hisse. Seviyeleri sen
             koyuyorsun ve alta inmesi çoğu zaman İYİ haber: beklediğin
             fiyat gelmiş oluyor. Bu yüzden uyarı metinleri ayrı.

İkisi aynı dosyada ve aynı 5 dakikalık kontrolde yaşıyor: iki paralel
sistem kurmak, birinde düzeltilen hatanın ötekinde kalması demekti.
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


def liste(tur: str | None = None) -> list[dict]:
    """Kayıtlar. `tur` verilirse yalnızca o tür.

    Eski kayıtlarda `tur` alanı yok — hepsi pozisyondu.
    """
    kayitlar = [{**p, "tur": p.get("tur", "pozisyon")}
                for p in _oku()["pozisyonlar"]]
    return [p for p in kayitlar if tur is None or p["tur"] == tur]


def izle(sembol: str, alt: float = 0.0, ust: float = 0.0,
         not_: str = "") -> dict:
    """İzleme listesine ekler. Aynı sembol varsa günceller.

    En az bir seviye gerekiyor: seviyesiz bir izleme kaydı hiç uyarı
    üretmez ve kullanıcı "ekledim ama hiç haber gelmiyor" der.
    """
    sembol = sembol.upper().replace(".IS", "").strip()
    if not sembol:
        raise ValueError("sembol boş")
    alt, ust = float(alt or 0), float(ust or 0)
    if alt <= 0 and ust <= 0:
        raise ValueError("en az bir seviye gerekiyor (alt ya da üst)")
    if alt > 0 and ust > 0 and alt >= ust:
        raise ValueError("alt seviye üst seviyenin altında olmalı")

    d = _oku()
    d["pozisyonlar"] = [p for p in d["pozisyonlar"]
                        if not (p["sembol"] == sembol
                                and p.get("tur", "pozisyon") == "izleme")]
    kayit = {"sembol": sembol, "tur": "izleme", "alt": alt, "ust": ust,
             "not": (not_ or "").strip()[:120],
             "tarih": date.today().isoformat(), "uyarildi": {}}
    d["pozisyonlar"].append(kayit)
    _yaz(d)
    return kayit


def izleme_sil(sembol: str) -> bool:
    sembol = sembol.upper().replace(".IS", "").strip()
    d = _oku()
    once = len(d["pozisyonlar"])
    d["pozisyonlar"] = [p for p in d["pozisyonlar"]
                        if not (p["sembol"] == sembol
                                and p.get("tur", "pozisyon") == "izleme")]
    _yaz(d)
    return len(d["pozisyonlar"]) < once


def ekle(sembol: str, stop: float, hedef: float = 0.0,
         giris: float = 0.0) -> dict:
    """Pozisyonu izlemeye alır. Aynı sembol varsa günceller."""
    sembol = sembol.upper().replace(".IS", "").strip()
    d = _oku()
    # Yalnızca POZİSYON kaydını değiştir: aynı hisseyi hem tutup hem
    # ayrı bir seviyeden izlemek mümkün olmalı.
    d["pozisyonlar"] = [p for p in d["pozisyonlar"]
                        if not (p["sembol"] == sembol
                                and p.get("tur", "pozisyon") == "pozisyon")]
    kayit = {"sembol": sembol, "tur": "pozisyon",
             "stop": float(stop), "hedef": float(hedef),
             "giris": float(giris or 0), "tarih": date.today().isoformat(),
             "uyarildi": {}}
    d["pozisyonlar"].append(kayit)
    _yaz(d)
    return kayit


def sil(sembol: str) -> bool:
    sembol = sembol.upper().replace(".IS", "").strip()
    d = _oku()
    once = len(d["pozisyonlar"])
    d["pozisyonlar"] = [p for p in d["pozisyonlar"]
                        if not (p["sembol"] == sembol
                                and p.get("tur", "pozisyon") == "pozisyon")]
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

    [(kayit, fiyat, tur)] döner. Türler:
      pozisyon kayıtları — stop_gecti | hedef_gecti | stop_yakin
      izleme kayıtları   — alt_gecti | ust_gecti

    Her tür kayıt başına günde bir kez üretilir.
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

        # ── izleme kaydı: sahip olmadığın, beklediğin hisse
        if p.get("tur", "pozisyon") == "izleme":
            alt = float(p.get("alt") or 0)
            ust = float(p.get("ust") or 0)
            if alt > 0 and fiyat <= alt and not _uyarildi_mi(p, "alt_gecti"):
                cikti.append((dict(p), fiyat, "alt_gecti"))
                _uyarildi_isaretle(p, "alt_gecti")
                degisti = True
            if ust > 0 and fiyat >= ust and not _uyarildi_mi(p, "ust_gecti"):
                cikti.append((dict(p), fiyat, "ust_gecti"))
                _uyarildi_isaretle(p, "ust_gecti")
                degisti = True
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
