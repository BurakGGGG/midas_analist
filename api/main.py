"""Midas Analist API — Flutter istemcisi için.

Tasarım: sunucu DURUMSUZDUR. Pozisyonlar ve tezler telefonda saklanır; sunucu
yalnızca hesap yapar. Sebebi: kullanıcının verisi cihazında kalsın, sunucu
kapalıyken bile geçmişini görebilsin, ve senkron sorunu hiç doğmasın.

Çalıştırma:
    .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Telefondan erişim için --host 0.0.0.0 şart (localhost sadece PC'den görünür).
"""
from __future__ import annotations

import uuid
import warnings
from threading import Thread
from typing import Any

warnings.filterwarnings("ignore")

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cekirdek import ortam  # noqa: F401  (.env yükler; anahtar okumadan önce)
from cekirdek import (veri, gostergeler, evren, tarayici, makro, sektor,
                      temel_veri, temel, degerleme, formasyon, istatistik,
                      portfoy_yonetimi, psikoloji, tez as tez_mod, ogren,
                      backtest as bt, strateji)
from cekirdek.risk import RiskAyarlari, pozisyon_hesapla
from cekirdek.strateji import Filtreler, STRATEJILER

from .donusum import guvenli, seri_noktalari, metin_akit
from . import onbellek

app = FastAPI(title="Midas Analist API", version="1.0.0",
              description="BIST karar destek sistemi — Flutter istemcisi için")

# Flutter web ve mobil geliştirme sırasında farklı origin'lerden gelir
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

# İsteğe bağlı API anahtarı. Yerelde (kendi Wi-Fi'ında) gereksiz; buluta
# açtığında ŞART - yoksa uç noktaların herkese açık olur ve kotanı yakar.
# Açmak için: export MIDAS_API_ANAHTARI="uzun-rastgele-bir-dize"
_ANAHTAR = __import__("os").environ.get("MIDAS_API_ANAHTARI", "").strip()


@app.middleware("http")
async def anahtar_kontrol(istek, sonraki):
    # CORS ön kontrolü (OPTIONS) tanım gereği özel başlık TAŞIMAZ — tarayıcı
    # onu "şu başlıkla istek atabilir miyim?" diye sormak için gönderir.
    # Burada 401 dönersek tarayıcı asıl isteği hiç yapmaz ve web istemcisi
    # sunucuya hiç bağlanamaz. Native mobil istemci ön kontrol yapmadığı için
    # bu hata yalnızca tarayıcıda görünür.
    if (_ANAHTAR and istek.method != "OPTIONS"
            and istek.url.path not in ("/saglik", "/docs", "/openapi.json")):
        if istek.headers.get("X-API-Anahtar", "") != _ANAHTAR:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Geçersiz veya eksik API anahtarı"},
                                status_code=401)
    return await sonraki(istek)


@app.on_event("startup")
def baslangic():
    onbellek.arka_planda_isit()
    onbellek.periyodik(4.0)


def _risk(sermaye: float, risk_yuzde: float = 1.5, azami_pozisyon: float = 35.0,
          azami_es: int = 4) -> RiskAyarlari:
    return RiskAyarlari(sermaye=sermaye, islem_basi_risk_yuzde=risk_yuzde,
                        azami_pozisyon_yuzde=azami_pozisyon, azami_es_zamanli=azami_es)


# ══════════════════════════════════════════════════════ durum

@app.get("/saglik")
def saglik():
    return {"durum": "ayakta", "onbellek": onbellek.DURUM,
            "evren": len(evren.evren_getir("bist100")),
            "anahtar_gerekli": bool(_ANAHTAR)}


# ══════════════════════════════════════════════════════ tarama

@app.get("/tarama")
def tarama(sermaye: float = 1000, evren_adi: str = "bist100",
           sadece_sinyal: bool = False, adet: int = 40,
           risk_yuzde: float = 1.5, azami_pozisyon: float = 35.0):
    ra = _risk(sermaye, risk_yuzde, azami_pozisyon)
    try:
        gecen, elenen = tarayici.tara(evren_adi=evren_adi, risk_ayar=ra,
                                      gun=500, sadece_sinyalli=sadece_sinyal)
    except Exception as e:
        raise HTTPException(503, f"tarama başarısız: {e}")

    # Karantina: canlı sicili beklenenin altında kalan stratejinin sinyali
    # gösterilir ama ÖNERİLMEZ. Karar veriye bağlı, strateji adına değil —
    # bozulan kendiliğinden girer, düzelen kendiliğinden çıkar.
    try:
        from cekirdek import ogrenme, ambar as _ambar
        _ambar.kur()
        siniflar = ogrenme.strateji_siniflari()
    except Exception:
        siniflar = {}
    onerilmeyen = {k for k, v in siniflar.items() if not v.get("onerilir", True)}

    def _ayir(a):
        d = guvenli(a.sozluk())
        sin = list(a.sinyaller or [])
        d["sinyaller_karantina"] = [x for x in sin if x in onerilmeyen]
        d["sinyaller_onerilen"] = [x for x in sin if x not in onerilmeyen]
        return d

    adaylar = [_ayir(a) for a in gecen[:adet]]

    # Yoğunlaşma: aynı gün çıkan sinyaller gerçekten farklı bahisler mi?
    # Ekranda "3 sinyal" görüp üç ayrı fırsat sanmak en pahalı yanılgı;
    # sistemin bütün sinyalleri uzun yönlü ve aynı anda açık.
    yogunlasma = {"yeterli_mi": False}
    try:
        from cekirdek import istatistik, sektor as _sektor
        sinyalli = [a.sembol for a in gecen if a.sinyaller][:12]
        if len(sinyalli) >= 2:
            fiyatlar = {}
            for sm in sinyalli:
                df = veri.fiyat_cek(sm, gun=200, onbellek_saat=12.0)
                if df is not None and not df.empty:
                    fiyatlar[sm] = df
            try:
                # sektor_haritasi {KOD: {"sektor":..., "pd":...}} döner ve
                # anahtarlarda .IS eki YOKTUR — iki ayrıntı da sessizce
                # yanlış eşleşmeye yol açıyordu.
                ham = _sektor.sektor_haritasi(sinyalli) or {}
                sektorler = {}
                for sm in sinyalli:
                    v = ham.get(sm.replace(".IS", "")) or ham.get(sm)
                    if isinstance(v, dict):
                        v = v.get("sektor")
                    elif isinstance(v, (list, tuple)):
                        v = v[0] if v else None
                    if v:
                        sektorler[sm] = str(v)
            except Exception:
                sektorler = None
            yogunlasma = istatistik.sinyal_yogunlasmasi(
                sinyalli, fiyatlar, sektorler)
    except Exception as e:
        yogunlasma = {"yeterli_mi": False, "not": f"hesaplanamadı: {str(e)[:80]}"}

    return {
        "hazir": onbellek.DURUM["hazir"],
        "toplam": len(gecen), "elenen": len(elenen),
        "sinyalli": sum(1 for a in gecen if a.sinyaller),
        "alinabilir": sum(1 for a in gecen if a.sinyaller and a.pozisyon
                          and a.pozisyon.uygulanabilir),
        # Karantina sonrası gerçekten önerilen sayısı. Eski alanlar
        # bozulmasın diye ayrı anahtar.
        "onerilen": sum(1 for a in gecen
                        if [x for x in (a.sinyaller or []) if x not in onerilmeyen]
                        and a.pozisyon and a.pozisyon.uygulanabilir),
        "strateji_durumlari": guvenli(siniflar),
        "yogunlasma": guvenli(yogunlasma),
        "adaylar": adaylar,
        "elenenler": [{"sembol": a.sembol, "skor": a.skor, "sebep": a.elendi}
                      for a in elenen[:12]],
    }


