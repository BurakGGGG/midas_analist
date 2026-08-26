"""Haber → hisse eşleştirme.

Problem: Türkçe haberler hisse KODU kullanmaz, şirket ADI kullanır. Ama
otomatik ad çıkarımı çöp üretir — "Türk Hava Yolları"ndan çıkan "TÜRK"
kelimesi, "Türkiye tarımsal hasıla" haberini THYAO'ya bağlar.

Çözüm: küratörlü takma ad listesi + jenerik kelime kara listesi + kelime
sınırı eşleşmesi. Otomatik çıkarım yalnızca YEDEK olarak, sıkı filtreyle.

Kesinlik (precision) hatırlamadan (recall) önemlidir: yanlış eşleşen haber,
hiç haber olmamasından kötüdür — analizi yanlış yöne çeker.
"""
from __future__ import annotations

import re
import unicodedata

# Tek başına asla eşleşme sayılmayacak kelimeler
JENERIK = {
    "TURK", "TURKIYE", "ANADOLU", "MERKEZ", "GENEL", "BUYUK", "YENI", "MILLI",
    "ULUSAL", "DEVLET", "HALK", "IS", "TICARET", "SANAYI", "HOLDING", "GRUP",
    "GRUBU", "YATIRIM", "ENERJI", "ELEKTRIK", "GIDA", "INSAAT", "OTOMOTIV",
    "BANKA", "BANKASI", "SIGORTA", "FABRIKA", "FABRIKALARI", "HACI", "OMER",
    "PETROL", "DEMIR", "CELIK", "CAM", "HAVA", "YOLLARI", "MAGAZALAR",
    "TEKNOLOJI", "SAGLIK", "TURIZM", "KIMYA", "MADEN", "CIMENTO", "SEKER",
    "ULUSLARARASI", "AS", "TAS", "ANONIM", "ORTAKLIGI", "SIRKETI",
}


def normalize(metin: str) -> str:
    """Türkçe karakterleri sadeleştirir ve büyütür.

    Sebep: yfinance 'Eregli Demir' der, haber 'Ereğli Demir' yazar. Aynı
    şirket, farklı yazım. Normalize edilmezse hiç eşleşmez.
    """
    if not metin:
        return ""
    t = metin.upper()
    for a, b in [("İ", "I"), ("I", "I"), ("Ş", "S"), ("Ğ", "G"),
                 ("Ü", "U"), ("Ö", "O"), ("Ç", "C")]:
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t)


# Küratörlü takma adlar. Yalnızca AYIRT EDİCİ olanlar — jenerik olan yazılmaz.
TAKMA_ADLAR: dict[str, list[str]] = {
    "AEFES": ["ANADOLU EFES", "EFES BIRACILIK"],
    "AKBNK": ["AKBANK"],
    "AKSEN": ["AKSA ENERJI"],
    "AKSA": ["AKSA AKRILIK"],
    "ALARK": ["ALARKO"],
    "ARCLK": ["ARCELIK", "BEKO"],
    "ASELS": ["ASELSAN"],
    "ASTOR": ["ASTOR ENERJI", "ASTOR TRAFO"],
    "BIMAS": ["BIM BIRLESIK", "BIM MAGAZALAR"],
    "BRSAN": ["BORUSAN MANNESMANN", "BORUSAN BORU"],
    "BRYAT": ["BORUSAN YATIRIM"],
    "CCOLA": ["COCA COLA ICECEK", "CCI"],
    "CIMSA": ["CIMSA"],
    "DOAS": ["DOGUS OTOMOTIV"],
    "DOHOL": ["DOGAN HOLDING"],
    "EKGYO": ["EMLAK KONUT"],
    "ENJSA": ["ENERJISA"],
    "ENKAI": ["ENKA INSAAT", "ENKA"],
    "EREGL": ["EREGLI DEMIR", "ERDEMIR"],
    "FROTO": ["FORD OTOSAN", "FORD OTOMOTIV"],
    "GARAN": ["GARANTI BBVA", "GARANTI BANKASI"],
    "GUBRF": ["GUBRE FABRIKALARI", "GUBRETAS"],
    "HALKB": ["HALKBANK", "TURKIYE HALK BANKASI"],
    "HEKTS": ["HEKTAS"],
    "ISCTR": ["IS BANKASI", "TURKIYE IS BANKASI"],
    "ISMEN": ["IS YATIRIM"],
    "KCHOL": ["KOC HOLDING"],
    "KRDMD": ["KARDEMIR"],
    "MAVI": ["MAVI GIYIM"],
    "MGROS": ["MIGROS"],
    "MPARK": ["MEDICAL PARK", "MLP SAGLIK"],
    "ODAS": ["ODAS ELEKTRIK"],
    "OTKAR": ["OTOKAR"],
    "OYAKC": ["OYAK CIMENTO"],
    "PETKM": ["PETKIM"],
    "PGSUS": ["PEGASUS"],
    "SAHOL": ["SABANCI HOLDING"],
    "SASA": ["SASA POLYESTER"],
    "SISE": ["SISECAM", "SISE VE CAM"],
    "SKBNK": ["SEKERBANK"],
    "SOKM": ["SOK MARKETLER"],
    "TAVHL": ["TAV HAVALIMANLARI"],
    "TCELL": ["TURKCELL"],
    "THYAO": ["TURK HAVA YOLLARI", "THY"],
    "TKFEN": ["TEKFEN"],
    "TOASO": ["TOFAS"],
    "TSKB": ["TSKB", "SINAI KALKINMA BANKASI"],
    "TTKOM": ["TURK TELEKOM"],
    "TUKAS": ["TUKAS"],
    "TUPRS": ["TUPRAS", "PETROL RAFINERILERI"],
    "TURSG": ["TURKIYE SIGORTA"],
    "ULKER": ["ULKER"],
    "VAKBN": ["VAKIFBANK"],
    "VESTL": ["VESTEL"],
    "YKBNK": ["YAPI KREDI"],
    "ZOREN": ["ZORLU ENERJI"],
    "FENER": ["FENERBAHCE"],
    "GSRAY": ["GALATASARAY"],
    "KOZAL": ["KOZA ALTIN"],
    "SARKY": ["SARKUYSAN"],
    "ECILC": ["ECZACIBASI ILAC"],
    "BERA": ["BERA HOLDING"],
    "MIATK": ["MIA TEKNOLOJI"],
    "REEDR": ["REEDER"],
    "GESAN": ["GIRISIM ELEKTRIK"],
    "EUPWR": ["EUROPOWER"],
    "CWENE": ["CW ENERJI"],
    "KONTR": ["KONTROLMATIK"],
}


