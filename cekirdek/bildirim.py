"""Bildirim metinleri — sistem durumunu okunabilir mesaja çevirir.

`telegram.py` TAŞIMA katmanı (nasıl gönderilir), bu modül İÇERİK katmanı
(ne yazılır). Ayrı tutulmalarının sebebi: içerik test edilebilir olmalı,
taşıma ise ağ gerektirir. Karışsalar, mesaj metnini sınamak için her
seferinde Telegram'a bağlanmak gerekirdi.

TASARIM KURALI: telefonda okunacak. Uzun rapor değil, bakınca anlaşılan
birkaç satır. Ayrıntı zaten uygulamada var — bildirim onun yerini almaz,
"aç bak" der.
"""
from __future__ import annotations

from .telegram import kacis


def _yuzde(v) -> str:
    try:
        return f"{float(v):+.2f}%"
    except Exception:
        return "—"


def gunluk_ozet(ozet: dict, siniflar: dict | None = None) -> str:
    """18:10 işinin sonucu — akşam cebe düşen mesaj."""
    if not ozet or ozet.get("hata"):
        return "⚠️ <b>Midas</b> — günlük iş çalıştı ama özet çıkarılamadı."

    s = [f"📊 <b>Midas · {kacis(ozet.get('tarih', ''))}</b>"]

    endeks = ozet.get("endeks_degisim")
    if endeks is not None:
        yon = "🔴" if float(endeks) < 0 else "🟢"
        s.append(f"{yon} XU100 {_yuzde(endeks)}  ·  "
                 f"{ozet.get('yukselen', 0)} yükselen / "
                 f"{ozet.get('dusen', 0)} düşen")

    reel = ozet.get("bist_reel_1y")
    if reel is not None and float(reel) < 0:
        # Reel getiri negatifken nominal rakama sevinmek en sık tuzak.
        s.append(f"   BIST 1 yıl <b>reel</b> getirisi {_yuzde(reel)}")

    rejim = (ozet.get("rejim") or {}).get("ad")
    if rejim:
        s.append(f"   Rejim: {kacis(rejim)}")

    # ── sinyaller
    sinyaller = ozet.get("sinyal_veren") or []
    onerilen = [x for x in sinyaller if x.get("onerilir", x.get("alinabilir"))]
    karantinali = [x for x in sinyaller if x.get("karantina")]

    s.append("")
    if onerilen:
        s.append(f"🎯 <b>{len(onerilen)} sinyal</b>")
        for x in onerilen[:5]:
            s.append(f"   <b>{kacis(x['sembol'])}</b> "
                     f"{kacis(x.get('sinyaller', []) and x['sinyaller'][0] or '')} "
                     f"· skor {x.get('skor', 0):.0f} · {x.get('fiyat', 0):.2f} ₺")
    elif karantinali:
        # "Sinyal yok" ile "sinyal var ama önerilmiyor" farklı şeyler.
        # İkincisini gizlemek, kullanıcıyı bilgisiz bırakır.
        s.append(f"⏸ <b>Önerilen sinyal yok</b> — {len(karantinali)} sinyal "
                 f"karantinadaki stratejilerden geldi.")
    else:
        s.append("😴 <b>Bugün sinyal yok.</b> Nakitte beklemek de bir pozisyondur.")

    # ── karantina durumu
    if siniflar:
        kapali = [k for k, v in siniflar.items() if not v.get("onerilir", True)]
        if kapali:
            s.append(f"   ⚠️ Karantinada: {kacis(', '.join(kapali))}")

    # ── KAP
    kap = ozet.get("kap_bildirim")
    if kap:
        s.append(f"\n📄 KAP: {kap} şirket bildirimi")

    return "\n".join(s)


def stop_uyarisi(pozisyon: dict, fiyat: float, tur: str) -> str:
    """Stop ya da hedef seviyesine yaklaşma/geçme uyarısı.

    Bu mesajın var olma sebebi tek: günlük iş 18:10'da çalışıyor. Stop
    saat 11:00'de geçilirse akşama kadar haberin olmaz — o da uygulamayı
    açarsan. Gerçek para kaybettiren boşluk burasıdır.
    """
    sem = kacis(pozisyon.get("sembol", "?"))
    giris = float(pozisyon.get("giris", 0) or 0)
    kar = ((fiyat / giris - 1) * 100) if giris > 0 else 0.0

    if tur == "stop_gecti":
        return (f"🛑 <b>{sem} STOP SEVİYESİNİN ALTINDA</b>\n"
                f"Şu an {fiyat:.2f} ₺ · stop {pozisyon.get('stop', 0):.2f} ₺\n"
                f"Giriş {giris:.2f} ₺ · {kar:+.1f}%\n\n"
                f"<i>Kararı sen verirsin — sistem emir göndermez.</i>")
    if tur == "hedef_gecti":
        return (f"🎯 <b>{sem} HEDEFE ULAŞTI</b>\n"
                f"Şu an {fiyat:.2f} ₺ · hedef {pozisyon.get('hedef', 0):.2f} ₺\n"
                f"Giriş {giris:.2f} ₺ · {kar:+.1f}%")
    if tur == "stop_yakin":
        return (f"⚠️ <b>{sem} stopa yaklaştı</b>\n"
                f"Şu an {fiyat:.2f} ₺ · stop {pozisyon.get('stop', 0):.2f} ₺ "
                f"({(fiyat / float(pozisyon['stop']) - 1) * 100:+.1f}%)")
    return ""


# Telegram menüsüne kaydedilen komutlar. Tek kaynak: hem menü hem
# yardım metni buradan üretilir, ikisi ayrışamaz.
KOMUTLAR = [
    ("durum",  "Günün özeti"),
    ("tarama", "Bugünün sinyalleri (stop/hedef ile)"),
    ("hisse",  "Tek hisse analizi — /hisse THYAO"),
    ("karne",  "Sistemin canlı sicili"),
    ("ders",   "Günün dersi"),
    ("aldim",  "Alım kaydet — /aldim THYAO 302 3"),
    ("sattim", "Satım kaydet — /sattim THYAO 315"),
    ("pozisyon", "Açık pozisyonlar ve anlık kâr/zarar"),
    ("defter", "Kendi karar karnen"),
    ("izle",   "Stop izle — /izle THYAO 250 300"),
    ("liste",  "İzlenen pozisyonlar"),
    ("birak",  "İzlemeyi bırak — /birak THYAO"),
    ("saglik", "Sunucu ve günlük iş durumu"),
    ("yardim", "Komut listesi"),
]


def yardim() -> str:
    s = ["🤖 <b>Midas botu</b>", ""]
    for k, a in KOMUTLAR:
        s.append(f"<b>/{k}</b> — {a}")
    s += ["", "Hisse kodunu tek başına da yazabilirsin: <code>THYAO</code>",
          "", "<i>Bot emir göndermez, yalnızca haber verir.</i>"]
    return "\n".join(s)