# ══════════════════════════════════════════════════════ tek hisse

@app.get("/hisse/{sembol}")
def hisse(sembol: str, sermaye: float = 1000, grafik: bool = True,
          gun_grafik: int = 180):
    ra = _risk(sermaye)
    r = tarayici.tek_hisse(sembol, ra)
    if r is None:
        raise HTTPException(404, f"{sembol} için veri yok")
    g = r["gostergeler"]
    cikti: dict[str, Any] = {
        "sembol": r["sembol"], "skor": guvenli(r["skor"]),
        "filtre": {"gecti": r["filtre"][0], "sebep": r["filtre"][1]},
        "seviyeler": guvenli(r["seviyeler"]),
        "pozisyon": guvenli(r["pozisyon"]),
    }
    if grafik:
        n = max(60, min(gun_grafik, 260))
        cikti["grafik"] = {
            "kapanis": seri_noktalari(g["Close"].tail(n), 130),
            "ema20": seri_noktalari(g["EMA20"].tail(n), 130),
            "sma200": seri_noktalari(g["SMA200"].tail(n), 130),
            "rsi": seri_noktalari(g["RSI14"].tail(n), 130),
        }
    return cikti


@app.get("/hisse/{sembol}/yapi")
def hisse_yapi(sembol: str):
    df = veri.fiyat_cek(sembol, gun=750)
    if df.empty or len(df) < 220:
        raise HTTPException(404, f"{sembol} için yeterli geçmiş yok")
    return guvenli(formasyon.tam_analiz(df))


@app.get("/hisse/{sembol}/sirket")
def hisse_sirket(sembol: str, sektor_kiyas: bool = True):
    f = temel_veri.finansal_cek(sembol)
    if f is None:
        raise HTTPException(404, f"{sembol} için finansal veri yok")
    o = temel.oranlar(f)
    c = degerleme.carpanlar(f)

    sektor_ort, hukum = None, None
    if sektor_kiyas:
        try:
            harita = sektor.sektor_haritasi()
            emsaller = [x for x, b in harita.items()
                        if b["sektor"] == f.sektor and x != f.sembol][:20]
            if emsaller:
                fin = temel_veri.toplu_finansal(emsaller, sessiz=True)
                sektor_ort = degerleme.sektor_ortalamasi(fin)
                hukum = degerleme.deger_hukmu(f, c, sektor_ort)
        except Exception:
            pass

    return {
        "sembol": f.sembol, "ad": f.ad, "sektor": f.sektor, "sanayi": f.sanayi,
        "fiyat": guvenli(f.fiyat), "piyasa_degeri": guvenli(f.piyasa_degeri),
        "tablo_para": f.tablo_para, "fiyat_para": f.fiyat_para,
        "kur_uyusmazligi": f.kur_uyusmazligi, "kur": guvenli(f.kur),
        "donemler": f.donemler,
        "kalite": guvenli(temel.kalite_skoru(f, o)),
        "bayraklar": temel.kirmizi_bayraklar(f, o),
        "oranlar": {k: guvenli(v) for k, v in o.items()},
        "carpanlar": {k: {**guvenli(v),
                          "sektor_ort": guvenli(sektor_ort.get(k)) if sektor_ort else None}
                      for k, v in c.items()},
        "ters_dcf": guvenli(degerleme.ters_dcf(f)),
        "hukum": guvenli(hukum),
        "sektor_rehberi": sektor.sektor_bilgi(f.sektor),
    }


# ══════════════════════════════════════════════════════ piyasa

@app.get("/makro")
def makro_durum(grafik: bool = False):
    """grafik=False varsayılan: liste ekranı 12 seriyi çizmez, sadece sayıları
    gösterir. Detaya girildiğinde grafik=true ile tek seri istenir."""
    m = makro.durum()
    d = {k: {kk: guvenli(vv) for kk, vv in v.items() if kk != "seri"}
         for k, v in m.degerler.items()}
    if grafik:
        for k, v in m.degerler.items():
            d[k]["grafik"] = seri_noktalari(v["seri"].tail(180), 70)
    xu = m.oz("xu100")
    reel = (xu["g365"] - m.enflasyon["yillik"]) if xu else None
    return {"tarih": m.tarih, "enflasyon": guvenli(m.enflasyon),
            "gostergeler": d, "rejim": guvenli(makro.rejim(m)),
            "bist_reel_getiri_1y": guvenli(reel)}


@app.get("/sektor")
def sektorler():
    r = sektor.liderler_gecikenler()
    if "hata" in r:
        raise HTTPException(503, r["hata"])
    return {"tablo": guvenli(r["tablo"].drop(columns=["uyeler"], errors="ignore")),
            "liderler": guvenli(r["liderler"]),
            "gecikenler": guvenli(r["gecikenler"]), "yorum": r["yorum"]}


# ══════════════════════════════════════════════════════ portföy & tez (durumsuz)

class Pozisyon(BaseModel):
    sembol: str
    adet: int
    giris: float
    stop: float
    hedef: float
    tarih: str
    strateji: str = "kirilim"


class PortfoyIstek(BaseModel):
    pozisyonlar: list[Pozisyon] = Field(default_factory=list)
    sermaye: float = 1000


