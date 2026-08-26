"""Terminal raporlama. Renk ve hizalama - okunabilirlik disiplini artırır."""
from __future__ import annotations

import shutil
from datetime import datetime

GENISLIK = min(shutil.get_terminal_size((100, 24)).columns, 104)

Y, K, S, M, G, B, R = (
    "\033[93m", "\033[91m", "\033[92m", "\033[95m", "\033[90m", "\033[1m", "\033[0m"
)


def _renk_kapat():
    global Y, K, S, M, G, B, R
    Y = K = S = M = G = B = R = ""


def baslik(metin: str, karakter: str = "═") -> None:
    print(f"\n{B}{karakter * GENISLIK}{R}")
    print(f"{B}  {metin}{R}")
    print(f"{B}{karakter * GENISLIK}{R}")


def alt_baslik(metin: str) -> None:
    print(f"\n{B}▸ {metin}{R}")
    print(G + "─" * GENISLIK + R)


def para(v: float) -> str:
    return f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def yuzde_renk(v: float, basamak: int = 2, genislik: int = 0) -> str:
    """Önce sayıyı sabit genişliğe doldur, SONRA renklendir.

    Tersi yapılırsa ANSI kaçış dizileri karakter sayılır ve --duz modunda
    tablo hizası kayar."""
    renk = S if v > 0 else (K if v < 0 else G)
    metin = f"{v:+.{basamak}f}%"
    return f"{renk}{metin:>{genislik}}{R}" if genislik else f"{renk}{metin}{R}"


def skor_renk(s: float) -> str:
    renk = S if s >= 70 else (Y if s >= 55 else (G if s >= 40 else K))
    return f"{renk}{s:5.1f}{R}"


