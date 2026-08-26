"""Sektör analizi: bir şirket kendi sektörü içinde değerlendirilir.

Sektörler arası çarpan kıyası anlamsızdır. Bankanın PD/DD'si 1.2, perakendenin
2.9 olabilir ve ikisi de normaldir — çünkü iş modelleri farklıdır. Bu modül
her hisseyi KENDİ sektörünün medyanıyla kıyaslar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import veri

# BIST sektör endeksleri (hepsi doğrulandı, 16/16 çalışıyor)
ENDEKSLER = {
    "XBANK": "Banka", "XUSIN": "Sınai", "XUTEK": "Teknoloji", "XULAS": "Ulaştırma",
    "XGIDA": "Gıda-İçecek", "XKMYA": "Kimya-Petrol", "XMANA": "Metal Ana",
    "XMESY": "Metal Eşya", "XELKT": "Elektrik", "XTRZM": "Turizm",
    "XINSA": "İnşaat", "XHOLD": "Holding", "XSGRT": "Sigorta",
    "XTAST": "Taş-Toprak", "XUHIZ": "Hizmet", "XILTM": "İletişim",
}

# yfinance'in İngilizce sektör adı → BIST endeksi + değerleme rehberi
ESLESME = {
    "Financial Services": {
        "endeks": "XBANK", "ad": "Banka & Finans",
        "carpanlar": ["pd_dd", "fk"],
        "rehber": "PD/DD ve F/K esastır. FD/FAVÖK, cari oran ve borç/özsermaye "
                  "ANLAMSIZDIR — bankada borç hammaddedir. ROE ve net faiz "
                  "marjına bak; takipteki kredi oranı en kritik risk.",
    },
    "Basic Materials": {
        "endeks": "XMANA", "ad": "Ana Metal & Hammadde",
        "carpanlar": ["fd_favok", "pd_dd"],
        "rehber": "Döngüsel sektör: kâr tepedeyken F/K DÜŞÜK görünür ve bu bir "
                  "tuzaktır. Emtia fiyatı ve kapasite kullanımına bak. "
                  "FD/FAVÖK, F/K'dan güvenilir.",
    },
    "Industrials": {
        "endeks": "XUSIN", "ad": "Sınai & Ulaştırma",
        "carpanlar": ["fd_favok", "fk"],
        "rehber": "Sermaye yoğun; amortisman büyük olduğu için FD/FAVÖK tercih "
                  "edilir. Havayollarında yakıt maliyeti ve doluluk oranı, "
                  "sanayide kapasite kullanımı belirleyici.",
    },
    "Consumer Defensive": {
        "endeks": "XGIDA", "ad": "Gıda & Perakende",
        "carpanlar": ["fk", "fd_favok"],
        "rehber": "Marjlar incedir (%2-5 net normaldir), hacim ve mağaza başına "
                  "ciro belirleyicidir. Enflasyonu fiyata geçirebilme hızı "
                  "en kritik değişken.",
    },
    "Consumer Cyclical": {
        "endeks": "XUHIZ", "ad": "Dayanıklı Tüketim",
        "carpanlar": ["fk", "fd_favok"],
        "rehber": "Faize ve kredi koşullarına çok duyarlı. Otomotiv ve beyaz "
                  "eşyada iç talep + ihracat dengesine bak.",
    },
    "Energy": {
        "endeks": "XKMYA", "ad": "Enerji & Petrol",
        "carpanlar": ["fd_favok", "fk"],
        "rehber": "Rafineri marjı (crack spread) kârı belirler. Stok kârı/zararı "
                  "net kârı yanıltıcı şekilde şişirip söndürebilir.",
    },
    "Utilities": {
        "endeks": "XELKT", "ad": "Elektrik & Altyapı",
        "carpanlar": ["fd_favok", "temettu_verim"],
        "rehber": "Borçlu ve düzenlemeye tabi. Temettü verimi ana çekicilik; "
                  "faiz yükselince tahvil gibi değer kaybeder.",
    },
    "Technology": {
        "endeks": "XUTEK", "ad": "Teknoloji",
        "carpanlar": ["fs", "fk"],
        "rehber": "Büyüme fiyatlanır; yüksek çarpan tek başına pahalı demek "
                  "değildir. Ama BIST'te teknoloji hisseleri çok oynaktır — "
                  "hikâye ile bilanço arasındaki farkı kontrol et.",
    },
    "Real Estate": {
        "endeks": "XINSA", "ad": "GYO & İnşaat",
        "carpanlar": ["pd_dd", "temettu_verim"],
        "rehber": "PD/DD esastır; net aktif değer (NAD) iskontosu asıl ölçüdür. "
                  "Faize aşırı duyarlı. F/K genelde anlamsız (değerleme kârı).",
    },
    "Communication Services": {
        "endeks": "XILTM", "ad": "İletişim",
        "carpanlar": ["fd_favok", "temettu_verim"],
        "rehber": "Sermaye yoğun, abone başına gelir (ARPU) belirleyici. "
                  "Dövizli borç yükü kur riskinin ana kaynağı.",
    },
    "Healthcare": {
        "endeks": "XUHIZ", "ad": "Sağlık",
        "carpanlar": ["fk", "fd_favok"],
        "rehber": "Düzenleme ve geri ödeme politikaları belirleyici.",
    },
}


def sektor_bilgi(sektor: str) -> dict:
    return ESLESME.get(sektor, {
        "endeks": None, "ad": sektor or "Bilinmiyor",
        "carpanlar": ["fk", "pd_dd"],
        "rehber": "Bu sektör için özel rehber tanımlı değil; genel çarpanlarla "
                  "değerlendirilir. Şirketin iş modelini kendin anla.",
    })


def sektor_haritasi(semboller: list[str] | None = None,
                    onbellek_saat: float = 24.0) -> dict:
    """{sembol: (sektör, piyasa_değeri)} haritası. Diske önbelleklenir."""
    import json, time
    from . import evren
    from .temel_veri import finansal_cek, ONBELLEK

    yol = ONBELLEK / "sektor_haritasi.json"
    if yol.exists() and (time.time() - yol.stat().st_mtime) < onbellek_saat * 3600:
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except Exception:
            pass

    semboller = semboller or evren.evren_getir("bist100")
    harita = {}
    for i, s in enumerate(semboller, 1):
        if i % 25 == 0:
            print(f"    sektör haritası {i}/{len(semboller)}...")
        f = finansal_cek(s, onbellek_saat=168.0)   # sektör bilgisi haftalarca sabit
        if f and f.sektor:
            harita[f.sembol] = {"sektor": f.sektor,
                                "pd": float(f.piyasa_degeri) if f.piyasa_degeri == f.piyasa_degeri else 0.0}
    try:
        yol.write_text(json.dumps(harita, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    return harita


def endeks_performans(gun: int = 400, onbellek_saat: float = 6.0,
                      asgari_hisse: int = 3) -> pd.DataFrame:
    """Sektör performansı — BİLEŞENLERDEN kurulur, hazır endeksten değil.

    Neden: yfinance BIST sektör endekslerinin (XUTEK, XGIDA, XKMYA...) yalnızca
    1 günlük geçmişini taşıyor. Sadece XU100 ve XBANK gerçek geçmişe sahip.
    Bu yüzden sektör serilerini hisselerden PİYASA DEĞERİ AĞIRLIKLI kuruyoruz —
    böylece hem 16 sektörün hepsi elde edilir hem de ağırlıklandırma şeffaf olur.
    """
    harita = sektor_haritasi()
    if not harita:
        return pd.DataFrame()

    xu = veri.fiyat_cek("XU100", gun=gun, onbellek_saat=onbellek_saat)
    if xu.empty:
        return pd.DataFrame()
    xk = xu["Close"]

    gruplar: dict[str, list[str]] = {}
    for sem, bilgi in harita.items():
        gruplar.setdefault(bilgi["sektor"], []).append(sem)

    fiyatlar = veri.toplu_cek(list(harita), gun=gun, onbellek_saat=onbellek_saat,
                              sessiz=True)

    satirlar = []
    for sekt, uyeler in gruplar.items():
        uygun = [u for u in uyeler if u in fiyatlar and len(fiyatlar[u]) > 70]
        if len(uygun) < asgari_hisse:
            continue

        # Piyasa değeri ağırlıklı bileşik getiri serisi
        seriler, agirliklar = [], []
        for u in uygun:
            k = fiyatlar[u]["Close"]
            seriler.append(k / k.iloc[0])
            agirliklar.append(max(harita[u]["pd"], 1.0))
        d = pd.concat(seriler, axis=1).ffill().dropna(how="all")
        w = np.array(agirliklar) / sum(agirliklar)
        endeks = (d * w).sum(axis=1)
        endeks = endeks[endeks > 0]
        if len(endeks) < 70:
            continue

        def get(n):
            if len(endeks) <= n:
                return np.nan
            return (endeks.iloc[-1] / endeks.iloc[-n - 1] - 1) * 100

        h = xk.reindex(endeks.index).ffill()

        def gg(n):
            if len(endeks) <= n or len(h) <= n:
                return np.nan
            ref = h.iloc[-n - 1]
            if not np.isfinite(ref) or ref == 0:
                return np.nan
            return get(n) - (h.iloc[-1] / ref - 1) * 100

        bilgi = sektor_bilgi(sekt)
        satirlar.append({
            "sektor": bilgi["ad"], "yf_sektor": sekt, "hisse": len(uygun),
            "g5": get(5), "g20": get(20), "g60": get(60), "g120": get(120),
            "gg20": gg(20), "gg60": gg(60),
            "uyeler": ", ".join(sorted(uygun)[:6]) + ("..." if len(uygun) > 6 else ""),
        })

    if not satirlar:
        return pd.DataFrame()
    return pd.DataFrame(satirlar).sort_values("gg60", ascending=False).reset_index(drop=True)


def liderler_gecikenler(gun: int = 400) -> dict:
    d = endeks_performans(gun)
    if d.empty:
        return {"hata": "sektör verisi alınamadı"}
    ge = d.dropna(subset=["gg60"])
    return {
        "tablo": d,
        "liderler": ge.head(3)[["sektor", "gg60", "g60", "hisse"]].to_dict("records"),
        "gecikenler": ge.tail(3)[["sektor", "gg60", "g60", "hisse"]].to_dict("records"),
        "yorum": "Momentum stratejileri lider sektörlerde daha iyi çalışır. "
                 "Geciken sektörde ucuzluk arıyorsan, ucuzluğun SEBEBİNİ bul — "
                 "sektör bir nedenle geride kalıyor olabilir.",
    }
