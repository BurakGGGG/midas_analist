#!/usr/bin/env python3
"""
MİDAS ANALİST — BIST karar destek sistemi

Bu bir OTOMATİK ALIM-SATIM BOTU DEĞİLDİR. Midas'ın geliştirici API'si yok;
hiçbir yazılım senin adına Midas'ta emir veremez. Bu araç ne yapar:

  · her gün BIST'i tarar, kurallara uyan hisseleri sıralar
  · sermayene göre KAÇ ADET alınacağını, stop ve hedefi hesaplar
  · alım yaptığında pozisyonu takip eder, çıkış zamanını söyler
  · her stratejiyi geçmiş veride dürüstçe test eder

Emri Midas uygulamasında sen girersin. Karar senin, disiplin bunun.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))

from cekirdek import ortam  # noqa: F401  (.env yükler; diğer içe aktarımlardan önce)
from cekirdek import rapor, veri, gostergeler, evren, portfoy, tarayici   # noqa: E402
from cekirdek.risk import RiskAyarlari                                    # noqa: E402
from cekirdek.strateji import Filtreler, STRATEJILER                      # noqa: E402


def ayarlari_oku() -> dict:
    yol = KOK / "ayarlar.yaml"
    varsayilan = {
        "sermaye": 1000.0,
        "risk": {}, "filtre": {}, "backtest": {"kayma_bp": 15, "gun": 1200},
        "evren": "bist100", "varsayilan_strateji": "kirilim",
    }
    if not yol.exists():
        return varsayilan
    try:
        import yaml
        a = yaml.safe_load(yol.read_text(encoding="utf-8")) or {}
        for k, v in varsayilan.items():
            a.setdefault(k, v)
        return a
    except Exception as e:
        print(f"ayarlar.yaml okunamadı ({e}), varsayılanlar kullanılıyor")
        return varsayilan


def risk_kur(a: dict, sermaye: float | None = None) -> RiskAyarlari:
    r = a.get("risk", {}) or {}
    return RiskAyarlari(
        sermaye=float(sermaye if sermaye is not None else a.get("sermaye", 1000)),
        islem_basi_risk_yuzde=float(r.get("islem_basi_risk_yuzde", 1.5)),
        azami_pozisyon_yuzde=float(r.get("azami_pozisyon_yuzde", 35)),
        azami_es_zamanli=int(r.get("azami_es_zamanli", 4)),
        atr_stop_kat=float(r.get("atr_stop_kat", 2.5)),
        atr_hedef_kat=float(r.get("atr_hedef_kat", 5.0)),
        gunluk_kayip_limiti_yuzde=float(r.get("gunluk_kayip_limiti_yuzde", 4)),
    )


def filtre_kur(a: dict) -> Filtreler:
    f = a.get("filtre", {}) or {}
    return Filtreler(
        asgari_tl_hacim=float(f.get("asgari_tl_hacim", 20_000_000)),
        azami_atr_yuzde=float(f.get("azami_atr_yuzde", 7.0)),
        asgari_atr_yuzde=float(f.get("asgari_atr_yuzde", 0.8)),
        tavan_esigi=float(f.get("tavan_esigi", 9.0)),
        asgari_veri=int(f.get("asgari_veri", 220)),
    )


# ─────────────────────────────────────────────────────────────── komutlar

def komut_tara(args, a):
    ra, fl = risk_kur(a, args.sermaye), filtre_kur(a)
    gecen, elenen = tarayici.tara(
        evren_adi=args.evren or a.get("evren", "bist100"),
        risk_ayar=ra, filtre=fl, gun=500,
        onbellek_saat=0 if args.taze else 6.0,
        sadece_sinyalli=args.sinyal,
    )
    rapor.tarama_raporu(gecen, elenen, ra, adet=args.adet, elenen_goster=args.elenen)


def komut_analiz(args, a):
    ra = risk_kur(a, args.sermaye)
    r = tarayici.tek_hisse(args.hisse, ra)
    if r is None:
        print(f"{args.hisse} için veri alınamadı.")
        return
    s, sv, p = r["skor"], r["seviyeler"], r["pozisyon"]
    rapor.baslik(f"{r['sembol']} · {s['fiyat']:.2f} TL · {rapor.yuzde_renk(s['gunluk_degisim'])}")

    rapor.alt_baslik("SKOR")
    print(f"  Toplam {rapor.skor_renk(s['skor'])}/100   "
          f"trend {s['trend']:.1f}/30 · momentum {s['momentum']:.1f}/25 · "
          f"zamanlama {s['zamanlama']:.1f}/25 · kalite {s['kalite']:.1f}/20")
    print(f"  Filtre: {'✓ ' + r['filtre'][1] if r['filtre'][0] else '✗ ' + r['filtre'][1]}")
    print(f"  Aktif sinyal: {', '.join(s['sinyaller']) if s['sinyaller'] else 'yok'}")

    rapor.alt_baslik("GÖSTERGELER")
    print(f"  RSI(14) {s['rsi']:.1f} · ADX {s['adx']:.1f} · ATR %{s['atr_yuzde']:.2f} · "
          f"endekse göre 60g {s['gg60'] if s['gg60'] is not None else '—'} puan")
    print(f"  Günlük ort. hacim: {s['tl_hacim']/1e6:,.0f} milyon TL")

    rapor.alt_baslik("SEVİYELER")
    for ad, v in [("EMA20", sv["EMA20"]), ("EMA50", sv["EMA50"]), ("SMA200", sv["SMA200"]),
                  ("Bollinger alt", sv["BB_alt"]), ("Bollinger üst", sv["BB_ust"]),
                  ("20g zirve (kırılım)", sv["DON_ust"]),
                  ("52 hafta zirve", sv["52h_zirve"]), ("52 hafta dip", sv["52h_dip"])]:
        if v is None:
            continue
        fark = (s["fiyat"] / v - 1) * 100
        print(f"  {ad:<22} {v:9.2f}   fiyat bunun {rapor.yuzde_renk(fark, 1)} {'üstünde' if fark>0 else 'altında'}")

    rapor.alt_baslik(f"POZİSYON PLANI ({rapor.para(ra.sermaye)} TL sermaye ile)")
    if p.uygulanabilir:
        print(f"  {p.adet} adet × {p.giris:.2f} = {rapor.para(p.maliyet)} TL "
              f"(sermayenin %{p.sermaye_payi:.0f}'i)")
        print(f"  Stop  {p.stop:8.2f}  → buraya düşerse {rapor.para(p.risk_tl)} TL kayıp "
              f"(sermayenin %{p.risk_tl/ra.sermaye*100:.1f}'i)")
        print(f"  Hedef {p.hedef:8.2f}  → buraya çıkarsa "
              f"{rapor.para((p.hedef - p.giris) * p.adet)} TL kâr")
        if p.uyari:
            print(f"  {rapor.Y}⚠ {p.uyari}{rapor.R}")
    else:
        print(f"  {rapor.K}Alınamıyor: {p.uyari}{rapor.R}")


def komut_portfoy(args, a):
    rapor.portfoy_raporu(portfoy.kontrol(), risk_kur(a).sermaye)


def komut_al(args, a):
    ra = risk_kur(a, args.sermaye)
    stop, hedef = args.stop, args.hedef
    if stop is None or hedef is None:
        r = tarayici.tek_hisse(args.hisse, ra)
        if r is None:
            print("Veri alınamadı, stop ve hedefi elle ver: --stop X --hedef Y")
            return
        from cekirdek.risk import pozisyon_hesapla
        sinyal = r["skor"]["sinyaller"]
        st = STRATEJILER.get(sinyal[0]) if sinyal else None
        p = pozisyon_hesapla(args.hisse, args.fiyat, r["skor"]["atr"], ra,
                             stop_kat=st.atr_stop_kat if st else None,
                             hedef_kat=st.atr_hedef_kat if st else None)
        stop = stop if stop is not None else p.stop
        hedef = hedef if hedef is not None else p.hedef
    # Kayıttan ÖNCE davranışsal tarama — uyarıyı iş işten geçtikten sonra
    # göstermenin faydası yok.
    from cekirdek import psikoloji as ps, gostergeler as gs, tez as tz
    from dataclasses import asdict
    sem = args.hisse.upper()
    try:
        g = gs.gosterge_seti(veri.fiyat_cek(sem, gun=400))
        tezler = [t for t in tz.yukle() if t.sembol == sem and t.acik]
        acik = [{"sembol": p.sembol, "giris": p.giris, "maliyet": p.maliyet}
                for p in portfoy.yukle()]
        gecmis = [asdict(t) for t in tz.yukle() if not t.acik]
        uyarilar = ps.alim_oncesi(sem, args.fiyat, args.adet, ra.sermaye,
                                  g.iloc[-1], gecmis, acik, tez_var_mi=bool(tezler))
    except Exception:
        uyarilar = []

    kritik = [u for u in uyarilar if u.seviye == "dur"]
    if uyarilar:
        rapor.psikoloji_raporu(uyarilar)

    if kritik and not args.onayla:
        print(f"\n  {rapor.K}{rapor.B}{len(kritik)} kritik uyarı var — kayıt YAPILMADI.{rapor.R}")
        print(f"  Yukarıdaki soruları cevapladıysan ve yine de devam etmek istiyorsan:")
        print(f"    {rapor.B}python analist.py al {sem} {args.adet} {args.fiyat} --onayla{rapor.R}")
        print(f"  {rapor.G}Bu ek adım bilerek var: kritik uyarıya rağmen alım yapmak")
        print(f"  bir karar olmalı, refleks değil.{rapor.R}")
        return

    y = portfoy.ekle(args.hisse, args.adet, args.fiyat, stop, hedef,
                     a.get("varsayilan_strateji", "kirilim"))
    print(f"\n  ✓ Kaydedildi: {y.sembol} {y.adet} adet × {y.giris:.2f} = "
          f"{rapor.para(y.maliyet)} TL")
    print(f"    Stop {y.stop:.2f} · Hedef {y.hedef:.2f}")
    print(f"    {rapor.Y}Bu emri Midas'ta gerçekten girdiğinden emin ol - "
          f"burası sadece kayıt tutar.{rapor.R}")
    if not [t for t in tz.yukle() if t.sembol == sem and t.acik]:
        print(f"    {rapor.G}Tezini henüz yazmadın: python analist.py tez {sem}{rapor.R}")


def komut_sat(args, a):
    print(f"  {'✓ Pozisyon kaydı silindi: ' + args.hisse.upper() if portfoy.cikar(args.hisse) else '✗ Böyle bir kayıt yok: ' + args.hisse.upper()}")


def komut_backtest(args, a):
    from cekirdek import backtest
    ra, fl = risk_kur(a, args.sermaye), filtre_kur(a)
    gun = int(args.gun or a["backtest"].get("gun", 1200))
    kayma = float(args.kayma if args.kayma is not None else a["backtest"].get("kayma_bp", 15))

    sem = evren.evren_getir(args.evren or a.get("evren", "bist100"))
    rapor.baslik(f"BACKTEST · {len(sem)} hisse · {gun} gün · kayma {kayma:.0f}bp · "
                 f"sermaye {rapor.para(ra.sermaye)} TL")
    print(f"\n  Veri indiriliyor...")
    ham = veri.toplu_cek(sem, gun=gun)
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=gun)
    G = {s: gostergeler.gosterge_seti(d, endeks["Close"])
         for s, d in ham.items() if len(d) >= 250}
    print(f"  {len(G)} hisse hazır.")

    hedef = [args.strateji] if args.strateji else list(STRATEJILER)
    for ad in hedef:
        st = STRATEJILER.get(ad)
        if st is None:
            print(f"  Bilinmeyen strateji: {ad}")
            continue
        s = backtest.calistir(G, st, ra, fl, kayma_bp=kayma)
        rapor.backtest_raporu(s.metrikler(endeks["Close"]), f"{ad.upper()} — {st.aciklama}")

    print(f"\n  {rapor.G}Backtest geçmişi anlatır, geleceği garanti etmez. Geçmişte çalışan")
    print(f"  bir kural, piyasa rejimi değiştiğinde çalışmayı bırakabilir.{rapor.R}")


def komut_gerceklik(args, a):
    """Hedefin matematiği. Bu komut kimseyi mutlu etmez ama para kaybettirmez."""
    import numpy as np
    hedef = args.hedef_yuzde
    ra = risk_kur(a, args.sermaye)
    s = ra.sermaye

    rapor.baslik(f"GERÇEKLİK KONTROLÜ · günde %{hedef} hedefi · {rapor.para(s)} TL sermaye")
    rapor.alt_baslik("BİLEŞİK GETİRİNİN MATEMATİĞİ")
    print(f"  {'süre':<22} {'işlem günü':>11} {'sermaye':>34}")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    for etiket, g in [("1 hafta", 5), ("1 ay", 21), ("3 ay", 63), ("6 ay", 126),
                      ("1 yıl", 252), ("2 yıl", 504)]:
        v = s * (1 + hedef / 100) ** g
        print(f"  {etiket:<22} {g:>11} {rapor.para(v):>34} TL")

    yil_gerek = np.log(2e12 / s) / np.log(1 + hedef / 100) / 252
    print(f"\n  Bu tempoyla {rapor.para(s)} TL, Türkiye'nin en büyük şirketinin piyasa değerini")
    print(f"  ({rapor.B}~2 trilyon TL{rapor.R}) {rapor.B}{yil_gerek:.1f} yılda{rapor.R} geçer.")
    print(f"  Dünyada bunu başarmış tek bir kişi, fon ya da algoritma yok.")

    rapor.alt_baslik("GERÇEKTE NE OLUYOR")
    print(f"  Bu depodaki backtestler (BIST 100, 3.25 yıl, gerçekçi kayma ile):")
    print(f"    kırılım stratejisi   günlük ortalama  %+0.10   → hedefin ~1/50'si")
    print(f"    trend stratejisi     günlük ortalama  %+0.08   → hedefin ~1/64'ü")
    print(f"    XU100 al-tut         günlük ortalama  %+0.15")
    print(f"\n  Günde %{hedef} 'düşük' görünür çünkü küçük bir sayı. Bileşiklendiğinde")
    print(f"  dünyanın en iyi yatırımcısının {int((1+hedef/100)**252 / 1.2):,}x üstünde bir performans demek.")
    print(f"  Warren Buffett'ın 60 yıllık ortalaması yılda ~%20 — günde %0.07.")

    rapor.alt_baslik("BU SERMAYEYLE GERÇEKÇİ OLAN")
    for ad, oran in [("iyi bir sistematik strateji", 0.30), ("çok iyi bir yıl", 0.60),
                     ("XU100 al-tut (son 3 yıl)", 0.41)]:
        print(f"  {ad:<32} yılda %{oran*100:>5.0f}  →  {rapor.para(s*(1+oran))} TL "
              f"({rapor.para(s*oran)} TL kâr)")
    print(f"\n  {rapor.Y}1000 TL'de asıl kısıt strateji değil, SERMAYE.{rapor.R}")
    print(f"  BIST'te kesirli hisse yok: 400 TL'lik bir hisseden 1 adet zaten sermayenin %40'ı.")
    print(f"  Aynı anda 2-3 hisseye sıkışırsın; sonucu strateji değil, şans belirler.")
    print(f"\n  {rapor.G}Bu 1000 TL'nin gerçek işi para kazanmak değil, ÖĞRENMEK.")
    print(f"  Sistemi 3 ay bu parayla işlet, kayıt tut, sonra sermaye ekleyip ekleme kararını ver.{rapor.R}")




# ─────────────────────────────────────────────── temel analiz & değerleme

def komut_sirket(args, a):
    from cekirdek import temel_veri, temel, degerleme, sektor as sk
    sem = args.hisse.upper()
    print(f"» {sem} finansalları çekiliyor...")
    f = temel_veri.finansal_cek(sem, zorla=args.taze)
    if f is None:
        print(f"{sem} için finansal veri alınamadı.")
        return

    o = temel.oranlar(f)
    kalite = temel.kalite_skoru(f, o)
    bayrak = temel.kirmizi_bayraklar(f, o)
    c = degerleme.carpanlar(f)
    dcf = degerleme.ters_dcf(f)
    sbilgi = sk.sektor_bilgi(f.sektor)

    sektor_ort, hukum = None, None
    if not args.hizli:
        print(f"» sektör medyanı için emsaller çekiliyor (ilk seferde yavaş)...")
        harita = sk.sektor_haritasi()
        emsaller = [x for x, b in harita.items()
                    if b["sektor"] == f.sektor and x != sem][:25]
        if emsaller:
            fin = temel_veri.toplu_finansal(emsaller, sessiz=True)
            sektor_ort = degerleme.sektor_ortalamasi(fin)
            hukum = degerleme.deger_hukmu(f, c, sektor_ort)

    rapor.sirket_raporu(f, o, kalite, bayrak, c, dcf, sbilgi, sektor_ort, hukum)

    if args.ai:
        from cekirdek import ai
        ok, sebep = ai.kullanilabilir()
        if not ok:
            print(f"\n  {rapor.G}AI yorumu atlandı: {sebep}{rapor.R}")
        else:
            print(f"\n  {rapor.G}AI yorumu üretiliyor...{rapor.R}")
            metin = ai.finansal_ozet(sem,
                {k: (round(v.deger, 2) if v.var_mi and v.gecerli else None) for k, v in o.items()},
                bayrak,
                {k: (round(v.deger, 2) if v.var_mi and v.gecerli else None) for k, v in c.items()},
                f.sektor)
            if metin:
                rapor.alt_baslik("AI YORUMU")
                print("  " + metin.replace("\n", "\n  "))


def komut_makro(args, a):
    from cekirdek import makro
    print("» makro veriler çekiliyor...")
    m = makro.durum(onbellek_saat=0 if args.taze else 6.0)
    rapor.makro_raporu(m, makro.rejim(m))


def komut_sektor(args, a):
    from cekirdek import sektor as sk
    print("» sektör haritası kuruluyor...")
    r = sk.liderler_gecikenler()
    if "hata" in r:
        print(" ", r["hata"]); return
    rapor.sektor_raporu(r["tablo"], r["liderler"], r["gecikenler"], r["yorum"])


# ─────────────────────────────────────────────── tez & psikoloji

def komut_tez(args, a):
    from cekirdek import tez as tz
    sem = args.hisse.upper()
    ra = risk_kur(a, args.sermaye)

    mevcut = [t for t in tz.yukle() if t.sembol == sem and t.acik]
    if mevcut and not args.yeni:
        t = mevcut[0]
        rapor.baslik(f"{sem} TEZİ · {t.tarih} · giriş {t.fiyat:.2f}")
        for anahtar, soru in tz.SORULAR:
            cevap = getattr(t, anahtar, "") or f"{rapor.K}[BOŞ]{rapor.R}"
            print(f"\n  {rapor.B}{soru}{rapor.R}\n    {cevap}")
        k = [x for x in tz.kontrol(ra.sermaye) if x["tez"].sembol == sem]
        if k:
            x = k[0]
            rapor.alt_baslik("BUGÜNKÜ DURUM")
            print(f"  Fiyat {x['guncel_fiyat']:.2f} "
                  f"({rapor.yuzde_renk(x['degisim_yuzde'] or 0)}) · {x['gun']} iş günü")
            print(f"  {rapor.Y}Yanılma koşulun: {x['hatirlatma']}{rapor.R}")
            if x["bozulmalar"]:
                print(f"\n  {rapor.K}TEZDE BOZULMA:{rapor.R}")
                for b in x["bozulmalar"]:
                    print(f"    ▲ {b}")
            else:
                print(f"  {rapor.S}Tezde ölçülebilir bozulma yok.{rapor.R}")
            print(f"\n  {rapor.G}{x['soru']}{rapor.R}")
        if args.ai:
            from cekirdek import ai
            from dataclasses import asdict
            ok, sebep = ai.kullanilabilir()
            if ok:
                print(f"\n  {rapor.G}AI tezini eleştiriyor...{rapor.R}")
                m = ai.tez_elestir(asdict(t), t.anlik)
                if m:
                    rapor.alt_baslik("ŞEYTANIN AVUKATI")
                    print("  " + m.replace("\n", "\n  "))
            else:
                print(f"\n  {rapor.G}AI eleştirisi atlandı: {sebep}{rapor.R}")
        return

    # yeni tez — soruları sırayla sor
    rapor.baslik(f"{sem} İÇİN YENİ TEZ")
    print(f"\n  {rapor.G}Her soruyu cevapla. Boş bırakabilirsin ama eksik tez,")
    print(f"  düştüğünde neden tuttuğunu bilememek demektir.{rapor.R}")
    print(f"  {rapor.G}Çıkmak için Ctrl+C.{rapor.R}\n")
    cevaplar = {}
    try:
        for anahtar, soru in tz.SORULAR:
            print(f"  {rapor.B}{soru}{rapor.R}")
            cevaplar[anahtar] = input("    > ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  İptal edildi, tez kaydedilmedi.")
        return

    fiyat = args.fiyat
    if fiyat is None:
        r = tarayici.tek_hisse(sem, ra)
        fiyat = r["skor"]["fiyat"] if r else 0.0
    t = tz.olustur(sem, fiyat, cevaplar, adet=args.adet or 0, sermaye=ra.sermaye)
    print(f"\n  {rapor.S}✓ Tez kaydedildi{rapor.R} — {sem} @ {fiyat:.2f}")
    if t.eksikler():
        print(f"  {rapor.Y}Eksik kalan sorular:{rapor.R}")
        for e in t.eksikler():
            print(f"    · {e}")


def komut_tezler(args, a):
    from cekirdek import tez as tz
    ra = risk_kur(a, args.sermaye)
    acik = tz.kontrol(ra.sermaye)
    rapor.baslik("YATIRIM TEZLERİ")
    if acik:
        rapor.alt_baslik(f"AÇIK ({len(acik)})")
        for x in acik:
            t = x["tez"]
            tam = f"{rapor.S}tam{rapor.R}" if t.tam_mi() else f"{rapor.K}eksik ({len(t.eksikler())} soru){rapor.R}"
            print(f"\n  {rapor.B}{t.sembol}{rapor.R} · {t.tarih} · giriş {t.fiyat:.2f} · "
                  f"güncel {x['guncel_fiyat']:.2f} "
                  f"({rapor.yuzde_renk(x['degisim_yuzde'] or 0)}) · {tam}")
            print(f"    {rapor.G}yanılma koşulu:{rapor.R} {t.yanilma_kosulu or '—'}")
            for b in x["bozulmalar"]:
                print(f"    {rapor.K}▲ {b}{rapor.R}")
    else:
        print(f"\n  {rapor.G}Açık tez yok.{rapor.R}")

    ozet = tz.gecmis_ozet()
    if ozet.get("islem"):
        rapor.alt_baslik("KARNEN — kapanmış tezler")
        print(f"  {ozet['islem']} işlem · kazanma %{ozet['kazanma_orani']} · "
              f"ortalama {rapor.yuzde_renk(ozet['ortalama_getiri'])}")
        print(f"  en iyi {rapor.yuzde_renk(ozet['en_iyi'])} · "
              f"en kötü {rapor.yuzde_renk(ozet['en_kotu'])}")
        if ozet.get("tam_tezle_ortalama") is not None and ozet.get("eksik_tezle_ortalama") is not None:
            print(f"\n  Tam tez yazdıkların ({ozet['tam_tez_sayisi']}): "
                  f"{rapor.yuzde_renk(ozet['tam_tezle_ortalama'])}")
            print(f"  Eksik tezliler ({ozet['eksik_tez_sayisi']}): "
                  f"{rapor.yuzde_renk(ozet['eksik_tezle_ortalama'])}")
            print(f"  {rapor.G}{ozet['yorum']}{rapor.R}")
        if ozet.get("dersler"):
            print(f"\n  {rapor.B}Kendi derslerin:{rapor.R}")
            for d in ozet["dersler"][-5:]:
                print(f"    · {d}")


def komut_kontrol(args, a):
    from cekirdek import psikoloji as ps, gostergeler as gs, tez as tz
    ra = risk_kur(a, args.sermaye)
    sem = args.hisse.upper()
    df = veri.fiyat_cek(sem, gun=400)
    if df.empty:
        print(f"{sem} verisi alınamadı."); return
    g = gs.gosterge_seti(df)
    tezler = [t for t in tz.yukle() if t.sembol == sem and t.acik]
    acik = [{"sembol": p.sembol, "giris": p.giris, "maliyet": p.maliyet}
            for p in portfoy.yukle()]
    from dataclasses import asdict
    gecmis = [asdict(t) for t in tz.yukle() if not t.acik]

    rapor.baslik(f"ALIM ÖNCESİ KONTROL · {sem} · {args.adet} adet × {args.fiyat:.2f}")
    u = ps.alim_oncesi(sem, args.fiyat, args.adet, ra.sermaye, g.iloc[-1],
                       gecmis, acik, tez_var_mi=bool(tezler))
    rapor.psikoloji_raporu(u, ps.gunluk_kontrol_listesi())
    dur = [x for x in u if x.seviye == "dur"]
    if dur:
        print(f"\n  {rapor.K}{rapor.B}{len(dur)} kritik uyarı var. "
              f"Bu emri girmeden önce yukarıdaki soruları cevapla.{rapor.R}")


def komut_risk(args, a):
    from cekirdek import istatistik as ist
    ra = risk_kur(a, args.sermaye)
    rapor.baslik(f"RİSK MATEMATİĞİ · {rapor.para(ra.sermaye)} TL sermaye")

    rapor.alt_baslik("BEKLENEN DEĞER — yüksek kazanma oranı yanıltıcıdır")
    ornekler = [("kırılım (ölçülen)", 0.459, 16.1, 7.3),
                ("çok kazanan, zararda", 0.90, 1.0, 15.0),
                ("az kazanan, kârlı", 0.35, 25.0, 8.0)]
    print(f"  {'strateji':<24} {'kazanma':>8} {'ödül/risk':>10} {'beklenti':>10} {'başabaş':>9}")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    for ad, p, k, z in ornekler:
        r = ist.beklenen_deger(p, k, z)
        renk = rapor.S if r["karli_mi"] else rapor.K
        print(f"  {ad:<24} {p*100:7.1f}% 1:{r['odul_risk']:<9.2f} "
              f"{renk}{r['beklenen_deger_yuzde']:>+9.3f}%{rapor.R} "
              f"{r['basabas_kazanma_orani']:>8.1f}%")
    print(f"\n  {rapor.G}Başabaş sütunu: bu ödül/risk oranıyla kârda kalmak için "
          f"gereken en düşük kazanma oranı.{rapor.R}")

    rapor.alt_baslik("İŞLEM BAŞI RİSK NE OLMALI — Monte Carlo, 200 işlem")
    print(f"  {'risk':>6} {'batma olasılığı':>17} {'kötü senaryo (%5)':>19} "
          f"{'zararla biten':>14} {'en uzun kayıp':>14}")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    for r_ in [1.0, 1.5, 2.5, 5.0, 10.0, 20.0]:
        b = ist.batma_riski(r_, 0.459, 16.1 / 7.3, islem=200)
        renk = rapor.S if b["batma_olasiligi_yuzde"] < 1 else (
            rapor.Y if b["batma_olasiligi_yuzde"] < 10 else rapor.K)
        print(f"  {r_:5.1f}% {renk}{b['batma_olasiligi_yuzde']:>16.1f}%{rapor.R} "
              f"{b['kotu_senaryo_5']:>18.2f}x {b['zarar_eden_deneme_yuzde']:>13.1f}% "
              f"{b['en_uzun_kayip_serisi']:>13d}")
    k = ist.kelly(0.459, 16.1, 7.3)
    print(f"\n  {k['yorum']}")
    print(f"  {rapor.Y}Yukarı taraf rakamlarına güvenme — kenarın 200 işlem boyunca")
    print(f"  bozulmadan süreceğini varsayarlar. Bu tablodan alınacak bilgi AŞAĞI taraftır.{rapor.R}")

    rapor.alt_baslik("NEDEN TÜM PARAYI TEK HİSSEYE YATIRMAMALI")
    print(f"  {'hisse':>6} {'yıllık oynaklık':>17} {'normal gün ±':>15} "
          f"{'kötü gün ±':>13} {'biri batarsa':>14}")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    for x in ist.tek_hisse_matematigi(ra.sermaye):
        print(f"  {x['hisse_sayisi']:>6} {x['yillik_oynaklik']:>16.1f}% "
              f"{x['gunluk_1std_tl']:>14.2f}₺ {x['kotu_gun_2std_tl']:>12.2f}₺ "
              f"{x['tek_hisse_iflas_kaybi_tl']:>13.2f}₺")
    print(f"\n  {rapor.G}Dikkat: 1'den 4 hisseye çıkmak oynaklığı %45'ten %35,6'ya indiriyor,")
    print(f"  ama 8'den 20'ye çıkmak neredeyse hiçbir şey kazandırmıyor. Korelasyon yüzünden —")
    print(f"  aynı piyasadaki hisseler birlikte hareket eder. Çeşitlendirmenin sınırı budur.{rapor.R}")

    # gerçek portföy varsa onu da ölç
    pozlar = portfoy.yukle()
    if len(pozlar) >= 2:
        rapor.alt_baslik("SENİN PORTFÖYÜN")
        fiyatlar = {p.sembol: veri.fiyat_cek(p.sembol, gun=200) for p in pozlar}
        agirlik = {p.sembol: p.maliyet for p in pozlar}
        pr = ist.portfoy_riski(agirlik, fiyatlar)
        if "hata" not in pr:
            print(f"  Portföy oynaklığı %{pr['portfoy_oynaklik_yuzde']} "
                  f"(ağırlıklı ortalama %{pr['agirlikli_ortalama_oynaklik']})")
            print(f"  Çeşitlendirme kazancı: %{pr['cesitlendirme_kazanci_yuzde']}")
            print(f"  Ortalama korelasyon: {pr['ortalama_korelasyon']} · "
                  f"etkin hisse sayısı {pr['etkin_hisse_sayisi']} "
                  f"(nominal {pr['nominal_hisse_sayisi']})")
            if pr.get("uyari"):
                print(f"  {rapor.K}{pr['uyari']}{rapor.R}")


def komut_yapi(args, a):
    from cekirdek import formasyon as fm
    sem = args.hisse.upper()
    df = veri.fiyat_cek(sem, gun=750)
    if df.empty or len(df) < 220:
        print(f"{sem} için yeterli veri yok."); return
    r = fm.tam_analiz(df)
    rapor.baslik(f"{sem} · YAPI, FIBONACCI, ÇOKLU ZAMAN")

    y = r["yapi"]
    rapor.alt_baslik("TREND YAPISI — tepe/dip dizilimi")
    renk = rapor.S if y["yapi"] == "YÜKSELEN" else (rapor.K if y["yapi"] == "DÜŞEN" else rapor.Y)
    print(f"  {renk}{rapor.B}{y['yapi']}{rapor.R} — {y['aciklama']}")
    if y.get("tepeler"):
        print(f"  son tepeler: {y['tepeler']}   son dipler: {y['dipler']}")
    print(f"  {rapor.G}Trendin gerçek tanımı budur — hareketli ortalama değil.{rapor.R}")

    c = r["cok_zamanli"]
    if "hata" not in c:
        rapor.alt_baslik("ÇOKLU ZAMAN DİLİMİ")
        for d in c["dilimler"]:
            ok = rapor.S if d["yon"] == "yukarı" else (rapor.K if d["yon"] == "aşağı" else rapor.G)
            print(f"  {d['dilim']:<10} {ok}{d['yon']:<7}{rapor.R} "
                  f"fiyat {d['fiyat']:>9,.2f}  orta ort {d['orta_ort']:>9,.2f}  "
                  f"uzun ort {d['uzun_ort']:>9,.2f}")
        renk = rapor.S if "yukarı" in c["uyum"] else (rapor.K if "aşağı" in c["uyum"] or "ÇELİŞKİ" in c["uyum"] else rapor.Y)
        print(f"\n  {renk}{rapor.B}{c['uyum']}{rapor.R} — {c['aciklama']}")
        print(f"  {rapor.G}{c['kural']}{rapor.R}")

    f = r["fibonacci"]
    if "hata" not in f:
        rapor.alt_baslik(f"FIBONACCI ({f['yon']} hareketi: {f['dip']} → {f['tepe']})")
        for ad, v in f["seviyeler"].items():
            fark = (f["fiyat"] / v - 1) * 100
            isaret = "◀ fiyat buraya en yakın" if ad == f["en_yakin"]["seviye"] else ""
            print(f"  {ad:>5}  {v:>10,.2f}   fiyat {rapor.yuzde_renk(fark, 1, 7)} "
                  f"{'üstünde' if fark > 0 else 'altında'}  {rapor.Y}{isaret}{rapor.R}")
        print(f"\n  {rapor.G}{f['not']}{rapor.R}")

    k = r["sahte_kirilim"]
    rapor.alt_baslik("KIRILIM GÜVENİLİRLİĞİ — bu hissede geçmişte ne oldu?")
    if "hata" in k:
        print(f"  {rapor.G}{k['hata']}{rapor.R}")
    else:
        renk = rapor.S if k["tutma_orani_yuzde"] >= 55 else rapor.K
        print(f"  {k['kirilim_sayisi']} kırılım · {k['tutan']} tuttu · "
              f"{renk}tutma oranı %{k['tutma_orani_yuzde']}{rapor.R} · "
              f"sahte %{k['sahte_orani_yuzde']}")
        print(f"  {k['yorum']}")


def komut_dagitim(args, a):
    from cekirdek import portfoy_yonetimi as py, makro
    from cekirdek.strateji import Filtreler
    ra = risk_kur(a, args.sermaye)
    print("» adaylar taranıyor...")
    gecen, _ = tarayici.tara(evren_adi=args.evren or a.get("evren", "bist100"),
                             risk_ayar=ra, filtre=filtre_kur(a), gun=500,
                             sadece_sinyalli=args.sinyal)
    adaylar = [(x.sembol, x.fiyat) for x in gecen[:12]]
    if not adaylar:
        print("  Uygun aday yok."); return

    d = py.dagitim(adaylar, ra.sermaye, args.profil)
    rapor.baslik(f"PORTFÖY DAĞITIMI · {rapor.para(ra.sermaye)} TL · {args.profil}")
    print(f"\n  {rapor.G}{d['aciklama']}{rapor.R}\n")
    print(f"  {'hisse':<8} {'fiyat':>10} {'hedef%':>8} {'adet':>5} {'tutar':>11} "
          f"{'gerçek%':>9}  not")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    for h in d["hedefler"]:
        renk = rapor.K if h.adet == 0 else ""
        print(f"  {renk}{h.sembol:<8} {h.fiyat:>10,.2f} {h.hedef_yuzde:>7.1f}% "
              f"{h.adet:>5} {h.tutar:>11,.2f} {h.gercek_yuzde:>8.1f}%{rapor.R}  "
              f"{rapor.G}{h.not_}{rapor.R}")
    print(rapor.G + "  " + "─" * (rapor.GENISLIK - 2) + rapor.R)
    print(f"  Yatırılan {rapor.para(d['yatirilan'])} TL · "
          f"Nakit {rapor.para(d['nakit'])} TL (%{d['nakit_yuzde']}, "
          f"hedef %{d['hedef_nakit_yuzde']})")
    if d.get("uyari"):
        print(f"\n  {rapor.Y}{d['uyari']}{rapor.R}")

    try:
        m = makro.durum(); r = makro.rejim(m)
        n = py.nakit_orani_onerisi(r["rejim"])
        rapor.alt_baslik("REJİME GÖRE NAKİT ÖNERİSİ")
        print(f"  Rejim '{n['rejim']}' → önerilen nakit %{n['onerilen_nakit_yuzde']}")
        print(f"  {n['gerekce']}")
        print(f"  {rapor.G}{n['matematik']}{rapor.R}")
    except Exception:
        pass

    pozlar = portfoy.yukle()
    if pozlar:
        fiyatlar = {}
        for p_ in pozlar:
            df = veri.fiyat_cek(p_.sembol, gun=30)
            if not df.empty:
                fiyatlar[p_.sembol] = float(df["Close"].iloc[-1])
        dg = py.dengeleme_gerekli_mi(pozlar, fiyatlar)
        if "agirliklar" in dg:
            rapor.alt_baslik("MEVCUT PORTFÖY DENGESİ")
            for s_, w in dg["agirliklar"].items():
                print(f"  {s_:<8} %{w:>5.1f}  (hedef %{dg['hedef_agirlik']}, "
                      f"sapma {dg['sapmalar'][s_]:+.1f})")
            print(f"\n  Dengeleme gerekli mi: "
                  f"{rapor.Y + 'EVET' + rapor.R if dg['gerekli'] else rapor.S + 'hayır' + rapor.R}")
            print(f"  {rapor.G}{dg['not']}{rapor.R}")


def komut_ogret(args, a):
    """Günlük eğitmen oturumu: önce DERS, sonra pekiştirme soruları."""
    from cekirdek import egitmen as eg, egitmen_dersler as ed
    sorular_il, dersler_il = eg.ilerleme_yukle()
    durum = eg.seviye_durumu(sorular_il, dersler_il)

    # ── 1) BUGÜNÜN DERSİ
    yeni_dersler = eg.gunluk_ders(dersler_il, args.ders)
    if yeni_dersler and not args.sadece_soru:
        for i, d in enumerate(yeni_dersler, 1):
            m = ed.ders_modulu(d.kod)
            rapor.ders_goster(d, m, f"ders {i}/{len(yeni_dersler)}")
            try:
                cevap = input(f"  {rapor.G}[Enter: okudum · i: işaretle · "
                              f"a: atla]{rapor.R} ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n  Oturum yarıda kesildi.")
                eg.ilerleme_kaydet(sorular_il, dersler_il)
                return
            if cevap == "a":
                continue
            dersler_il = eg.ders_okundu(dersler_il, d.kod)
            if cevap == "i":
                dersler_il = eg.ders_isaretle(dersler_il, d.kod, True)
                print(f"  {rapor.Y}İşaretlendi — bu derse döneceksin.{rapor.R}")
        eg.ilerleme_kaydet(sorular_il, dersler_il)
    elif not yeni_dersler and not args.sadece_soru:
        print(f"\n  {rapor.S}Müfredattaki tüm dersleri okudun.{rapor.R}")
        print(f"  {rapor.G}Tekrar için: python analist.py ders d101{rapor.R}")

    # ── 2) PEKİŞTİRME SORULARI (sadece okuduğun derslerden)
    if args.soru > 0:
        banka = eg.gunluk_secim(sorular_il, args.soru, dersler=dersler_il)
        canlilar = []
        if not args.sadece_banka:
            try:
                from cekirdek import tarayici as tr, makro as mk, temel_veri as tv, \
                    temel as tm, degerleme as dg
                ra = risk_kur(a, args.sermaye)
                gecen, _ = tr.tara(risk_ayar=ra, gun=500)
                tarama = {"adaylar": [x.sozluk() for x in gecen[:12]]}
                m = mk.durum(); xu = m.oz("xu100")
                makro_d = {"enflasyon": m.enflasyon,
                           "bist_reel_getiri_1y": (xu["g365"] - m.enflasyon["yillik"]) if xu else None,
                           "gostergeler": {"xu100": {"g365": xu["g365"] if xu else None}}}
                sirketler = []
                for sem in [x.sembol for x in gecen[:3]] + ["EREGL", "THYAO"]:
                    f = tv.finansal_cek(sem)
                    if f is None:
                        continue
                    c = dg.carpanlar(f)
                    sirketler.append({
                        "sembol": f.sembol, "kur_uyusmazligi": f.kur_uyusmazligi,
                        "tablo_para": f.tablo_para, "fiyat_para": f.fiyat_para,
                        "kalite": tm.kalite_skoru(f),
                        "carpanlar": {k: {"deger": v.deger if v.var_mi and v.gecerli else None}
                                      for k, v in c.items()}})
                pozlar = [{"sembol": p["poz"].sembol, "kar_yuzde": p["kar_yuzde"]}
                          for p in portfoy.kontrol() if "hata" not in p]
                canlilar = eg.canli_sorular(tarama, makro_d, sirketler, pozlar,
                                            azami=args.canli)
            except Exception:
                pass

        hepsi = canlilar + banka
        if hepsi:
            rapor.baslik(f"PEKİŞTİRME · {len(hepsi)} soru")
            print(f"\n  {rapor.G}Cevabı görmeden önce kendin kur.{rapor.R}")
            try:
                for i, q in enumerate(hepsi, 1):
                    rapor.soru_goster(q, i, len(hepsi))
                    input(f"\n  {rapor.G}[Enter]{rapor.R} ")
                    rapor.cevap_goster(q)
                    if getattr(q, "canli", False):
                        continue
                    print(f"\n  {rapor.B}Kendini değerlendir:{rapor.R}  "
                          f"{rapor.K}1{rapor.R} bilmiyordum · "
                          f"{rapor.Y}2{rapor.R} kısmen · "
                          f"{rapor.S}3{rapor.R} biliyordum")
                    secim = input("  > ").strip()
                    kalite = {"1": 1, "2": 3, "3": 5}.get(secim, 3)
                    sorular_il[q.kod] = eg.guncelle(
                        sorular_il.get(q.kod, eg.Kayit(kod=q.kod)), kalite)
            except (KeyboardInterrupt, EOFError):
                print("\n\n  Yarıda kesildi — cevapladıkların kaydedildi.")
            eg.ilerleme_kaydet(sorular_il, dersler_il)

    yeni_durum = eg.seviye_durumu(sorular_il, dersler_il)
    print(f"\n{rapor.B}{'─' * rapor.GENISLIK}{rapor.R}")
    print(f"  {yeni_durum['ders']['okunan']}/{yeni_durum['ders']['toplam']} ders "
          f"· %{yeni_durum['bilesik_yuzde']} tamamlandı "
          f"· {yeni_durum['ders']['dakika_kalan']} dk kaldı")
    if yeni_durum["seviye"] > durum["seviye"]:
        print(f"  {rapor.S}{rapor.B}SEVİYE ATLADIN: {yeni_durum['unvan']}{rapor.R}")
    print(f"  {rapor.Y}{eg.ilke_gunun()}{rapor.R}")


def komut_ders(args, a):
    """Belirli bir dersi oku."""
    from cekirdek import egitmen as eg, egitmen_dersler as ed
    d = ed.ders_getir(args.kod)
    if d is None:
        print(f"'{args.kod}' bulunamadı. Müfredat için: python analist.py mufredat")
        return
    rapor.ders_goster(d, ed.ders_modulu(d.kod))
    if d.sorular:
        print(f"  {rapor.G}Bu dersin pekiştirme soruları: {', '.join(d.sorular)}{rapor.R}")
    sorular_il, dersler_il = eg.ilerleme_yukle()
    if not args.okuma:
        dersler_il = eg.ders_okundu(dersler_il, d.kod)
        eg.ilerleme_kaydet(sorular_il, dersler_il)


def komut_mufredat(args, a):
    from cekirdek import egitmen as eg, egitmen_dersler as ed
    sorular_il, dersler_il = eg.ilerleme_yukle()
    durum = eg.seviye_durumu(sorular_il, dersler_il)

    if args.modul:
        m = ed.modul_getir(args.modul)
        if m is None:
            print(f"'{args.modul}' bulunamadı.")
            return
        rapor.baslik(f"{m.kod.upper()} · {m.ad}")
        print(f"\n  {rapor.G}{m.aciklama}{rapor.R}\n")
        for d in m.dersler:
            k = dersler_il.get(d.kod)
            isaret = (f"{rapor.S}✓{rapor.R}" if k and k.okundu else f"{rapor.G}○{rapor.R}")
            im = f" {rapor.Y}★{rapor.R}" if k and k.isaretli else ""
            print(f"  {isaret} {rapor.B}{d.kod}{R if False else rapor.R}  "
                  f"{d.baslik:<46} ~{d.sure:2d} dk{im}")
            print(f"      {rapor.G}{d.ozet}{rapor.R}")
        print(f"\n  {rapor.G}Okumak için: python analist.py ders {m.dersler[0].kod}{rapor.R}")
        return

    rapor.mufredat_goster(durum["moduller"], durum)
    isaretli = eg.isaretli_dersler(dersler_il)
    if isaretli:
        rapor.alt_baslik("İŞARETLEDİĞİN DERSLER")
        for d in isaretli:
            print(f"  ★ {d.kod}  {d.baslik}")


def komut_ilerleme(args, a):
    from cekirdek import egitmen as eg
    sorular_il, dersler_il = eg.ilerleme_yukle()
    durum = eg.seviye_durumu(sorular_il, dersler_il)
    rapor.mufredat_goster(durum["moduller"], durum)
    rapor.egitmen_ozet(durum, eg.istatistik(sorular_il), eg.ilke_gunun())


def komut_sirket_oku(args, a):
    """'Bu şirketi bana 10 dakikada anlat' egzersizi."""
    from cekirdek import egitmen_sorular as es, temel_veri, temel, degerleme, sektor as sk
    sem = args.hisse.upper()
    rapor.baslik(f"{sem} · ŞİRKET OKUMA EGZERSİZİ")
    print(f"\n  {rapor.G}16 adım. Her adımda ÖNCE kendi cevabını söyle, sonra")
    print(f"  sistemin ölçtüğü rakama bak. Amaç doğru hisseyi seçmen değil,")
    print(f"  doğru düşünce sürecini kurman.{rapor.R}")

    f = temel_veri.finansal_cek(sem)
    o = temel.oranlar(f) if f else {}
    c = degerleme.carpanlar(f) if f else {}
    kalite = temel.kalite_skoru(f, o) if f else {}
    dcf = degerleme.ters_dcf(f) if f else {}

    def oran(k):
        r = o.get(k)
        return f"{r.deger:,.2f}{r.birim}" if r and r.var_mi and r.gecerli else "—"

    def carp(k):
        r = c.get(k)
        return f"{r.deger:,.2f}" if r and r.var_mi and r.gecerli else "—"

    veri_notu = {
        "is_modeli": f"{f.ad} · {f.sektor} / {f.sanayi}" if f else "—",
        "gelir_buyume": f"yıllık {oran('hasilat_buyume')} · 3 yıl {oran('hasilat_cagr3')} "
                        f"(kıyas: {f.tablo_para} enflasyonu %{f.enflasyon_referansi():.1f})" if f else "—",
        "kar_buyume": f"net kâr {oran('kar_buyume')} · net marj {oran('net_marj')}",
        "borc": f"Net Borç/FAVÖK {oran('net_borc_favok')} · faiz karşılama "
                f"{oran('faiz_karsilama')} · borç/özsermaye {oran('borc_ozsermaye')}",
        "nakit": f"FCF marjı {oran('fcf_marj')} · nakit/net kâr {oran('kar_kalitesi')}",
        "karlilik": f"brüt {oran('brut_marj')} · faaliyet {oran('faaliyet_marj')} · "
                    f"ROE {oran('roe')} · ROIC {oran('roic')}",
        "pahali_mi": f"F/K {carp('fk')} · PD/DD {carp('pd_dd')} · FD/FAVÖK {carp('fd_favok')} "
                     f"· FCF verimi {carp('fcf_verim')}",
        "ucuz_mu": dcf.get("yorum", dcf.get("hata", "—")),
        "sektor": sk.sektor_bilgi(f.sektor)["rehber"] if f else "—",
    }

    try:
        for i, (anahtar, soru, aciklama) in enumerate(es.SIRKET_OKUMA, 1):
            print(f"\n{rapor.B}{'─' * rapor.GENISLIK}{rapor.R}")
            print(f"  {rapor.G}ADIM {i}/16{rapor.R}")
            print(f"  {rapor.B}{soru}{rapor.R}")
            print(f"  {rapor.G}{aciklama}{rapor.R}")
            input(f"\n  {rapor.G}[cevabını düşün, sonra Enter]{rapor.R} ")
            if anahtar in veri_notu:
                print(f"  {rapor.S}Sistem ne ölçüyor:{rapor.R}")
                for satir in rapor._sar(str(veri_notu[anahtar]), rapor.GENISLIK - 6):
                    print(f"    {satir}")
            else:
                print(f"  {rapor.G}(bu adımda sayı yok — kendi araştırman gerekiyor){rapor.R}")
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Egzersiz yarıda kesildi.")
        return

    if kalite.get("skor") is not None:
        rapor.alt_baslik("SİSTEMİN ÖZETİ")
        print(f"  Kalite skoru: {rapor.skor_renk(kalite['skor'])}/100")
        for b in temel.kirmizi_bayraklar(f, o):
            print(f"  {rapor.K}▲ {b}{rapor.R}")
    print(f"\n  {rapor.Y}Son soru: bu şirketi neden ALIRSIN, neden ALMAZSIN?")
    print(f"  İkisini de yazamıyorsan yeterince düşünmemişsindir.{rapor.R}")


def komut_gunluk(args, a):
    """Günlük işi elle çalıştır."""
    from cekirdek import gunluk
    ra = risk_kur(a, args.sermaye)
    acik, sebep = gunluk.islem_gunu_mu()
    if not acik and not args.zorla:
        print(f"  BIST bugün kapalı ({sebep}).")
        print(f"  Yine de çalıştırmak için: python analist.py gunluk --zorla")
        return
    r = gunluk.calistir(sermaye=ra.sermaye, haber_topla=not args.habersiz)
    if r.get("ozet"):
        rapor.gun_ozeti_goster(r["ozet"])


def komut_doldur(args, a):
    """Geçmişi yeniden üretip sicili baştan doldur."""
    from cekirdek import gunluk
    ra = risk_kur(a, args.sermaye)
    print(f"  {rapor.G}Geçmiş {args.gun} gün yeniden üretilecek. "
          f"Bu birkaç dakika sürebilir.{rapor.R}")
    r = gunluk.geriye_doldur(gun_sayisi=args.gun, sermaye=ra.sermaye)
    if r.get("hata"):
        print(f"  {rapor.K}{r['hata']}{rapor.R}"); return
    print(f"\n  {rapor.S}Tamamlandı{rapor.R}: {r['hisse']} hisse · {r['gun']} gün "
          f"({r['baslangic']} → {r['bitis']})")
    print(f"  {r['fiyat']:,} fiyat kaydı · {r['sinyal']:,} sinyal · "
          f"{sum(r['sonuc'].values()):,} sonuç")
    print(f"\n  {rapor.G}Şimdi bak: python analist.py karne{rapor.R}")


def komut_ozet(args, a):
    """Kaydedilmiş gün özetini göster."""
    from cekirdek import ambar
    o = ambar.ozet_oku(args.tarih)
    if o is None:
        print("  Kayıtlı gün özeti yok. Önce: python analist.py gunluk")
        return
    rapor.gun_ozeti_goster(o)
    if not args.tarih:
        t = ambar.ozet_tarihleri(10)
        if len(t) > 1:
            print(f"\n  {rapor.G}Diğer günler: {', '.join(t[1:8])}{rapor.R}")


def komut_gecmis(args, a):
    """Bir hissenin ambardaki günlük seyri."""
    from cekirdek import gunluk
    rapor.degisim_goster(gunluk.degisim_raporu(args.hisse, args.gun))


def komut_karne(args, a):
    """Sistemin kendi sinyallerinin gerçek sicili."""
    from cekirdek import ogrenme
    rapor.karne_goster(ogrenme.karne(), ogrenme.kayma_analizi(),
                       ogrenme.filtre_etkisi(), ogrenme.olcum_kapsami(),
                       ogrenme.KIYAS_UYARILARI)


def komut_ambar(args, a):
    """Veri ambarı durumu ve son çalışmalar."""
    from cekirdek import ambar
    ambar.kur()
    ist = ambar.istatistik()
    rapor.baslik("VERİ AMBARI")
    print()
    for ad, anahtar in [("Fiyat kaydı", "fiyat_kaydi"), ("Haber", "haber"),
                        ("Haber eşleşmesi", "haber_eslesme"), ("Sinyal", "sinyal"),
                        ("Sinyal sonucu", "sinyal_sonuc"), ("Gün özeti", "gunluk_ozet")]:
        print(f"  {ad:<20} {ist[anahtar]:>8,}")
    print(f"  {'Kapsanan dönem':<20} {ist['ilk_tarih'] or '—'} → {ist['son_tarih'] or '—'}")
    print(f"  {'Dosya boyutu':<20} {ist['boyut_kb']:>8,.1f} KB")

    _ai_butce_yaz()

    calismalar = ambar.son_calismalar(8)
    if calismalar:
        rapor.alt_baslik("SON ÇALIŞMALAR")
        for c in calismalar:
            renk = rapor.S if c["durum"] == "başarılı" else rapor.K
            print(f"  {c['baslangic'][:16]}  {renk}{c['durum']:<10}{rapor.R} "
                  f"{(c['ozet'] or '')[:56]}")
    else:
        print(f"\n  {rapor.G}Henüz çalıştırılmadı. "
              f"Başlat: python analist.py gunluk{rapor.R}")


def _ai_butce_yaz():
    """AI harcaması — para gidiyorsa görünsün."""
    from cekirdek import ai, ambar
    b = ai.butce_durumu()
    dokum = ambar.ai_dokum()
    if not dokum and b["harcanan_tl"] == 0:
        return
    rapor.alt_baslik(f"AI HARCAMASI ({b['ay']})")
    if b["tavan_tl"] is None:
        print(f"  Harcanan {b['harcanan_tl']:.2f} TL · tavan yok")
    else:
        oran = b["oran"] or 0
        renk = rapor.K if oran >= 90 else (rapor.Y if oran >= 60 else rapor.S)
        print(f"  {renk}{b['harcanan_tl']:.2f} / {b['tavan_tl']:.0f} TL"
              f"  (%{oran:.0f}){rapor.R}   kalan {b['kalan_tl']:.2f} TL")
        if b["asildi"]:
            print(f"  {rapor.K}Tavan doldu — AI çağrıları duruyor. "
                  f"Yükseltmek için: export MIDAS_AI_TAVAN_TL=200{rapor.R}")
    for d in dokum:
        print(f"    {d['is_adi']:<20} {d['model']:<18} "
              f"{d['adet']:>4} çağrı  {d['tl']:>7.2f} TL")


def komut_aibutce(args, a):
    """AI harcaması: bu ay nereye ne kadar gitti."""
    from cekirdek import ai, ambar
    ambar.kur()
    b = ai.butce_durumu()
    rapor.baslik("AI BÜTÇESİ")
    print()
    ok, sebep = ai.kullanilabilir()
    durum = f"{rapor.S}hazır{rapor.R}" if ok else f"{rapor.Y}{sebep}{rapor.R}"
    print(f"  Durum                {durum}")
    print(f"  Ay                   {b['ay']}")
    if b["tavan_tl"] is None:
        print(f"  Tavan                yok (MIDAS_AI_TAVAN_TL=0)")
    else:
        print(f"  Tavan                {b['tavan_tl']:.0f} TL")
        print(f"  Harcanan             {b['harcanan_tl']:.2f} TL (%{b['oran']:.0f})")
        print(f"  Kalan                {b['kalan_tl']:.2f} TL")

    dokum = ambar.ai_dokum(args.ay if getattr(args, "ay", None) else None)
    if dokum:
        rapor.alt_baslik("İŞ BAZINDA")
        print(f"  {'iş':<20}{'model':<18}{'çağrı':>7}{'giriş':>10}"
              f"{'çıkış':>9}{'TL':>9}")
        print("  " + "─" * 74)
        for d in dokum:
            print(f"  {d['is_adi']:<20}{d['model']:<18}{d['adet']:>7}"
                  f"{d['giris'] or 0:>10,}{d['cikis'] or 0:>9,}{d['tl']:>9.2f}")
    else:
        print(f"\n  {rapor.G}Bu ay AI çağrısı yapılmadı.{rapor.R}")

    rapor.alt_baslik("MODEL DAĞILIMI")
    for isim, model in sorted(ai.MODELLER.items()):
        f = ai.FIYAT.get(model, {})
        print(f"  {isim:<20} {model:<18} "
              f"${f.get('giris', 0):.0f}/${f.get('cikis', 0):.0f} per 1M")
    print(f"\n  {rapor.G}Her iş kendi modelini kullanır — hepsine en pahalı")
    print(f"  modeli koşmak israftır.{rapor.R}")
    print(f"\n  {rapor.Y}API gideri işlem kârından DEĞİL, eğitim bütçesinden")
    print(f"  çıkmalı. 1.000 TL sermayede aylık 50 TL, gerçekçi aylık getiri")
    print(f"  hedefinin üstündedir.{rapor.R}")


def komut_sozluk(args, a):
    """Uygulamanın kendi terimleri. Ders değil, karşılık."""
    from cekirdek import sozluk as sz

    if args.terim:
        t = sz.terim_getir(args.terim)
        if t is not None:
            rapor.terim_goster(t, tam=True)
            return
        eslesen = sz.ara(args.terim)
        if not eslesen:
            rapor.sozluk_goster([], arama=args.terim)
            return
        # Tek eşleşme varsa doğrudan aç; birden çoksa listele.
        if len(eslesen) == 1:
            rapor.terim_goster(eslesen[0], tam=True)
            return
        bolumler = [sz.Bolum(b.kod, b.ad, b.aciklama,
                             [t for t in b.terimler if t in eslesen])
                    for b in sz.BOLUMLER]
        rapor.sozluk_goster([b for b in bolumler if b.terimler],
                            arama=args.terim, tam=False)
        return

    rapor.sozluk_goster(sz.BOLUMLER, tam=bool(args.tam))


def komut_ogren(args, a):
    """Eski 10 konuluk referans — artık tam müfredata yönlendiriyor."""
    from cekirdek import ogren as og, egitmen_dersler as ed

    # Eski konu adlarını yeni derslere eşle
    ESLESME = {
        "borsa": ["d101", "d102", "d106"],
        "emir": ["d103", "d104"],
        "spread": ["d102", "d105"],
        "aciga_satis": ["d109"],
        "temettu": ["d107", "d108"],
        "gostergeler": ["d708", "d704", "d703"],
        "temel_analiz": ["d201", "d202", "d203", "d204", "d206"],
        "degerleme": ["d401", "d402", "d403", "d404"],
        "risk": ["d801", "d802", "d803", "d804", "d805"],
        "psikoloji": ["d1001", "d1002", "d1003", "d1004"],
    }

    if not args.konu:
        rapor.baslik("EĞİTİM")
        print(f"\n  {rapor.G}Bu komut eski 10 konuluk özet referanstı. Artık"
              f"\n  {len(ed.MODULLER)} modül ve {len(ed.TUM_DERSLER)} derslik "
              f"tam müfredat var.{rapor.R}\n")
        print(f"  {rapor.B}python analist.py mufredat{rapor.R}   müfredat haritası")
        print(f"  {rapor.B}python analist.py ogret{rapor.R}       bugünün dersi")
        print(f"  {rapor.B}python analist.py ders d101{rapor.R}   belirli bir ders")
        print(f"\n  {rapor.G}Eski konu adları da çalışıyor ve ilgili derse yönlendirir:{rapor.R}")
        for k, b in og.konu_listesi():
            hedef = ESLESME.get(k, [])
            print(f"    {k:14s} → {', '.join(hedef) if hedef else '—'}")
        return

    anahtar = args.konu.lower().strip()
    hedefler = ESLESME.get(anahtar)
    if hedefler is None:
        k = og.konu_getir(anahtar)
        if k:
            hedefler = ESLESME.get(k["anahtar"], [])
    if not hedefler:
        print(f"'{args.konu}' bulunamadı. Müfredat: python analist.py mufredat")
        return

    print(f"  {rapor.G}'{anahtar}' konusu şu derslerde işleniyor:{rapor.R}")
    for kod in hedefler:
        d = ed.ders_getir(kod)
        if d:
            m = ed.ders_modulu(kod)
            print(f"    {rapor.B}{kod}{rapor.R}  {d.baslik}  "
                  f"{rapor.G}({m.ad if m else ''}, ~{d.sure} dk){rapor.R}")
    # ilkini doğrudan göster
    ilk = ed.ders_getir(hedefler[0])
    if ilk:
        rapor.ders_goster(ilk, ed.ders_modulu(ilk.kod))
        if len(hedefler) > 1:
            print(f"  {rapor.G}Diğerleri: "
                  f"{' · '.join('python analist.py ders ' + k for k in hedefler[1:])}{rapor.R}")



# ─────────────────────────────────────────────────────────────── giriş

def main():
    # Ortak bayraklar: hem "analist --duz tara" hem "analist tara --duz" çalışsın
    ortak = argparse.ArgumentParser(add_help=False)
    ortak.add_argument("--sermaye", type=float,
                       help="Bu çalıştırma için sermayeyi geçersiz kıl")
    ortak.add_argument("--duz", action="store_true",
                       help="Renksiz çıktı (dosyaya yönlendirme için)")

    p = argparse.ArgumentParser(
        prog="analist", description=__doc__, parents=[ortak],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest="komut", required=True)

    t = alt.add_parser("tara", help="Tüm evreni tara ve sırala", parents=[ortak])
    t.add_argument("--evren", help="bist30 | bist100 | hepsi | THYAO,GARAN")
    t.add_argument("--adet", type=int, default=15, help="Kaç satır gösterilsin")
    t.add_argument("--sinyal", action="store_true", help="Sadece sinyal verenleri göster")
    t.add_argument("--elenen", type=int, default=0, help="Kaç elenen gösterilsin")
    t.add_argument("--taze", action="store_true", help="Önbelleği yok say, yeniden indir")
    t.set_defaults(fn=komut_tara)

    an = alt.add_parser("analiz", help="Tek hisse ayrıntılı analiz", parents=[ortak])
    an.add_argument("hisse")
    an.set_defaults(fn=komut_analiz)

    pf = alt.add_parser("portfoy", help="Açık pozisyonları kontrol et", parents=[ortak])
    pf.set_defaults(fn=komut_portfoy)

    al = alt.add_parser("al", help="Midas'ta yaptığın alımı kaydet", parents=[ortak])
    al.add_argument("hisse"); al.add_argument("adet", type=int); al.add_argument("fiyat", type=float)
    al.add_argument("--stop", type=float); al.add_argument("--hedef", type=float)
    al.add_argument("--onayla", action="store_true",
                    help="Kritik davranışsal uyarılara rağmen kaydet")
    al.set_defaults(fn=komut_al)

    st = alt.add_parser("sat", help="Pozisyon kaydını sil", parents=[ortak])
    st.add_argument("hisse"); st.set_defaults(fn=komut_sat)

    bt = alt.add_parser("backtest", help="Stratejileri geçmiş veride test et", parents=[ortak])
    bt.add_argument("--strateji", choices=list(STRATEJILER))
    bt.add_argument("--evren"); bt.add_argument("--gun", type=int)
    bt.add_argument("--kayma", type=float, help="Kayma, baz puan (varsayılan 15)")
    bt.set_defaults(fn=komut_backtest)

    gk = alt.add_parser("gerceklik", help="Hedefinin matematiği", parents=[ortak])
    gk.add_argument("--hedef-yuzde", type=float, default=5.0, dest="hedef_yuzde")
    gk.set_defaults(fn=komut_gerceklik)

    sr = alt.add_parser("sirket", help="Temel analiz + değerleme", parents=[ortak])
    sr.add_argument("hisse")
    sr.add_argument("--hizli", action="store_true", help="Sektör kıyasını atla (hızlı)")
    sr.add_argument("--taze", action="store_true", help="Önbelleği yok say")
    sr.add_argument("--ai", action="store_true", help="AI yorumu ekle (API anahtarı gerekir)")
    sr.set_defaults(fn=komut_sirket)

    mk = alt.add_parser("makro", help="Makro gösterge paneli ve piyasa rejimi", parents=[ortak])
    mk.add_argument("--taze", action="store_true")
    mk.set_defaults(fn=komut_makro)

    sk_ = alt.add_parser("sektor", help="Sektör haritası: lider ve gecikenler", parents=[ortak])
    sk_.set_defaults(fn=komut_sektor)

    tz_ = alt.add_parser("tez", help="Yatırım tezi yaz / görüntüle", parents=[ortak])
    tz_.add_argument("hisse")
    tz_.add_argument("--yeni", action="store_true", help="Mevcut tez olsa da yenisini yaz")
    tz_.add_argument("--fiyat", type=float); tz_.add_argument("--adet", type=int)
    tz_.add_argument("--ai", action="store_true", help="AI tezini eleştirsin")
    tz_.set_defaults(fn=komut_tez)

    tzl = alt.add_parser("tezler", help="Tüm tezler ve karnen", parents=[ortak])
    tzl.set_defaults(fn=komut_tezler)

    kn = alt.add_parser("kontrol", help="Alım öncesi davranışsal kontrol", parents=[ortak])
    kn.add_argument("hisse"); kn.add_argument("adet", type=int); kn.add_argument("fiyat", type=float)
    kn.set_defaults(fn=komut_kontrol)

    rk = alt.add_parser("risk", help="Risk matematiği ve portföy riski", parents=[ortak])
    rk.set_defaults(fn=komut_risk)

    yp = alt.add_parser("yapi", help="Trend yapısı, Fibonacci, çoklu zaman dilimi", parents=[ortak])
    yp.add_argument("hisse"); yp.set_defaults(fn=komut_yapi)

    dg_ = alt.add_parser("dagitim", help="Portföy dağıtımı ve nakit oranı", parents=[ortak])
    dg_.add_argument("--profil", choices=["temkinli", "dengeli", "agresif"], default="dengeli")
    dg_.add_argument("--evren"); dg_.add_argument("--sinyal", action="store_true")
    dg_.set_defaults(fn=komut_dagitim)

    gn = alt.add_parser("gunluk", help="Günlük işi elle çalıştır (18:10'da otomatik)",
                        parents=[ortak])
    gn.add_argument("--zorla", action="store_true", help="Piyasa kapalıyken de çalıştır")
    gn.add_argument("--habersiz", action="store_true", help="Haber toplamayı atla")
    gn.set_defaults(fn=komut_gunluk)

    dl = alt.add_parser("doldur", help="Geçmişi yeniden üretip sicili doldur",
                        parents=[ortak])
    dl.add_argument("--gun", type=int, default=90)
    dl.set_defaults(fn=komut_doldur)

    oz = alt.add_parser("ozet", help="Gün özeti (piyasa, hareket edenler, sinyaller)",
                        parents=[ortak])
    oz.add_argument("tarih", nargs="?", help="YYYY-AA-GG (boşsa en son)")
    oz.set_defaults(fn=komut_ozet)

    gc = alt.add_parser("gecmis", help="Bir hissenin günlük seyri ve haberleri",
                        parents=[ortak])
    gc.add_argument("hisse"); gc.add_argument("--gun", type=int, default=15)
    gc.set_defaults(fn=komut_gecmis)

    kr = alt.add_parser("karne", help="Sistemin kendi sinyallerinin gerçek sicili",
                        parents=[ortak])
    kr.set_defaults(fn=komut_karne)

    am = alt.add_parser("ambar", help="Veri ambarı durumu", parents=[ortak])
    am.set_defaults(fn=komut_ambar)

    ab = alt.add_parser("ai-butce", help="AI harcaması ve aylık tavan",
                        parents=[ortak])
    ab.add_argument("--ay", help="YYYY-MM (varsayılan: bu ay)")
    ab.set_defaults(fn=komut_aibutce)

    ot = alt.add_parser("ogret", help="Günlük ders + pekiştirme soruları", parents=[ortak])
    ot.add_argument("--ders", type=int, default=1, help="Kaç yeni ders okunsun")
    ot.add_argument("--soru", type=int, default=3, help="Kaç pekiştirme sorusu")
    ot.add_argument("--canli", type=int, default=1, help="Kaç canlı soru")
    ot.add_argument("--sadece-soru", action="store_true", dest="sadece_soru",
                    help="Ders atla, sadece soru sor")
    ot.add_argument("--sadece-banka", action="store_true", dest="sadece_banka",
                    help="Canlı soru üretme (hızlı)")
    ot.set_defaults(fn=komut_ogret)

    dr = alt.add_parser("ders", help="Belirli bir dersi oku", parents=[ortak])
    dr.add_argument("kod", help="örn. d101, d402")
    dr.add_argument("--okuma", action="store_true",
                    help="Okundu olarak işaretleme (sadece göster)")
    dr.set_defaults(fn=komut_ders)

    mf = alt.add_parser("mufredat", help="13 modül — müfredat haritası",
                        parents=[ortak])
    mf.add_argument("modul", nargs="?", help="örn. m4 (boş bırakırsan tümü)")
    mf.set_defaults(fn=komut_mufredat)

    ilr = alt.add_parser("ilerleme", help="Eğitim ilerlemen ve seviyen", parents=[ortak])
    ilr.set_defaults(fn=komut_ilerleme)

    so = alt.add_parser("sirket-oku", help="'Bu şirketi 10 dakikada anlat' egzersizi",
                        parents=[ortak])
    so.add_argument("hisse"); so.set_defaults(fn=komut_sirket_oku)

    sz_ = alt.add_parser("sozluk",
                         help="Uygulamadaki terimlerin karşılıkları",
                         parents=[ortak])
    sz_.add_argument("terim", nargs="?",
                     help="Terim ya da sütun adı (GG60, ATR_yuzde, Sharpe)")
    sz_.add_argument("--tam", action="store_true",
                     help="Bütün terimleri açıklamalarıyla bas")
    sz_.set_defaults(fn=komut_sozluk)

    og_ = alt.add_parser("ogren", help="Borsa eğitimi: terimler ve tuzaklar", parents=[ortak])
    og_.add_argument("konu", nargs="?")
    og_.set_defaults(fn=komut_ogren)

    args = p.parse_args()
    if args.duz:
        rapor._renk_kapat()
    args.fn(args, ayarlari_oku())


if __name__ == "__main__":
    main()