@app.post("/portfoy/kontrol")
def portfoy_kontrol(istek: PortfoyIstek):
    """Pozisyonlar telefondan gelir, sunucu değerlendirir. Durum tutulmaz."""
    from datetime import date, datetime as dt
    import numpy as np
    sonuc = []
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=400)
    ek = endeks["Close"] if not endeks.empty else None

    for p in istek.pozisyonlar:
        df = veri.fiyat_cek(p.sembol, gun=400, onbellek_saat=2.0)
        if df.empty:
            sonuc.append({"sembol": p.sembol, "hata": "veri alınamadı"})
            continue
        g = gostergeler.gosterge_seti(df, ek)
        s = g.iloc[-1]
        fiyat = float(s["Close"])
        st = STRATEJILER.get(p.strateji, STRATEJILER["kirilim"])
        try:
            cikis = bool(st.cikis(g).iloc[-1])
        except Exception:
            cikis = False
        try:
            gun = int(np.busday_count(dt.fromisoformat(p.tarih).date(), date.today()))
        except Exception:
            gun = 0

        if fiyat <= p.stop:
            aksiyon, aciklama = "SAT", f"STOP tetiklendi ({fiyat:.2f} ≤ {p.stop:.2f})"
        elif fiyat >= p.hedef:
            aksiyon, aciklama = "SAT", f"HEDEF geldi ({fiyat:.2f} ≥ {p.hedef:.2f})"
        elif cikis:
            aksiyon, aciklama = "SAT", "strateji çıkış sinyali verdi"
        elif gun >= st.azami_tutma:
            aksiyon, aciklama = "SAT", f"azami tutma süresi doldu ({gun} iş günü)"
        else:
            aksiyon = "TUT"
            aciklama = (f"stop'a %{(fiyat - p.stop) / fiyat * 100:.1f}, "
                        f"hedefe %{(p.hedef - fiyat) / fiyat * 100:.1f}")

        oneri = ""
        atr = float(s["ATR14"]) if np.isfinite(s["ATR14"]) else 0
        if aksiyon == "TUT" and fiyat > p.giris and atr > 0:
            yeni = max(p.stop, fiyat - st.atr_stop_kat * atr)
            if yeni > p.stop * 1.005:
                oneri = f"stop'u {p.stop:.2f} → {yeni:.2f} yukarı çek"

        sonuc.append(guvenli({
            "sembol": p.sembol, "fiyat": fiyat, "adet": p.adet, "giris": p.giris,
            "stop": p.stop, "hedef": p.hedef,
            "kar": (fiyat - p.giris) * p.adet,
            "kar_yuzde": (fiyat / p.giris - 1) * 100 if p.giris else 0,
            "gunluk_degisim": (fiyat / float(g["Close"].iloc[-2]) - 1) * 100,
            "aksiyon": aksiyon, "aciklama": aciklama, "oneri": oneri,
            "gun": gun, "rsi": float(s["RSI14"]),
        }))

    maliyet = sum(p.adet * p.giris for p in istek.pozisyonlar)
    deger = sum(x.get("fiyat", 0) * x.get("adet", 0) for x in sonuc if "hata" not in x)
    return {
        "pozisyonlar": sonuc,
        "ozet": guvenli({
            "maliyet": maliyet, "deger": deger, "kar": deger - maliyet,
            "kar_yuzde": (deger / maliyet - 1) * 100 if maliyet else 0,
            "piyasa_yuzde": deger / istek.sermaye * 100 if istek.sermaye else 0,
            "nakit": max(0.0, istek.sermaye - maliyet),
            "satilacak": sum(1 for x in sonuc if x.get("aksiyon") == "SAT"),
        }),
    }


class AlimIstek(BaseModel):
    sembol: str
    adet: int
    fiyat: float
    sermaye: float = 1000
    tez_var_mi: bool = False
    acik_pozisyonlar: list[Pozisyon] = Field(default_factory=list)
    gecmis_getiriler: list[dict] = Field(default_factory=list)


@app.post("/alim/kontrol")
def alim_kontrol(istek: AlimIstek):
    """Alım öncesi davranışsal tarama — FOMO, intikam, yoğunlaşma."""
    df = veri.fiyat_cek(istek.sembol, gun=400)
    if df.empty:
        raise HTTPException(404, f"{istek.sembol} verisi yok")
    g = gostergeler.gosterge_seti(df)
    acik = [{"sembol": p.sembol, "giris": p.giris, "maliyet": p.adet * p.giris}
            for p in istek.acik_pozisyonlar]
    u = psikoloji.alim_oncesi(istek.sembol, istek.fiyat, istek.adet, istek.sermaye,
                              g.iloc[-1], istek.gecmis_getiriler, acik,
                              tez_var_mi=istek.tez_var_mi)
    return {
        "uyarilar": [guvenli(x) for x in u],
        "kritik": sum(1 for x in u if x.seviye == "dur"),
        "gecebilir": not any(x.seviye == "dur" for x in u),
        "kontrol_listesi": psikoloji.gunluk_kontrol_listesi(),
    }


@app.get("/tez/sorular")
def tez_sorulari():
    return {"sorular": [{"anahtar": a, "soru": s} for a, s in tez_mod.SORULAR]}


@app.get("/tez/anlik/{sembol}")
def tez_anlik(sembol: str, sermaye: float = 1000):
    """Alım anındaki objektif durum — telefonda tezle birlikte saklanır."""
    return guvenli(tez_mod.anlik_goruntu(sembol, sermaye))


class TezKarsilastir(BaseModel):
    sembol: str
    anlik: dict
    sermaye: float = 1000


@app.post("/tez/kontrol")
def tez_kontrol(istek: TezKarsilastir):
    """Kaydedilmiş anlık görüntüyü bugünle karşılaştır: tez bozuldu mu?"""
    simdi = tez_mod.anlik_goruntu(istek.sembol, istek.sermaye)
    eski, bozulmalar = istek.anlik, []

    e_kal = (eski.get("temel") or {}).get("kalite_skoru")
    y_kal = (simdi.get("temel") or {}).get("kalite_skoru")
    if e_kal and y_kal and y_kal < e_kal - 10:
        bozulmalar.append(f"Kalite skoru {e_kal} → {y_kal} (şirket temeli bozuluyor)")
    for b in set((simdi.get("temel") or {}).get("kirmizi_bayrak", [])) - \
             set((eski.get("temel") or {}).get("kirmizi_bayrak", [])):
        bozulmalar.append(f"YENİ kırmızı bayrak: {b}")
    if (eski.get("teknik") or {}).get("sma200_ustu") and \
       not (simdi.get("teknik") or {}).get("sma200_ustu"):
        bozulmalar.append("Fiyat 200 günlük ortalamanın ALTINA düştü (trend kırıldı)")

    return {"simdi": guvenli(simdi), "bozulmalar": bozulmalar,
            "soru": "Yazdığın yanılma koşulu gerçekleşti mi?"}


# ══════════════════════════════════════════════════════ risk & dağıtım

@app.get("/risk")
def risk_matematigi(sermaye: float = 1000):
    ornekler = [("kırılım (ölçülen)", 0.459, 16.1, 7.3),
                ("çok kazanan, zararda", 0.90, 1.0, 15.0),
                ("az kazanan, kârlı", 0.35, 25.0, 8.0)]
    return guvenli({
        "beklenen_deger": [{"ad": ad, **istatistik.beklenen_deger(p, k, z)}
                           for ad, p, k, z in ornekler],
        "monte_carlo": [{"risk_yuzde": r,
                         **istatistik.batma_riski(r, 0.459, 16.1 / 7.3, islem=200)}
                        for r in [1.0, 1.5, 2.5, 5.0, 10.0, 20.0]],
        "kelly": istatistik.kelly(0.459, 16.1, 7.3),
        "cesitlendirme": istatistik.tek_hisse_matematigi(sermaye),
    })


