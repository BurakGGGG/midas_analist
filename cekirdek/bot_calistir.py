"""`python -m cekirdek.bot_calistir` — Telegram botunun periyodik turu.

SÜREKLİ ÇALIŞAN SÜREÇ YOK. Bu betik zamanlayıcıdan 5 dakikada bir
çağrılır: gelen komutları işler, izlenen pozisyonları kontrol eder, çıkar.

Neden daemon değil: tek kullanıcılı bir sistemde sürekli açık bir süreç,
izlenmesi ve yeniden başlatılması gereken fazladan bir hareketli parça
demek. Periyodik tur, systemd'nin zaten yaptığı işi kullanıyor ve çökerse
bir sonraki turda kendiliğinden toparlanıyor.
"""
from __future__ import annotations

import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")


def _fiyat_getir(sembol: str) -> float | None:
    from . import veri
    # onbellek_saat=0.15 (~9 dk): 5 dakikalık turda her sembol için yeniden
    # indirmek hem yavaş hem gereksiz; BIST verisi zaten ~15 dk gecikmeli.
    df = veri.fiyat_cek(f"{sembol}.IS", gun=10, onbellek_saat=0.15)
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])



def _gunun_sinyalleri() -> str:
    """Son günlük işin ürettiği sinyaller — stop ve hedefle birlikte.

    CANLI TARAMA YAPMAZ: tarama 100 hisse indirmek demek, bir sohbet
    komutu için kabul edilemez bir gecikme. Ambardaki son iş sonucu
    okunur; zaten kararlar kapanış verisiyle veriliyor.
    """
    from . import ambar, ogrenme
    ambar.kur()
    with ambar.baglan() as con:
        gun = con.execute("SELECT MAX(tarih) t FROM sinyal").fetchone()["t"]
        if not gun:
            return "Henüz kayıtlı sinyal yok."
        satirlar = [dict(r) for r in con.execute("""
            SELECT sembol, strateji, skor, fiyat, stop, hedef, alinabilir
            FROM sinyal WHERE tarih = ? ORDER BY skor DESC""", (gun,))]
    if not satirlar:
        return f"{gun} için sinyal yok."

    try:
        siniflar = ogrenme.strateji_siniflari()
    except Exception:
        siniflar = {}
    kapali = {k for k, v in siniflar.items() if not v.get("onerilir", True)}

    onerilen = [r for r in satirlar if r["strateji"] not in kapali]
    diger = [r for r in satirlar if r["strateji"] in kapali]

    s = [f"🎯 <b>Sinyaller · {gun}</b>"]

    def satir(r, isaret=""):
        return (f"\n<b>{r['sembol']}</b> {isaret}\n"
                f"   {r['strateji']} · skor {r['skor']:.0f} · "
                f"{r['fiyat']:.2f} ₺\n"
                f"   stop {r['stop']:.2f} · hedef {r['hedef']:.2f}"
                + ("" if r["alinabilir"] else "  <i>(sermaye yetmiyor)</i>"))

    if onerilen:
        for r in onerilen[:6]:
            s.append(satir(r))
    else:
        s.append("\n<i>Önerilen sinyal yok.</i>")

    if diger:
        s.append(f"\n⚠️ <b>Karantinadaki stratejilerden {len(diger)} sinyal</b> "
                 f"(gösteriliyor, önerilmiyor):")
        for r in diger[:4]:
            s.append(satir(r, "⚠"))
        s.append("\n<i>Bu stratejilerin canlı sicili beklenen aralığın "
                 "altında. Ayrıntı: /karne</i>")
    return "".join(s) if len(s) == 1 else s[0] + "".join(s[1:])


