"""Telegram bildirimleri — sunucunun kullanıcıya ULAŞABİLMESİ.

NEDEN VAR: günlük iş her akşam çalışıp günü özetliyordu, sonra
kullanıcı uygulamayı açana kadar bekliyordu. Ölçüldü: 65 dersten 1'i
okunmuştu, sebep içerik değil erişimdi. Sunucu 7/24 çalışıyor ama tek
yönlü — dışarı hiçbir şey söylemiyordu.

Telegram seçildi çünkü: uygulama derlemeye, mağazaya, Firebase anahtarına
gerek yok; bedava; her telefonda çalışır; ve iki yönlü (bot komut da
alabilir, bkz. `komutlari_oku`).

BAĞIMLILIK EKLENMEDİ: urllib yetiyor. ARM sunucuda her yeni paket kurulum
süresi demek; tek bir HTTPS POST için kütüphane taşımaya değmez.

YAPILANDIRMA (.env):
    MIDAS_TELEGRAM_TOKEN   BotFather'dan alınan bot anahtarı
    MIDAS_TELEGRAM_SOHBET  mesajların gideceği sohbet kimliği

Yapılandırma yoksa bütün fonksiyonlar sessizce False döner. Bildirim
gönderilemedi diye günlük iş ÇÖKMEMELİ — bildirim işin kendisi değil,
üstüne eklenen bir katman.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{yontem}"

# Telegram tek mesajda en fazla 4096 karakter kabul eder. Sınıra dayanmak
# yerine biraz altında kesiyoruz: HTML etiketleri de sayılıyor.
AZAMI_UZUNLUK = 3900


def _ayar() -> tuple[str, str]:
    return (os.environ.get("MIDAS_TELEGRAM_TOKEN", "").strip(),
            os.environ.get("MIDAS_TELEGRAM_SOHBET", "").strip())


def kurulu_mu() -> bool:
    t, s = _ayar()
    return bool(t and s)


def _cagir(yontem: str, veri: dict, zaman_asimi: float = 20.0) -> dict | None:
    token, _ = _ayar()
    if not token:
        return None
    try:
        istek = urllib.request.Request(
            API.format(token=token, yontem=yontem),
            data=urllib.parse.urlencode(veri).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as c:
            return json.loads(c.read())
    except Exception:
        return None


def kacis(metin: str) -> str:
    """HTML kipi için kaçış. Şirket adlarında & ve < geçebiliyor."""
    return (str(metin).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def gonder(metin: str, sessiz: bool = False) -> bool:
    """Mesaj gönderir. Uzunsa böler — kesmek yerine bölmek, çünkü kesilen
    yerde önemli bilgi kalabilir."""
    token, sohbet = _ayar()
    if not (token and sohbet) or not metin:
        return False

    parcalar, kalan = [], metin
    while len(kalan) > AZAMI_UZUNLUK:
        # Satır sonundan böl: cümle ortasından bölmek okunmaz hale getirir.
        kes = kalan.rfind("\n", 0, AZAMI_UZUNLUK)
        if kes < AZAMI_UZUNLUK // 2:
            kes = AZAMI_UZUNLUK
        parcalar.append(kalan[:kes])
        kalan = kalan[kes:].lstrip("\n")
    parcalar.append(kalan)

    tamam = True
    for p in parcalar:
        c = _cagir("sendMessage", {
            "chat_id": sohbet, "text": p, "parse_mode": "HTML",
            "disable_web_page_preview": "true",
            "disable_notification": "true" if sessiz else "false"})
        tamam = tamam and bool(c and c.get("ok"))
    return tamam


def komutlari_oku(son_id: int = 0, bekle: int = 0) -> tuple[list[dict], int]:
    """Bota gelen yeni mesajları okur.

    (mesajlar, son_islenen_id) döner. `son_id` sonrasını ister; Telegram
    okunanları 24 saat sonra siler, bu yüzden en son işlenen kimliği
    çağıran taraf saklamalıdır.

    Sürekli çalışan bir süreç YOK: bu fonksiyon zamanlayıcıdan periyodik
    çağrılır. Bot'u daemon yapmak, tek kullanıcılı bir sistem için
    gereksiz bir hareketli parça olurdu.
    """
    # UZUN YOKLAMA: `bekle` saniye boyunca mesaj bekler. 1 dakikalık
    # zamanlayıcı + 45 saniyelik bekleme = komut neredeyse anında
    # cevaplanır. Beklemesiz çalışsaydı gecikme ortalama yarım dakika
    # olurdu; bir sohbet botunda bu kırık hissettirir.
    #
    # urlopen zaman aşımı Telegram'ınkinden BÜYÜK olmalı, yoksa bağlantı
    # sunucu cevap vermeden önce kopar.
    c = _cagir("getUpdates",
               {"offset": son_id + 1, "timeout": bekle, "limit": 20},
               zaman_asimi=bekle + 15)
    if not c or not c.get("ok"):
        return [], son_id
    mesajlar, en_son = [], son_id
    for g in c.get("result", []):
        en_son = max(en_son, int(g.get("update_id", 0)))
        m = g.get("message") or {}
        metin = (m.get("text") or "").strip()
        if metin:
            mesajlar.append({
                "metin": metin,
                "sohbet": str((m.get("chat") or {}).get("id", "")),
                "kimlik": int(g.get("update_id", 0)),
            })
    return mesajlar, en_son


def dogrula() -> dict:
    """Kurulum kontrolü — token geçerli mi, bot kim?"""
    if not kurulu_mu():
        return {"tamam": False, "not": "MIDAS_TELEGRAM_TOKEN / "
                                       "MIDAS_TELEGRAM_SOHBET .env'de yok"}
    c = _cagir("getMe", {})
    if not c or not c.get("ok"):
        return {"tamam": False, "not": "Token geçersiz ya da Telegram'a "
                                       "ulaşılamadı"}
    r = c.get("result", {})
    return {"tamam": True, "bot": r.get("username"), "ad": r.get("first_name")}


def komut_menusu_kur(komutlar: list[tuple[str, str]]) -> bool:
    """Telegram arayüzündeki komut menüsünü kaydeder.

    Menü olmadan kullanıcı komutları ezberlemek zorunda kalır — bir botun
    kullanılmama sebeplerinin başında bu gelir. Bir kez çağrılması yeterli,
    Telegram tarafında saklanır.
    """
    return bool(_cagir("setMyCommands", {
        "commands": json.dumps([{"command": k, "description": a}
                                for k, a in komutlar])}))
