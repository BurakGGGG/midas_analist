"""Sistem sağlığı — sessiz arızayı sesli hale getirir.

NEDEN VAR: bu sistemin bütün değeri her akşam 18:10'da çalışan işte.
O iş çökerse ne olurdu? Bugüne kadar HİÇBİR ŞEY: hata ambara yazılıyor,
kayda düşüyor ve orada kalıyordu. Kullanıcı akşam mesajı gelmeyince
"bugün sinyal yoktur" diye düşünürdü. Bir hafta böyle geçse öğrenme
kaydında kapatılamaz bir delik oluşurdu — o günlerin fiyatları ve
sinyalleri geri getirilemez.

ÜÇ KORUMA:
  1) İş çökerse Telegram'a hata mesajı gider (gunluk.calistir içinde).
  2) İş HİÇ çalışmazsa (zamanlayıcı bozuk, sunucu kapalı) nöbetçi yakalar.
  3) Her başarılı çalışmadan sonra ambar yedeklenir.

Nöbetçinin sessiz kalması da bir karar: yanlış alarm, gerçek alarmı
değersizleştirir. Bu yüzden yalnızca İŞLEM GÜNÜNDE ve saat 19:00'dan
sonra, günde bir kez uyarır.
"""
from __future__ import annotations

import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from . import ambar

YEDEK_DIZIN = Path(__file__).resolve().parent.parent / "veri" / "yedek"
YEDEK_SAYISI = 7          # bir haftalık geriye dönüş
NOBET_SAATI = 19          # işin 18:10'da bitmiş olması beklenir
DISK_ESIK_YUZDE = 85


def bugun_calisti_mi(gun: date | None = None, yol=None) -> dict:
    """Bugün başarılı bir günlük iş var mı?"""
    gun = gun or date.today()
    with ambar.baglan(yol) as con:
        satirlar = [dict(r) for r in con.execute(
            "SELECT durum, baslangic, ozet FROM calisma "
            "WHERE substr(baslangic,1,10) = ? ORDER BY id DESC",
            (gun.isoformat(),))]
    basarili = [r for r in satirlar if r["durum"] == "başarılı"]
    hatali = [r for r in satirlar if r["durum"] == "hata"]
    return {"calisti": bool(basarili), "deneme": len(satirlar),
            "hata_sayisi": len(hatali),
            "son_hata": (hatali[0]["ozet"][:300] if hatali else None)}


UYARI_DOSYA = Path(__file__).resolve().parent.parent / "veri" / "uyari.json"


def uyarildi_mi(tur: str, gun: date | None = None) -> bool:
    """Bu uyarı bugün zaten gönderildi mi?"""
    import json
    gun = gun or date.today()
    try:
        return json.loads(UYARI_DOSYA.read_text(encoding="utf-8")).get(tur) \
            == gun.isoformat()
    except Exception:
        return False


def uyari_isaretle(tur: str, gun: date | None = None) -> None:
    """Uyarının gönderildiğini kaydeder.

    Nöbetçi bir EMNİYET AĞI, kopya değil: iş çöktüğünde anlık mesaj zaten
    gitmişse 19:00'da aynı şeyi tekrar söylemek gürültüdür. Ama anlık
    mesaj gönderilemediyse (Telegram erişilemedi, süreç sert öldü)
    nöbetçinin devreye girmesi şart.
    """
    import json
    gun = gun or date.today()
    try:
        UYARI_DOSYA.parent.mkdir(parents=True, exist_ok=True)
        d = {}
        if UYARI_DOSYA.exists():
            d = json.loads(UYARI_DOSYA.read_text(encoding="utf-8"))
        d[tur] = gun.isoformat()
        UYARI_DOSYA.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass


def nobet(simdi: datetime | None = None, yol=None) -> str | None:
    """İş çalışmadıysa uyarı metni döndürür, aksi halde None.

    Sessiz kalma koşulları bilinçli:
      - hafta sonu: BIST kapalı, iş zaten çalışmaz
      - 19:00'dan önce: iş henüz çalışmamış olabilir
      - iş başarılıysa: söylenecek bir şey yok
    """
    simdi = simdi or datetime.now()
    if simdi.weekday() >= 5:
        return None
    if simdi.hour < NOBET_SAATI:
        return None

    d = bugun_calisti_mi(simdi.date(), yol)
    if d["calisti"]:
        return None
    # Çökme anında mesaj gittiyse tekrar söyleme.
    if uyarildi_mi("gunluk_is", simdi.date()):
        return None

    if d["deneme"] == 0:
        return ("🔴 <b>Günlük iş bugün HİÇ ÇALIŞMADI</b>\n\n"
                "Zamanlayıcı tetiklenmemiş ya da sunucu kapalıydı. "
                "Bugünün fiyatları ve sinyalleri kaydedilmedi — bu veri "
                "geri getirilemez.\n\n"
                "<code>systemctl status midas-gunluk.timer</code>")
    return (f"🔴 <b>Günlük iş BAŞARISIZ</b>\n\n"
            f"{d['deneme']} deneme, {d['hata_sayisi']} hata.\n\n"
            f"<code>{d['son_hata']}</code>")


def yedek_al(kaynak: Path | None = None) -> dict:
    """Ambarı yedekler ve eskileri döndürür.

    NEYE KARŞI KORUR: bozulan veritabanı, hatalı göç, yanlış silme.
    NEYE KARŞI KORUMAZ: sunucunun tamamen kaybolması — yedek aynı diskte.
    Onun için düzenli olarak dışarı çekmek gerekir:
        rsync -az midas:midas/veri/ ~/midas_yedek/
    """
    kaynak = kaynak or ambar.VERITABANI
    if not kaynak.exists():
        return {"alindi": False, "not": "ambar yok"}
    YEDEK_DIZIN.mkdir(parents=True, exist_ok=True)
    hedef = YEDEK_DIZIN / f"ambar_{date.today().isoformat()}.db"
    try:
        # sqlite3 backup API: WAL kipinde açık bağlantı varken bile
        # tutarlı kopya üretir. Düz dosya kopyası yarım işlem yakalayabilir.
        import sqlite3
        with sqlite3.connect(kaynak) as k, sqlite3.connect(hedef) as h:
            k.backup(h)
    except Exception:
        shutil.copy2(kaynak, hedef)

    yedekler = sorted(YEDEK_DIZIN.glob("ambar_*.db"))
    silinen = 0
    for eski in yedekler[:-YEDEK_SAYISI]:
        try:
            eski.unlink(); silinen += 1
        except Exception:
            pass
    return {"alindi": True, "dosya": hedef.name,
            "boyut_mb": round(hedef.stat().st_size / 1e6, 1),
            "tutulan": len(yedekler) - silinen, "silinen": silinen}


def disk_durumu() -> dict:
    try:
        t, k, b = shutil.disk_usage(str(ambar.VERITABANI.parent))
        yuzde = round(k / t * 100)
        return {"kullanilan_yuzde": yuzde, "bos_gb": round(b / 1e9, 1),
                "uyari": yuzde >= DISK_ESIK_YUZDE}
    except Exception:
        return {"uyari": False}


def ozet(yol=None) -> dict:
    """Botun /durum komutu ve nöbet için toplu sağlık görünümü."""
    d = bugun_calisti_mi(yol=yol)
    disk = disk_durumu()
    yedekler = sorted(YEDEK_DIZIN.glob("ambar_*.db")) if YEDEK_DIZIN.exists() else []
    return {
        "gunluk_is": d,
        "disk": disk,
        "yedek_sayisi": len(yedekler),
        "son_yedek": yedekler[-1].name if yedekler else None,
    }