def _hisse_ozeti(kod: str) -> str:
    """Tek hisse — canlı. Birkaç saniye sürer, kabul edilebilir."""
    from . import tarayici, evren
    kod = kod.upper().replace(".IS", "").strip()
    try:
        d = tarayici.tek_hisse(f"{kod}.IS")
    except Exception as e:
        return f"<b>{kod}</b> analiz edilemedi: {str(e)[:80]}"
    if not d:
        return f"<b>{kod}</b> için veri bulunamadı — kod doğru mu?"

    r = d["skor"]
    sev = d.get("seviyeler") or {}
    uygun, sebep = d.get("filtre", (True, ""))
    fiyat = r.get("fiyat") or 0
    sma200 = sev.get("SMA200")

    s = [f"📈 <b>{d['sembol']}</b> · {fiyat:.2f} ₺",
         f"Skor {r.get('skor', 0):.0f}/100 · RSI {r.get('rsi', 0):.0f} · "
         f"ADX {r.get('adx', 0):.0f}"]

    if sma200:
        yon = "ÜSTÜNDE ✅" if fiyat > sma200 else "ALTINDA ❌"
        s.append(f"SMA200 {sma200:.2f} — fiyat {yon}")

    zirve, dip = sev.get("52h_zirve"), sev.get("52h_dip")
    if zirve and dip:
        s.append(f"52 hafta: {dip:.2f} — {zirve:.2f}")

    if not uygun:
        s.append(f"\n⛔️ <b>Filtreyi geçmiyor:</b> {sebep}")
    elif r.get("sinyaller"):
        poz = d.get("pozisyon")
        s.append(f"\n🎯 <b>Sinyal: {', '.join(r['sinyaller'])}</b>")
        if poz and getattr(poz, "uygulanabilir", False):
            s.append(f"   {poz.adet} adet · {poz.maliyet:.2f} ₺\n"
                     f"   stop {poz.stop:.2f} · hedef {poz.hedef:.2f}")
    else:
        s.append("\n<i>Şu an giriş sinyali yok.</i>")

    s.append("\n<i>Bu bir tavsiye değil — emri sen verirsin.</i>")
    return "\n".join(s)


def _karne_ozeti() -> str:
    from . import ambar, ogrenme
    ambar.kur()
    s = ["📋 <b>Sistemin sicili</b>", "<i>backtest değil, canlı sonuçlar</i>"]
    try:
        k = ogrenme.olcum_kapsami()
        s.append(f"\nKapsam: {k.get('ilk', '?')} → {k.get('son', '?')} · "
                 f"{k.get('sinyal', 0)} sinyal")
    except Exception:
        pass
    try:
        for x in ogrenme.kayma_analizi():
            if not x.get("yeterli_mi"):
                s.append(f"\n<b>{x['strateji']}</b>: hüküm verilemez")
                continue
            a = x.get("aralik") or {}
            isaret = "⚠️" if "KÖTÜ" in x["durum"] else "✅"
            s.append(f"\n{isaret} <b>{x['strateji']}</b> "
                     f"%{x['canli']['kazanma_orani']} kazanma\n"
                     f"   beklenen %{a.get('alt')}-%{a.get('ust')} "
                     f"({a.get('ay')} ay)")
    except Exception as e:
        s.append(f"\nkarne okunamadı: {str(e)[:80]}")
    s.append("\n<i>Örneklem sinyal sayısı değil AY sayısıdır — "
             "kısa pencerede oran çok savrulur.</i>")
    return "\n".join(s)


def _gunun_dersi() -> str:
    from . import ambar, egitmen, izleme, ogrenme
    ambar.kur()
    ozet = ambar.ozet_oku() or {}
    try:
        siniflar = ogrenme.strateji_siniflari()
    except Exception:
        siniflar = {}
    sinyaller = ozet.get("sinyal_veren") or []
    onerilen = sum(1 for x in sinyaller
                   if x.get("onerilir", x.get("alinabilir", False)))
    durum = egitmen.gunun_durumu(
        tarama={"strateji_durumlari": siniflar, "onerilen": onerilen},
        ozet=ozet, portfoy_adet=len(izleme.liste()))
    d = egitmen.baglamsal_ders(durum)
    if not d:
        return "Bugün için ders bulunamadı."
    return (f"🎓 <b>{d['baslik']}</b>  <i>({d['sure']} dk)</i>\n\n"
            f"{d['neden']}\n\n"
            f"<i>Tam metni uygulamada: Daha → Eğitmen → {d['kod']}</i>")



