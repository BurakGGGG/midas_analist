"""Derslerin görselleri — CANLI veriden.

NEDEN CANLI: ders kitabındaki uydurma grafik, öğrenilen şeyin gerçek
piyasada nasıl göründüğünü göstermez. "RSI 70 üstü sat" ezberinin neden
yanlış olduğunu, gerçek bir BIST hissesinin gerçek RSI'sinde görmek,
çizilmiş bir örnekten farklıdır.

Her görsel `{tur, baslik, aciklama, ...veri}` döndürür. Veri gelmezse
`{"yok": True}` döner ve ekran görseli hiç göstermez — boş bir kutu
göstermek, görsel olmamasından kötüdür.

Ders → görsel eşlemesi DERS_GORSEL'de. Bir dersin görseli olmak zorunda
değil; çoğu ders metinle daha iyi anlatılır.
"""
from __future__ import annotations

import numpy as np

# Hangi ders hangi görseli gösterir. Ders içeriğine BAKILARAK seçildi —
# her derse grafik koymak gürültü olur, grafiğin anlattığı bir şey olmalı.
DERS_GORSEL: dict[str, str] = {
    "d601": "nominal_reel",      # Enflasyon: nominal ile reelin farkı
    "d603": "nominal_reel",      # Kur: kim kazanır kim kaybeder
    "d701": "fiyat_sma",         # Trendin gerçek tanımı
    "d703": "fiyat_sma",         # Hareketli ortalamalar
    "d704": "rsi",               # Momentum göstergeleri
    "d705": "oynaklik",          # Oynaklık: ATR ve Bollinger
    "d801": "kayip_asimetrisi",  # Kayıp asimetrisi
    "d804": "korelasyon",        # Çeşitlendirme ve korelasyon
    "d1202": "sicil_aylik",      # Strateji geliştirme ve backtest
    "d1203": "sicil_aylik",      # Karar günlüğü ve kendi karnen
    # m13 — grafik okuma. Bunlar ŞEMA: kavramı canlı verinin gürültüsü
    # içinde değil, temiz bir çizimde gösterir. Destek nedir sorusunun
    # cevabı gerçek bir grafikte kaybolur, zikzakta iki etiketle anlaşılır.
    "d1301": "sema:zaman_dilimi",
    "d1302": "sema:mum_anatomisi",
    "d1303": "sema:destek_direnc",
    "d1304": "sema:trend_cizgisi",
    "d1305": "sema:bosluk",
    "d1306": "sema:mum_formasyonlari",
    "d1307": "sema:zaman_dilimi",
    "d1308": "sema:retest",
    "d1309": "sema:mum_sozlugu",
    "d1310": "sema:formasyon_sicili",
    "d1311": "sema:zaman_serisi",
}


