"""Bilanço, temettü ve ekonomi takvimi.

NEDEN VAR: bilanço günü pozisyon taşımak AYRI BİR RİSKTİR. Stop hesabı
o günü kapsamıyor — sonuç seans dışında açıklanıyor ve ertesi gün
boşluklu açılış stopu atlıyor. "Yarın bilanço var" bilgisi bugün
almama kararı verdirir.

Temettüde ise SON ALIM GÜNÜ kaçırılırsa temettü alınamaz; ertesi gün
fiyat temettü kadar düşer ve sebebini bilmeyen kullanıcı panikler.
(Aynı mekanik düşüş sorunu: bkz. sermaye_islemi.py)

İKİ TÜR KAYIT — ve ayrımı gizlemek yanlış olurdu:

  duyurulan — KAP bildiriminde tarih YAZILI. Temettü ödeme günü, genel
              kurul tarihi. Kaynağı belli, güvenilir.

  beklenen  — mevzuattan HESAPLANAN. SPK II-14.1 finansal raporun
              hesap dönemi bitiminden itibaren kaç gün içinde
              yayımlanacağını belirliyor; şirket tam gününü sonra
              duyuruyor. "12 Eylül'de bilanço var" demek yanlış olurdu;
              "9 Kasım'a kadar açıklanmalı" doğru.

Kullanıcı ikisini ayırt edebilmeli: birine göre gün planlanır,
ötekine göre yalnızca dikkatli olunur.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

# SPK II-14.1 — finansal rapor yayımlama süreleri (hesap dönemi
# bitiminden itibaren, gün).
#
# BIST100'ün büyük çoğunluğu konsolide rapor veriyor; tek tek hangisinin
# konsolide olduğunu bilmediğimiz için GEÇ olanı kullanıyoruz. Erken
# tarihi göstermek "bilanço geçti" sanılmasına yol açardı.
SURE_ARA_KONSOLIDE = 40      # 1., 2., 3. çeyrek
SURE_YILLIK_KONSOLIDE = 70   # yıllık

# Hesap dönemi sonları (ay, gün) ve insan adı.
DONEMLER = [
    ((3, 31), "1. çeyrek", SURE_ARA_KONSOLIDE),
    ((6, 30), "2. çeyrek", SURE_ARA_KONSOLIDE),
    ((9, 30), "3. çeyrek", SURE_ARA_KONSOLIDE),
    ((12, 31), "yıllık", SURE_YILLIK_KONSOLIDE),
]

_AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5,
    "mayis": 5, "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8,
    "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11, "kasim": 11,
    "aralık": 12, "aralik": 12,
}

_TARIH_DESENLERI = [
    re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b"),
    re.compile(r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\b"),
]


def tarih_cikar(metin: str, en_erken: date | None = None) -> list[date]:
    """Metindeki tarihleri bulur. Sıralı ve tekrarsız.

    `en_erken` verilirse ondan önceki tarihler atılır: bildirim metni
    geçmiş dönemlere de atıf yapıyor ("2025 yılı kârından") ve onları
    takvime koymak takvimi çöpe çevirirdi.
    """
    if not metin:
        return []
    bulunan: set[date] = set()
    for desen in _TARIH_DESENLERI:
        for m in desen.finditer(metin):
            g, a, y = m.group(1), m.group(2), m.group(3)
            try:
                ay = int(a) if a.isdigit() else _AYLAR.get(a.lower())
                if not ay:
                    continue
                t = date(int(y), ay, int(g))
            except Exception:
                continue
            if en_erken and t < en_erken:
                continue
            bulunan.add(t)
    return sorted(bulunan)


def bilanco_penceresi(bugun: date | None = None,
                      ileri_gun: int = 120) -> list[dict]:
    """Önümüzdeki dönemde beklenen finansal rapor son tarihleri.

    HESAPLANAN, duyurulan değil: şirket tam gününü ayrıca açıklıyor.
    Buradaki tarih "bu güne kadar açıklanmak zorunda" demek.
    """
    bugun = bugun or date.today()
    son = bugun + timedelta(days=ileri_gun)
    cikti = []
    for yil in (bugun.year - 1, bugun.year, bugun.year + 1):
        for (ay, gun), ad, sure in DONEMLER:
            try:
                donem_sonu = date(yil, ay, gun)
            except ValueError:
                continue
            bitis = donem_sonu + timedelta(days=sure)
            if bugun <= bitis <= son:
                cikti.append({
                    "tarih": bitis.isoformat(),
                    "tur": "bilanço",
                    "kaynak": "beklenen",
                    "baslik": f"{donem_sonu.year} {ad} bilanço son tarihi",
                    "aciklama": (
                        f"{donem_sonu.strftime('%d.%m.%Y')} dönemi "
                        f"finansal raporları bu tarihe kadar açıklanmalı. "
                        f"Şirketler genelde son günü beklemiyor — kesin "
                        f"gün ayrıca duyurulur."),
                    "sembol": "",
                })
    cikti.sort(key=lambda x: x["tarih"])
    return cikti


# ── KAP'ın duyurduğu olaylar ───────────────────────────────────────────────

# Konu → (etiket, insan adı). KAP'ın kendi konu başlığından geliyor.
KAP_OLAYLARI = [
    (("kar payı", "kâr payı", "temettü"), "temettü", "Temettü"),
    (("genel kurul",), "genel_kurul", "Genel kurul"),
    (("finansal rapor", "faaliyet raporu"), "bilanço", "Finansal rapor"),
]


def _olay_turu(metin: str) -> tuple[str, str]:
    d = (metin or "").lower()
    for anahtarlar, etiket, ad in KAP_OLAYLARI:
        if any(a in d for a in anahtarlar):
            return etiket, ad
    return "", ""


def kap_olaylari(semboller: list[str], gecmis_gun: int = 45,
                 ileri_gun: int = 120, bugun: date | None = None,
                 yol=None) -> list[dict]:
    """KAP bildirimlerinden çıkarılan İLERİ TARİHLİ olaylar.

    Bildirim geçmişte yayımlanmış olabilir ama içindeki tarih ileride:
    "kâr payı 12.09.2026'da ödenecek" bildirimi ağustosta çıkıyor.
    Bu yüzden geçmiş bildirimlere bakıp ileri tarih arıyoruz.
    """
    from . import ambar

    bugun = bugun or date.today()
    son = bugun + timedelta(days=ileri_gun)
    cikti: list[dict] = []
    gorulen: set[tuple[str, str, str]] = set()

    for sem in {s.upper().strip() for s in semboller if s}:
        try:
            haberler = ambar.hisse_haberleri(sem, gun=gecmis_gun, yol=yol)
        except Exception:
            continue
        for h in haberler:
            metin = f"{h.get('baslik', '')} {h.get('ozet', '')}"
            etiket, ad = _olay_turu(metin)
            if not etiket:
                continue
            for t in tarih_cikar(metin, en_erken=bugun):
                if t > son:
                    continue
                anahtar = (sem, etiket, t.isoformat())
                if anahtar in gorulen:
                    continue
                gorulen.add(anahtar)
                cikti.append({
                    "tarih": t.isoformat(),
                    "tur": etiket,
                    "kaynak": "duyurulan",
                    "sembol": sem,
                    "baslik": f"{sem} · {ad}",
                    "aciklama": (h.get("baslik") or "")[:200],
                    "url": h.get("url", ""),
                })
    cikti.sort(key=lambda x: x["tarih"])
    return cikti


# ── ekonomi takvimi ────────────────────────────────────────────────────────
#
# YALNIZCA YAPISAL OLARAK BİLİNEN veri: TÜİK enflasyonu her ayın 3'ünde
# (hafta sonuna denk gelirse sonraki iş günü) açıklıyor.
#
# TCMB PPK tarihleri BURADA YOK ve bu bilinçli. PPK takvimi yılda bir
# yayımlanıyor ve elimizde güvenilir bir kaynak yok; uydurmak, olmayan
# bir günü "faiz kararı var" diye göstermek olurdu. Kaynak bulununca
# eklenecek — o güne kadar eksik olduğunu söylemek, yanlış tarih
# göstermekten iyi.


def enflasyon_gunleri(bugun: date | None = None,
                      ileri_gun: int = 120) -> list[dict]:
    """TÜİK enflasyon açıklama günleri."""
    bugun = bugun or date.today()
    son = bugun + timedelta(days=ileri_gun)
    cikti = []
    yil, ay = bugun.year, bugun.month
    for _ in range(int(ileri_gun / 28) + 2):
        try:
            t = date(yil, ay, 3)
        except ValueError:
            t = date(yil, ay, 1)
        # Hafta sonuna denk gelirse sonraki iş günü
        while t.weekday() >= 5:
            t += timedelta(days=1)
        if bugun <= t <= son:
            cikti.append({
                "tarih": t.isoformat(),
                "tur": "ekonomi",
                "kaynak": "beklenen",
                "sembol": "",
                "baslik": "TÜİK enflasyon verisi",
                "aciklama": (
                    "Enflasyon açıklama günü. BIST'te oynaklık genelde "
                    "artar; o gün için koyduğun stop dar kalabilir."),
            })
        ay += 1
        if ay > 12:
            ay, yil = 1, yil + 1
    return cikti


def takvim(semboller: list[str] | None = None, ileri_gun: int = 120,
           bugun: date | None = None, yol=None) -> list[dict]:
    """Birleşik takvim: bilanço pencereleri + KAP olayları + ekonomi."""
    bugun = bugun or date.today()
    olaylar: list[dict] = []
    olaylar += bilanco_penceresi(bugun, ileri_gun)
    olaylar += enflasyon_gunleri(bugun, ileri_gun)
    if semboller:
        olaylar += kap_olaylari(semboller, ileri_gun=ileri_gun,
                                bugun=bugun, yol=yol)
    for o in olaylar:
        o["kalan_gun"] = (date.fromisoformat(o["tarih"]) - bugun).days
    olaylar.sort(key=lambda x: (x["tarih"], x["sembol"]))
    return olaylar
