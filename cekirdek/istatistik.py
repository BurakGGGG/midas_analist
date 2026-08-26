"""Yatırım matematiği: sezginin yanıldığı yerler.

Buradaki hesaplar 'hangi hisse' sorusuna cevap vermez. Daha önemli bir soruya
cevap verir: bu sistemle oynamaya devam edersem uzun vadede ne olur?
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────── beklenen değer

def beklenen_deger(kazanma_orani: float, ort_kazanc: float,
                   ort_kayip: float) -> dict:
    """Bir stratejinin işlem başına matematiksel beklentisi.

    kazanma_orani: 0-1 arası. ort_kazanc/ort_kayip: pozitif yüzdeler.

    Kritik sezgi: yüksek kazanma oranı iyi strateji DEMEK DEĞİLDİR.
    %90 kazanıp %1 kâr alan, %10 kaybedip %15 zarar eden strateji zarardadır.
    """
    p, k, z = kazanma_orani, abs(ort_kazanc), abs(ort_kayip)
    bd = p * k - (1 - p) * z
    odul_risk = k / z if z else np.nan
    basabas_oran = z / (k + z) * 100 if (k + z) else np.nan
    return {
        "beklenen_deger_yuzde": round(bd, 3),
        "odul_risk": round(odul_risk, 2) if np.isfinite(odul_risk) else None,
        "basabas_kazanma_orani": round(basabas_oran, 1) if np.isfinite(basabas_oran) else None,
        "karli_mi": bd > 0,
        "yorum": (
            f"İşlem başına beklenti %{bd:+.3f}. "
            f"Bu ödül/risk oranıyla (1:{odul_risk:.2f}) başabaş için "
            f"%{basabas_oran:.1f} kazanma oranı yeterli; sen %{p*100:.1f} yapıyorsun."
        ) if np.isfinite(odul_risk) and np.isfinite(basabas_oran) else "",
    }


def kelly(kazanma_orani: float, ort_kazanc: float, ort_kayip: float,
          kesir: float = 0.25) -> dict:
    """Kelly kriteri: teorik optimum pozisyon büyüklüğü.

    UYARI: Tam Kelly matematiksel olarak optimaldir ama dayanılmaz derecede
    oynaktır — %50 düşüşler normaldir. Profesyoneller çeyrek Kelly kullanır.
    """
    p, k, z = kazanma_orani, abs(ort_kazanc), abs(ort_kayip)
    if z <= 0 or not 0 < p < 1:
        return {"hata": "geçersiz girdi"}
    b = k / z
    tam = (p * (b + 1) - 1) / b
    tam = max(0.0, min(tam, 1.0))
    return {
        "tam_kelly_yuzde": round(tam * 100, 2),
        "onerilen_yuzde": round(tam * kesir * 100, 2),
        "kesir": kesir,
        "yorum": (f"Tam Kelly sermayenin %{tam*100:.1f}'ini söyler — bu kadarını "
                  f"koyma. {kesir:.0%} Kelly ile %{tam*kesir*100:.1f} makul."
                  if tam > 0 else
                  "Kelly sıfır veya negatif: bu stratejinin pozitif beklentisi yok, "
                  "pozisyon açma."),
    }


def batma_riski(risk_yuzde: float, kazanma_orani: float, odul_risk: float,
                islem: int = 200, deneme: int = 4000,
                batma_esigi: float = 0.5, tohum: int = 42) -> dict:
    """Monte Carlo: bu risk seviyesiyle sermayenin yarısını kaybetme olasılığı.

    'Üst üste 10 kayıp gelmez' diye düşünülür. 200 işlemde %50 kazanma
    oranıyla 10'lu kayıp serisi neredeyse KESİNDİR.
    """
    rng = np.random.default_rng(tohum)
    r = risk_yuzde / 100
    kazanc = r * odul_risk
    sonuclar = np.ones(deneme)
    batan = 0
    en_uzun_kayip = 0

    for i in range(deneme):
        sermaye, dip = 1.0, 1.0
        seri = rng.random(islem) < kazanma_orani
        kayip_serisi = uzun = 0
        for kazandi in seri:
            sermaye *= (1 + kazanc) if kazandi else (1 - r)
            dip = min(dip, sermaye)
            kayip_serisi = 0 if kazandi else kayip_serisi + 1
            uzun = max(uzun, kayip_serisi)
        sonuclar[i] = sermaye
        en_uzun_kayip = max(en_uzun_kayip, uzun)
        if dip <= batma_esigi:
            batan += 1

    medyan = float(np.median(sonuclar))
    return {
        "batma_olasiligi_yuzde": round(batan / deneme * 100, 1),
        "medyan_sonuc": round(medyan, 3),
        "kotu_senaryo_5": round(float(np.percentile(sonuclar, 5)), 3),
        "iyi_senaryo_95": round(float(np.percentile(sonuclar, 95)), 3),
        "en_uzun_kayip_serisi": int(en_uzun_kayip),
        "zarar_eden_deneme_yuzde": round(float((sonuclar < 1).mean() * 100), 1),
        "yorum": (
            f"{islem} işlemde sermayenin yarısını kaybetme olasılığı "
            f"%{batan/deneme*100:.1f}. En uzun kayıp serisi {en_uzun_kayip} işlem — "
            f"buna psikolojik olarak hazır mısın?"
        ),
        # Bu simülasyonun ASIL işi aşağı tarafı ölçmektir. Yukarı taraf
        # güvenilmezdir: kazanma oranının ve ödül/riskin 200 işlem boyunca hiç
        # bozulmadan süreceğini varsayar. Gerçekte kenar zamanla aşınır, piyasa
        # rejimi değişir. Yüksek medyan sayıları hedef değil, uyarıdır:
        # o sayıyı üreten risk seviyesi seni aynı hızla sıfıra da götürebilir.
        "yukari_taraf_guvenilir_mi": False,
        "uyari": (
            f"Medyan {medyan:.1f}x rakamına GÜVENME — kenarın {islem} işlem boyunca "
            f"hiç bozulmadan süreceğini varsayar. Bu simülasyondan alınacak tek "
            f"sağlam bilgi aşağı taraftır: %{batan/deneme*100:.1f} batma olasılığı ve "
            f"{en_uzun_kayip} işlemlik kayıp serisi."
            if medyan > 5 else
            f"En uzun kayıp serisi {en_uzun_kayip} işlem. Kötü senaryoda (%5 dilim) "
            f"sermaye {float(np.percentile(sonuclar,5)):.2f}x oluyor."
        ),
    }


# ─────────────────────────────────────────────────── portföy riski

def korelasyon(fiyatlar: dict[str, pd.DataFrame], gun: int = 120) -> pd.DataFrame:
    """Günlük getiri korelasyon matrisi.

    Çeşitlendirme YANILSAMASI buradan görülür: 5 farklı banka hissesi almak
    çeşitlendirme değildir, tek bir bahsi beş parçaya bölmektir.
    """
    seriler = {}
    for sem, df in fiyatlar.items():
        if df is None or len(df) < gun + 5:
            continue
        seriler[sem] = df["Close"].pct_change().tail(gun)
    if len(seriler) < 2:
        return pd.DataFrame()
    return pd.DataFrame(seriler).corr()


def portfoy_riski(agirliklar: dict[str, float], fiyatlar: dict[str, pd.DataFrame],
                  gun: int = 120) -> dict:
    """Portföyün TOPLAM riski — parçaların toplamı değildir.

    Korelasyon 1'e yakınsa çeşitlendirme hiçbir şey kazandırmaz.
    """
    ortak = [s for s in agirliklar if s in fiyatlar and len(fiyatlar[s]) > gun]
    if len(ortak) < 1:
        return {"hata": "yeterli veri yok"}

    get = pd.DataFrame({s: fiyatlar[s]["Close"].pct_change().tail(gun) for s in ortak}).dropna()
    if get.empty:
        return {"hata": "getiri hesaplanamadı"}

    w = np.array([agirliklar[s] for s in ortak], dtype=float)
    if w.sum() <= 0:
        return {"hata": "ağırlık toplamı sıfır"}
    w = w / w.sum()

    kov = get.cov().values * 252
    port_oynaklik = float(np.sqrt(w @ kov @ w)) * 100
    tekil = np.sqrt(np.diag(kov)) * 100
    agirlikli_ort = float(w @ tekil)

    kor = get.corr().values
    ust = kor[np.triu_indices_from(kor, 1)]
    ort_kor = float(np.mean(ust)) if len(ust) else np.nan

    # Etkin çeşitlendirme sayısı (Herfindahl tersi)
    etkin_n = 1 / float((w ** 2).sum())

    return {
        "portfoy_oynaklik_yuzde": round(port_oynaklik, 1),
        "agirlikli_ortalama_oynaklik": round(agirlikli_ort, 1),
        "cesitlendirme_kazanci_yuzde": round((1 - port_oynaklik / agirlikli_ort) * 100, 1)
            if agirlikli_ort else None,
        "ortalama_korelasyon": round(ort_kor, 2) if np.isfinite(ort_kor) else None,
        "etkin_hisse_sayisi": round(etkin_n, 1),
        "nominal_hisse_sayisi": len(ortak),
        "gunluk_risk_1std_yuzde": round(port_oynaklik / np.sqrt(252), 2),
        "uyari": (
            "Ortalama korelasyon 0.7'nin üstünde — bu portföy çeşitlendirilmiş "
            "GÖRÜNÜYOR ama tek bir bahis gibi hareket ediyor."
            if np.isfinite(ort_kor) and ort_kor > 0.7 else ""
        ),
    }


def tek_hisse_matematigi(sermaye: float = 1000, hisse_oynaklik: float = 45.0,
                         hisse_sayisi_listesi=(1, 2, 4, 8, 20),
                         korelasyon_varsayim: float = 0.5) -> list[dict]:
    """'Neden tüm parayı tek hisseye yatırmamalı?' — sayılarla.

    Türkiye'de tipik bir BIST hissesinin yıllık oynaklığı %40-60'tır.
    """
    cikti = []
    for n in hisse_sayisi_listesi:
        # Eşit ağırlıklı, sabit korelasyonlu portföyün oynaklığı
        var = (hisse_oynaklik ** 2) * (1 / n + (1 - 1 / n) * korelasyon_varsayim)
        oyn = float(np.sqrt(var))
        gunluk = oyn / np.sqrt(252)
        cikti.append({
            "hisse_sayisi": n,
            "yillik_oynaklik": round(oyn, 1),
            "gunluk_1std_tl": round(sermaye * gunluk / 100, 2),
            "kotu_gun_2std_tl": round(sermaye * gunluk * 2 / 100, 2),
            "tek_hisse_iflas_kaybi_tl": round(sermaye / n, 2),
        })
    return cikti


# ─────────────────────────────────────────────────── performans ölçüleri

def performans(ozkaynak: pd.Series, risksiz_yillik: float = 40.0) -> dict:
    """Sharpe, Sortino, Calmar, maksimum düşüş.

    risksiz_yillik: Türkiye'de mevduat/tahvil faizi. BU ÖNEMLİ — %40 faizin
    olduğu ülkede %35 getiri, risksiz alternatifin ALTINDADIR.
    """
    if ozkaynak is None or len(ozkaynak) < 3:
        return {"hata": "yetersiz veri"}
    g = ozkaynak.pct_change().dropna()
    if len(g) < 2 or g.std(ddof=0) == 0:
        return {"hata": "getiri değişkenliği yok"}

    yil = len(ozkaynak) / 252
    toplam = float(ozkaynak.iloc[-1] / ozkaynak.iloc[0] - 1)
    cagr = (1 + toplam) ** (1 / yil) - 1 if yil > 0 else np.nan

    rf_gunluk = (1 + risksiz_yillik / 100) ** (1 / 252) - 1
    fazla = g - rf_gunluk
    sharpe = float(fazla.mean() / g.std(ddof=0) * np.sqrt(252))
    neg = g[g < 0]
    sortino = float(fazla.mean() / neg.std(ddof=0) * np.sqrt(252)) if len(neg) > 1 and neg.std(ddof=0) > 0 else np.nan
    dd = (ozkaynak / ozkaynak.cummax() - 1)
    maxdd = float(dd.min()) * 100
    calmar = float(cagr * 100 / abs(maxdd)) if maxdd < 0 else np.nan

    # Düşüşten çıkma süresi
    dip = dd.idxmin()
    toparlanma = None
    try:
        zirve = ozkaynak.loc[:dip].idxmax()
        sonrasi = ozkaynak.loc[dip:]
        geri = sonrasi[sonrasi >= ozkaynak.loc[zirve]]
        if len(geri):
            toparlanma = int(np.busday_count(dip.date(), geri.index[0].date()))
    except Exception:
        pass

    return {
        "toplam_getiri_yuzde": round(toplam * 100, 2),
        "yillik_getiri_yuzde": round(cagr * 100, 2) if np.isfinite(cagr) else None,
        "risksiz_getiri_yuzde": risksiz_yillik,
        "risksize_gore_fark": round(cagr * 100 - risksiz_yillik, 2) if np.isfinite(cagr) else None,
        "oynaklik_yuzde": round(float(g.std(ddof=0) * np.sqrt(252) * 100), 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2) if np.isfinite(sortino) else None,
        "calmar": round(calmar, 2) if np.isfinite(calmar) else None,
        "azami_dusus_yuzde": round(maxdd, 2),
        "dususten_cikis_gun": toparlanma,
        "kazanan_gun_yuzde": round(float((g > 0).mean() * 100), 1),
        "en_iyi_gun_yuzde": round(float(g.max() * 100), 2),
        "en_kotu_gun_yuzde": round(float(g.min() * 100), 2),
    }


def bagimsiz_bahis_sayisi(ortalama_korelasyon: float, adet: int) -> float:
    """n adet korelasyonlu bahis, kaç BAĞIMSIZ bahse denk?

        N_etkin = n / (1 + (n-1) · ρ̄)

    Sezgi: 4 hisse alıp "çeşitlendirdim" demek, aralarındaki korelasyon
    0,8'se aslında 1,2 bahis yapmaktır. Risk dört parçaya bölünmez —
    dördü birden aynı yöne gider.

    ρ̄ = 0 ise sonuç n (tam çeşitlendirme), ρ̄ = 1 ise 1 (hiç çeşitlendirme).
    """
    if adet <= 1:
        return float(max(adet, 0))
    r = max(0.0, min(1.0, float(ortalama_korelasyon)))
    return adet / (1.0 + (adet - 1) * r)


def sinyal_yogunlasmasi(semboller: list[str], fiyatlar: dict,
                        sektorler: dict[str, str] | None = None,
                        gun: int = 120) -> dict:
    """Aynı gün çıkan sinyaller gerçekten farklı bahisler mi?

    NEDEN VAR: sistemin bütün sinyalleri UZUN yönlü ve aynı anda açık.
    Ölçüldü — aylık kazanma oranı %17 ile %81 arasında savruluyor, çünkü
    bir ayın sinyalleri aynı kaderi paylaşıyor. Kullanıcı ekranda "3 sinyal"
    görüp üç ayrı fırsat sanıyor; oysa çoğu zaman tek bir bahsin üç parçası.

    Karar üretmez, ölçer ve söyler.
    """
    sem = [s for s in semboller if s in fiyatlar]
    if len(sem) < 2:
        return {"yeterli_mi": False, "adet": len(sem),
                "not": "Yoğunlaşma ölçmek için en az 2 sinyal gerekir."}

    k = korelasyon({s: fiyatlar[s] for s in sem}, gun=gun)
    if k.empty or len(k) < 2:
        return {"yeterli_mi": False, "adet": len(sem),
                "not": "Korelasyon için yeterli ortak geçmiş yok."}

    import numpy as _np
    m = k.to_numpy(dtype=float)
    ust = m[_np.triu_indices_from(m, k=1)]
    ust = ust[_np.isfinite(ust)]
    if ust.size == 0:
        return {"yeterli_mi": False, "adet": len(sem), "not": "korelasyon boş"}

    ort = float(_np.mean(ust))
    n_etkin = bagimsiz_bahis_sayisi(ort, len(k))

    # En yüksek korelasyonlu çift — "şu ikisi aynı bahis" demenin en somut hâli
    en_yuksek, cift = float(_np.max(ust)), None
    idx = _np.triu_indices_from(m, k=1)
    for a, b, v in zip(idx[0], idx[1], m[idx]):
        if v == en_yuksek:
            cift = [str(k.index[a]), str(k.columns[b])]
            break

    cikti = {
        "yeterli_mi": True,
        "adet": int(len(k)),
        "ortalama_korelasyon": round(ort, 2),
        "bagimsiz_bahis": round(n_etkin, 1),
        "en_yuksek_korelasyon": round(en_yuksek, 2),
        "en_yakin_cift": cift,
    }

    if sektorler:
        sayac: dict[str, int] = {}
        for s in k.index:
            # Sektör değeri sözlük/demet gelebilir; anahtar olarak
            # kullanmadan önce metne indir.
            ad = sektorler.get(str(s), "bilinmiyor")
            if isinstance(ad, dict):
                ad = ad.get("sektor", "bilinmiyor")
            elif isinstance(ad, (list, tuple)):
                ad = ad[0] if ad else "bilinmiyor"
            ad = str(ad or "bilinmiyor")
            sayac[ad] = sayac.get(ad, 0) + 1
        baskin = max(sayac.items(), key=lambda x: x[1])
        cikti["sektor_dagilimi"] = sayac
        cikti["baskin_sektor"] = {"sektor": baskin[0], "adet": baskin[1],
                                  "oran": round(baskin[1] / len(k) * 100)}

    # Yorum: sayıyı kullanıcının anlayacağı cümleye çevir
    if n_etkin < 1.5:
        cikti["yorum"] = (f"{len(k)} sinyal var ama bunlar yaklaşık "
                          f"{n_etkin:.1f} BAĞIMSIZ bahse denk — neredeyse tek "
                          f"bir bahis. Hepsini almak çeşitlendirme değil, "
                          f"aynı riski büyütmektir.")
    elif n_etkin < len(k) * 0.6:
        cikti["yorum"] = (f"{len(k)} sinyal ≈ {n_etkin:.1f} bağımsız bahis. "
                          f"Beklediğinden az çeşitlendirme; ortalama "
                          f"korelasyon {ort:.2f}.")
    else:
        cikti["yorum"] = (f"{len(k)} sinyal ≈ {n_etkin:.1f} bağımsız bahis. "
                          f"Makul çeşitlendirme (ortalama korelasyon {ort:.2f}).")

    # Sektör yoğunlaşması korelasyondan AYRI bir risk: geçmiş getiriler
    # ayrışmış olsa bile tek bir sektör haberi hepsini birden vurur.
    # Bunu yoruma katmazsak kart kendi kendiyle çelişir — "makul
    # çeşitlendirme" der, altında "%100'ü tek sektörde" yazar.
    bs = cikti.get("baskin_sektor")
    if bs and bs.get("oran", 0) >= 60 and len(k) >= 2:
        cikti["yorum"] += (f" Ama sinyallerin %{bs['oran']}'i tek sektörde "
                           f"({bs['sektor']}): korelasyon düşük olsa bile "
                           f"sektöre özel bir haber hepsini birden vurur.")
        cikti["sektor_uyarisi"] = True
    return cikti
