"""Sinyale yakınlık — "bugün değil ama yakın" durumunu ölçer.

NEDEN VAR: sistem her gün ya "AL" diyordu ya susuyordu. Arada koca bir
alan var ve kullanıcı orada yaşıyor: "bu hisse tutuyor mu", "bu hafta
olur mu", "neden bugün değil".

Bu modül her hisse için stratejilerin giriş koşullarını TEK TEK ölçüp
hangisinin karşılandığını, hangisinin ne kadar uzakta olduğunu söylüyor.
Tahmin yok: yalnızca "şu koşul şu kadar uzakta" diyor.

KOŞULLAR TEK YERDE: aşağıdaki tanımlar `strateji.py`deki giriş
fonksiyonlarının aynısı olmak zorunda. İki yerde yazılırsa biri
sessizce kayar ve ekran "yaklaşıyor" derken sinyal hiç gelmez (ya da
tersi). testler/test_yakinlik.py bu iki tanımın GERÇEK VERİDE aynı
sonucu verdiğini doğruluyor.

YAKIN NE DEMEK: tek bir koşul eksik ve o da eşiğine yakınsa. İki koşul
eksikse "yaklaşıyor" demek kullanıcıyı boşuna beklettirir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Sinyalin gerçekleşmesi için tek koşul kalmışsa ve uzaklık bu oranın
# altındaysa "yakın" sayılır. %3: bir hisse tipik olarak birkaç günde
# bu kadar yol alır — daha geniş bir eşik "yakın" kelimesini anlamsız
# yapardı.
YAKIN_ESIK = 3.0


def _oran_uzaklik(deger: float, hedef: float) -> float:
    """`deger`in `hedef`e yüzde kaç uzakta olduğu (yukarı yönlü)."""
    if not np.isfinite(deger) or not np.isfinite(hedef) or deger <= 0:
        return float("inf")
    return (hedef / deger - 1) * 100


def yakin_orani(deger: float, hedef: float) -> bool:
    """Fiyat koşulları için: eşiğe YAKIN_ESIK'ten daha yakın mı.

    Yön önemsiz — kimi koşul yükselmeyi, kimi gerilemeyi ister.
    """
    u = _oran_uzaklik(deger, hedef)
    return bool(np.isfinite(u) and abs(u) <= YAKIN_ESIK)


def _kosullar(s: pd.Series, onceki_kapanis: float) -> dict[str, list[dict]]:
    """Her stratejinin koşulları, karşılandı bilgisiyle birlikte.

    Her koşul: {ad, saglandi, aciklama, uzaklik_yuzde}
    `uzaklik_yuzde` yalnızca ÖLÇÜLEBİLİR uzaklıklarda dolu; ikili
    koşullarda (SMA200 üstünde mi) None.
    """
    def g(ad, vars=np.nan):
        v = s.get(ad, vars)
        return float(v) if v is not None and np.isfinite(v) else np.nan

    kapanis = g("Close")
    don_ust, hacim = g("DON_ust"), g("Hacim_orani")
    sma200, adx = g("SMA200"), g("ADX14")
    ema20, ema50 = g("EMA20"), g("EMA50")
    acilis, rsi2, bb = g("Open"), g("RSI2"), g("BB_konum")
    dusuk3 = g("_dusuk3", np.nan)

    return {
        "kirilim": [
            {"ad": "20 günlük zirve kırılımı",
             "saglandi": bool(kapanis > don_ust),
             "aciklama": f"zirve {don_ust:.2f} ₺",
             "yakin_mi": yakin_orani(kapanis, don_ust),
             "uzaklik_yuzde": round(_oran_uzaklik(kapanis, don_ust), 2)
                              if kapanis <= don_ust else 0.0},
            {"ad": "hacim teyidi",
             "saglandi": bool(hacim > 1.4),
             "aciklama": f"hacim {hacim:.2f}× (1,40 gerekiyor)",
             "yakin_mi": bool(np.isfinite(hacim) and hacim >= 1.26),
             "uzaklik_yuzde": None},
            {"ad": "uzun vadeli trend",
             "saglandi": bool(kapanis > sma200),
             "aciklama": f"SMA200 {sma200:.2f} ₺",
             "yakin_mi": yakin_orani(kapanis, sma200),
             "uzaklik_yuzde": round(_oran_uzaklik(kapanis, sma200), 2)
                              if kapanis <= sma200 else 0.0},
            {"ad": "trend gücü",
             "saglandi": bool(adx > 20),
             "aciklama": f"ADX {adx:.1f} (20 gerekiyor)",
             "yakin_mi": bool(np.isfinite(adx) and adx >= 17),
             "uzaklik_yuzde": None},
        ],
        "trend": [
            {"ad": "yükselen trend",
             "saglandi": bool(kapanis > sma200 and ema20 > ema50),
             "aciklama": f"SMA200 {sma200:.2f} · EMA20/50 "
                         f"{ema20:.2f}/{ema50:.2f}",
             "yakin_mi": bool(yakin_orani(kapanis, sma200)
                              and np.isfinite(ema20) and np.isfinite(ema50)
                              and ema20 >= ema50 * 0.99),
             "uzaklik_yuzde": None},
            {"ad": "EMA20'ye geri çekilme",
             "saglandi": bool(np.isfinite(dusuk3) and dusuk3 <= ema20 * 1.01),
             "aciklama": f"EMA20 {ema20:.2f} ₺",
             "yakin_mi": yakin_orani(dusuk3, ema20 * 1.01),
             # Bu koşul fiyatın DÜŞMESİNİ istiyor, o yüzden uzaklık
             # negatif çıkar. Ölçülebilir olması önemli: uzaklık
             # yazılmazsa EMA20'nin %40 üstündeki hisse de "yakın"
             # sayılırdı (28 Ağustos 2026'da tam bunu yapıyordu).
             "uzaklik_yuzde": round(
                 _oran_uzaklik(dusuk3, ema20 * 1.01), 2)},
            {"ad": "toparlanma (yükselen mum, EMA20 üstü)",
             "saglandi": bool(kapanis > acilis and kapanis > ema20),
             "aciklama": "gün yükselen kapanmalı ve EMA20 üstünde olmalı",
             "yakin_mi": True,
             "uzaklik_yuzde": None},
            {"ad": "trend gücü",
             "saglandi": bool(adx > 18),
             "aciklama": f"ADX {adx:.1f} (18 gerekiyor)",
             "yakin_mi": bool(np.isfinite(adx) and adx >= 15),
             "uzaklik_yuzde": None},
        ],
        "tepki": [
            {"ad": "uzun vadeli trend",
             "saglandi": bool(kapanis > sma200),
             "aciklama": f"SMA200 {sma200:.2f} ₺",
             "yakin_mi": yakin_orani(kapanis, sma200),
             "uzaklik_yuzde": round(_oran_uzaklik(kapanis, sma200), 2)
                              if kapanis <= sma200 else 0.0},
            {"ad": "aşırı satım (RSI2)",
             "saglandi": bool(rsi2 < 10),
             "aciklama": f"RSI2 {rsi2:.1f} (10 altı gerekiyor)",
             "yakin_mi": bool(np.isfinite(rsi2) and rsi2 <= 25),
             "uzaklik_yuzde": None},
            {"ad": "Bollinger alt bölge",
             "saglandi": bool(bb < 0.20),
             "aciklama": f"BB konum {bb:.2f} (0,20 altı gerekiyor)",
             "yakin_mi": bool(np.isfinite(bb) and bb <= 0.32),
             "uzaklik_yuzde": None},
            {"ad": "panik çöküşü değil",
             "saglandi": bool(onceki_kapanis <= 0
                              or kapanis > onceki_kapanis * 0.90),
             "aciklama": "önceki güne göre %10'dan fazla düşmemeli",
             "yakin_mi": True,
             "uzaklik_yuzde": None},
        ],
    }


def olc(g: pd.DataFrame, i: int = -1) -> dict:
    """Bir hissenin her stratejiye yakınlığı.

    Döner: {strateji: {karsilanan, toplam, eksikler, sinyal, yakin,
                       en_yakin_eksik}}
    """
    if g is None or len(g) < 2:
        return {}

    # İNDEKSİ ÖNCE NORMALLEŞTİR. Negatif i ile dilim almak sessizce
    # yanlış pencere üretiyordu: i=-60 için max(0, i-2) sıfır oluyor ve
    # "son 3 gün" yerine BAŞTAN 341 günün en düşüğü alınıyordu. O da
    # doğal olarak eşiğin altında kaldığı için koşul hep sağlanmış
    # görünüyor, yakınlık sinyal var sanıyordu.
    n = len(g)
    poz = i if i >= 0 else n + i
    if poz < 1 or poz >= n:
        return {}

    s = g.iloc[poz].copy()
    onceki = float(g["Close"].iloc[poz - 1])

    # trend stratejisi son 3 günün en düşüğüne bakıyor; satıra
    # iliştiriliyor ki koşul tanımı tek yerde kalsın.
    try:
        s["_dusuk3"] = float(g["Low"].iloc[max(0, poz - 2): poz + 1].min())
    except Exception:
        s["_dusuk3"] = np.nan

    cikti = {}
    for ad, kosullar in _kosullar(s, onceki).items():
        eksik = [k for k in kosullar if not k["saglandi"]]
        sinyal = not eksik
        yakin = False
        en_yakin = None
        if len(eksik) == 1:
            en_yakin = eksik[0]
            # Kararı koşulun KENDİSİ verir: RSI'ın 10'a uzaklığını
            # yüzdeyle ölçmek anlamsız, hacmin 1,40'a uzaklığını da.
            # Her koşul kendi biriminde "bir-iki günde kapanır mı"
            # sorusunu cevaplıyor (bkz. _kosullar).
            yakin = bool(en_yakin.get("yakin_mi", False))
        cikti[ad] = {
            "karsilanan": len(kosullar) - len(eksik),
            "toplam": len(kosullar),
            "sinyal": sinyal,
            "yakin": yakin,
            "eksikler": eksik,
            "en_yakin_eksik": en_yakin,
        }
    return cikti


def ozet(g: pd.DataFrame, i: int = -1) -> dict | None:
    """Kullanıcıya gösterilecek tek satırlık yakınlık özeti.

    En ileri durumdaki stratejiyi seçer: önce sinyal, sonra yakın, sonra
    en çok koşul karşılayan.
    """
    d = olc(g, i)
    if not d:
        return None
    sirali = sorted(d.items(),
                    key=lambda x: (x[1]["sinyal"], x[1]["yakin"],
                                   x[1]["karsilanan"]), reverse=True)
    ad, v = sirali[0]
    return {"strateji": ad, "mesaj": _mesaj(ad, v), **v}


def _mesaj(ad: str, v: dict) -> str:
    """Tek satırlık insan cümlesi. Arayüzler bunu olduğu gibi basar."""
    if v["sinyal"]:
        return f"{ad} sinyali verdi"
    eksik = v.get("en_yakin_eksik")
    if not eksik:
        return f"{ad}: {v['karsilanan']}/{v['toplam']} koşul"
    u = eksik.get("uzaklik_yuzde")
    if u is not None and np.isfinite(u):
        yon = "yükselmesi" if u > 0 else "gerilemesi"
        nokta = f"%{abs(u):.1f} {yon} gerekiyor".replace(".", ",")
        return f"{eksik['ad']} için {nokta} ({eksik['aciklama']})"
    return f"tek eksik: {eksik['ad']} — {eksik['aciklama']}"