def _alim_komutu(parca: list[str]) -> str:
    """/aldim KOD FİYAT [ADET] — karar günlüğüne yazar.

    Alım kaydedilince stop izlemesi KENDİLİĞİNDEN başlar. Ayrıca /izle
    yazmak gerekseydi çoğu zaman unutulurdu — ve tam da unutulan
    pozisyonlar zarar ettirir.
    """
    from . import defter, izleme
    if len(parca) < 3:
        return ("Kullanım: <code>/aldim KOD FİYAT [ADET]</code>\n"
                "örnek: <code>/aldim THYAO 302 3</code>\n\n"
                "<i>Varsayılan kağıt üzerinedir. Gerçek parayla aldıysan "
                "sonuna <code>gercek</code> ekle.</i>")
    try:
        sembol = parca[1].upper().replace(".IS", "")
        fiyat = float(parca[2].replace(",", "."))
        adet = int(parca[3]) if len(parca) > 3 and parca[3].isdigit() else 1
    except ValueError:
        return "Sayılar okunamadı. Örnek: <code>/aldim THYAO 302 3</code>"

    kagit = "gercek" not in [x.lower() for x in parca]

    # Sistemin o hisse için önerdiği stop/hedef varsa onları kullan.
    stop = hedef = 0.0
    strateji_notu = ""
    try:
        from . import ambar
        from .defter import SINYAL_TAZELIK_GUN
        from datetime import date, timedelta
        ambar.kur()
        # Taze sinyal penceresi: eski bir sinyalin stop seviyesi bugünün
        # fiyatına göre anlamsızdır ve yanlış yere stop kurdurur.
        en_eski = (date.today() - timedelta(days=SINYAL_TAZELIK_GUN)).isoformat()
        with ambar.baglan() as con:
            r = con.execute("""
                SELECT strateji, stop, hedef, skor FROM sinyal
                WHERE sembol = ? AND tarih >= ?
                ORDER BY tarih DESC, skor DESC LIMIT 1""",
                (sembol, en_eski)).fetchone()
        if r:
            stop, hedef = float(r["stop"] or 0), float(r["hedef"] or 0)
            strateji_notu = f"\nSistem sinyali: {r['strateji']} · skor {r['skor']:.0f}"
    except Exception:
        pass

    k = defter.alim(sembol, fiyat, adet, kagit=kagit, stop=stop, hedef=hedef)

    if stop:
        izleme.ekle(sembol, stop, hedef, fiyat)

    s = [f"📝 <b>Kaydedildi</b> — {'kağıt' if kagit else '💰 GERÇEK PARA'}",
         f"<b>{sembol}</b> {adet} adet · {fiyat:.2f} ₺ "
         f"(toplam {adet * fiyat:.2f} ₺)"]
    if strateji_notu:
        s.append(strateji_notu.strip())
        if k.get("onerilir") == 0:
            # Karantinadaki stratejiden alım. Engellenmiyor — karar
            # kullanıcının. Ama sessiz kalmak da doğru olmaz.
            s.append("⚠️ <i>Bu strateji karantinada: canlı sicili beklenen "
                     "aralığın altında. Kararı sen verdin, günlüğe böyle "
                     "kaydedildi.</i>")
    else:
        s.append("<i>Bu hisse için sistem sinyali yoktu — kendi fikrin "
                 "olarak kaydedildi.</i>")
    if stop:
        s.append(f"\n🔔 Stop izlemesi başladı: {stop:.2f} ₺"
                 + (f" · hedef {hedef:.2f} ₺" if hedef else ""))
    else:
        s.append("\n<i>Stop bilgisi yok — <code>/izle "
                 f"{sembol} STOP</code> ile ekleyebilirsin.</i>")
    return "\n".join(s)


