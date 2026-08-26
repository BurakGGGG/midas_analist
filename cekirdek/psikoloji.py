"""Davranışsal korumalar: en pahalı hatalar bilgi eksikliğinden değil,
duygudan doğar.

Bu modül seni durdurmaz — durduramaz. Yaptığı tek şey, alım emrini girmeden
önce o anda göremediğin şeyi ekrana koymak. Bir işlemin kötü olduğunu
sonradan anlamak kolaydır; zor olan, tam o anda fark etmektir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np


@dataclass
class Uyari:
    kod: str
    seviye: str            # "dur" | "dikkat" | "bilgi"
    baslik: str
    aciklama: str
    soru: str = ""

    @property
    def agirlik(self) -> int:
        return {"dur": 3, "dikkat": 2, "bilgi": 1}.get(self.seviye, 1)


def _gun_farki(tarih_str: str) -> int:
    try:
        return (date.today() - datetime.fromisoformat(tarih_str).date()).days
    except Exception:
        return 999


def alim_oncesi(sembol: str, fiyat: float, adet: int, sermaye: float,
                gostergeler_son=None, gecmis_islemler=None,
                acik_pozisyonlar=None, tez_var_mi: bool = False) -> list[Uyari]:
    """Alım emrini girmeden önce çalıştır. Duygusal tuzakları tarar."""
    u: list[Uyari] = []
    s = gostergeler_son
    gecmis = gecmis_islemler or []
    acik = acik_pozisyonlar or []

    # ---------- 1) FOMO: kovalama alımı ----------
    if s is not None:
        rsi = float(s.get("RSI14", 50))
        if rsi > 75:
            u.append(Uyari("fomo_rsi", "dur", "Aşırı alım bölgesinde alıyorsun",
                f"RSI {rsi:.0f}. Bu seviyelerden alınan pozisyonların çoğu, "
                "birkaç gün içinde daha ucuza alınabilecekken alınmıştır.",
                "Bu hisseyi 3 gün önce de almak istiyor muydun, yoksa yükseldiği için mi istiyorsun?"))
        try:
            g5 = float(s.get("Getiri_5g", 0))
            if g5 > 20:
                u.append(Uyari("fomo_ivme", "dur", "Hisse 5 günde %{:.0f} yükselmiş".format(g5),
                    "Parabolik hareketin sonuna yakın giriliyor olabilir. Bu tür "
                    "hareketlerde geri çekilme, çıkıştan hızlı olur.",
                    "Bu yükselişi kaçırdığın için mi alıyorsun?"))
        except Exception:
            pass
        try:
            bb = float(s.get("BB_konum", 0.5))
            if bb > 0.98:
                u.append(Uyari("bb_ust", "dikkat", "Fiyat Bollinger üst bandının dışında",
                    "İstatistiksel olarak aşırı uzamış bölge. Trend güçlüyse devam "
                    "edebilir ama giriş için en kötü noktalardan biridir."))
        except Exception:
            pass

    # ---------- 2) İNTİKAM İŞLEMİ ----------
    son_kayiplar = [g for g in gecmis
                    if g.get("kapanis") and _gun_farki(g["kapanis"].get("tarih", "")) <= 5
                    and g["kapanis"].get("getiri_yuzde", 0) < 0]
    if len(son_kayiplar) >= 2:
        toplam = sum(g["kapanis"]["getiri_yuzde"] for g in son_kayiplar)
        u.append(Uyari("intikam", "dur", f"Son 5 günde {len(son_kayiplar)} zararlı işlem kapattın",
            f"Toplam %{toplam:.1f}. Kaybı geri alma dürtüsü, pozisyonu büyütmenin "
            "ve kuralı esnetmenin en yaygın sebebidir.",
            "Bu işlemi kaybını kapatmak için mi yapıyorsun?"))

    # ---------- 3) POZİSYON BÜYÜTME ----------
    if gecmis:
        gecmis_ort = np.mean([g.get("adet", 0) * g.get("fiyat", 0)
                              for g in gecmis[-10:] if g.get("fiyat")])
        yeni = adet * fiyat
        if np.isfinite(gecmis_ort) and gecmis_ort > 0 and yeni > gecmis_ort * 1.8:
            u.append(Uyari("boyut_artisi", "dikkat", "Bu pozisyon her zamankinden çok daha büyük",
                f"Son 10 işlemin ortalaması {gecmis_ort:,.0f} TL, bu {yeni:,.0f} TL "
                f"({yeni/gecmis_ort:.1f} kat).",
                "Boyutu neden artırdın? Sisteminde bunu söyleyen bir kural var mı?"))

    # ---------- 4) YOĞUNLAŞMA ----------
    yeni_tutar = adet * fiyat
    pay = yeni_tutar / sermaye * 100 if sermaye else 0
    if pay > 40:
        u.append(Uyari("yogunlasma", "dur", f"Sermayenin %{pay:.0f}'i tek hissede",
            "Tek bir şirket haberi portföyünün yarısını silebilir. BIST'te "
            "günlük tavan/taban ±%20 — bir gecede bunun gerçekleştiğini görürsün.",
            "Bu hisse %30 düşerse ne hissedersin, ne yaparsın?"))

    mevcut = sum(p.get("maliyet", 0) for p in acik)
    if sermaye and (mevcut + yeni_tutar) / sermaye > 0.95:
        u.append(Uyari("nakit_yok", "dikkat", "Neredeyse tüm sermaye piyasada olacak",
            "Nakitsiz kalmak, iyi fırsat çıktığında hareket edememek demektir. "
            "Ayrıca düşüşte panik satışı yapma olasılığını artırır."))

    # ---------- 5) ZARARINA ORTALAMA ----------
    ayni = [p for p in acik if p.get("sembol") == sembol.upper()]
    if ayni:
        eski = ayni[0]
        if fiyat < eski.get("giris", fiyat) * 0.95:
            u.append(Uyari("ortalama_dusurme", "dur", "Zararına ortalama düşürüyorsun",
                f"Mevcut girişin {eski.get('giris', 0):.2f}, şimdi {fiyat:.2f}'den ekliyorsun. "
                "Bu, yanılmış olma ihtimaline karşı bahsi büyütmektir. Profesyoneller "
                "kazanan pozisyonu büyütür, kaybedeni değil.",
                "Tezin değişti mi, yoksa sadece fiyat mı düştü?"))

    # ---------- 6) TEZ YOK ----------
    if not tez_var_mi:
        u.append(Uyari("tez_yok", "dur", "Bu alım için yazılı tezin yok",
            "Neden aldığını yazmadıysan, düştüğünde neden tuttuğunu da bilemezsin. "
            "O boşluğu umut doldurur.",
            f"python analist.py tez {sembol.upper()}  → önce tezini yaz"))

    return sorted(u, key=lambda x: -x.agirlik)


def gunluk_durum(gecmis_islemler=None, ozkaynak_seri=None) -> list[Uyari]:
    """Gün başında: bugün işlem yapacak psikolojik durumda mısın?"""
    u = []
    gecmis = gecmis_islemler or []

    bugun = [g for g in gecmis if g.get("kapanis")
             and _gun_farki(g["kapanis"].get("tarih", "")) == 0]
    if len(bugun) >= 3:
        u.append(Uyari("asiri_islem", "dur", f"Bugün zaten {len(bugun)} işlem kapattın",
            "Aşırı işlem, sıkılmanın ya da kaybı telafi çabasının belirtisidir. "
            "Komisyon sıfır olsa bile kayma ve kötü karar maliyeti gerçektir.",
            "Bugünü kapat. Yarın bak."))

    if ozkaynak_seri is not None and len(ozkaynak_seri) > 5:
        try:
            dd = float((ozkaynak_seri.iloc[-1] / ozkaynak_seri.cummax().iloc[-1] - 1) * 100)
            if dd < -15:
                u.append(Uyari("dusus_icinde", "dikkat", f"Portföy zirveden %{abs(dd):.0f} aşağıda",
                    "Düşüş dönemlerinde iki hata yaygındır: hepsini satıp dibi kaçırmak, "
                    "ya da 'geri alacağım' diye riski artırmak. İkisi de sistemi terk etmektir.",
                    "Sistemin kuralları değişti mi, yoksa sadece canın mı sıkkın?"))
        except Exception:
            pass
    return u


def gunluk_kontrol_listesi() -> list[str]:
    """Her alım öncesi okunacak. Uzun değil — okunmayan liste işe yaramaz."""
    return [
        "Bu işlemin stop seviyesi belli mi? (belli değilse işlem yapma)",
        "Stop'a düşerse kaybedeceğim TL tutarını yazdım mı?",
        "Bu kaybı yaşarsam sisteme devam edebilir miyim?",
        "Bu alımı sistemim mi söylüyor, yoksa ben mi istiyorum?",
        "Bir haber/söylenti yüzünden mi alıyorum? Kaynağı doğrulanmış mı?",
        "Aynı sektörde kaç pozisyonum var? (aynı bahsi tekrar oynuyor muyum?)",
        "Yanıldığımı hangi olayda kabul edeceğim? Yazdım mı?",
    ]


# Bilgi kaynağı değerlendirme (madde 12)
KAYNAK_SINIFLARI = {
    "kap": ("KAP bildirimi", 5, "Yasal zorunlulukla açıklanır, yanlışsa yaptırımı var. En güvenilir."),
    "finansal_rapor": ("Denetlenmiş finansal rapor", 5, "Bağımsız denetimden geçmiş. Gecikmeli ama sağlam."),
    "sirket_aciklamasi": ("Şirket açıklaması/sunumu", 4, "Doğru ama SEÇİLMİŞ bilgi. İyi haber öne çıkarılır."),
    "analist_raporu": ("Analist raporu", 3, "Modele dayanır ama varsayımlar tartışmalı. Kurumun çıkar ilişkisine bak."),
    "haber_ajansi": ("Haber ajansı", 3, "Hızlı ama bazen eksik/yanlış aktarır. Kaynağı KAP'tan doğrula."),
    "gazete_yorum": ("Köşe yazısı / yorum", 2, "Görüş, veri değil. Yazarın pozisyonu olabilir."),
    "sosyal_medya": ("X/Telegram paylaşımı", 1, "En düşük güvenilirlik. 'Bu hisse uçacak' diyen genelde ZATEN ALMIŞTIR ve senin alımınla çıkacaktır."),
    "soylenti": ("Söylenti / duyum", 0, "Doğrulanana kadar bilgi değildir. Çoğu zaman doğrulanmaz."),
}


def kaynak_degerlendir(sinif: str) -> dict:
    ad, puan, aciklama = KAYNAK_SINIFLARI.get(
        sinif, ("Bilinmeyen kaynak", 0, "Sınıflandırılamadı — güvenme."))
    return {
        "kaynak": ad, "guven_puani": puan, "aciklama": aciklama,
        "karar": ("Bu bilgiye dayanarak işlem yapılabilir" if puan >= 4 else
                  "Doğrulamadan işlem yapma" if puan >= 2 else
                  "İŞLEM GEREKÇESİ OLAMAZ"),
        "hatirlatma": "Gerçekleşmiş veri ile BEKLENTİ farklıdır. Fiyat beklentiyi "
                      "zaten içeriyor olabilir — 'iyi haber geldi ama hisse düştü' bundandır.",
    }
