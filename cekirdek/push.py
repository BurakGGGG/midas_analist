"""Uygulama push bildirimleri (Firebase Cloud Messaging, HTTP v1).

`telegram.py` ile AYNI SÖZLEŞME: bu modül TAŞIMA katmanı (nasıl
gönderilir), `bildirim.py` İÇERİK katmanı (ne yazılır). İkisi ayrı
tutuluyor ki mesaj metni ağ olmadan test edilebilsin.

NEDEN TELEGRAM'IN YANINA: kullanıcı Telegram'ı çok kullanmak istemedi.
Ama Telegram kapatılmıyor — ikisi de yapılandırılmışsa ikisine de
gidiyor. Bir gün .env'den Telegram anahtarlarını silersen o kanal
kendiliğinden susar; kod değişikliği gerekmez.

YAPILANDIRMA (.env):
    MIDAS_FCM_ANAHTAR   Firebase servis hesabı JSON dosyasının YOLU

Anahtar yoksa bütün fonksiyonlar sessizce "gönderilmedi" döner. Bildirim
gönderilemedi diye günlük iş ÇÖKMEMELİ — bildirim işin kendisi değil,
üstüne eklenen katman. Bu kural telegram.py'den geliyor ve aynı sebeple
burada da geçerli.

NEDEN LEGACY DEĞİL HTTP v1: eski FCM sunucu-anahtarı API'si (tek bir
Authorization başlığıyla çalışan basit olan) 2024'te kapatıldı. HTTP v1
servis hesabıyla OAuth2 jetonu istiyor; jetonu google-auth üretiyor,
elle RSA imzalamıyoruz.

GEÇERSİZ JETON: kullanıcı uygulamayı silerse ya da jeton yenilenirse FCM
404/UNREGISTERED döner. Bu jetonlar temizlenmezse her gönderimde boşuna
istek atılır ve hata sayısı şişer. `gonder` onları ayrıca döndürüyor,
çağıran siliyor (bkz. cekirdek/cihaz.py).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

KAPSAM = ["https://www.googleapis.com/auth/firebase.messaging"]
UC = "https://fcm.googleapis.com/v1/projects/{proje}/messages:send"
ZAMAN_ASIMI = 15.0

# Jeton bir saat geçerli; her bildirimde yeniden üretmek gereksiz ağ turu.
_onbellek: dict = {"kimlik": None, "proje": ""}


def _anahtar_yolu() -> str:
    return os.environ.get("MIDAS_FCM_ANAHTAR", "").strip()


def kurulu_mu() -> bool:
    y = _anahtar_yolu()
    return bool(y) and Path(y).is_file()


def _kimlik():
    """Servis hesabı kimliği ve proje kimliği. Başarısızsa (None, '')."""
    if _onbellek["kimlik"] is not None:
        return _onbellek["kimlik"], _onbellek["proje"]
    if not kurulu_mu():
        return None, ""
    try:
        from google.oauth2 import service_account
        yol = _anahtar_yolu()
        proje = json.loads(Path(yol).read_text(encoding="utf-8")).get("project_id", "")
        k = service_account.Credentials.from_service_account_file(yol, scopes=KAPSAM)
        _onbellek["kimlik"], _onbellek["proje"] = k, proje
        return k, proje
    except Exception:
        return None, ""


def _erisim_jetonu() -> tuple[str, str]:
    k, proje = _kimlik()
    if k is None:
        return "", ""
    try:
        from google.auth.transport.requests import Request
        if not k.valid:
            k.refresh(Request())
        return k.token or "", proje
    except Exception:
        return "", ""


def gonder(baslik: str, govde: str, jetonlar: list[str],
           veri: dict | None = None) -> dict:
    """Bildirimi cihazlara gönderir.

    FCM HTTP v1 toplu gönderim kabul etmiyor; her cihaz ayrı istek.
    Cihaz sayısı bir kullanıcının telefonlarıyla sınırlı olduğu için
    (bir, belki iki) bu bir sorun değil.

    Döner: {"gonderildi": n, "basarisiz": n, "gecersiz": [jeton, ...]}
    """
    sonuc = {"gonderildi": 0, "basarisiz": 0, "gecersiz": []}
    jetonlar = [j for j in (jetonlar or []) if j]
    if not jetonlar or not kurulu_mu():
        return sonuc

    erisim, proje = _erisim_jetonu()
    if not erisim or not proje:
        sonuc["basarisiz"] = len(jetonlar)
        return sonuc

    import requests
    url = UC.format(proje=proje)
    basliklar = {"Authorization": f"Bearer {erisim}",
                 "Content-Type": "application/json; charset=UTF-8"}

    for j in jetonlar:
        govde_json = {
            "message": {
                "token": j,
                "notification": {"title": baslik, "body": govde},
                # Veri alanı uygulamanın bildirime dokununca doğru ekrana
                # gitmesi için. FCM veri değerlerinin STRING olmasını
                # şart koşuyor; sayı gönderilirse istek reddedilir.
                "data": {k: str(v) for k, v in (veri or {}).items()},
                "android": {
                    "priority": "high",
                    "notification": {
                        # Uygulamanın kendi rengi; sistem varsayılan mavisi
                        # tema ile çelişiyordu.
                        "color": "#A3E635",
                        "default_sound": True,
                    },
                },
            }
        }
        try:
            c = requests.post(url, headers=basliklar, json=govde_json,
                              timeout=ZAMAN_ASIMI)
            if c.status_code == 200:
                sonuc["gonderildi"] += 1
                continue
            sonuc["basarisiz"] += 1
            # 404 UNREGISTERED / 400 INVALID_ARGUMENT: jeton ölü.
            if c.status_code in (400, 404):
                metin = c.text or ""
                if "UNREGISTERED" in metin or "INVALID_ARGUMENT" in metin:
                    sonuc["gecersiz"].append(j)
        except Exception:
            sonuc["basarisiz"] += 1
    return sonuc


def dogrula() -> dict:
    """Kurulum kontrolü — anahtar okunuyor mu, jeton alınabiliyor mu."""
    if not _anahtar_yolu():
        return {"tamam": False, "not": "MIDAS_FCM_ANAHTAR .env'de yok"}
    if not Path(_anahtar_yolu()).is_file():
        return {"tamam": False,
                "not": f"anahtar dosyası bulunamadı: {_anahtar_yolu()}"}
    erisim, proje = _erisim_jetonu()
    if not erisim:
        return {"tamam": False, "not": "erişim jetonu alınamadı — "
                                       "anahtar bozuk ya da yetki yok"}
    return {"tamam": True, "proje": proje}
