"""Günlük iş: BIST kapanışından sonra çalışır, veriyi toplar, ölçer, kaydeder.

BIST 18:00'de kapanır. İş 18:10'da çalışacak şekilde tasarlandı — veri
sağlayıcının kapanış fiyatını işlemesi için birkaç dakika payı var.

Ne yapar:
  1. Tüm BIST 100 hisselerinin taze fiyatını çeker
  2. Göstergeleri ve skorları hesaplar
  3. Günlük anlık görüntüyü ambara yazar (dün → bugün değişimiyle)
  4. Türkçe finans beslemelerinden haber toplar, hisselere eşler
  5. Bugünkü sinyalleri kaydeder
  6. Geçmiş sinyallerin 1/5/20 günlük sonucunu ölçer  ← ASIL ÖĞRENME
  7. Günün özetini çıkarır ve saklar

Ne YAPMAZ: internetten okuyup "daha iyi analist" olmaz. Öğrenme dediğimiz şey,
kendi sinyallerinin sonucunu ölçüp sicil biriktirmesidir.
"""
from __future__ import annotations

import os

import traceback
from datetime import date, datetime

import numpy as np

from . import (ambar, dogrulama, haber, haber_ai, haber_esleme, kap, ogrenme, tarayici, makro, sektor,
               temel_veri, evren, veri)
from .risk import RiskAyarlari


# BIST 2026 resmi tatilleri (Borsa İstanbul tatil tablosu)
TATILLER_2026 = {
    "2026-01-01", "2026-03-19", "2026-03-20", "2026-03-21", "2026-04-23",
    "2026-05-01", "2026-05-19", "2026-05-26", "2026-05-27", "2026-05-28",
    "2026-05-29", "2026-07-15", "2026-08-30", "2026-10-29",
}


def islem_gunu_mu(gun: date | None = None) -> tuple[bool, str]:
    """BIST bugün açık mı? Kapalıysa iş boşuna çalışmamalı.

    Tatil listesi yıllık güncellenmelidir; eksikse iş çalışır ve önceki günün
    verisini tekrar yazar — zararsız ama gereksizdir.
    """
    g = gun or date.today()
    if g.weekday() >= 5:
        return False, "hafta sonu"
    if g.isoformat() in TATILLER_2026:
        return False, "resmi tatil"
    return True, "işlem günü"


def _ad_haritasi(semboller: list[str]) -> dict[str, str]:
    """Haber eşleştirmesi için şirket uzun adları (haftalık önbellekten)."""
    harita = {}
    for s in semboller:
        try:
            f = temel_veri.finansal_cek(s, onbellek_saat=168.0)
            if f and f.ad:
                harita[s] = f.ad
        except Exception:
            continue
    return harita