def tarama_raporu(gecenler, elenenler, risk_ayar, adet: int = 15,
                  elenen_goster: int = 0) -> None:
    baslik(f"GÜNLÜK TARAMA · {datetime.now():%d.%m.%Y %H:%M} · sermaye {para(risk_ayar.sermaye)} TL")

    sinyalli = [a for a in gecenler if a.sinyaller]
    alinabilir = [a for a in sinyalli if a.pozisyon and a.pozisyon.uygulanabilir]

    print(f"\n  {len(gecenler)} hisse filtreyi geçti · {len(sinyalli)} tanesi sinyal veriyor "
          f"· {len(alinabilir)} tanesi {para(risk_ayar.sermaye)} TL ile ALINABILIR")

    if sinyalli:
        alt_baslik("BUGÜN SİNYAL VEREN HİSSELER")
        print(f"  {'hisse':<7} {'skor':>5} {'fiyat':>9} {'gün%':>7} {'RSI':>5} {'ADX':>5} "
              f"{'ATR%':>5} {'GG60':>6}  {'sinyal':<18} {'adet':>4} {'tutar':>9} {'stop':>8} {'hedef':>8}")
        print(G + "  " + "─" * (GENISLIK - 2) + R)
        for a in sinyalli[:adet]:
            p = a.pozisyon
            if p and p.uygulanabilir:
                poz_str = f"{p.adet:4d} {para(p.maliyet):>9} {p.stop:8.2f} {p.hedef:8.2f}"
            else:
                poz_str = f"{K}  —  alınamıyor: {p.uyari if p else ''}{R}"
            gg = f"{a.gg60:+6.1f}" if a.gg60 is not None else "     —"
            print(f"  {B}{a.sembol:<7}{R} {skor_renk(a.skor)} {a.fiyat:9.2f} "
                  f"{yuzde_renk(a.gunluk_degisim, 1, 7)} {a.rsi:5.1f} {a.adx:5.1f} "
                  f"{a.atr_yuzde:5.2f} {gg}  {M}{','.join(a.sinyaller):<18}{R} {poz_str}")
    else:
        print(f"\n  {Y}Bugün hiçbir hisse giriş sinyali vermiyor.{R}")
        print(f"  {G}Bu bir sorun değil - sinyal yoksa işlem yapılmaz. Nakitte beklemek de bir pozisyondur.{R}")

    alt_baslik(f"SKOR SIRALAMASI (ilk {adet}) — sinyal olmasa da izleme listesi")
    skora_gore = sorted(gecenler, key=lambda a: a.skor, reverse=True)
    print(f"  {'hisse':<7} {'skor':>5}  {'trend':>6} {'moment':>7} {'zaman':>6} {'kalite':>7}  "
          f"{'fiyat':>9} {'gün%':>7} {'RSI':>5}  {'200g':>5}  {'hacim(M₺)':>10}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for a in skora_gore[:adet]:
        ust = f"{S}▲{R}" if a.sma200_ustu else f"{K}▼{R}"
        print(f"  {B}{a.sembol:<7}{R} {skor_renk(a.skor)}  {a.trend:6.1f} {a.momentum:7.1f} "
              f"{a.zamanlama:6.1f} {a.kalite:7.1f}  {a.fiyat:9.2f} "
              f"{yuzde_renk(a.gunluk_degisim, 1, 7)} {a.rsi:5.1f}   {ust}   {a.tl_hacim/1e6:10,.0f}")

    if elenen_goster and elenenler:
        alt_baslik(f"ELENENLER (ilk {elenen_goster}) — neden bakmıyoruz")
        for a in elenenler[:elenen_goster]:
            print(f"  {a.sembol:<7} {a.skor:5.1f}  {K}{a.elendi}{R}")

    print(f"\n  {G}Skor bir kesinlik değil, SIRALAMA aracıdır. 80 puanlık hisse de zarar ettirebilir.")
    print(f"  Emirleri Midas uygulamasında sen giriyorsun - Midas'ın API'si yok.{R}")


def portfoy_raporu(durumlar, sermaye: float) -> None:
    baslik(f"AÇIK POZİSYONLAR · {datetime.now():%d.%m.%Y %H:%M}")
    if not durumlar:
        print(f"\n  {G}Kayıtlı açık pozisyon yok.")
        print(f"  Midas'ta bir alım yaptıysan kaydet:  python analist.py al THYAO 3 300.50{R}")
        return

    toplam_maliyet = toplam_deger = 0.0
    print(f"\n  {'hisse':<7} {'adet':>4} {'giriş':>9} {'güncel':>9} {'gün%':>7} {'kâr TL':>10} "
          f"{'kâr%':>8} {'gün':>4} {'stop':>8} {'hedef':>8}  {'aksiyon':<5}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for d in durumlar:
        p = d["poz"]
        if "hata" in d:
            print(f"  {p.sembol:<7} {K}{d['hata']}{R}")
            continue
        toplam_maliyet += p.maliyet
        toplam_deger += d["fiyat"] * p.adet
        ak = f"{K}{B}SAT{R}" if d["aksiyon"] == "SAT" else f"{S}TUT{R}"
        print(f"  {B}{p.sembol:<7}{R} {p.adet:4d} {p.giris:9.2f} {d['fiyat']:9.2f} "
              f"{yuzde_renk(d['gunluk_degisim'], 1, 7)} "
              f"{(S if d['kar']>0 else K)}{d['kar']:10.2f}{R} "
              f"{yuzde_renk(d['kar_yuzde'], 2, 8)} {d['gun']:4d} {p.stop:8.2f} {p.hedef:8.2f}  {ak}")
        print(f"           {G}└ {d['aciklama']}{R}")
        if d["oneri"]:
            print(f"           {Y}└ {d['oneri']}{R}")

    if toplam_maliyet:
        kar = toplam_deger - toplam_maliyet
        print(G + "  " + "─" * (GENISLIK - 2) + R)
        print(f"  {B}TOPLAM{R}  maliyet {para(toplam_maliyet)} TL · güncel {para(toplam_deger)} TL · "
              f"kâr {(S if kar>0 else K)}{para(kar)} TL{R} ({yuzde_renk(kar/toplam_maliyet*100)})")
        print(f"  Sermayenin %{toplam_deger/sermaye*100:.0f}'i piyasada, "
              f"%{max(0, (sermaye-toplam_maliyet))/sermaye*100:.0f}'i nakitte")


def backtest_raporu(m: dict, baslik_metni: str) -> None:
    alt_baslik(baslik_metni)
    if "hata" in m:
        print(f"  {K}{m['hata']}{R}")
        return
    sat = [
        ("Toplam getiri", f"{m['toplam_getiri_yuzde']:+.1f}%", m['toplam_getiri_yuzde']),
        ("Yıllık getiri (TL)", f"{m['yillik_getiri_yuzde']:+.1f}%", m['yillik_getiri_yuzde']),
        ("XU100 aynı dönem", f"{m.get('kiyas_getiri_yuzde', 0):+.1f}%", m.get('kiyas_getiri_yuzde', 0)),
        ("Alfa (endeks farkı)", f"{m.get('alfa_yuzde', 0):+.1f}%", m.get('alfa_yuzde', 0)),
        ("Azami düşüş", f"{m['azami_dusus_yuzde']:.1f}%", m['azami_dusus_yuzde']),
        ("Sharpe", f"{m['sharpe']:.2f}", m['sharpe'] - 1),
        ("Günlük ortalama", f"{m['gunluk_ort_yuzde']:+.3f}%", m['gunluk_ort_yuzde']),
        ("İşlem sayısı", f"{m['islem_sayisi']}", 0),
        ("Kazanma oranı", f"{m['kazanma_orani']:.0f}%", m['kazanma_orani'] - 50),
        ("Kâr faktörü", f"{m['kar_faktoru']:.2f}", m['kar_faktoru'] - 1),
        ("Ort. kazanç / kayıp", f"{m['ort_kazanc_yuzde']:+.1f}% / {m['ort_kayip_yuzde']:+.1f}%", 0),
        ("Ort. tutma süresi", f"{m['ort_tutma_gun']:.0f} iş günü", 0),
        ("En kötü tek işlem", f"{m['en_kotu_islem_yuzde']:.1f}%", m['en_kotu_islem_yuzde']),
        ("Sermaye yüzünden kaçan", f"{m['kacirilan_sinyal']} sinyal", 0),
    ]
    for ad, deger, isaret in sat:
        renk = S if isaret > 0 else (K if isaret < 0 else "")
        print(f"  {ad:<26} {renk}{deger:>22}{R}")


# ═══════════════════════════════════════════════ temel analiz & değerleme

def _durum_isaret(durum: str) -> str:
    """Renk kapalıyken (--duz) de ayırt edilebilsin diye şekil de değişir."""
    duz = not S            # renkler kapalıysa S boş string
    if duz:
        return {"iyi": "+", "orta": "~", "kotu": "!"}.get(durum, " ")
    return {"iyi": f"{S}●{R}", "orta": f"{Y}◐{R}",
            "kotu": f"{K}○{R}"}.get(durum, f"{G}·{R}")


def sirket_raporu(f, oranlar, kalite, bayraklar, carpanlar, dcf,
                  sektor_bilgi, sektor_ort=None, hukum=None) -> None:
    baslik(f"{f.sembol} · {f.ad[:52]}")
    print(f"\n  {G}{f.sektor} / {f.sanayi}{R}")
    print(f"  Fiyat {f.fiyat:,.2f} {f.fiyat_para} · Piyasa değeri "
          f"{f.piyasa_degeri/1e9:,.1f} milyar TL")
    if f.kur_uyusmazligi:
        print(f"  {Y}⚠ Finansallar {f.tablo_para} cinsinden açıklanıyor "
              f"(kur {f.kur:.2f} ile TL'ye çevrildi){R}")
    print(f"  Dönemler: {', '.join(f.donemler[:4]) if f.donemler else 'veri yok'}")

    sk = kalite.get("skor")
    alt_baslik(f"KALİTE SKORU: {skor_renk(sk) if sk else '—'}/100"
               f"{'  (banka modu)' if kalite.get('banka_modu') else ''}")
    gruplar = [
        ("Kârlılık", ["brut_marj", "faaliyet_marj", "favok_marj", "net_marj"]),
        ("Sermaye getirisi", ["roe", "roa", "roic"]),
        ("Borçluluk", ["borc_ozsermaye", "net_borc_favok", "faiz_karsilama"]),
        ("Likidite", ["cari_oran", "asit_test"]),
        ("Nakit & kalite", ["fcf_marj", "kar_kalitesi"]),
        ("Büyüme", ["hasilat_buyume", "hasilat_cagr3", "kar_buyume"]),
    ]
    for grup, anahtarlar in gruplar:
        satirlar = [oranlar[a] for a in anahtarlar if a in oranlar]
        if not any(o.gecerli for o in satirlar):
            continue
        print(f"\n  {B}{grup}{R}")
        for o in satirlar:
            if not o.gecerli:
                print(f"    {G}{o.ad:<34} —  (bu sektörde anlamsız){R}")
            elif not o.var_mi:
                print(f"    {G}{o.ad:<34} veri yok{R}")
            else:
                print(f"    {_durum_isaret(o.durum)} {o.ad:<32} "
                      f"{o.deger:>10,.2f}{o.birim}")

    if bayraklar:
        alt_baslik("KIRMIZI BAYRAKLAR")
        for b in bayraklar:
            print(f"  {K}▲ {b}{R}")

    alt_baslik("DEĞERLEME")
    print(f"  {'çarpan':<30} {'değer':>10}   {'sektör medyanı':>16}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for ad, c in carpanlar.items():
        if not c.gecerli:
            continue
        v = f"{c.deger:>10,.2f}" if c.var_mi else "         —"
        so = ""
        if sektor_ort and ad in sektor_ort:
            c.sektor_ort = sektor_ort[ad]
            so = f"{c.sektor_ort:>10,.2f}  {c.sektore_gore}"
        print(f"  {c.ad:<30} {v}   {so}")

    if hukum and hukum.get("hukum"):
        h = hukum["hukum"]
        renk = S if "UCUZ" in h or "ucuz" in h else (K if "PAHALI" in h or "pahalı" in h else Y)
        print(f"\n  Hüküm: {renk}{B}{h}{R}")
        for g in hukum.get("gerekce", [])[:4]:
            print(f"    {G}· {g}{R}")
        if hukum.get("uyari"):
            print(f"  {Y}{hukum['uyari']}{R}")

    if dcf and "hata" not in dcf:
        alt_baslik("TERS DCF — fiyat hangi büyümeyi ima ediyor?")
        print(f"  {dcf['yorum']}")
        print(f"  {dcf['kiyas']}")
        print(f"  {G}Soru şu: bu büyüme sence makul mü? Değilse fiyat pahalıdır.{R}")
    elif dcf:
        print(f"\n  {G}Ters DCF: {dcf['hata']}{R}")

    alt_baslik("SEKTÖR REHBERİ")
    print(f"  {B}{sektor_bilgi['ad']}{R}")
    for satir in sektor_bilgi["rehber"].split(". "):
        if satir.strip():
            print(f"  {satir.strip().rstrip('.')}.")


def makro_raporu(m, rejim_bilgi) -> None:
    baslik(f"MAKRO DURUM · {m.tarih}")
    e = m.enflasyon
    print(f"\n  {B}Enflasyon (TÜFE){R}  yıllık %{e['yillik']:.2f} · "
          f"aylık %{e['aylik']:.2f}  ({e['donem']}, {e['kaynak']})")
    r = rejim_bilgi
    renk = S if "AÇIK" in r["rejim"] else (K if "SAVUNMA" in r["rejim"] else Y)
    print(f"  {B}Rejim{R}  {renk}{B}{r['rejim']}{R} — {r['aciklama']}")
    for n in r["notlar"]:
        print(f"    {G}· {n}{R}")

    alt_baslik("GÖSTERGELER")
    print(f"  {'':<20} {'son':>12} {'1 gün':>8} {'1 ay':>8} {'3 ay':>8} {'1 yıl':>9}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    son_grup = None
    for k, v in m.degerler.items():
        if v["grup"] != son_grup:
            son_grup = v["grup"]
            print(f"  {G}{son_grup.upper()}{R}")
        print(f"    {v['ad']:<18} {v['son']:>12,.2f} "
              f"{yuzde_renk(v['g1'], 1, 8)} {yuzde_renk(v['g30'], 1, 8)} "
              f"{yuzde_renk(v['g90'], 1, 8)} {yuzde_renk(v['g365'], 1, 9)}")

    xu = m.oz("xu100")
    if xu and e.get("yillik"):
        reel = xu["g365"] - e["yillik"]
        print(f"\n  {B}BIST 100 reel getirisi (1 yıl){R}: %{xu['g365']:.1f} nominal − "
              f"%{e['yillik']:.1f} enflasyon = {yuzde_renk(reel, 1)}")
        print(f"  {G}Nominal getiri seni kandırır. Bakılacak sayı budur.{R}")


def sektor_raporu(d, liderler, gecikenler, yorum) -> None:
    baslik("SEKTÖR HARİTASI")
    print(f"\n  {G}Sektör serileri BİLEŞENLERDEN kuruldu (piyasa değeri ağırlıklı) —")
    print(f"  yfinance BIST sektör endekslerinin geçmişini taşımıyor.{R}\n")
    print(f"  {'sektör':<22} {'hisse':>5} {'20 gün':>9} {'60 gün':>9} {'120 gün':>9}"
          f" {'GG20':>8} {'GG60':>8}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for _, x in d.iterrows():
        gg = x["gg60"]
        isaret = f"{S}▲{R}" if gg > 5 else (f"{K}▼{R}" if gg < -5 else f"{G}─{R}")
        print(f"  {isaret} {x['sektor']:<20} {int(x['hisse']):>5} "
              f"{yuzde_renk(x['g20'], 1, 9)} {yuzde_renk(x['g60'], 1, 9)} "
              f"{yuzde_renk(x['g120'], 1, 9)} {yuzde_renk(x['gg20'], 1, 8)} "
              f"{yuzde_renk(x['gg60'], 1, 8)}")
    print(f"\n  {G}GG = endekse göre göreli güç (yüzde puan). Pozitif = XU100'ü yeniyor.{R}")
    print(f"\n  {S}{B}LİDERLER{R}    " +
          " · ".join(f"{l['sektor']} ({l['gg60']:+.1f})" for l in liderler))
    print(f"  {K}{B}GECİKENLER{R}  " +
          " · ".join(f"{l['sektor']} ({l['gg60']:+.1f})" for l in gecikenler))
    print(f"\n  {G}{yorum}{R}")


def psikoloji_raporu(uyarilar, kontrol_listesi=None) -> None:
    if not uyarilar:
        print(f"\n  {S}✓ Davranışsal uyarı yok.{R}")
    else:
        dur = [u for u in uyarilar if u.seviye == "dur"]
        alt_baslik(f"DAVRANIŞSAL UYARILAR ({len(dur)} kritik)")
        for u in uyarilar:
            renk = K if u.seviye == "dur" else (Y if u.seviye == "dikkat" else G)
            etiket = {"dur": "DUR", "dikkat": "DİKKAT", "bilgi": "BİLGİ"}[u.seviye]
            print(f"\n  {renk}{B}[{etiket}]{R} {B}{u.baslik}{R}")
            for satir in u.aciklama.split("\n"):
                print(f"        {satir.strip()}")
            if u.soru:
                print(f"        {Y}→ {u.soru}{R}")
    if kontrol_listesi:
        alt_baslik("ALIM ÖNCESİ KONTROL LİSTESİ")
        for i, s in enumerate(kontrol_listesi, 1):
            print(f"  {G}{i}.{R} {s}")


def ogren_raporu(k) -> None:
    baslik(k["baslik"].upper())
    print()
    for satir in k["ozet"].split("\n"):
        print(f"  {satir}")
    if k.get("bist_ozel"):
        alt_baslik("BIST / MİDAS ÖZELİ")
        for satir in k["bist_ozel"].split("\n"):
            print(f"  {satir}")
    if k.get("tuzak"):
        alt_baslik("TUZAK")
        for satir in k["tuzak"].split("\n"):
            print(f"  {K if satir.strip().startswith('•') else ''}{satir}{R if satir.strip().startswith('•') else ''}")


# ═══════════════════════════════════════════════ eğitmen

def soru_goster(s, sira: int = 0, toplam: int = 0) -> None:
    """Soruyu gösterir — cevabı GÖSTERMEZ. Önce düşünmen gerekiyor."""
    ust = f"SORU {sira}/{toplam}" if toplam else "SORU"
    seviye_ad = {1: "temel", 2: "orta", 3: "usta"}.get(getattr(s, "seviye", 1), "")
    canli = getattr(s, "canli", False)
    etiket = f"{S}● CANLI{R}" if canli else f"{G}{seviye_ad}{R}"
    # Seviye ve kategori aynıysa iki kez yazma
    kat = "" if s.kategori == seviye_ad else f"  {G}{s.kategori}{R}"
    print(f"\n{B}{'─' * GENISLIK}{R}")
    print(f"  {G}{ust}{R}  {etiket}{kat}")
    print(f"{B}{'─' * GENISLIK}{R}\n")
    for satir in _sar(s.soru, GENISLIK - 4):
        print(f"  {B}{satir}{R}")


def cevap_goster(s) -> None:
    print(f"\n  {S}{B}CEVAP{R}")
    for parca in s.cevap.split("\n"):
        if not parca.strip():
            print()
            continue
        for satir in _sar(parca, GENISLIK - 4):
            print(f"  {satir}")
    if getattr(s, "tuzak", ""):
        print(f"\n  {K}{B}YAYGIN HATA{R}")
        for parca in s.tuzak.split("\n"):
            if not parca.strip():
                print(); continue
            for satir in _sar(parca, GENISLIK - 4):
                print(f"  {K}{satir}{R}")
    anahtar = getattr(s, "anahtar", None)
    if anahtar:
        print(f"\n  {G}Anahtar kavramlar: {', '.join(anahtar)}{R}")


def _sar(metin: str, genislik: int) -> list[str]:
    """Kelime bölmeden satır sarma.

    Kaynak metin ~78 karakterde elle sarılmış olabilir; terminal daha genişse
    o sarma yanlış görünür. Bu yüzden önce paragraf içi satır sonları
    birleştirilir, sonra terminalin kendi genişliğine sarılır.
    """
    satirlar = []
    for ham in _paragraf_birlestir(metin).split("\n"):
        if not ham.strip():
            satirlar.append("")
            continue
        kelimeler, o = ham.split(), ""
        for k in kelimeler:
            if len(o) + len(k) + 1 > genislik:
                satirlar.append(o)
                o = k
            else:
                o = f"{o} {k}".strip()
        if o:
            satirlar.append(o)
    return satirlar


def _paragraf_birlestir(metin: str, sarma_genisligi: int = 62) -> str:
    """Paragraf içi SARMA kaynaklı satır sonlarını birleştirir, KASITLI
    olanları korur.

    Kaynak metinler ~78 karakterde elle sarılmıştır (dosyada okunabilir olsun
    diye). Terminal ya da telefon farklı genişlikteyse o sarma yanlış görünür.
    Ama ders içeriğinde kasıtlı kısa satırlar da var (tanımlar, etiketler).

    Ayırt etme kuralı — satır sonu KORUNUR eğer:
      · satır cümle sonu noktalamasıyla bitiyorsa (. : ! ? " )
      · satır sarma genişliğinden belirgin kısaysa (kasıtlı bitmiş)
      · sonraki satır madde/numara işaretiyle başlıyorsa
    Aksi halde satır bir sonrakiyle birleştirilir.
    """
    if not metin:
        return metin

    def madde_mi(t: str) -> bool:
        return (t[:2] in ("· ", "- ", "• ")
                or (len(t) > 2 and t[0].isdigit() and t[1] in (")", ".")))

    cikti = []
    for p in metin.split("\n\n"):
        satirlar = [x.rstrip() for x in p.split("\n")]
        birlesik, o = [], ""
        for i, sat in enumerate(satirlar):
            t = sat.strip()
            if not t:
                continue
            sonraki = satirlar[i + 1].strip() if i + 1 < len(satirlar) else ""
            if o and (madde_mi(t) or _kasitli_son(o, sarma_genisligi)
                      or madde_mi(sonraki) and False):
                birlesik.append(o)
                o = t
            else:
                o = f"{o} {t}".strip() if o else t
            # bu satır kasıtlı bittiyse burada kes
            if _kasitli_son(t, sarma_genisligi) and o:
                birlesik.append(o)
                o = ""
        if o:
            birlesik.append(o)
        cikti.append("\n".join(birlesik))
    return "\n\n".join(cikti)


def _kasitli_son(satir: str, sarma_genisligi: int) -> bool:
    """Bu satır sarma yüzünden mi bitti, kasıtlı mı?"""
    t = satir.rstrip()
    if not t:
        return False
    if t[-1] in '.:!?"\u201d)':
        return True
    # sarma genişliğinden belirgin kısa satır, kasıtlı bitmiştir
    return len(t) < sarma_genisligi


def egitmen_ozet(durum: dict, ist: dict, ilke: str) -> None:
    baslik(f"EĞİTMEN · {durum['unvan']} (seviye {durum['seviye']}/3)")
    print()
    for ad, anahtar in [("Temel", "temel"), ("Orta", "orta"), ("Usta", "usta")]:
        d = durum[anahtar]
        dolu = int(d["yuzde"] / 100 * 28)
        renk = S if d["yuzde"] >= 70 else (Y if d["yuzde"] >= 35 else G)
        print(f"  {ad:<6} {renk}{'█' * dolu}{G}{'░' * (28 - dolu)}{R} "
              f"{d['ogrenilen']:>2}/{d['toplam']:<2} (%{d['yuzde']})")
    print(f"\n  {G}{durum['sonraki_seviye']}{R}")

    if ist.get("calisilan"):
        alt_baslik("İSTATİSTİK")
        print(f"  Çalışılan soru      {ist['calisilan']}/{durum['toplam_soru']}")
        print(f"  Öğrenilen           {ist['ogrenilen']}")
        print(f"  Doğru oranı         %{ist['dogru_orani']}")
        print(f"  Bugün vadesi gelen  {ist['bugun_vadesi_gelen']}")
        if ist.get("en_zorlananlar"):
            print(f"\n  {B}En çok zorlandıkların:{R}")
            for z in ist["en_zorlananlar"]:
                print(f"    {K}✗{z['yanlis']}{R}/{S}✓{z['dogru']}{R}  {z['soru'][:62]}")

    print(f"\n{B}{'─' * GENISLIK}{R}")
    print(f"  {Y}{ilke}{R}")
    print(f"{B}{'─' * GENISLIK}{R}")


def ders_goster(ders, modul=None, sira: str = "") -> None:
    """Bir dersi okunabilir biçimde yazar."""
    baslik(ders.baslik.upper())
    if modul:
        print(f"\n  {G}{modul.ad}{R}{'  ·  ' + sira if sira else ''}"
              f"  ·  ~{ders.sure} dk")
    print(f"\n  {Y}{ders.ozet}{R}")
    print(f"\n{G}{'─' * GENISLIK}{R}")

    for parca in ders.icerik.split("\n\n"):
        print()
        for satir in _sar(parca, GENISLIK - 4):
            print(f"  {satir}")

    if ders.ornek:
        alt_baslik("ÖRNEK")
        for parca in ders.ornek.split("\n\n"):
            for satir in _sar(parca, GENISLIK - 4):
                print(f"  {satir}")
            print()

    if ders.bist:
        alt_baslik("BIST / MİDAS ÖZELİ")
        for parca in ders.bist.split("\n\n"):
            print()
            for satir in _sar(parca, GENISLIK - 4):
                print(f"  {S}{satir}{R}")

    if ders.tuzak:
        alt_baslik("TUZAK")
        for parca in ders.tuzak.split("\n\n"):
            print()
            for satir in _sar(parca, GENISLIK - 4):
                print(f"  {K}{satir}{R}")
    print()


def mufredat_goster(moduller: list[dict], durum: dict) -> None:
    baslik(f"MÜFREDAT · {durum['unvan']} · %{durum['bilesik_yuzde']}")
    print(f"\n  {durum['ders']['okunan']}/{durum['ders']['toplam']} ders okundu"
          f"  ·  {durum['ders']['dakika_kalan']} dakika kaldı\n")
    for m in moduller:
        dolu = int(m["yuzde"] / 100 * 20)
        renk = S if m["bitti"] else (Y if m["okunan"] else G)
        sv = {1: "giriş", 2: "orta", 3: "ileri"}.get(m["seviye"], "")
        print(f"  {B}{m['kod']:4s}{R} {m['ad']:<32} "
              f"{renk}{'█' * dolu}{G}{'░' * (20 - dolu)}{R} "
              f"{m['okunan']:2d}/{m['toplam']:<2d} ~{m['dakika']:3d}dk  {G}{sv}{R}")
    print(f"\n  {G}Bir modülü görmek için:  python analist.py mufredat m4{R}")


# ═══════════════════════════════════════════════ günlük iş ve öğrenme

def gun_ozeti_goster(o: dict) -> None:
    baslik(f"GÜN ÖZETİ · {o.get('tarih','—')}")
    if o.get("hata"):
        print(f"\n  {K}{o['hata']}{R}")
        return

    e_deg = o.get("endeks_degisim")
    print(f"\n  {B}XU100{R}  {para(o.get('endeks', 0))}  "
          f"{yuzde_renk(e_deg) if e_deg is not None else '—'}")
    yuk, dus = o.get("yukselen", 0), o.get("dusen", 0)
    genislik = o.get("genislik", 0)
    dolu = int(genislik / 100 * 30)
    print(f"\n  Piyasa genişliği  {S}{'█' * dolu}{K}{'█' * (30 - dolu)}{R}  "
          f"{S}{yuk} yükselen{R} / {K}{dus} düşen{R} (%{genislik})")
    print(f"  Ortalama {yuzde_renk(o.get('ortalama_degisim', 0))} · "
          f"medyan {yuzde_renk(o.get('medyan_degisim', 0))}")

    if o.get("rejim"):
        r = o["rejim"]
        renk = S if "AÇIK" in r["ad"] else (K if "SAVUNMA" in r["ad"] else Y)
        print(f"\n  Rejim  {renk}{B}{r['ad']}{R} — {r['aciklama']}")
    if o.get("bist_reel_1y") is not None:
        print(f"  BIST 1 yıl REEL getiri: {yuzde_renk(o['bist_reel_1y'])}")

    alt_baslik("EN ÇOK HAREKET EDENLER")
    print(f"  {'':2}{'hisse':<8} {'dün':>10} {'bugün':>10} {'değişim':>9}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for x in o.get("en_cok_artan", [])[:5]:
        print(f"  {S}▲{R} {x['sembol']:<8} {x['onceki']:>10,.2f} "
              f"{x['kapanis']:>10,.2f} {yuzde_renk(x['degisim'], 2, 9)}")
    for x in o.get("en_cok_azalan", [])[:5]:
        print(f"  {K}▼{R} {x['sembol']:<8} {x['onceki']:>10,.2f} "
              f"{x['kapanis']:>10,.2f} {yuzde_renk(x['degisim'], 2, 9)}")

    if o.get("sinyal_veren"):
        alt_baslik("SİNYAL VERENLER")
        for s in o["sinyal_veren"]:
            al = f"{S}alınabilir{R}" if s.get("alinabilir") else f"{G}alınamıyor{R}"
            print(f"  {B}{s['sembol']:<8}{R} skor {skor_renk(s['skor'])} "
                  f"· {M}{','.join(s['sinyaller'])}{R} · {s['fiyat']:,.2f} ₺ · {al}")

    if o.get("sektor_lider"):
        alt_baslik("SEKTÖR")
        print(f"  {S}lider{R}     " + " · ".join(
            f"{x['sektor']} ({x['gg60']:+.1f})" for x in o["sektor_lider"]))
        print(f"  {K}geciken{R}   " + " · ".join(
            f"{x['sektor']} ({x['gg60']:+.1f})" for x in o.get("sektor_geciken", [])))

    if o.get("haberli_hisseler"):
        alt_baslik("HABERİ OLAN HİSSELER")
        for k, v in o["haberli_hisseler"].items():
            print(f"  {B}{k}{R}  {v[0][:74]}")
        print(f"\n  {G}Not: Türkçe finans beslemeleri genel ekonomi yayınlar; "
              f"çoğu gün çoğu hisse için haber çıkmaz.{R}")


def degisim_goster(r: dict) -> None:
    if r.get("hata"):
        print(f"  {K}{r['sembol']}: {r['hata']}{R}")
        return
    baslik(f"{r['sembol']} · GÜNLÜK SEYİR")
    print(f"\n  {'tarih':<12} {'kapanış':>10} {'önceki':>10} {'değişim':>9} "
          f"{'RSI':>6} {'skor':>6}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for g in r["gunler"]:
        print(f"  {g['tarih']:<12} {g['kapanis']:>10,.2f} "
              f"{(g['onceki'] or 0):>10,.2f} {yuzde_renk(g['degisim'], 2, 9)} "
              f"{(g['rsi'] or 0):>6.1f} {(g['skor'] or 0):>6.1f}")
    if r.get("donem_getiri") is not None:
        print(f"\n  Dönem getirisi: {yuzde_renk(r['donem_getiri'])}")
    if r.get("haberler"):
        alt_baslik(f"HABERLER ({len(r['haberler'])})")
        for h in r["haberler"][:6]:
            print(f"  {G}{h['tarih']}{R} [{h['kaynak']}] {h['baslik'][:70]}")


def karne_goster(k: dict, kayma: list, filtre: dict,
                 kapsam: dict | None = None, uyarilar: list | None = None) -> None:
    baslik("SİSTEMİN KENDİ SİCİLİ")
    print(f"\n  {G}Bu, backtest DEĞİL. Sistemin canlıda ürettiği sinyallerin")
    print(f"  gerçekte ne yaptığı. Backtest geçmişe uydurulmuş olabilir;")
    print(f"  canlı sicil uydurulamaz.{R}")
    if kapsam and kapsam.get("sinyal"):
        renk = S if kapsam["ay"] >= 12 else Y
        print(f"\n  Kapsam: {kapsam['ilk']} → {kapsam['son']}  "
              f"({renk}{kapsam['ay']} ay{R}, {kapsam['sinyal']:,} sinyal)")
        if kapsam["ay"] < 12:
            print(f"  {Y}Bu süre tek bir piyasa rejimini kapsıyor olabilir — "
                  f"yorumu buna göre yap.{R}")

    alt_baslik("VADELERE GÖRE — stop ve hedef uygulanmış (kural bazlı)")
    print(f"  {'vade':<8} {'sinyal':>7} {'kazanma':>9} {'ort. getiri':>12} "
          f"{'ort. kazanç':>12} {'ort. kayıp':>11}")
    print(G + "  " + "─" * (GENISLIK - 2) + R)
    for gun, v in k.get("vadeler", {}).items():
        if not v.get("sinyal"):
            print(f"  {gun:>2} gün   {0:>7} {G}henüz sonuçlanmış sinyal yok{R}")
            continue
        print(f"  {gun:>2} gün   {v['sinyal']:>7} {v['kazanma_orani']:>8.1f}% "
              f"{yuzde_renk(v['ortalama_getiri'], 2, 12)} "
              f"{yuzde_renk(v['ort_kazanc'], 2, 12)} "
              f"{yuzde_renk(v['ort_kayip'], 2, 11)}")
        ham = v.get("ham") or {}
        if ham:
            print(f"  {G}         (stop'suz N gün tutulsaydı: kazanma "
                  f"%{ham['kazanma_orani']}, ortalama {ham['ortalama_getiri']:+.2f}%){R}")
        d = v.get("cikis_dagilimi") or {}
        if d:
            print(f"  {G}         çıkış: " + " · ".join(
                f"{a} {n}" for a, n in sorted(d.items(), key=lambda x: -x[1])) + R)

    if k.get("stratejiler"):
        alt_baslik("STRATEJİYE GÖRE (20 günlük vade)")
        for st, v in k["stratejiler"].items():
            print(f"  {B}{st:<10}{R} {v['sinyal']:>4} sinyal · "
                  f"kazanma %{v['kazanma_orani']} · "
                  f"ortalama {yuzde_renk(v['ortalama_getiri'])}")

    alt_baslik("CANLI vs BACKTEST — kenar aşınıyor mu?")
    for x in kayma:
        if not x["yeterli_mi"]:
            print(f"  {B}{x['strateji']:<10}{R} {G}{x['not']}{R}")
            continue
        renk = S if "İYİ" in x["durum"] else (K if "KÖTÜ" in x["durum"] else Y)
        print(f"  {B}{x['strateji']:<10}{R} canlı kazanma %{x['canli']['kazanma_orani']} "
              f"vs backtest %{x['backtest']['kazanma_orani']}  "
              f"({x['kazanma_farki']:+.1f} puan)  {renk}{x['durum']}{R}")

    if uyarilar:
        alt_baslik("BU KIYASI OKURKEN")
        for u in uyarilar:
            for i, satir in enumerate(_sar(u, GENISLIK - 6)):
                print(f"  {G}{'· ' if i == 0 else '  '}{satir}{R}")

    alt_baslik("FİLTRELER İŞ GÖRÜYOR MU?")
    if not filtre.get("yeterli_mi"):
        print(f"  {G}{filtre['not']}{R}")
    else:
        for ad, anahtar in [("SMA200 üstü", "sma200_ustu"), ("SMA200 altı", "sma200_alti"),
                            ("Alınabilir", "alinabilir"), ("Alınamaz", "alinamaz")]:
            v = filtre.get(anahtar)
            if v:
                print(f"  {ad:<14} {v['n']:>4} sinyal · ortalama "
                      f"{yuzde_renk(v['ortalama'])} · kazanma %{v['kazanma']}")
        print(f"\n  {G}{filtre['not']}{R}")