def _satim_komutu(parca: list[str]) -> str:
    from . import defter, izleme
    if len(parca) < 3:
        return ("Kullanım: <code>/sattim KOD FİYAT [ADET]</code>\n"
                "örnek: <code>/sattim THYAO 315</code>  "
                "<i>(adet yazmazsan tamamı)</i>")
    try:
        sembol = parca[1].upper().replace(".IS", "")
        fiyat = float(parca[2].replace(",", "."))
        adet = int(parca[3]) if len(parca) > 3 and parca[3].isdigit() else 0
    except ValueError:
        return "Sayılar okunamadı. Örnek: <code>/sattim THYAO 315</code>"

    k = defter.satim(sembol, fiyat, adet)
    if k.get("hata"):
        return f"⚠️ {k['hata']}"

    getiri = k.get("getiri", 0)
    isaret = "🟢" if getiri > 0 else "🔴"
    s = [f"{isaret} <b>{sembol} satıldı</b>",
         f"{k['adet']} adet · giriş {k['giris']:.2f} → çıkış {fiyat:.2f} ₺",
         f"<b>{getiri:+.2f}%</b>"]
    if k.get("stopun_altinda_satildi"):
        s.append("\n⚠️ <i>Stop seviyesinin altında satıldı — stopa "
                 "zamanında uyulmamış. Disiplin ölçümüne böyle geçti.</i>")
    if not defter.acik_pozisyon(sembol):
        izleme.sil(sembol)
        s.append("\n<i>Stop izlemesi kapatıldı.</i>")
    return "\n".join(s)


def _pozisyonlar() -> str:
    from . import defter
    p = defter.acik_pozisyonlar()
    if not p:
        return ("Açık pozisyon yok.\n"
                "<code>/aldim THYAO 302</code> ile kaydedebilirsin.")
    s = ["💼 <b>Açık pozisyonlar</b>"]
    toplam_m = toplam_d = 0.0
    for x in p:
        fiyat = _fiyat_getir(x["sembol"]) or x["giris"]
        getiri = (fiyat / x["giris"] - 1) * 100 if x["giris"] else 0
        isaret = "🟢" if getiri >= 0 else "🔴"
        etiket = "" if x.get("kagit", 1) else " 💰"
        s.append(f"\n{isaret} <b>{x['sembol']}</b>{etiket} {x['adet']} adet\n"
                 f"   {x['giris']:.2f} → {fiyat:.2f} ₺  <b>{getiri:+.1f}%</b>"
                 + (f"\n   stop {x['stop']:.2f}" if x.get("stop") else ""))
        toplam_m += x["maliyet"]
        toplam_d += fiyat * x["adet"]
    if toplam_m:
        s.append(f"\n<b>Toplam:</b> {toplam_m:.2f} → {toplam_d:.2f} ₺  "
                 f"({(toplam_d / toplam_m - 1) * 100:+.1f}%)")
    return "".join(s) if len(s) == 1 else s[0] + "".join(s[1:])


def _defter_karnesi() -> str:
    from . import defter
    d = defter.karne()
    if d.get("not"):
        return ("📓 <b>Karar defterin</b>\n\n" + d["not"] + "\n\n"
                "<i>Sistem kendi sinyallerini ölçüyor; bu defter SENİN "
                "kararlarını ölçer. Aradaki fark, seçim becerindir.</i>")

    s = ["📓 <b>Karar defterin</b>",
         f"\n{d['alim_sayisi']} alım · {d['kapanan']} kapandı · "
         f"{d['acik']} açık"]

    if "kazanma_orani" in d:
        s.append(f"\n<b>Kazanma {d['kazanma_orani']}%</b> · "
                 f"ortalama {d['ortalama_getiri']:+.2f}%")
        s.append(f"En iyi {d['en_iyi']:+.1f}% · en kötü {d['en_kotu']:+.1f}%")

    s.append(f"\n<b>Sistemi takip:</b> %{d.get('sistem_takip_orani', 0)} "
             f"({d.get('sinyalli_alim', 0)}/{d['alim_sayisi']} alım sinyalliydi)")
    if d.get("karantinali_alim"):
        s.append(f"⚠️ {d['karantinali_alim']} alım karantinadaki stratejiden")

    for ad, baslik in (("sinyalli", "Sinyalli alımlar"),
                       ("kendi_fikrin", "Kendi fikrin")):
        if ad in d:
            x = d[ad]
            s.append(f"\n<b>{baslik}:</b> {x['n']} işlem · "
                     f"%{x['kazanma']} kazanma · {x['ortalama']:+.2f}%")

    sd = d.get("stop_disiplini")
    if sd:
        s.append(f"\n<b>Stop disiplini:</b> {sd['not']}")

    if d.get("uyari"):
        s.append(f"\n<i>{d['uyari']}</i>")
    return "\n".join(s)