class PortfoyRisk(BaseModel):
    pozisyonlar: list[Pozisyon] = Field(default_factory=list)


@app.post("/risk/portfoy")
def risk_portfoy(istek: PortfoyRisk):
    if len(istek.pozisyonlar) < 2:
        return {"hata": "en az 2 pozisyon gerekir"}
    fiyatlar = {p.sembol: veri.fiyat_cek(p.sembol, gun=200) for p in istek.pozisyonlar}
    agirlik = {p.sembol: p.adet * p.giris for p in istek.pozisyonlar}
    return guvenli(istatistik.portfoy_riski(agirlik, fiyatlar))


@app.get("/dagitim")
def dagitim(sermaye: float = 1000, profil: str = "dengeli",
            sadece_sinyal: bool = True):
    ra = _risk(sermaye)
    gecen, _ = tarayici.tara(risk_ayar=ra, gun=500, sadece_sinyalli=sadece_sinyal)
    adaylar = [(x.sembol, x.fiyat) for x in gecen[:12]]
    if not adaylar:
        return {"hata": "uygun aday yok"}
    d = portfoy_yonetimi.dagitim(adaylar, sermaye, profil)
    try:
        m = makro.durum()
        d["nakit_onerisi"] = portfoy_yonetimi.nakit_orani_onerisi(makro.rejim(m)["rejim"])
    except Exception:
        pass
    return guvenli(d)


# ══════════════════════════════════════════════════════ eğitim

@app.get("/ogren")
def ogren_liste():
    return {"konular": [{"anahtar": k, "baslik": b} for k, b in ogren.konu_listesi()]}


@app.get("/ogren/{konu}")
def ogren_konu(konu: str):
    k = ogren.konu_getir(konu)
    if k is None:
        raise HTTPException(404, f"'{konu}' bulunamadı")
    return k


# ══════════════════════════════════════════════════════ backtest (arka plan)

ISLER: dict[str, dict] = {}


class BacktestIstek(BaseModel):
    strateji: str | None = None
    sermaye: float = 1000
    gun: int = 1200
    kayma_bp: float = 15.0
    evren_adi: str = "bist100"


def _backtest_calistir(is_id: str, istek: BacktestIstek):
    try:
        ISLER[is_id]["durum"] = "veri indiriliyor"
        sem = evren.evren_getir(istek.evren_adi)
        ham = veri.toplu_cek(sem, gun=istek.gun, sessiz=True)
        endeks = veri.fiyat_cek(evren.ENDEKS, gun=istek.gun)
        G = {s: gostergeler.gosterge_seti(d, endeks["Close"])
             for s, d in ham.items() if len(d) >= 250}
        ra = _risk(istek.sermaye)
        hedef = [istek.strateji] if istek.strateji else list(STRATEJILER)
        sonuc = {}
        for i, ad in enumerate(hedef):
            ISLER[is_id]["durum"] = f"{ad} test ediliyor ({i+1}/{len(hedef)})"
            st = STRATEJILER.get(ad)
            if st is None:
                continue
            s = bt.calistir(G, st, ra, Filtreler(), kayma_bp=istek.kayma_bp)
            m = s.metrikler(endeks["Close"])
            sonuc[ad] = {"metrikler": guvenli(m), "aciklama": st.aciklama,
                         "ozkaynak": seri_noktalari(s.ozkaynak, 150)}
        kiyas = endeks["Close"].tail(len(list(G.values())[0])) if G else None
        ISLER[is_id].update(durum="bitti", tamam=True, sonuc=sonuc,
                            hisse_sayisi=len(G))
    except Exception as e:
        ISLER[is_id].update(durum="hata", tamam=True, hata=str(e)[:300])


@app.post("/backtest")
def backtest_baslat(istek: BacktestIstek):
    """Backtest uzun sürer (dakikalar). İş kimliği döner, sonucu sorgulanır."""
    is_id = uuid.uuid4().hex[:12]
    ISLER[is_id] = {"durum": "kuyrukta", "tamam": False}
    Thread(target=_backtest_calistir, args=(is_id, istek), daemon=True).start()
    return {"is_id": is_id}


@app.get("/backtest/{is_id}")
def backtest_sonuc(is_id: str):
    if is_id not in ISLER:
        raise HTTPException(404, "iş bulunamadı")
    return ISLER[is_id]


# ══════════════════════════════════════════════════════ eğitmen

@app.get("/egitmen/mufredat")
def egitmen_mufredat():
    """Tüm müfredat: 13 modül. Cihaz bir kez indirip saklar — dersler
    internetsiz okunabilir olmalı.

    `surum` artınca istemci bankayı yeniden indirir. Yeni ders eklenip
    sürüm artmazsa telefon eski müfredatı kullanmaya devam eder ve
    kimse fark etmez. Ders sayısı yanıtta zaten var; docstring'e yazmak
    ikinci bir gerçek kaynağı olur ve o eskir."""
    from cekirdek import egitmen_dersler as ed

    def ders_akit(d: dict) -> dict:
        for alan in ("icerik", "bist", "tuzak", "ornek", "ozet"):
            if d.get(alan):
                d[alan] = metin_akit(d[alan])
        return d

    return {
        "surum": 5,   # m13'e 4 ders eklendi (retest, mum sözlüğü, sicil, zaman serisi)
        "moduller": [
            {
                "kod": m.kod, "ad": m.ad, "aciklama": m.aciklama,
                "seviye": m.seviye,
                "dakika": sum(x.sure for x in m.dersler),
                "dersler": [ders_akit(guvenli(d)) for d in m.dersler],
            }
            for m in ed.MODULLER
        ],
        "toplam_ders": len(ed.TUM_DERSLER),
        "toplam_dakika": sum(d.sure for d in ed.TUM_DERSLER),
    }



