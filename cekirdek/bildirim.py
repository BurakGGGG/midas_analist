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
    """Günlük işin sonucu — akşam cebe düşen mesaj."""
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
            satir = (f"   <b>{kacis(x['sembol'])}</b> "
                     f"{kacis(x.get('sinyaller', []) and x['sinyaller'][0] or '')} "
                     f"· skor {x.get('skor', 0):.0f} · {x.get('fiyat', 0):.2f} ₺")
            if x.get("vade"):
                satir += f"\n      tipik tutma: {kacis(x['vade'])}"
            s.append(satir)
    elif karantinali:
        # "Sinyal yok" ile "sinyal var ama önerilmiyor" farklı şeyler.
        # İkincisini gizlemek, kullanıcıyı bilgisiz bırakır.
        s.append(f"⏸ <b>Önerilen sinyal yok</b> — {len(karantinali)} sinyal "
                 f"karantinadaki stratejilerden geldi.")
    else:
        s.append("😴 <b>Bugün sinyal yok.</b> Nakitte beklemek de bir pozisyondur.")

    # ── yaklaşanlar
    # "Sinyal yok" bir sonuç, ama tam bir cevap değil. Tek koşulu eksik
    # hisseleri görmek, kullanıcıyı sinyal gelmeden hazırlıklı kılıyor —
    # ve sinyal geldiğinde hisse yabancı gelmiyor.
    yaklasanlar = ozet.get("yaklasanlar") or []
    if yaklasanlar:
        s.append("")
        s.append(f"👀 <b>{len(yaklasanlar)} hisse sinyale yakın</b>")
        for x in yaklasanlar[:4]:
            s.append(f"   <b>{kacis(x['sembol'])}</b> "
                     f"({kacis(x['strateji'])} {x['karsilanan']}/{x['toplam']}) "
                     f"· {kacis(x['mesaj'])}")
        s.append("   <i>Bunlar sinyal DEĞİL — izleme listesi.</i>")

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


def sabah_hatirlatici(plan: dict) -> str:
    """09:45 mesajı — dün akşamki sinyaller, emir rakamlarıyla.

    Akşamki özetten farkı ve varlık sebebi: orada sembol, sinyal ve fiyat
    var; burada ADET, STOP ve HEDEF var. Emri girerken lazım olanlar
    bunlar ve sabah kimse onları söylemiyordu.

    Tavan satırı süs değil: backtest, ertesi gün önceki kapanışın %19,5
    üstünde AÇAN hisseyi alınamaz sayıyor. Gerçekte de alamazsın, tavanda
    satıcı yoktur. O kuralı burada söylemezsek sicil ile gerçek ayrışır.
    """
    emirler = plan.get("emirler") or []
    if not emirler:
        return ""

    s = [f"🔔 <b>Bugün açılışta — {len(emirler)} emir</b>"]
    rejim = plan.get("rejim")
    if rejim:
        s.append(f"   Rejim: {kacis(rejim)}")
    s.append("")

    for e in emirler:
        sinyal = (e.get("sinyaller") or [""])[0]
        s.append(f"<b>{kacis(e['sembol'])}</b> · {kacis(sinyal)} "
                 f"· skor {e.get('skor', 0):.0f}")
        s.append(f"   {e.get('adet', 0)} adet · ≈{e.get('fiyat', 0):.2f} ₺ "
                 f"· maliyet {e.get('maliyet', 0):.0f} ₺")
        s.append(f"   stop <b>{e.get('stop', 0):.2f}</b> · "
                 f"hedef <b>{e.get('hedef', 0):.2f}</b> · "
                 f"risk {e.get('risk_tl', 0):.0f} ₺")
        # Emri verirken tutma süresini bilmek, çıkışı fiyata değil plana
        # bağlar. Sonradan sorulduğunda cevap artık kâr/zarara bakıyor.
        if e.get("vade"):
            s.append(f"   tipik tutma: {kacis(e['vade'])}")
        tavan = e.get("tavan_fiyat") or 0
        if tavan:
            s.append(f"   {tavan:.2f} ₺ üstünde açarsa bu emri GEÇ (tavan)")
        s.append("")

    s.append("<i>Rakamlar dünkü kapanışa göre. Boşluklu açılışta giriş "
             "fiyatı değişir; adet ve stop da onunla kayar.</i>")
    return "\n".join(s)