def _komut_isle(metin: str) -> str:
    from . import bildirim, izleme

    parca = metin.split()
    komut = parca[0].lower().lstrip("/").split("@")[0]

    if komut in ("start", "yardim", "help"):
        return bildirim.yardim()

    if komut == "liste":
        p = izleme.liste()
        if not p:
            return ("İzlenen pozisyon yok.\n"
                    "<code>/izle THYAO 250 300</code> ile ekleyebilirsin.")
        s = ["👁 <b>İzlenen pozisyonlar</b>"]
        for x in p:
            s.append(f"   <b>{x['sembol']}</b> · stop {x['stop']:.2f}"
                     + (f" · hedef {x['hedef']:.2f}" if x.get("hedef") else ""))
        return "\n".join(s)

    if komut == "izle":
        if len(parca) < 3:
            return ("Kullanım: <code>/izle KOD STOP [HEDEF] [GİRİŞ]</code>\n"
                    "örnek: <code>/izle THYAO 250 300</code>")
        try:
            sembol = parca[1]
            stop = float(parca[2].replace(",", "."))
            hedef = float(parca[3].replace(",", ".")) if len(parca) > 3 else 0.0
            giris = float(parca[4].replace(",", ".")) if len(parca) > 4 else 0.0
        except ValueError:
            return "Sayılar okunamadı. Örnek: <code>/izle THYAO 250 300</code>"

        fiyat = _fiyat_getir(sembol)
        if fiyat is None:
            return (f"<b>{sembol.upper()}</b> için fiyat verisi bulunamadı — "
                    f"kod doğru mu?")
        k = izleme.ekle(sembol, stop, hedef, giris or fiyat)
        return (f"✅ <b>{k['sembol']}</b> izlemeye alındı\n"
                f"Şu an {fiyat:.2f} ₺ · stop {k['stop']:.2f} ₺"
                + (f" · hedef {k['hedef']:.2f} ₺" if k["hedef"] else ""))

    if komut == "birak":
        if len(parca) < 2:
            return "Kullanım: <code>/birak THYAO</code>"
        return ("✅ Bırakıldı." if izleme.sil(parca[1])
                else "Bu kodda izlenen pozisyon yok.")

    if komut == "durum":
        from . import ambar, ogrenme, bildirim as b
        ambar.kur()
        try:
            siniflar = ogrenme.strateji_siniflari()
        except Exception:
            siniflar = {}
        return b.gunluk_ozet(ambar.ozet_oku() or {}, siniflar)

    if komut in ("tarama", "sinyal", "sinyaller"):
        return _gunun_sinyalleri()

    if komut == "hisse":
        if len(parca) < 2:
            return "Kullanım: <code>/hisse THYAO</code>"
        return _hisse_ozeti(parca[1])

    if komut in ("karne", "sicil"):
        return _karne_ozeti()

    if komut in ("saglik", "sağlık"):
        from . import saglik
        d = saglik.ozet()
        g, disk = d["gunluk_is"], d["disk"]
        s = ["🩺 <b>Sistem sağlığı</b>"]
        s.append(f"\nGünlük iş bugün: "
                 + ("✅ çalıştı" if g["calisti"]
                    else ("⏳ henüz çalışmadı" if g["deneme"] == 0
                          else f"🔴 {g['hata_sayisi']} hata")))
        if g.get("son_hata"):
            s.append(f"<code>{telegram.kacis(g['son_hata'][:200])}</code>")
        s.append(f"Disk: %{disk.get('kullanilan_yuzde', '?')} dolu · "
                 f"{disk.get('bos_gb', '?')} GB boş"
                 + ("  ⚠️" if disk.get("uyari") else ""))
        s.append(f"Yedek: {d['yedek_sayisi']} kopya"
                 + (f" · son {d['son_yedek']}" if d["son_yedek"] else ""))
        return "\n".join(s)

    if komut == "ders":
        return _gunun_dersi()

    if komut in ("aldim", "aldım", "al"):
        return _alim_komutu(parca)

    if komut in ("sattim", "sattım", "sat"):
        return _satim_komutu(parca)

    if komut in ("pozisyon", "pozisyonlar", "portfoy", "portföy"):
        return _pozisyonlar()

    if komut in ("defter", "kararlarim"):
        return _defter_karnesi()

    # Komut değil de düz bir hisse kodu yazılmışsa onu analiz et:
    # "/hisse THYAO" yerine sadece "THYAO" yazmak daha doğal.
    ham = metin.strip().upper()
    if not metin.startswith("/") and ham.isalpha() and 4 <= len(ham) <= 5:
        return _hisse_ozeti(ham)

    return ("Anlamadım. <b>/yardim</b> yazarak komutları görebilirsin.")