@app.get("/egitmen/gunun-dersi")
def egitmen_gunun_dersi(portfoy_adet: int = 0, okunan: str = ""):
    """Bugünün durumuna bağlı tek ders.

    Neden ayrı uç: 65 derslik müfredat ayrı bir iş gibi durduğu için
    açılmıyordu (ölçüldü: 1/65 okunmuş). Ders günün olayına bağlanınca
    ayrı zaman ayırmak gerekmiyor.

    TARAMA ÇALIŞTIRMAZ — her şey ambardan okunur, uç ucuzdur. Sunucu
    durumsuz olduğu için okunan dersler istemciden gelir (`okunan`,
    virgülle ayrılmış ders kodları).
    """
    from cekirdek import ogrenme, egitmen, ambar as _a
    _a.kur()

    ozet = {}
    try:
        ozet = _a.ozet_oku() or {}
    except Exception:
        pass

    try:
        siniflar = ogrenme.strateji_siniflari()
    except Exception:
        siniflar = {}

    # Bugün önerilen sinyal var mı — gün özetindeki listeden
    sinyaller = ozet.get("sinyal_veren") or []
    onerilen = sum(1 for x in sinyaller
                   if x.get("onerilir", x.get("alinabilir", False)))

    kap_sayisi = 0
    try:
        kap_sayisi = sum(1 for h in _a.gun_haberleri(azami=200)
                         if (h.get("kaynak") or "") == "KAP")
    except Exception:
        pass

    durum = egitmen.gunun_durumu(
        tarama={"strateji_durumlari": siniflar, "onerilen": onerilen},
        ozet={**ozet, "kap_bildirim": kap_sayisi},
        portfoy_adet=portfoy_adet)

    okundu = {k.strip(): egitmen.DersKaydi(kod=k.strip(), okundu=True)
              for k in okunan.split(",") if k.strip()}
    ders = egitmen.baglamsal_ders(durum, okundu)
    return guvenli({"ders": ders, "durum": durum})

@app.get("/egitmen/ders/{kod}")
def egitmen_ders(kod: str):
    from cekirdek import egitmen_dersler as ed
    d = ed.ders_getir(kod)
    if d is None:
        raise HTTPException(404, f"'{kod}' dersi bulunamadı")
    m = ed.ders_modulu(d.kod)
    ham = guvenli(d)
    for alan in ("icerik", "bist", "tuzak", "ornek", "ozet"):
        if ham.get(alan):
            ham[alan] = metin_akit(ham[alan])
    from cekirdek.egitmen_gorsel import DERS_GORSEL
    return {"ders": ham,
            "modul": {"kod": m.kod, "ad": m.ad} if m else None,
            # Ekran görseli ayrı uçtan çeker; olmayan ders için boşuna
            # istek atmasın diye burada haber veriyoruz.
            "gorsel_var": kod in DERS_GORSEL}



@app.get("/egitmen/gorsel/{kod}")
def egitmen_gorsel(kod: str):
    """Bir dersin görseli — CANLI veriden üretilir.

    Dersten AYRI uç: bazı görseller (korelasyon) tarama gerektirir ve
    yavaştır. Aynı çağrıya koyarsak ders metni de bekler; oysa metin
    hemen gösterilebilir, grafik sonra düşebilir.
    """
    from cekirdek import egitmen_gorsel as gg
    return guvenli(gg.ders_gorseli(kod))

@app.get("/egitmen/sorular")
def egitmen_sorular():
    """Tüm soru bankası. Cihaz bir kez indirip saklar — aralıklı tekrar
    hesabı telefonda yapılır, böylece sunucusuz da çalışılabilir."""
    from cekirdek import egitmen_sorular as es

    def akit(d: dict) -> dict:
        for alan in ("soru", "cevap", "tuzak", "ipucu"):
            if d.get(alan):
                d[alan] = metin_akit(d[alan])
        return d

    return {
        "surum": 4,
        "sorular": [akit(guvenli(s)) for s in es.TUM_SORULAR],
        "sirket_okuma": [{"anahtar": a, "soru": q, "aciklama": d}
                         for a, q, d in es.SIRKET_OKUMA],
        "alim_oncesi": [{"anahtar": a, "soru": q} for a, q in es.ALIM_ONCESI],
        "ilkeler": es.ILKELER,
    }


class CanliIstek(BaseModel):
    sermaye: float = 1000
    azami: int = 3
    pozisyonlar: list[Pozisyon] = Field(default_factory=list)


@app.post("/egitmen/canli")
def egitmen_canli(istek: CanliIstek):
    """Bugünkü gerçek veriden soru üretir. Statik sınavı yatırımdan ayıran şey."""
    from cekirdek import egitmen as eg
    ra = _risk(istek.sermaye)
    try:
        gecen, _ = tarayici.tara(risk_ayar=ra, gun=500)
        tarama = {"adaylar": [x.sozluk() for x in gecen[:12]]}
    except Exception:
        tarama = None

    try:
        m = makro.durum()
        xu = m.oz("xu100")
        makro_d = {
            "enflasyon": m.enflasyon,
            "bist_reel_getiri_1y": (xu["g365"] - m.enflasyon["yillik"]) if xu else None,
            "gostergeler": {"xu100": {"g365": xu["g365"] if xu else None}},
        }
    except Exception:
        makro_d = None

    sirketler = []
    adaylar = [x.sembol for x in (gecen[:4] if tarama else [])] + ["EREGL", "THYAO"]
    for sem in adaylar:
        try:
            f = temel_veri.finansal_cek(sem)
            if f is None:
                continue
            c = degerleme.carpanlar(f)
            sirketler.append({
                "sembol": f.sembol, "kur_uyusmazligi": f.kur_uyusmazligi,
                "tablo_para": f.tablo_para, "fiyat_para": f.fiyat_para,
                "kalite": temel.kalite_skoru(f),
                "carpanlar": {k: {"deger": v.deger if v.var_mi and v.gecerli else None}
                              for k, v in c.items()},
            })
        except Exception:
            continue

    # Kullanıcının pozisyonları cihazdan gelir
    pozlar = []
    for p in istek.pozisyonlar:
        try:
            df = veri.fiyat_cek(p.sembol, gun=60, onbellek_saat=2.0)
            if df.empty:
                continue
            fiyat = float(df["Close"].iloc[-1])
            pozlar.append({"sembol": p.sembol,
                           "kar_yuzde": (fiyat / p.giris - 1) * 100 if p.giris else 0})
        except Exception:
            continue

    sorular = eg.canli_sorular(tarama, makro_d, sirketler, pozlar, azami=istek.azami)

    def akit(d: dict) -> dict:
        for alan in ("soru", "cevap", "tuzak"):
            if d.get(alan):
                d[alan] = metin_akit(d[alan])
        return d

    return {"sorular": [akit(guvenli(q)) for q in sorular],
            "ilke": eg.ilke_gunun()}