def _otomatik_adlar(uzun_ad: str) -> list[str]:
    """Küratörlü listede olmayan hisseler için yedek ad çıkarımı.

    Sıkı: yalnızca en az iki kelimelik, jenerik olmayan öbekler kabul edilir.
    Tek kelime asla kabul edilmez — 'TURK' gibi bir eşleşme çöp üretir.
    """
    t = normalize(uzun_ad)
    t = re.sub(r"[^\w\s]", " ", t)
    kelimeler = [k for k in t.split() if len(k) > 2 and k not in JENERIK]
    if len(kelimeler) >= 2:
        return [" ".join(kelimeler[:2])]
    return []


class Eslestirici:
    """Metin içinde hangi hisselerin geçtiğini bulur."""

    def __init__(self, uzun_adlar: dict[str, str] | None = None):
        self.desenler: dict[str, list[re.Pattern]] = {}
        uzun_adlar = uzun_adlar or {}

        for kod in set(list(TAKMA_ADLAR) + list(uzun_adlar)):
            adaylar = list(TAKMA_ADLAR.get(kod, []))
            if not adaylar and kod in uzun_adlar:
                adaylar = _otomatik_adlar(uzun_adlar[kod])
            desen = [re.compile(rf"\b{re.escape(kod)}\b")]      # ticker kodu
            for a in adaylar:
                n = normalize(a)
                if n and n not in JENERIK:
                    desen.append(re.compile(rf"\b{re.escape(n)}\b"))
            self.desenler[kod] = desen

    def bul(self, metin: str) -> list[tuple[str, str]]:
        """(hisse_kodu, eşleşen_ifade) listesi."""
        n = normalize(re.sub(r"<[^>]+>", " ", metin or ""))
        sonuc = []
        for kod, desenler in self.desenler.items():
            for d in desenler:
                m = d.search(n)
                if m:
                    sonuc.append((kod, m.group(0)))
                    break
        return sonuc


def ilgili_parca(baslik: str, ifade: str) -> str:
    """Türkçe finans siteleri tek başlıkta birkaç konuyu '|' ile birleştiriyor:
    "Fonlara vergi | Altın rallisi! | Ülker şoku | Tera'nın dev alımı".
    Tamamını göstermek, ilgisiz konular o hisseye aitmiş gibi okunur.
    Eşleşmenin geçtiği parçayı ayıkla; bulunamazsa başlığı olduğu gibi bırak."""
    if "|" not in baslik or not ifade:
        return baslik
    hedef = normalize(ifade)
    if not hedef:
        return baslik
    for parca in baslik.split("|"):
        p = parca.strip()
        if hedef in normalize(p):
            return p
    return baslik