# ── push karşılıkları ──────────────────────────────────────────────────────
#
# Telegram mesajları uzun ve HTML'li; push bildirimi kilit ekranında iki
# satır gösteriyor ve etiket kaldırmıyor. Aynı metni ikisine de vermek,
# birinde etiket kalabalığı diğerinde yarım cümle demekti. Bu yüzden her
# haberin iki biçimi var ve ikisi de burada — tek içerik katmanı.


def sabah_push(plan: dict) -> tuple[str, str]:
    """(başlık, gövde) — 09:45 bildirimi."""
    emirler = plan.get("emirler") or []
    if not emirler:
        return "", ""
    n = len(emirler)
    baslik = f"Bugün açılışta {n} emir"
    if n == 1:
        e = emirler[0]
        govde = (f"{e['sembol']} · {e.get('adet', 0)} adet · "
                 f"stop {e.get('stop', 0):.2f} · hedef {e.get('hedef', 0):.2f}")
    else:
        govde = " · ".join(f"{e['sembol']} {e.get('adet', 0)} adet"
                           for e in emirler[:3])
        if n > 3:
            govde += f" · +{n - 3} tane daha"
    return baslik, govde


def gunluk_push(ozet: dict) -> tuple[str, str]:
    """(başlık, gövde) — akşam bildirimi."""
    if not ozet or ozet.get("hata"):
        return "Midas", "Günlük iş çalıştı ama özet çıkarılamadı."
    sinyaller = ozet.get("sinyal_veren") or []
    onerilen = [x for x in sinyaller if x.get("onerilir", x.get("alinabilir"))]
    endeks = ozet.get("endeks_degisim")
    bas = f"Midas · XU100 {_yuzde(endeks)}" if endeks is not None else "Midas"
    if onerilen:
        adlar = ", ".join(x["sembol"] for x in onerilen[:3])
        govde = f"{len(onerilen)} sinyal: {adlar}"
        if len(onerilen) > 3:
            govde += f" +{len(onerilen) - 3}"
        govde += " — yarın açılışta"
    else:
        yak = ozet.get("yaklasanlar") or []
        if yak:
            adlar = ", ".join(x["sembol"] for x in yak[:3])
            govde = f"Sinyal yok. Sinyale yakın {len(yak)}: {adlar}"
        else:
            govde = "Bugün önerilen sinyal yok. Nakitte beklemek de bir pozisyon."
    return bas, govde


def stop_push(pozisyon: dict, fiyat: float, tur: str) -> tuple[str, str]:
    """(başlık, gövde) — gün içi stop/hedef uyarısı.

    Bu üçü gerçek para kaybettiren an; push'ta da kısa ve net olmalı."""
    sem = pozisyon.get("sembol", "?")
    if tur == "stop_gecti":
        return (f"🛑 {sem} stop altında",
                f"Şu an {fiyat:.2f} ₺ · stop {pozisyon.get('stop', 0):.2f} ₺")
    if tur == "hedef_gecti":
        return (f"🎯 {sem} hedefe ulaştı",
                f"Şu an {fiyat:.2f} ₺ · hedef {pozisyon.get('hedef', 0):.2f} ₺")
    if tur == "stop_yakin":
        return (f"⚠️ {sem} stopa yaklaştı",
                f"Şu an {fiyat:.2f} ₺ · stop {pozisyon.get('stop', 0):.2f} ₺")
    return "", ""


def stop_uyarisi(pozisyon: dict, fiyat: float, tur: str) -> str:
    """Stop ya da hedef seviyesine yaklaşma/geçme uyarısı.

    Bu mesajın var olma sebebi tek: günlük iş akşam çalışıyor. Stop
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