@app.get("/egitmen/sirket-oku/{sembol}")
def egitmen_sirket_oku(sembol: str):
    """Şirket okuma egzersizi: 16 adım + her adımda sistemin ölçtüğü rakam."""
    from cekirdek import egitmen_sorular as es
    f = temel_veri.finansal_cek(sembol)
    if f is None:
        raise HTTPException(404, f"{sembol} için finansal veri yok")
    o = temel.oranlar(f)
    c = degerleme.carpanlar(f)
    dcf = degerleme.ters_dcf(f)

    def oran(k):
        r = o.get(k)
        return f"{r.deger:,.2f}{r.birim}" if r and r.var_mi and r.gecerli else None

    def carp(k):
        r = c.get(k)
        return f"{r.deger:,.2f}" if r and r.var_mi and r.gecerli else None

    veri_notu = {
        "is_modeli": f"{f.ad} · {f.sektor} / {f.sanayi}",
        "gelir_buyume": f"yıllık {oran('hasilat_buyume')} · 3 yıl ortalama "
                        f"{oran('hasilat_cagr3')} — kıyas ölçütü {f.tablo_para} "
                        f"enflasyonu %{f.enflasyon_referansi():.1f}",
        "kar_buyume": f"net kâr {oran('kar_buyume')} · net marj {oran('net_marj')}",
        "borc": f"Net Borç/FAVÖK {oran('net_borc_favok')} · faiz karşılama "
                f"{oran('faiz_karsilama')} · borç/özsermaye {oran('borc_ozsermaye')}",
        "nakit": f"serbest nakit marjı {oran('fcf_marj')} · "
                 f"nakit/net kâr {oran('kar_kalitesi')}",
        "karlilik": f"brüt {oran('brut_marj')} · faaliyet {oran('faaliyet_marj')} · "
                    f"ROE {oran('roe')} · ROIC {oran('roic')}",
        "sektor": sektor.sektor_bilgi(f.sektor)["rehber"],
        "pahali_mi": f"F/K {carp('fk')} · PD/DD {carp('pd_dd')} · "
                     f"FD/FAVÖK {carp('fd_favok')} · FCF verimi {carp('fcf_verim')}",
        "ucuz_mu": dcf.get("yorum") or dcf.get("hata"),
    }

    return {
        "sembol": f.sembol, "ad": f.ad,
        "adimlar": [{"anahtar": a, "soru": q, "aciklama": d,
                     "veri": veri_notu.get(a)}
                    for a, q, d in es.SIRKET_OKUMA],
        "kalite": guvenli(temel.kalite_skoru(f, o)),
        "bayraklar": temel.kirmizi_bayraklar(f, o),
    }


# ══════════════════════════════════════════════════════ günlük iş & öğrenme

@app.get("/gunluk/ozet")
def gunluk_ozet(tarih: str | None = None):
    """Kaydedilmiş gün özeti: piyasa genişliği, hareket edenler, rejim, sinyaller."""
    from cekirdek import ambar
    ambar.kur()
    o = ambar.ozet_oku(tarih)
    if o is None:
        raise HTTPException(404, "Kayıtlı gün özeti yok — günlük iş henüz çalışmadı")
    return {"ozet": guvenli(o), "tarihler": ambar.ozet_tarihleri(20)}


@app.get("/gunluk/hisse/{sembol}")
def gunluk_hisse(sembol: str, gun: int = 15):
    """Bir hissenin günlük seyri (dün → bugün) ve haberleri."""
    from cekirdek import gunluk
    return guvenli(gunluk.degisim_raporu(sembol, gun))


@app.get("/gunluk/haberler")
def gunluk_haberler(tarih: str | None = None, azami: int = 40):
    from cekirdek import ambar, haber
    ambar.kur()
    haberler = ambar.gun_haberleri(tarih, azami=azami)
    return {"haberler": guvenli(haberler),
            "kaynaklar": list(haber.KAYNAKLAR),
            "not": "Türkçe finans beslemeleri genel ekonomi yayınlar; çoğu gün "
                   "çoğu hisse için haber çıkmaz. KAP entegre değildir."}


@app.get("/gunluk/karne")
def gunluk_karne():
    """Sistemin canlı sicili — backtest değil, gerçek sinyal sonuçları."""
    from cekirdek import ogrenme, ambar
    ambar.kur()
    return guvenli({
        "karne": ogrenme.karne(),
        "kayma": ogrenme.kayma_analizi(),
        "filtre": ogrenme.filtre_etkisi(),
        "kapsam": ogrenme.olcum_kapsami(),
        "uyarilar": ogrenme.KIYAS_UYARILARI,
    })


@app.get("/gunluk/durum")
def gunluk_durum():
    from cekirdek import ai, ambar, gunluk
    ambar.kur()
    acik, sebep = gunluk.islem_gunu_mu()
    ai_ok, ai_sebep = ai.kullanilabilir()
    return guvenli({
        "islem_gunu": acik, "sebep": sebep,
        "ambar": ambar.istatistik(),
        "son_calismalar": ambar.son_calismalar(5),
        # AI harcaması burada görünsün: para gidiyorsa sistem durumunun
        # parçasıdır, ayrı bir yerde saklanmamalı.
        "ai": {**ai.butce_durumu(), "hazir": ai_ok, "durum": ai_sebep,
               "dokum": ambar.ai_dokum()},
    })


class DoldurIstek(BaseModel):
    gun: int = 90
    sermaye: float = 1000


@app.post("/gunluk/calistir")
def gunluk_calistir_uc(istek: DoldurIstek):
    """Günlük işi arka planda çalıştırır (elle tetikleme)."""
    from cekirdek import gunluk as gj
    is_id = uuid.uuid4().hex[:12]
    ISLER[is_id] = {"durum": "kuyrukta", "tamam": False}

    def _calis():
        try:
            ISLER[is_id]["durum"] = "çalışıyor"
            r = gj.calistir(sermaye=istek.sermaye, sessiz=True)
            ISLER[is_id].update(durum="bitti", tamam=True, sonuc=guvenli(r))
        except Exception as e:
            ISLER[is_id].update(durum="hata", tamam=True, hata=str(e)[:300])

    Thread(target=_calis, daemon=True).start()
    return {"is_id": is_id}



@app.get("/defter")
def defter_oku(kagit: bool | None = None):
    """Karar günlüğü — kullanıcının kendi sicili.

    `/gunluk/karne` SİSTEMİN sinyallerini ölçer; bu uç KULLANICININ
    kararlarını. İkisi ayrı tutulur çünkü ölçülmek istenen şey aradaki
    farktır: sistem ne önerdi, sen ne yaptın.

    Kayıtlar bot üzerinden girilir (/aldim, /sattim) ve sunucuda yaşar —
    portföy hesabı hâlâ telefonda, bu yalnızca KARAR kaydı.
    """
    from cekirdek import defter
    return guvenli({
        "karne": defter.karne(kagit),
        "acik": defter.acik_pozisyonlar(kagit),
        "kapali": defter.kapali_islemler(kagit)[-30:],
    })


class DefterAlim(BaseModel):
    sembol: str
    fiyat: float
    adet: int = 1
    kagit: bool = True
    stop: float = 0.0
    hedef: float = 0.0
    gerekce: str = ""


class DefterSatim(BaseModel):
    sembol: str
    fiyat: float
    adet: int = 0          # 0 = tamamı
    gerekce: str = ""