def calistir(sermaye: float = 1000.0, evren_adi: str = "bist100",
             haber_topla: bool = True, sessiz: bool = False,
             tatilde_calis: bool = False, ai_haber: bool | None = None) -> dict:
    """Günlük işi baştan sona çalıştırır ve özet döndürür.

    ai_haber: haberleri Claude ile de sınıflandır. None ise MIDAS_AI_HABER
    ortam değişkenine bakılır (varsayılan kapalı — bkz. aşağıdaki not).
    Anahtar yoksa ya da aylık bütçe dolduysa zaten atlanır; kelime eşlemesi
    taban olarak çalışmaya devam eder.

    NEDEN VARSAYILAN KAPALI: 2026-08-25 ölçümü — 95 gerçek haberde AI katmanı
    yalnızca 1 eşleşme ekledi ve o eşleşme YANLIŞTI (Marmarabirlik → ULKER).
    Sebep sınıflandırıcı değil, kaynak: mevcut 5 RSS beslemesi genel ekonomi
    yayınlıyor, BIST şirket haberi taşımıyor. Kaynak düzelmeden bu katman
    para harcayıp değer üretmez. Açmak için: MIDAS_AI_HABER=1
    """
    if ai_haber is None:
        ai_haber = os.environ.get("MIDAS_AI_HABER", "0").strip() in ("1", "true", "evet")
    acik, sebep = islem_gunu_mu()
    if not acik and not tatilde_calis:
        if not sessiz:
            print(f"BIST bugün kapalı ({sebep}) — iş atlandı.")
        return {"tarih": date.today().isoformat(), "durum": "atlandi",
                "sebep": sebep}
    ambar.kur()
    is_id = ambar.calisma_basla()
    bugun = date.today().isoformat()
    rapor = {"tarih": bugun, "adimlar": {}}

    def yaz(m: str):
        if not sessiz:
            print(m, flush=True)

    try:
        # ── 1) FİYAT VE GÖSTERGELER
        yaz("» 1/6  Fiyat verisi çekiliyor...")
        ra = RiskAyarlari(sermaye=sermaye)
        gecen, elenen = tarayici.tara(evren_adi=evren_adi, risk_ayar=ra,
                                      gun=500, onbellek_saat=0.0)
        yaz(f"       {len(gecen)} hisse filtreyi geçti, {len(elenen)} elendi")

        # ── 2) ANLIK GÖRÜNTÜ (dün → bugün)
        yaz("» 2/6  Günlük anlık görüntü yazılıyor...")
        satirlar, gunun_tarihi = [], None
        for a in gecen + elenen:
            df = veri.fiyat_cek(a.sembol, gun=30, onbellek_saat=6.0)
            if df.empty or len(df) < 2:
                continue
            son, onceki = df.iloc[-1], df.iloc[-2]
            t = df.index[-1].date().isoformat()
            gunun_tarihi = gunun_tarihi or t
            satirlar.append({
                "tarih": t, "sembol": a.sembol,
                "kapanis": float(son["Close"]), "acilis": float(son["Open"]),
                "yuksek": float(son["High"]), "dusuk": float(son["Low"]),
                "hacim": float(son["Volume"]),
                "onceki": float(onceki["Close"]),
                "degisim": round((float(son["Close"]) / float(onceki["Close"]) - 1) * 100, 3),
                "tl_hacim": float(a.tl_hacim),
                "rsi": float(a.rsi), "adx": float(a.adx),
                "atr_yuzde": float(a.atr_yuzde),
                "sma200_ustu": 1 if a.sma200_ustu else 0,
                "skor": float(a.skor),
            })
        n = ambar.fiyat_yaz(satirlar)
        gunun_tarihi = gunun_tarihi or bugun
        rapor["adimlar"]["fiyat"] = n
        yaz(f"       {n} hisse kaydedildi ({gunun_tarihi})")

        # ── 2b) İKİNCİ KAYNAKLA ÇAPRAZ KONTROL
        # Sadece filtreyi GEÇENLER kontrol edilir: bozuk fiyatın tehlikeli
        # olduğu tek yer, o hisseye sinyal üretilmesidir. 100 hissenin
        # tamamını sorgulamak hem yavaş hem gereksiz.
        #
        # Yakaladığı sorun sınıfı gerçek: yfinance bazı BIST bedelsiz/
        # sermaye işlemlerini bilmiyor ve geçmişi düzeltmiyor; seride sahte
        # bir uçurum kalıyor (2026-08-25'te CVKMD'de %61 sapma böyle bulundu).
        try:
            def _kapanislar(sem: str) -> dict:
                d = veri.fiyat_cek(sem, gun=90, onbellek_saat=6.0)
                if d is None or d.empty:
                    return {}
                return {t.date().isoformat(): float(v)
                        for t, v in d["Close"].items()}

            # İstek sayısını sınırla: aday listesi uzunsa en yüksek skorlular.
            adaylar = [a.sembol for a in sorted(
                gecen, key=lambda x: float(x.skor), reverse=True)][:30]
            sapmalar = dogrulama.capraz_kontrol(adaylar, _kapanislar, gun=30)
            rapor["adimlar"]["capraz_kontrol"] = {
                "bakilan": len(adaylar), "sapan": len(sapmalar),
                "sapmalar": sapmalar[:10]}
            if sapmalar:
                yaz(f"       ⚠ {len(sapmalar)}/{len(adaylar)} hissede ikinci "
                    f"kaynakla sapma — bu hisselerin verisi şüpheli:")
                for x in sapmalar[:5]:
                    yaz(f"         {x['sembol']:10} azami %{x['azami_fark_yuzde']} "
                        f"({x['gun']}: yf={x['yfinance']} iy={x['isyatirim']})")
            else:
                yaz(f"       çapraz kontrol: {len(adaylar)} adayın hepsi ikinci "
                    f"kaynakla örtüşüyor")
        except Exception as e:
            rapor["adimlar"]["capraz_kontrol"] = {"hata": str(e)[:200]}
            yaz(f"       çapraz kontrol atlandı: {str(e)[:80]}")

        # ── 3) HABER
        if haber_topla:
            yaz("» 3/6  Haber toplanıyor...")
            try:
                haberler = haber.topla()
                semboller_h = evren.evren_getir(evren_adi)
                es = haber_esleme.Eslestirici(_ad_haritasi(semboller_h))
                eslesme = haber.eslestir(haberler, es)
                makro_h = haber.makro_haberler(haberler)

                # AI katmanı: kelime eşlemesi TABAN, model üstüne ekler.
                # Model çökse ya da bütçe dolsa da eski davranış aynen sürer.
                ai_bilgi = None
                if ai_haber:
                    ai_es, ai_hata = haber_ai.sinifla(haberler, semboller_h)
                    if ai_hata:
                        ai_bilgi = {"hata": ai_hata[:120]}
                        yaz(f"       AI haber katmanı atlandı: {ai_hata[:70]}")
                    else:
                        eslesme, ai_bilgi = haber_ai.birlestir(eslesme, ai_es)

                hn, en = ambar.haber_yaz(haberler, eslesme)
                rapor["adimlar"]["haber"] = {
                    "toplanan": hn, "hisse_eslesmesi": en,
                    "makro": len(makro_h), "ai": ai_bilgi}
                ek = ""
                if ai_bilgi and "ai_yeni" in ai_bilgi:
                    ek = (f" (kelime {ai_bilgi['kelime']} + AI "
                          f"{ai_bilgi['ai_yeni']}, önemli {ai_bilgi['ai_onemli']})")
                yaz(f"       {hn} haber · {en} hisse eşleşmesi{ek} · "
                    f"{len(makro_h)} makro")
            except Exception as e:
                rapor["adimlar"]["haber"] = {"hata": str(e)[:200]}
                yaz(f"       haber toplanamadı: {str(e)[:80]}")

            # KAP ayrı kabukta: RSS çökerse bildirimler yine gelsin. RSS
            # kaynakları BIST şirket haberi taşımıyor, asıl değer burada.
            try:
                # asgari_onem=2: yalnızca rutin ihraç/form bildirimleri elenir.
                # Tanınmayan konu 2 döner, yani yeni bir konu türü sessizce
                # kaybolmaz.
                k_kayit, k_esles = kap.topla(asgari_onem=2, sessiz=sessiz)
                if k_kayit:
                    # _onem haber tablosunda yok: sayımı yap ve kaydı temizle.
                    onemli = sum(x.pop("_onem", 2) >= 3 for x in k_kayit)
                    kn, ken = ambar.haber_yaz(k_kayit, k_esles)
                    rapor["adimlar"]["kap"] = {
                        "bildirim": kn, "hisse_eslesmesi": ken, "onemli": onemli}
                    yaz(f"       KAP: {kn} bildirim · {ken} hisse eşleşmesi · "
                        f"{onemli} yüksek önem")
                else:
                    rapor["adimlar"]["kap"] = {"bildirim": 0}
                    yaz("       KAP: bildirim alınamadı")
            except Exception as e:
                rapor["adimlar"]["kap"] = {"hata": str(e)[:200]}
                yaz(f"       KAP alınamadı: {str(e)[:80]}")
        else:
            rapor["adimlar"]["haber"] = {"atlandi": True}
            rapor["adimlar"]["kap"] = {"atlandi": True}

        # ── 4) SİNYALLERİ KAYDET
        yaz("» 4/6  Sinyaller kaydediliyor...")
        sn = ogrenme.sinyalleri_kaydet(gunun_tarihi, gecen)
        rapor["adimlar"]["sinyal"] = sn
        yaz(f"       {sn} sinyal kaydedildi")

        # ── 5) GEÇMİŞ SİNYALLERİN SONUCUNU ÖLÇ
        yaz("» 5/6  Geçmiş sinyallerin sonucu ölçülüyor...")
        olculen = ogrenme.sonuclari_olc(sessiz=sessiz)
        rapor["adimlar"]["sonuc"] = olculen
        yaz(f"       {sum(olculen.values())} sinyal sonuçlandı "
            f"(vadeler: {olculen})")

        # ── 6) GÜNÜN ÖZETİ
        yaz("» 6/6  Gün özeti çıkarılıyor...")
        ozet = gun_ozeti(gunun_tarihi, gecen, sermaye)
        ambar.ozet_yaz(gunun_tarihi, ozet)
        rapor["ozet"] = ozet
        yaz(f"       {ozet['yukselen']} yükselen · {ozet['dusen']} düşen · "
            f"XU100 {ozet.get('endeks_degisim', 0):+.2f}%")

        ambar.calisma_bitir(is_id, "başarılı",
                            f"{n} fiyat, {sn} sinyal, "
                            f"{sum(olculen.values())} sonuç")
        rapor["durum"] = "başarılı"

        # ── 7) BİLDİRİM
        # En sonda ve kendi kabuğunda: özet ambara YAZILDIKTAN sonra
        # gönderilir. Telegram çökerse günlük iş başarılı sayılmalı —
        # bildirim işin kendisi değil, üstüne eklenen katman.
        try:
            from . import bildirim as _b, telegram as _t
            if _t.kurulu_mu():
                try:
                    _siniflar = ogrenme.strateji_siniflari()
                except Exception:
                    _siniflar = {}
                _ozet = dict(ozet)
                _ozet["kap_bildirim"] = (rapor["adimlar"].get("kap") or {}).get(
                    "bildirim", 0)
                if _t.gonder(_b.gunluk_ozet(_ozet, _siniflar)):
                    yaz("       Telegram bildirimi gönderildi")
                    rapor["adimlar"]["bildirim"] = {"gonderildi": True}
                else:
                    rapor["adimlar"]["bildirim"] = {"gonderildi": False}
        except Exception as e:
            rapor["adimlar"]["bildirim"] = {"hata": str(e)[:150]}

        return rapor

    except Exception as e:
        iz = traceback.format_exc()[-1500:]
        ambar.calisma_bitir(is_id, "hata", iz)
        rapor["durum"] = "hata"
        rapor["hata"] = str(e)[:300]
        yaz(f"  HATA: {str(e)[:200]}")
        return rapor