def main() -> int:
    from . import ortam  # noqa: F401  (.env yükler)
    from . import bildirim, haberci, izleme, telegram

    kanallar = haberci.acik_kanallar()
    if not any(kanallar.values()):
        # Hiçbir kanal yoksa yapacak iş yok. Yapılandırılmamış olmak HATA
        # DEĞİL: çıkış kodu 1 dönseydi timer her dakika başarısız birim
        # kaydı düşürür, journal kırmızıya boğulur ve gerçek bir arıza
        # çıktığında kimse fark etmezdi. "Yanlış alarm gerçek alarmı
        # değersizleştirir" ilkesi burada da geçerli.
        print("Hiçbir bildirim kanalı yapılandırılmamış — bot turu atlandı "
              "(.env: MIDAS_TELEGRAM_TOKEN / MIDAS_FCM_ANAHTAR)")
        return 0

    # ── 1) gelen komutlar — YALNIZCA Telegram'a özgü
    # Komut okumak iki yönlü bir kanal ister; push tek yönlüdür. Bu blok
    # eskiden tüm fonksiyonu kapıda tutuyordu: Telegram kurulu değilse
    # stop alarmı da çalışmıyordu. Artık yalnızca kendi bölümünü atlıyor,
    # çünkü stop uyarısı push ile de gidebilir.
    if kanallar["telegram"]:
        # 45 sn bekle: 1 dakikalık timer ile birleşince komut neredeyse
        # anında cevaplanır.
        mesajlar, en_son = telegram.komutlari_oku(izleme.son_id(), bekle=45)
        for m in mesajlar:
            try:
                telegram.gonder(_komut_isle(m["metin"]))
            except Exception as e:
                telegram.gonder(f"Komut işlenemedi: {str(e)[:120]}")
        if en_son != izleme.son_id():
            izleme.son_id(en_son)

    # ── 1b) NÖBET: günlük iş çalıştı mı?
    # Günde en fazla bir kez uyarır. İşaret dosyası izleme defterinde
    # tutulur — bot her dakika çalıştığı için, durum dosyaya yazılmazsa
    # aynı uyarı 60 kez giderdi ve kullanıcı botu susturur.
    try:
        from . import saglik
        uyari = saglik.nobet()
        if uyari:
            r = haberci.yolla(uyari, "Midas · günlük iş çalışmadı",
                              "Akşam işi bugün çalışmamış görünüyor.",
                              veri={"ekran": "saglik"})
            if r.get("telegram") or r["push"]["gonderildi"]:
                saglik.uyari_isaretle("gunluk_is")
    except Exception:
        pass   # nöbetçi çökerse bot durmasın

    # ── 2) pozisyon kontrolü (yalnızca seans saatlerinde)
    # Seans dışında fiyat değişmiyor; her 5 dakikada bir 100 hisse
    # sorgulamak boşuna trafik ve boşuna gecikme.
    simdi = datetime.now()
    seansta = (simdi.weekday() < 5 and 10 <= simdi.hour < 19)
    if seansta and izleme.liste():
        for poz, fiyat, tur in izleme.kontrol(_fiyat_getir):
            # Stop/hedef gün içinde geçilir ve gerçek para burada
            # kaybedilir; her açık kanala birden gitmeli.
            _bas, _gov = bildirim.stop_push(poz, fiyat, tur)
            haberci.yolla(bildirim.stop_uyarisi(poz, fiyat, tur), _bas, _gov,
                          veri={"ekran": "portfoy", "sembol": poz.get("sembol", "")})

    return 0


if __name__ == "__main__":
    sys.exit(main())