@app.post("/defter/alim")
def defter_alim(istek: DefterAlim):
    """Alım kararını günlüğe yazar.

    Sunucu artık pozisyonlar için TEK KAYNAK. Eskiden telefon kendi
    listesini tutuyordu; iki kaynak birbirinden sapabildiği için defter
    tek doğru kabul edildi. Telefon yerel kopyayı yalnızca çevrimdışı
    okumak için saklar.
    """
    from cekirdek import defter, izleme
    k = defter.alim(istek.sembol, istek.fiyat, istek.adet,
                    kagit=istek.kagit, stop=istek.stop, hedef=istek.hedef,
                    gerekce=istek.gerekce)
    # Stop varsa izleme kendiliğinden başlar — ayrı bir adım olsaydı
    # unutulurdu ve tam da unutulan pozisyonlar zarar ettirir.
    if istek.stop:
        izleme.ekle(k["sembol"], istek.stop, istek.hedef, istek.fiyat)
    return guvenli({"karar": k, "acik": defter.acik_pozisyonlar()})


@app.post("/defter/satim")
def defter_satim(istek: DefterSatim):
    from cekirdek import defter, izleme
    k = defter.satim(istek.sembol, istek.fiyat, istek.adet,
                     gerekce=istek.gerekce)
    if k.get("hata"):
        raise HTTPException(400, k["hata"])
    if not defter.acik_pozisyon(istek.sembol):
        izleme.sil(istek.sembol)
    return guvenli({"karar": k, "acik": defter.acik_pozisyonlar()})

# ══════════════════════════════════════════════════════ hesap ve bulut yedeği
#
# Bu katman API'nin durumsuzluğunu BOZMUYOR: tarama, risk, backtest hâlâ
# gönderdiğin veriyle hesaplıyor ve hiçbir şey hatırlamıyor. Sunucunun
# sakladığı tek şey telefonun durumunun bir KOPYASI — geri yükleme noktası.
#
# Uçlar mevcut API anahtarı kapısının ARKASINDA. Yani buraya ulaşmak için
# önce anahtar, sonra jeton gerekiyor; parola katmanı onun yerine değil,
# üstüne. Caddy TLS verdiği için parola düz metin gitmiyor.


class KayitIstek(BaseModel):
    eposta: str
    parola: str
    cihaz: str = ""


class ParolaIstek(BaseModel):
    eski: str
    yeni: str


class YedekIstek(BaseModel):
    icerik: dict
    cihaz: str = ""
    # İstemcinin elindeki sürüm. Sunucudaki daha yeniyse yazma reddedilir —
    # bir hafta açılmamış ikinci telefon güncel yedeği ezmesin.
    beklenen_surum: int | None = None


def _kullanici(authorization: str | None) -> int:
    """Bearer jetonundan kullanıcı id'si. Geçersizse 401."""
    from cekirdek import hesap
    jeton = ""
    if authorization and authorization.lower().startswith("bearer "):
        jeton = authorization[7:].strip()
    kid = hesap.jeton_dogrula(jeton)
    if kid is None:
        raise HTTPException(401, "Oturum geçersiz ya da süresi dolmuş.")
    return kid


@app.post("/hesap/kayit")
def hesap_kayit(istek: KayitIstek):
    from cekirdek import hesap
    try:
        return hesap.kayit(istek.eposta, istek.parola, istek.cihaz)
    except hesap.HesapHata as e:
        raise HTTPException(400, str(e))


@app.post("/hesap/giris")
def hesap_giris(istek: KayitIstek):
    from cekirdek import hesap
    try:
        return hesap.giris(istek.eposta, istek.parola, istek.cihaz)
    except hesap.HesapHata as e:
        # 401 değil 400: "kilitlendin" ile "parola yanlış" ikisi de burada
        # ve istemci ikisini de kullanıcıya aynı şekilde gösteriyor.
        raise HTTPException(400, str(e))


@app.post("/hesap/cikis")
def hesap_cikis(authorization: str | None = Header(default=None)):
    from cekirdek import hesap
    jeton = authorization[7:].strip() if (
        authorization and authorization.lower().startswith("bearer ")) else ""
    return {"dustu": hesap.cikis(jeton)}


@app.get("/hesap")
def hesap_bilgi(authorization: str | None = Header(default=None)):
    from cekirdek import hesap
    return hesap.bilgi(_kullanici(authorization))


@app.post("/hesap/parola")
def hesap_parola(istek: ParolaIstek,
                 authorization: str | None = Header(default=None)):
    from cekirdek import hesap
    kid = _kullanici(authorization)
    try:
        hesap.parola_degistir(kid, istek.eski, istek.yeni)
    except hesap.HesapHata as e:
        raise HTTPException(400, str(e))
    # Tüm oturumlar düştü; istemci yeniden giriş yapmalı.
    return {"degisti": True, "yeniden_giris_gerekli": True}


# ══════════════════════════════════════════════════════ alıştırma kum havuzu
#
# Durum TELEFONDA: bakiye, pozisyonlar ve görev ilerlemesi orada yaşıyor ve
# bulut yedeğiyle taşınıyor. Sunucu yalnızca fiyat veriyor ve çıkış
# kurallarını uyguluyor — API'nin durumsuzluğu korunuyor.
#
# Çıkış kurallarının sunucuda olması bilinçli: aynı kurallar backtest'te de
# var ve İKİ YERDE kopyalanırsa biri sessizce kayar. Alıştırmada stop başka
# türlü çalışırsa kullanıcı yanlış şey öğrenir.


class IlerletIstek(BaseModel):
    tarih: str
    pozisyonlar: list[dict] = Field(default_factory=list)
    semboller: list[str] = Field(default_factory=list)


@app.get("/alistirma/gorevler")
def alistirma_gorevler():
    """Rehberli görevler. Müfredat gibi bir kez indirilip saklanır."""
    from cekirdek import alistirma_gorevler as ag

    def akit(g) -> dict:
        d = guvenli(g.__dict__.copy())
        for alan in ("anlatim", "aciklama"):
            if d.get(alan):
                d[alan] = metin_akit(d[alan])
        return d

    return {"surum": 1, "baslangic_bakiye": __import__(
                "cekirdek.alistirma", fromlist=["x"]).BASLANGIC_BAKIYE,
            "gorevler": [akit(g) for g in ag.GOREVLER]}


@app.get("/alistirma/gun")
def alistirma_gun(sembol: str, tarih: str | None = None):
    """Tek günün barı. Tarih işlem günü değilse önceki işlem günü döner."""
    from cekirdek import alistirma
    b = alistirma.gun(sembol.upper().strip(), tarih)
    if b is None:
        raise HTTPException(404, f"{sembol} için {tarih or 'bugün'} verisi yok")
    return guvenli(b.sozluk())