def gun_ozeti(tarih: str, adaylar: list, sermaye: float) -> dict:
    """Günün piyasa özeti: hareket edenler, genişlik, sektör, rejim."""
    fiyatlar = ambar.gun_fiyatlari(tarih)
    if not fiyatlar:
        return {"tarih": tarih, "hata": "fiyat verisi yok"}

    # Sicili zayıf stratejiler. Hata durumunda boş küme: karantina
    # bilinemiyorsa sinyali gizlemek değil, işaretsiz göstermek doğrusu —
    # eksik bilgi yüzünden sinyali saklamak kullanıcıyı daha çok yanıltır.
    try:
        _onerilmeyen = {k for k, v in ogrenme.strateji_siniflari().items()
                        if not v.get("onerilir", True)}
    except Exception:
        _onerilmeyen = set()

    degisimler = [f["degisim"] for f in fiyatlar if f["degisim"] is not None]
    yukselen = sum(1 for d in degisimler if d > 0)
    dusen = sum(1 for d in degisimler if d < 0)

    ozet = {
        "tarih": tarih,
        "hisse_sayisi": len(fiyatlar),
        "yukselen": yukselen, "dusen": dusen,
        "yatay": len(degisimler) - yukselen - dusen,
        "genislik": round(yukselen / max(1, len(degisimler)) * 100, 1),
        "ortalama_degisim": round(float(np.mean(degisimler)), 2) if degisimler else 0,
        "medyan_degisim": round(float(np.median(degisimler)), 2) if degisimler else 0,
        "en_cok_artan": [
            {"sembol": f["sembol"], "degisim": f["degisim"],
             "kapanis": f["kapanis"], "onceki": f["onceki"]}
            for f in fiyatlar[:6]],
        "en_cok_azalan": [
            {"sembol": f["sembol"], "degisim": f["degisim"],
             "kapanis": f["kapanis"], "onceki": f["onceki"]}
            for f in fiyatlar[-6:][::-1]],
        "sinyal_veren": [
            {"sembol": a.sembol, "skor": a.skor, "sinyaller": a.sinyaller,
             "fiyat": a.fiyat,
             "alinabilir": bool(a.pozisyon and a.pozisyon.uygulanabilir),
             # Gün özeti taramadan AYRI bir ekran; karantina orada da
             # görünmezse kullanıcı zayıf sicilli sinyali onaylanmış sanır.
             "karantina": [x for x in (a.sinyaller or []) if x in _onerilmeyen],
             "onerilir": bool([x for x in (a.sinyaller or [])
                               if x not in _onerilmeyen])}
            for a in adaylar if a.sinyaller][:10],
    }

    # Endeks
    try:
        x = veri.fiyat_cek("XU100", gun=30, onbellek_saat=6.0)
        if len(x) >= 2:
            ozet["endeks"] = round(float(x["Close"].iloc[-1]), 2)
            ozet["endeks_degisim"] = round(
                (float(x["Close"].iloc[-1]) / float(x["Close"].iloc[-2]) - 1) * 100, 2)
    except Exception:
        pass

    # Makro rejim
    try:
        m = makro.durum(onbellek_saat=1.0)
        r = makro.rejim(m)
        xu = m.oz("xu100")
        ozet["rejim"] = {"ad": r["rejim"], "puan": r["puan"],
                         "aciklama": r["aciklama"], "notlar": r["notlar"]}
        ozet["enflasyon"] = m.enflasyon
        if xu:
            ozet["bist_reel_1y"] = round(xu["g365"] - m.enflasyon["yillik"], 2)
    except Exception:
        pass

    # Sektör
    try:
        d = sektor.endeks_performans(onbellek_saat=6.0)
        if not d.empty:
            ozet["sektor_lider"] = [
                {"sektor": r["sektor"], "gg60": round(float(r["gg60"]), 1)}
                for _, r in d.head(3).iterrows()]
            ozet["sektor_geciken"] = [
                {"sektor": r["sektor"], "gg60": round(float(r["gg60"]), 1)}
                for _, r in d.tail(3).iterrows()][::-1]
    except Exception:
        pass

    # Haberi olan hisseler
    try:
        haberli = {}
        for h in ambar.gun_haberleri(tarih, azami=120):
            ifadeler = h.get("ifadeler") or {}
            for s in h.get("hisseler", []):
                haberli.setdefault(s, []).append(
                    haber_esleme.ilgili_parca(h["baslik"], ifadeler.get(s, "")))
        ozet["haberli_hisseler"] = {k: v[:2] for k, v in list(haberli.items())[:10]}
    except Exception:
        pass

    # Kendi sicilimiz
    try:
        ozet["karne"] = ogrenme.karne()
    except Exception:
        pass

    return ozet