def _seri(x, azami: int = 120) -> list[dict]:
    """Mobil grafik bileşenlerinin beklediği biçim: [{"t":..., "d":...}].

    Seyreltme bilinçli: telefon ekranında 500 nokta zaten birkaç piksele
    düşer, ama yükü beş katına çıkarır. api/donusum.seri_noktalari ile
    aynı sözleşme — iki farklı biçim olursa grafik bileşeni ikisini de
    bilmek zorunda kalır.
    """
    try:
        import pandas as pd
        if isinstance(x, pd.Series):
            x = x.dropna()
            adim = max(1, len(x) // azami)
            return [{"t": (i.strftime("%Y-%m-%d")
                           if hasattr(i, "strftime") else str(i)),
                     "d": float(v)}
                    for i, v in x.iloc[::adim].items()
                    if v is not None and np.isfinite(float(v))]
    except Exception:
        pass
    ham = [float(v) for v in x if v is not None and np.isfinite(float(v))]
    adim = max(1, len(ham) // azami)
    return [{"t": str(i), "d": v} for i, v in enumerate(ham[::adim])]


# ── görseller ──────────────────────────────────────────────────────────────

def nominal_reel(gun: int = 500) -> dict:
    """XU100'ün TL ve dolar bazlı seyri, ikisi de 100'e endekslenmiş.

    Bu grafik tek bir şeyi gösterir ve çok net gösterir: TL bazında
    yükselen endeks, dolar bazında düşüyor olabilir. Nominal getiriyi
    enflasyondan arındırmadan 'kazandım' demek buradan görülür.
    """
    from . import veri, evren
    xu = veri.fiyat_cek(evren.ENDEKS, gun=gun, onbellek_saat=12.0)
    usd = veri.fiyat_cek("TRY=X", gun=gun, onbellek_saat=12.0)
    if xu is None or xu.empty or usd is None or usd.empty:
        return {"yok": True}
    k = xu["Close"]
    u = usd["Close"].reindex(k.index).ffill().bfill()
    dolar = k / u
    if len(k) < 20:
        return {"yok": True}
    tl100 = (k / k.iloc[0] * 100)
    usd100 = (dolar / dolar.iloc[0] * 100)
    return {
        "tur": "cift_seri",
        "baslik": "BIST 100: TL bazında vs dolar bazında",
        "aciklama": ("İkisi de başlangıçta 100. Aradaki makas, enflasyonun "
                     "nominal getiriyi nasıl şişirdiğini gösterir."),
        "seri1": {"ad": "TL bazında", "veri": _seri(tl100)},
        "seri2": {"ad": "Dolar bazında", "veri": _seri(usd100)},
        "sonuc": (f"Dönem sonunda TL bazında {tl100.iloc[-1]:.0f}, "
                  f"dolar bazında {usd100.iloc[-1]:.0f}."),
    }


def fiyat_sma(sembol: str | None = None, gun: int = 300) -> dict:
    """Gerçek bir hissenin fiyatı + EMA20 + SMA200."""
    from . import veri, evren, gostergeler
    sembol = sembol or evren.evren_getir("bist100")[0]
    df = veri.fiyat_cek(sembol, gun=gun, onbellek_saat=12.0)
    if df is None or len(df) < 210:
        return {"yok": True}
    g = gostergeler.gosterge_seti(df, None)
    son = g.iloc[-1]
    ustunde = bool(son["Close"] > son["SMA200"])
    return {
        "tur": "fiyat",
        "baslik": f"{sembol.replace('.IS', '')} — fiyat, EMA20 ve SMA200",
        "aciklama": ("Trend tanımı fiyatın SMA200'e göre konumuyla başlar. "
                     "EMA20 kısa vadeli, SMA200 uzun vadeli hafızadır."),
        "kapanis": _seri(g["Close"]),
        "ema20": _seri(g["EMA20"]),
        "sma200": _seri(g["SMA200"]),
        "sonuc": (f"Şu an fiyat SMA200'ün {'ÜSTÜNDE' if ustunde else 'ALTINDA'} "
                  f"— sistem yalnızca üstündekilere trend sinyali arar."),
    }


def rsi(sembol: str | None = None, gun: int = 300) -> dict:
    """Gerçek RSI — 'RSI 70 üstü sat' ezberinin neden yanlış olduğu."""
    from . import veri, evren, gostergeler
    sembol = sembol or evren.evren_getir("bist100")[0]
    df = veri.fiyat_cek(sembol, gun=gun, onbellek_saat=12.0)
    if df is None or len(df) < 60:
        return {"yok": True}
    g = gostergeler.gosterge_seti(df, None)
    r = g["RSI14"].dropna()
    if len(r) < 20:
        return {"yok": True}
    ust = int((r > 70).sum())
    # RSI 70'i aştıktan sonraki 20 günde fiyat ne yapmış?
    sonraki = []
    kapanis = g["Close"]
    for i in range(len(g) - 21):
        if np.isfinite(g["RSI14"].iloc[i]) and g["RSI14"].iloc[i] > 70:
            a, b = float(kapanis.iloc[i]), float(kapanis.iloc[i + 20])
            if a > 0:
                sonraki.append((b / a - 1) * 100)
    ort = float(np.mean(sonraki)) if sonraki else None
    return {
        "tur": "rsi",
        "baslik": f"{sembol.replace('.IS', '')} — RSI(14)",
        "aciklama": ("30 ve 70 çizgileri 'aşırı satım/alım' diye anlatılır. "
                     "Trendli piyasada RSI 70'in üstünde haftalarca kalır."),
        "rsi": _seri(r.tail(180)),
        "sonuc": (f"Bu hissede RSI son dönemde {ust} gün 70'in üstünde kaldı."
                  + (f" RSI 70'i aştıktan sonraki 20 günde ortalama getiri "
                     f"%{ort:+.1f} — 'aşırı alım' satış sinyali değil."
                     if ort is not None else "")),
    }


def oynaklik(sembol: str | None = None, gun: int = 300) -> dict:
    """ATR yüzdesi: aynı pozisyon boyutu, farklı oynaklıkta farklı risktir."""
    from . import veri, evren, gostergeler
    sembol = sembol or evren.evren_getir("bist100")[0]
    df = veri.fiyat_cek(sembol, gun=gun, onbellek_saat=12.0)
    if df is None or len(df) < 60:
        return {"yok": True}
    g = gostergeler.gosterge_seti(df, None)
    a = g["ATR_yuzde"].dropna()
    if len(a) < 20:
        return {"yok": True}
    son, ortalama = float(a.iloc[-1]), float(a.mean())
    return {
        "tur": "tek_seri",
        "baslik": f"{sembol.replace('.IS', '')} — günlük oynaklık (ATR %)",
        "aciklama": ("ATR, hissenin bir günde tipik olarak kaç yüzde "
                     "oynadığını söyler. Stop mesafesi buna göre kurulur."),
        "seri": _seri(a.tail(180)),
        "sonuc": (f"Şu an %{son:.1f}, dönem ortalaması %{ortalama:.1f}. "
                  f"Oynaklık iki katına çıkarsa aynı stop mesafesi yarı "
                  f"kadar koruma sağlar."),
    }


def kayip_asimetrisi() -> dict:
    """%50 kaybeden, başa dönmek için %100 kazanmak zorundadır.

    Veri gerektirmez — saf matematik. Ama bu grafiği bir kez gören,
    stop kullanmayı bir daha tartışmaz.
    """
    kayiplar = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    gerekli = [round(k / (100 - k) * 100, 1) for k in kayiplar]
    return {
        "tur": "cubuk",
        "baslik": "Kaybı telafi etmek için gereken kazanç",
        "aciklama": ("Kayıp ve kazanç simetrik değildir. Kayıp büyüdükçe "
                     "telafi için gereken kazanç çok daha hızlı büyür."),
        "etiketler": [f"-%{k}" for k in kayiplar],
        "degerler": gerekli,
        "sonuc": ("%50 kaybeden başa dönmek için %100 kazanmak zorundadır. "
                  "Stop'un tek işi bu eğrinin sağ tarafına hiç geçmemektir."),
    }


def korelasyon(gun: int = 120) -> dict:
    """Bugünün sinyalleri gerçekten farklı bahisler mi?"""
    from . import veri, evren, gostergeler, istatistik
    from .strateji import Filtreler, STRATEJILER, filtre_maskesi
    semboller = evren.evren_getir("bist100")
    ham = veri.toplu_cek(semboller, gun=260, onbellek_saat=12.0, sessiz=True)
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=260, onbellek_saat=12.0)
    ek = endeks["Close"] if endeks is not None and not endeks.empty else None
    sinyalli = []
    for sem, df in ham.items():
        if df is None or len(df) < 230:
            continue
        try:
            g = gostergeler.gosterge_seti(df, ek)
            uygun = filtre_maskesi(g, Filtreler())
            if any(st.giris(g).fillna(False).iloc[-1] and bool(uygun.iloc[-1])
                   for st in STRATEJILER.values()):
                sinyalli.append(sem)
        except Exception:
            continue
    if len(sinyalli) < 2:
        # Sinyal yoksa evrenden örnek göster — ders yine anlatılabilsin
        sinyalli = semboller[:6]
    fiyatlar = {s: ham[s] for s in sinyalli if s in ham}
    k = istatistik.korelasyon(fiyatlar, gun=gun)
    if k.empty or len(k) < 2:
        return {"yok": True}
    m = k.to_numpy(dtype=float)
    ust = m[np.triu_indices_from(m, k=1)]
    ust = ust[np.isfinite(ust)]
    ort = float(np.mean(ust))
    n_etkin = istatistik.bagimsiz_bahis_sayisi(ort, len(k))
    ciftler = []
    idx = np.triu_indices_from(m, k=1)
    for a, b, v in zip(idx[0], idx[1], m[idx]):
        if np.isfinite(v):
            ciftler.append((f"{k.index[a]}".replace(".IS", "") + " / " +
                            f"{k.columns[b]}".replace(".IS", ""), round(float(v), 2)))
    ciftler.sort(key=lambda x: -x[1])
    ciftler = ciftler[:8]
    return {
        "tur": "cubuk",
        "baslik": "Hisse çiftleri arasında korelasyon",
        "aciklama": ("1'e yakın korelasyon, iki hissenin aynı yöne gitmesi "
                     "demektir. İkisini birden almak çeşitlendirme değildir."),
        "etiketler": [a for a, _ in ciftler],
        "degerler": [v for _, v in ciftler],
        "sonuc": (f"{len(k)} hisse ≈ {n_etkin:.1f} bağımsız bahis "
                  f"(ortalama korelasyon {ort:.2f})."),
    }


def sicil_aylik() -> dict:
    """Sistemin kendi aylık kazanma oranı — backtest değil, canlı."""
    from . import ambar
    from .ogrenme import BACKTEST_AYLIK
    ambar.kur()
    with ambar.baglan() as con:
        satirlar = con.execute("""
            SELECT substr(s.tarih, 1, 7) ay,
                   AVG(CASE WHEN r.kural_getiri > 0 THEN 1.0 ELSE 0 END)*100 kaz,
                   COUNT(*) n
            FROM sinyal s JOIN sinyal_sonuc r ON r.sinyal_id = s.id
            WHERE r.gun = 20 AND r.kural_getiri IS NOT NULL
            GROUP BY 1 HAVING n >= 5 ORDER BY 1""").fetchall()
    if len(satirlar) < 2:
        return {"yok": True}
    aylar = [r["ay"] for r in satirlar]
    oranlar = [round(float(r["kaz"]), 1) for r in satirlar]
    tarihsel = [v for seri in BACKTEST_AYLIK.values() for v in seri]
    ort_tarihsel = round(float(np.mean(tarihsel)), 1) if tarihsel else None
    return {
        "tur": "cubuk",
        "baslik": "Sistemin aylık kazanma oranı (canlı)",
        "aciklama": ("Aynı ayın sinyalleri aynı kaderi paylaşır. Bu yüzden "
                     "aylık oran savrulur — ve tek bir ayın sonucundan "
                     "strateji hakkında hüküm çıkmaz."),
        "etiketler": aylar,
        "degerler": oranlar,
        "referans": ort_tarihsel,
        "sonuc": (f"{len(aylar)} ay: en düşük %{min(oranlar)}, en yüksek "
                  f"%{max(oranlar)}. Tarihsel ortalama %{ort_tarihsel}."),
    }


URETICILER = {
    "nominal_reel": nominal_reel,
    "fiyat_sma": fiyat_sma,
    "rsi": rsi,
    "oynaklik": oynaklik,
    "kayip_asimetrisi": kayip_asimetrisi,
    "korelasyon": korelasyon,
    "sicil_aylik": sicil_aylik,
}


def ders_gorseli(kod: str) -> dict:
    """Bir dersin görselini üretir. Görseli yoksa ya da veri gelmezse
    {"yok": True} — ekran boş kutu göstermez.

    "sema:" önekli olanlar öğretici çizimdir (canlı veri kullanmaz);
    gerisi canlı veriden üretilir.
    """
    tur = DERS_GORSEL.get(kod)
    if not tur:
        return {"yok": True}
    if tur.startswith("sema:"):
        from .egitmen_sema import sema_getir
        return sema_getir(tur.split(":", 1)[1])
    uretici = URETICILER.get(tur)
    if not uretici:
        return {"yok": True}
    try:
        return uretici()
    except Exception as e:
        return {"yok": True, "hata": str(e)[:120]}