@app.post("/alistirma/ilerlet")
def alistirma_ilerlet(istek: IlerletIstek):
    """Bir işlem günü ileri gider ve stop/hedef çalıştı mı söyler.

    Farklı hisselerin işlem takvimi teoride ayrışabilir; bu yüzden yeni
    tarih, tüm sembollerin bir sonraki gününün EN ERKENİ olarak seçiliyor
    ve herkes o tarihe hizalanıyor. Aksi halde pozisyonlar farklı günlerde
    yaşar ve kum havuzunun zamanı tutarsızlaşırdı.
    """
    from cekirdek import alistirma

    semboller = list({(p.get("sembol") or "").upper()
                      for p in istek.pozisyonlar if p.get("sembol")}
                     | {s.upper() for s in istek.semboller if s})
    if not semboller:
        raise HTTPException(400, "en az bir sembol gerekir")

    adaylar = []
    for sem in semboller:
        b = alistirma.sonraki_gun(sem, istek.tarih)
        if b:
            adaylar.append(b.tarih)
    if not adaylar:
        raise HTTPException(404, "ileride işlem günü yok "
                                 "(geçmiş modunda bugüne ulaştın)")
    yeni_tarih = min(adaylar)

    fiyatlar, cikislar = {}, []
    for sem in semboller:
        b = alistirma.gun(sem, yeni_tarih)
        if b is None or b.tarih != yeni_tarih:
            continue
        fiyatlar[sem] = b.sozluk()
        for poz in istek.pozisyonlar:
            if (poz.get("sembol") or "").upper() != sem:
                continue
            c = alistirma.cikis_kontrol(poz, b)
            if c:
                cikislar.append({"sembol": c.sembol, "fiyat": round(c.fiyat, 4),
                                 "sebep": c.sebep, "tarih": c.tarih})

    return guvenli({"tarih": yeni_tarih, "fiyatlar": fiyatlar,
                    "cikislar": cikislar})


@app.get("/alistirma/adet")
def alistirma_adet(bakiye: float, fiyat: float, stop: float,
                   risk_yuzde: float = 1.5, azami_pozisyon: float = 35.0):
    """Pozisyon boyutu — uygulamanın gerçek hesabının aynısı."""
    from cekirdek import alistirma
    return guvenli(alistirma.adet_oner(bakiye, fiyat, stop,
                                       risk_yuzde, azami_pozisyon))


class CihazIstek(BaseModel):
    jeton: str
    platform: str = ""


@app.post("/cihaz")
def cihaz_kaydet(istek: CihazIstek,
                 authorization: str | None = Header(default=None)):
    """Push jetonunu kaydeder. İstemci HER AÇILIŞTA çağırır.

    Firebase jetonu kalıcı değil: uygulama yeniden kurulunca, veri
    temizlenince ya da kendiliğinden yenilenebilir. Tek seferlik kayıt
    yapsaydık jeton yenilendiği gün bildirimler sessizce kesilirdi."""
    from cekirdek import cihaz
    kid = _kullanici(authorization)
    r = cihaz.kaydet(kid, istek.jeton, istek.platform)
    if not r.get("kayitli"):
        raise HTTPException(400, r.get("not", "jeton kaydedilemedi"))
    return {**r, "cihaz_sayisi": len(cihaz.liste(kid))}


@app.delete("/cihaz")
def cihaz_sil(jeton: str = Query(...),
              authorization: str | None = Header(default=None)):
    """Çıkış yaparken çağrılır — bu telefona artık bildirim gitmesin."""
    from cekirdek import cihaz
    _kullanici(authorization)
    return {"silindi": cihaz.sil(jeton)}


@app.get("/bildirim/durum")
def bildirim_durum(authorization: str | None = Header(default=None)):
    """Hangi kanallar açık ve kaç cihaz kayıtlı. Hesap ekranı gösteriyor."""
    from cekirdek import cihaz, haberci
    kid = _kullanici(authorization)
    return {"kanallar": haberci.acik_kanallar(),
            "cihazlar": cihaz.liste(kid)}


@app.get("/yedek")
def yedek_getir(authorization: str | None = Header(default=None)):
    from cekirdek import hesap
    y = hesap.yedek_oku(_kullanici(authorization))
    if y is None:
        return {"var": False}
    return {"var": True, **y}


@app.put("/yedek")
def yedek_koy(istek: YedekIstek,
              authorization: str | None = Header(default=None)):
    from cekirdek import hesap
    kid = _kullanici(authorization)
    try:
        return hesap.yedek_yaz(kid, istek.icerik, istek.cihaz,
                               beklenen_surum=istek.beklenen_surum)
    except hesap.HesapHata as e:
        raise HTTPException(400, str(e))


@app.get("/sozluk")
def sozluk():
    """Uygulama sözlüğü: ekranlarda geçen terimlerin karşılıkları.

    Müfredat gibi bir kez indirilip saklanır — sözlüğe en çok bakılacak
    an, tarama ekranında bir sütuna takıldığın andır ve o an internet
    olmayabilir. `surum` artınca istemci yeniden indirir.

    `kolonlar` alanı istemcinin sütun başlığından terime gitmesini
    sağlar: kullanıcı 'GG60' başlığına dokunur, ekran 'Göreli güç'
    maddesini açar.
    """
    from cekirdek import sozluk as sz

    def terim_akit(t) -> dict:
        return {
            "terim": t.terim,
            "kisa": t.kisa,
            "aciklama": metin_akit(t.aciklama) if t.aciklama else "",
            "nerede": metin_akit(t.nerede) if t.nerede else "",
            "ders": t.ders,
            "kolonlar": t.kolonlar,
        }

    return {
        "surum": 1,
        "bolumler": [
            {"kod": b.kod, "ad": b.ad, "aciklama": b.aciklama,
             "terimler": [terim_akit(t) for t in b.terimler]}
            for b in sz.BOLUMLER
        ],
        "toplam_terim": len(sz.TUM_TERIMLER),
    }


@app.get("/sozluk/{ad}")
def sozluk_terim(ad: str):
    """Tek terim — sütun başlığı ('ATR_yuzde') ya da terim adı ile."""
    from cekirdek import sozluk as sz
    t = sz.terim_getir(ad)
    if t is None:
        eslesen = sz.ara(ad)
        if not eslesen:
            raise HTTPException(404, f"{ad} sözlükte yok")
        t = eslesen[0]
    return {"terim": t.terim, "kisa": t.kisa,
            "aciklama": metin_akit(t.aciklama) if t.aciklama else "",
            "nerede": metin_akit(t.nerede) if t.nerede else "",
            "ders": t.ders, "kolonlar": t.kolonlar}


@app.get("/stratejiler")
def stratejiler():
    return {"stratejiler": [{"ad": a, "aciklama": s.aciklama,
                             "azami_tutma": s.azami_tutma,
                             "atr_stop_kat": s.atr_stop_kat,
                             "atr_hedef_kat": s.atr_hedef_kat}
                            for a, s in STRATEJILER.items()]}