def _haber_kirp(haberler: list[dict]) -> list[dict]:
    """Derleme başlıklarında yalnızca bu hisseyi ilgilendiren parçayı bırak.
    Tek yerde yapılır: CLI, API ve mobil aynı kırpılmış başlığı görsün."""
    for h in haberler:
        h["baslik"] = haber_esleme.ilgili_parca(h.get("baslik") or "",
                                                h.get("ifade") or "")
    return haberler


def degisim_raporu(sembol: str, gun: int = 10) -> dict:
    """'Dün 100 TL, bugün 103 TL' — bir hissenin günlük seyri."""
    gecmis = ambar.fiyat_gecmis(sembol, gun)
    if not gecmis:
        return {"sembol": sembol.upper(), "hata": "ambarda kayıt yok"}
    satirlar = [{
        "tarih": g["tarih"], "kapanis": g["kapanis"], "onceki": g["onceki"],
        "degisim": g["degisim"], "hacim": g["hacim"], "rsi": g["rsi"],
        "skor": g["skor"],
    } for g in gecmis]
    ilk, son = gecmis[-1], gecmis[0]
    return {
        "sembol": sembol.upper(),
        "gunler": satirlar,
        "donem_getiri": round((son["kapanis"] / ilk["kapanis"] - 1) * 100, 2)
                        if ilk["kapanis"] else None,
        "haberler": _haber_kirp(ambar.hisse_haberleri(sembol, gun=gun)),
    }


