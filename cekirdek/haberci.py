"""Bildirim dağıtıcı — aynı haberi tüm açık kanallara yollar.

KATMANLAR: `bildirim.py` ne yazılacağını, `telegram.py` ve `push.py`
nasıl gönderileceğini biliyor. Bu modül üçünü birleştiriyor ve tek
sorusu var: hangi kanallar açık?

NEDEN AYRI MODÜL: dağıtımı `bildirim.py` içine koymak onun "ağ
gerektirmez, saf metin üretir" özelliğini bozardı — o özellik mesaj
metinlerinin ağsız test edilebilmesini sağlıyor.

KANAL SEÇİMİ YAPILANDIRMADAN: her iki kanal da .env'de tanımlıysa
ikisine birden gider. Telegram anahtarlarını silersen o kanal
kendiliğinden susar, push anahtarını silersen o susar. Kod değişikliği
ya da bayrak yok — kurulum neyi açtıysa o çalışır.

HİÇBİR ŞEY FIRLATMAZ: bildirim gönderilemedi diye günlük iş çökmemeli.
Bu kural telegram.py'den geliyor ve dağıtıcıda da geçerli.
"""
from __future__ import annotations


def yolla(metin: str, baslik: str, govde: str,
          veri: dict | None = None, kullanici_id: int | None = None) -> dict:
    """Telegram'a `metin` (HTML), push'a `baslik`/`govde` (düz) gönderir.

    İkisi ayrı parametre çünkü ayrı biçimler: Telegram uzun ve HTML
    kaldırır, push bildirimi kilit ekranında iki satır gösterir. Aynı
    metni ikisine de vermek, birinde etiket kalabalığı diğerinde
    kırpılmış cümle demekti.
    """
    sonuc = {"telegram": False, "push": {"gonderildi": 0, "basarisiz": 0}}

    try:
        from . import telegram
        if metin and telegram.kurulu_mu():
            sonuc["telegram"] = bool(telegram.gonder(metin))
    except Exception as e:
        sonuc["telegram_hata"] = str(e)[:120]

    try:
        from . import push, cihaz
        if baslik and push.kurulu_mu():
            jetonlar = cihaz.jetonlar(kullanici_id)
            if jetonlar:
                r = push.gonder(baslik, govde, jetonlar, veri)
                sonuc["push"] = {"gonderildi": r["gonderildi"],
                                 "basarisiz": r["basarisiz"]}
                # Ölü jetonları hemen at: birikirlerse her bildirimde
                # boşuna istek atılır ve hata sayısı gerçek arızayı gizler.
                if r["gecersiz"]:
                    sonuc["push"]["atilan"] = cihaz.temizle(r["gecersiz"])
    except Exception as e:
        sonuc["push_hata"] = str(e)[:120]

    return sonuc


def acik_kanallar() -> dict:
    """Hangi kanallar yapılandırılmış? Sağlık ve kurulum ekranları için."""
    d = {"telegram": False, "push": False}
    try:
        from . import telegram
        d["telegram"] = telegram.kurulu_mu()
    except Exception:
        pass
    try:
        from . import push
        d["push"] = push.kurulu_mu()
    except Exception:
        pass
    return d
