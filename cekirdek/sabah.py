"""Sabah emir hatırlatıcısı.

NEDEN VAR: sinyal t günü KAPANIŞINDA üretiliyor, işlem t+1 AÇILIŞINDA
yapılıyor (bkz. cekirdek/strateji.py). Arada 16 saat ve bir uyku var.
Akşam işi "bugün ne oldu" diyor; sabah kimse "şimdi şunu yap" demiyordu.

Kullanıcının ilk sorusu tam buydu: "pazartesi baktım, salı mı alacağım?"

NE YAPMAZ — yeni analiz. Yeni tarama sabah 09:45'te yapılamaz zaten:
piyasa kapalı, elde yalnızca dünkü kapanış var ve dünkü kapanışla bugün
sabah tarama yapmak dün akşamki taramanın aynısını üretir. Bu iş
ambardaki kaydı OKUR, hesaplamaz.

NE ZAMAN: sürekli işlem 10:00'da başlıyor, iş 09:45'te çalışıyor —
mesajı görüp emri açılışa yetiştirebilesin diye. Daha geç çalışsaydı
(mesela 10:05) açılış fiyatını bilirdik ama o noktada artık AÇILIŞTAN
işlem yapmıyor olurdun ve backtestin ölçtüğü şeyden sapardın.

BEDELİ: 09:45'te açılış fiyatı bilinmiyor. Rakamlar dünkü kapanışa göre;
hisse boşluklu açarsa adet ve stop kayar. Mesaj bunu gizlemiyor, tavan
sınırını da açıkça yazıyor — backtestin açılışta uyguladığı kuralın
aynısı.

SESSİZ KALMA KURALI: önerilen sinyal yoksa mesaj GÖNDERİLMEZ. "Bugün bir
şey yok" bildirimi, bildirimleri görmezden gelmeyi öğretir; akşamki mesaj
zaten sinyal olmadığını söylemişti.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import ambar
from .gunluk import islem_gunu_mu

# Ambardaki özet bu kadar günden eskiyse hatırlatma yapılmaz. Uzun tatil
# sonrası eski bir listeyle emir vermek, hiç hatırlatmamaktan kötüdür.
AZAMI_YAS_GUN = 5

# BIST ana pazar günlük tavan ~%20. Backtest %19,5 üstünde açan hisseyi
# "alınamaz" sayar (backtest.TAVAN_ORANI); mesaj aynı eşiği söyler.
TAVAN_ORANI = 1.195


def _onceki_islem_gunu(bugun: date) -> date:
    g = bugun - timedelta(days=1)
    for _ in range(10):
        if islem_gunu_mu(g)[0]:
            return g
        g -= timedelta(days=1)
    return g


def hazirla(bugun: date | None = None, yol=None) -> dict:
    """Bugün sabah gönderilecek hatırlatmanın içeriğini üretir.

    Dönen sözlükte `gonder` alanı kararı taşır; çağıran onu okur ve
    yalnızca True ise mesaj atar. Kararı burada vermek, "ne zaman
    susulur" kuralının tek yerde durmasını sağlıyor.
    """
    bugun = bugun or date.today()

    acik, sebep = islem_gunu_mu(bugun)
    if not acik:
        return {"gonder": False, "sebep": f"bugün {sebep}"}

    beklenen = _onceki_islem_gunu(bugun)
    try:
        ozet = ambar.ozet_oku(beklenen.isoformat(), yol=yol)
        if ozet is None:
            # Son çareyi dene: belki akşam işi gecikmeli çalıştı ve başka
            # bir tarihe yazdı. En yeni özeti al, yaşına bak.
            tarihler = ambar.ozet_tarihleri(azami=5, yol=yol)
            ozet = ambar.ozet_oku(tarihler[0], yol=yol) if tarihler else None
    except Exception as e:
        # Taze kurulumda ambar tabloları henüz yok (ilk akşam işinden
        # önce). Hatırlatıcının bu yüzden ÇÖKMESİ, sessizce susmasından
        # daha kötü: nöbetçi katmanı gereksiz yere alarm verir.
        return {"gonder": False, "sebep": f"ambar okunamadı: {str(e)[:80]}"}

    if ozet is None:
        return {"gonder": False, "sebep": "ambarda özet yok"}

    tarih = ozet.get("tarih") or ""
    try:
        yas = (bugun - date.fromisoformat(tarih)).days
    except Exception:
        return {"gonder": False, "sebep": "özet tarihi okunamadı"}

    if yas > AZAMI_YAS_GUN:
        return {"gonder": False,
                "sebep": f"son özet {yas} günlük — emir vermek için eski"}

    sinyaller = ozet.get("sinyal_veren") or []
    # Yalnızca ÖNERİLEN ve ALINABİLİR olanlar. Karantinadaki stratejiden
    # gelen sinyali sabah "şunu al" diye hatırlatmak, akşam konulan
    # "önerilmez" işaretini boşa çıkarırdı.
    emirler = [s for s in sinyaller
               if s.get("onerilir") and s.get("alinabilir")
               and (s.get("adet") or 0) >= 1]

    if not emirler:
        return {"gonder": False, "sebep": "önerilen ve alınabilir sinyal yok",
                "tarih": tarih}

    for e in emirler:
        fiyat = float(e.get("fiyat") or 0)
        e["tavan_fiyat"] = round(fiyat * TAVAN_ORANI, 2) if fiyat else 0.0

    return {"gonder": True, "tarih": tarih, "yas": yas, "emirler": emirler,
            "rejim": (ozet.get("rejim") or {}).get("ad", "")}