def geriye_doldur(gun_sayisi: int = 90, sermaye: float = 1000.0,
                  evren_adi: str = "bist100", sessiz: bool = False) -> dict:
    """Geçmiş günler için sinyalleri YENİDEN ÜRETİR ve sonuçlarını ölçer.

    Neden gerekli: sistem yeni kurulduğunda karne boştur ve haftalarca öyle
    kalır. Geriye doldurma, ilk günden gerçek bir sicil verir.

    GELECEĞE BAKMAMA: her T günü için veri yalnızca T'ye kadar kesilir ve
    göstergeler o dilimden hesaplanır. Aksi halde sinyaller, o gün bilinmesi
    imkânsız bilgiyle üretilir ve sicil sahte çıkar.

    Bu bir backtest DEĞİLDİR — pozisyon boyutu, nakit ve portföy kısıtı yok.
    Sadece "sistem o gün ne derdi ve sonra ne oldu" sorusunu cevaplar.
    """
    from . import gostergeler, strateji
    from .strateji import Filtreler, STRATEJILER, skorla
    from .risk import pozisyon_hesapla

    ambar.kur()
    ra = RiskAyarlari(sermaye=sermaye)
    filtre = Filtreler()
    semboller = evren.evren_getir(evren_adi)

    if not sessiz:
        print(f"» {len(semboller)} hisse için {gun_sayisi} günlük geçmiş yeniden üretiliyor...")

    ham = veri.toplu_cek(semboller, gun=max(500, gun_sayisi + 320),
                         onbellek_saat=12.0, sessiz=sessiz)
    endeks = veri.fiyat_cek(evren.ENDEKS, gun=max(500, gun_sayisi + 320))
    ek = endeks["Close"] if not endeks.empty else None

    G = {}
    for sem, df in ham.items():
        if len(df) >= 250:
            try:
                G[sem] = gostergeler.gosterge_seti(df, ek)
            except Exception:
                continue
    if not G:
        return {"hata": "yeterli veri yok"}

    # İşlem günleri takvimi
    takvim = sorted({t for g in G.values() for t in g.index})[-gun_sayisi:]
    if not sessiz:
        print(f"  {len(G)} hisse · {len(takvim)} işlem günü "
              f"({takvim[0].date()} → {takvim[-1].date()})")

    fiyat_satirlari, sinyal_satirlari = [], []
    for i, t in enumerate(takvim):
        if not sessiz and i % 20 == 0:
            print(f"    {i}/{len(takvim)} gün işlendi...")
        tarih = t.date().isoformat()

        for sem, g in G.items():
            if t not in g.index:
                continue
            konum = g.index.get_loc(t)
            if konum < 220:            # SMA200 için yeterli geçmiş yok
                continue

            dilim = g.iloc[: konum + 1]          # ← yalnızca T'ye kadar
            son = dilim.iloc[-1]
            onceki = dilim.iloc[-2]

            uygun, _ = filtre.gecer_mi(dilim)
            try:
                r = skorla(dilim)
            except Exception:
                continue

            fiyat_satirlari.append({
                "tarih": tarih, "sembol": sem,
                "kapanis": float(son["Close"]), "acilis": float(son["Open"]),
                "yuksek": float(son["High"]), "dusuk": float(son["Low"]),
                "hacim": float(son["Volume"]), "onceki": float(onceki["Close"]),
                "degisim": round((float(son["Close"]) / float(onceki["Close"]) - 1) * 100, 3),
                "tl_hacim": float(son.get("TL_hacim_ort20") or 0),
                "rsi": r["rsi"], "adx": r["adx"], "atr_yuzde": r["atr_yuzde"],
                "sma200_ustu": 1 if r["sma200_ustu"] else 0, "skor": r["skor"],
            })

            if not uygun or not r["sinyaller"]:
                continue
            for st_ad in r["sinyaller"]:
                st = STRATEJILER.get(st_ad)
                poz = pozisyon_hesapla(
                    sem, r["fiyat"], r["atr"], ra,
                    stop_kat=st.atr_stop_kat if st else None,
                    hedef_kat=st.atr_hedef_kat if st else None)
                sinyal_satirlari.append({
                    "tarih": tarih, "sembol": sem, "strateji": st_ad,
                    "skor": r["skor"], "fiyat": r["fiyat"],
                    "stop": poz.stop, "hedef": poz.hedef,
                    "rsi": r["rsi"], "adx": r["adx"],
                    "sma200_ustu": 1 if r["sma200_ustu"] else 0,
                    "alinabilir": 1 if poz.uygulanabilir else 0,
                })

    fn = ambar.fiyat_yaz(fiyat_satirlari)
    sn = ambar.sinyal_yaz(sinyal_satirlari)
    if not sessiz:
        print(f"  {fn} fiyat kaydı · {sn} sinyal yazıldı")
        print("» Sinyal sonuçları ölçülüyor...")
    olculen = ogrenme.sonuclari_olc(sessiz=sessiz)
    if not sessiz:
        print(f"  {sum(olculen.values())} sonuç kaydedildi")

    return {"fiyat": fn, "sinyal": sn, "sonuc": olculen,
            "gun": len(takvim), "hisse": len(G),
            "baslangic": takvim[0].date().isoformat(),
            "bitis": takvim[-1].date().isoformat()}
