"""Haber toplama: Türkçe finans RSS beslemeleri → hisse eşleşmesi.

DÜRÜST SINIR: bu beslemeler GENEL ekonomi haberleri yayınlar, hisse bazında
değil. Ölçüm: 100 haberde ortalama 3-6 hisse eşleşmesi çıkıyor. Yani her
hisse için her gün haber BEKLEME — çoğu gün çoğu hisse için haber olmaz.

Şirkete özel resmi açıklamalar bu modülde DEĞİL: onlar `cekirdek/kap.py`
üzerinden KAP'tan gelir ve aynı ambar tablosuna yazılır. Bu modülün
beslemeleri makro/genel bağlam içindir.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date, datetime, timezone

KAYNAKLAR = {
    "AA Ekonomi":  "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
    "Dünya":       "https://www.dunya.com/rss",
    "Ekonomim":    "https://www.ekonomim.com/rss",
    "Investing":   "https://tr.investing.com/rss/news_25.rss",
    "Investing Piyasa": "https://tr.investing.com/rss/market_overview.rss",
    # 2026-08-25: bu besleme 2026-08-06'dan beri güncellenmiyor (19 gün).
    # 36 saat filtresi hepsini eliyor, yani pratikte 5 kaynak var. Silmiyoruz;
    # yayıncı düzeltirse kendiliğinden geri gelsin.
    "BloombergHT": "https://www.bloomberght.com/rss",
}

# Makro ilgi anahtarları — hisseye bağlanamayan ama piyasayı ilgilendiren haberler
MAKRO_ANAHTAR = [
    "ENFLASYON", "TUFE", "UFE", "FAIZ", "MERKEZ BANKASI", "TCMB", "PPK",
    "DOLAR", "EURO", "KUR", "ALTIN", "PETROL", "BRENT", "FED", "ECB",
    "BORSA ISTANBUL", "BIST", "ENDEKS", "CARI ACIK", "ISSIZLIK", "BUYUME",
    "REZERV", "TAHVIL", "CDS", "KREDI DERECELENDIRME", "MOODY", "FITCH", "S&P",
]


def _kimlik(url: str, baslik: str) -> str:
    return hashlib.sha1(f"{url}|{baslik}".encode("utf-8")).hexdigest()[:16]


def _tarih(giris) -> tuple[str, str]:
    """(gün, tam zaman) döndürür."""
    t = giris.get("published_parsed") or giris.get("updated_parsed")
    if t:
        dt = datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
        return dt.date().isoformat(), dt.isoformat(timespec="seconds")
    b = date.today()
    return b.isoformat(), datetime.now().isoformat(timespec="seconds")


def _temizle(metin: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", metin or "")).strip()


def topla(azami_saat: float = 36.0, sessiz: bool = True) -> list[dict]:
    """Tüm kaynaklardan taze haberleri toplar."""
    try:
        import feedparser
    except ImportError:
        if not sessiz:
            print("  feedparser kurulu değil (pip install feedparser)")
        return []

    cikti, gorulen = [], set()
    for ad, url in KAYNAKLAR.items():
        try:
            f = feedparser.parse(url)
        except Exception:
            continue
        alinan = 0
        for e in f.entries:
            baslik = _temizle(e.get("title", ""))
            link = e.get("link", "")
            if not baslik or not link:
                continue
            kid = _kimlik(link, baslik)
            if kid in gorulen:
                continue
            gun, yayin = _tarih(e)
            # eski haberi alma
            try:
                yas = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(yayin)).total_seconds() / 3600
                if yas > azami_saat:
                    continue
            except Exception:
                pass
            gorulen.add(kid)
            cikti.append({
                "id": kid, "tarih": gun, "kaynak": ad, "baslik": baslik,
                "ozet": _temizle(e.get("summary", ""))[:600],
                "url": link, "yayin": yayin,
            })
            alinan += 1
        if not sessiz:
            print(f"    {ad:20s} {alinan} taze haber")
    return cikti


def eslestir(haberler: list[dict], eslestirici) -> list[dict]:
    """Haberleri hisselere bağlar. Eşleşmeyen haber de saklanır (makro olabilir)."""
    cikti = []
    for h in haberler:
        for kod, ifade in eslestirici.bul(f"{h['baslik']} {h['ozet']}"):
            cikti.append({"haber_id": h["id"], "sembol": kod, "ifade": ifade})
    return cikti


# Kelime sınırıyla derlenmiş desenler. Alt dize eşleşmesi çöp üretir:
# "KUR" anahtarı "KURESEL" (küresel) içinde eşleşir ve alakasız haberi makro sayar.
_MAKRO_DESEN = [(a, re.compile(rf"\b{re.escape(a)}\b")) for a in MAKRO_ANAHTAR]


def makro_haberler(haberler: list[dict]) -> list[dict]:
    """Hisseye bağlanamayan ama piyasayı ilgilendiren haberler."""
    from .haber_esleme import normalize
    cikti = []
    for h in haberler:
        n = normalize(f"{h['baslik']} {h['ozet']}")
        vurus = [a for a, d in _MAKRO_DESEN if d.search(n)]
        if vurus:
            cikti.append({**h, "anahtarlar": vurus[:4]})
    return cikti
