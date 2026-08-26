"""AI akıl yürütme katmanı — isteğe bağlı.

TASARIM KURALI: model asla sayı ÜRETMEZ, sadece sistemin hesapladığı sayılar
üzerine akıl yürütür. Finansal veriyi modele sorduğun anda uydurma riski
başlar; bizde tüm rakamlar yfinance + kendi hesabımızdan gelir, model yalnızca
yorumlar, itiraz eder, sınıflandırır ve açıklar.

İKİNCİ KURAL — BÜTÇE: her çağrı ambara yazılır ve aylık tavan aşılırsa
çağrılar durur. Sebebi aritmetik: 1.000 TL sermayede ayda 54 TL API gideri,
gerçekçi aylık getiri hedefinin (%3-5) ÜSTÜNDEDİR. Bu parayı işlem kârından
çıkarırsan matematiksel olarak kaybedersin; eğitim bütçesi say, ayrı tut.

Her iş kendi modelini kullanır — hepsine en pahalı modeli koşmak israftır:
  · haber sınıflandırma → Haiku (hacimli, basit, günde 1 kez)
  · tez eleştirisi      → Opus  (seyrek, yüksek değerli, zor)
  · anlatım/özet        → Sonnet

Kurulum:
    pip install anthropic
    export ANTHROPIC_API_KEY="..."
Anahtar yoksa modül sessizce devre dışı kalır, sistemin geri kalanı çalışır.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from . import ambar, ortam  # noqa: F401  (ortam .env'i içe aktarıldığında yükler)

# ── modeller ve fiyatlar ────────────────────────────────────────────────
# $/1M token. Fiyat değişirse BURAYI güncelle — bütçe hesabı buradan çıkar.
# Kaynak: Anthropic fiyat sayfası (2026-06 anlık görüntüsü).
FIYAT = {
    "claude-opus-5":   {"giris": 5.0, "cikis": 25.0},
    "claude-sonnet-5": {"giris": 3.0, "cikis": 15.0},
    "claude-haiku-4-5": {"giris": 1.0, "cikis": 5.0},
}
# Önbellek: yazma girişin ~1,25 katı, okuma ~0,1 katı.
ONBELLEK_YAZMA_KAT = 1.25
ONBELLEK_OKUMA_KAT = 0.10

# İş → model eşlemesi. Tek yerden değiştirilsin.
MODELLER = {
    "haber_sinifla": "claude-haiku-4-5",
    "gunluk_yorum": "claude-haiku-4-5",
    "tez_elestir": "claude-opus-5",
    "finansal_ozet": "claude-sonnet-5",
    "haber_degerlendir": "claude-sonnet-5",
    "sirket_anlat": "claude-sonnet-5",
}
VARSAYILAN_MODEL = "claude-sonnet-5"

AZAMI_TOKEN = 2000

# ── bütçe ───────────────────────────────────────────────────────────────
AYLIK_TAVAN_TL = float(os.environ.get("MIDAS_AI_TAVAN_TL", "100"))
USD_TRY_YEDEK = 48.0     # kur çekilemezse kullanılır (eksik saymaktansa fazla say)


def _kur() -> float:
    """USD/TRY. Bütçe TL cinsinden tutuluyor çünkü sermaye TL."""
    try:
        from . import veri
        k = veri.usd_try()
        return k if k > 0 else USD_TRY_YEDEK
    except Exception:
        return USD_TRY_YEDEK


def butce_durumu() -> dict:
    """Bu ayki harcama, tavan ve kalan. Tavan yoksa sınırsız."""
    try:
        harcanan = ambar.ai_ay_toplami()
    except Exception:
        harcanan = 0.0
    sinirsiz = AYLIK_TAVAN_TL <= 0
    return {
        "ay": datetime.now().strftime("%Y-%m"),
        "harcanan_tl": round(harcanan, 2),
        "tavan_tl": None if sinirsiz else AYLIK_TAVAN_TL,
        "kalan_tl": None if sinirsiz else round(AYLIK_TAVAN_TL - harcanan, 2),
        "asildi": (not sinirsiz) and harcanan >= AYLIK_TAVAN_TL,
        "oran": None if sinirsiz else round(harcanan / AYLIK_TAVAN_TL * 100, 1),
    }


def _maliyet_tl(model: str, kul, kur: float) -> tuple[float, float]:
    """(usd, tl) — SDK'nın bildirdiği gerçek token sayılarından.

    Tahmin etmiyoruz: usage alanları faturaya esas olan sayılardır.
    """
    f = FIYAT.get(model) or FIYAT[VARSAYILAN_MODEL]
    gir = getattr(kul, "input_tokens", 0) or 0
    cik = getattr(kul, "output_tokens", 0) or 0
    oy = getattr(kul, "cache_creation_input_tokens", 0) or 0
    oo = getattr(kul, "cache_read_input_tokens", 0) or 0
    usd = (
        gir * f["giris"]
        + oy * f["giris"] * ONBELLEK_YAZMA_KAT
        + oo * f["giris"] * ONBELLEK_OKUMA_KAT
        + cik * f["cikis"]
    ) / 1e6
    return usd, usd * kur


def kullanilabilir() -> tuple[bool, str]:
    """(hazır mı, sebep). Bütçe aşımı da 'kullanılamaz' sayılır."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False, "ANTHROPIC_API_KEY tanımlı değil"
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, "anthropic paketi kurulu değil (pip install anthropic)"
    b = butce_durumu()
    if b["asildi"]:
        return False, (f"aylık AI bütçesi doldu ({b['harcanan_tl']:.2f} / "
                       f"{b['tavan_tl']:.0f} TL). MIDAS_AI_TAVAN_TL ile "
                       f"yükseltebilirsin.")
    return True, "hazır"


def _cagir(is_adi: str, sistem, mesaj, azami: int = AZAMI_TOKEN,
           sema=None) -> tuple[object | None, str | None]:
    """Tek çağrı noktası: model seçimi, bütçe kontrolü ve harcama kaydı.

    Döner: (yanıt, hata). Yanıt varsa hata None, tersi de doğru.
    """
    ok, sebep = kullanilabilir()
    if not ok:
        return None, sebep

    model = MODELLER.get(is_adi, VARSAYILAN_MODEL)
    try:
        import anthropic
        y = anthropic.Anthropic()
        istek = dict(
            model=model,
            max_tokens=azami,
            system=sistem,
            messages=[{"role": "user", "content": mesaj}],
        )
        if sema is not None:
            c = y.messages.parse(**istek, output_format=sema)
        else:
            c = y.messages.create(**istek)
    except Exception as e:
        return None, f"AI hatası: {str(e)[:180]}"

    # Harcamayı KAYDET — çağrı başarılı olduysa para gitti, yazmazsak
    # bütçe tavanı yalan söyler.
    try:
        usd, tl = _maliyet_tl(model, c.usage, _kur())
        simdi = datetime.now()
        ambar.kur()
        ambar.ai_harcama_yaz({
            "zaman": simdi.isoformat(timespec="seconds"),
            "ay": simdi.strftime("%Y-%m"),
            "is_adi": is_adi,
            "model": model,
            "giris": getattr(c.usage, "input_tokens", 0) or 0,
            "cikis": getattr(c.usage, "output_tokens", 0) or 0,
            "onbellek_yazma": getattr(c.usage, "cache_creation_input_tokens", 0) or 0,
            "onbellek_okuma": getattr(c.usage, "cache_read_input_tokens", 0) or 0,
            "usd": round(usd, 6),
            "tl": round(tl, 4),
        })
    except Exception:
        pass   # kayıt tutulamadıysa da yanıtı ver, ama sessiz geçme riski var

    return c, None


def _sor(is_adi: str, sistem: str, mesaj: str,
         azami: int = AZAMI_TOKEN) -> str | None:
    """Serbest metin isteyen işler için sarmalayıcı."""
    c, hata = _cagir(is_adi, sistem, mesaj, azami)
    if hata:
        return f"[{hata}]"
    return "".join(b.text for b in c.content if getattr(b, "type", "") == "text")


SISTEM_ANALIST = """Sen BIST (Borsa İstanbul) konusunda deneyimli, şüpheci bir
yatırım analistisin. Türkçe cevap veriyorsun.

KURALLAR:
- Sana verilen sayıların DIŞINDA hiçbir rakam üretme. Bilmediğin bir veri
  gerekiyorsa "bu veri elimde yok" de.
- Yatırım tavsiyesi verme; gözlem ve itiraz üret.
- Türkiye bağlamını hesaba kat: yüksek enflasyon, TL değer kaybı, yüksek faiz.
  Nominal TL büyümesi reel büyüme DEĞİLDİR.
- Kısa ve doğrudan yaz. Süsleme yapma, maddeler halinde konuş.
- Kullanıcı küçük sermayeli bireysel yatırımcıdır; pozisyon önerilerini buna
  göre ölçekle."""


def tez_elestir(tez_sozluk: dict, anlik: dict) -> str | None:
    """Kullanıcının tezine KARŞI argüman üret. En değerli AI kullanımı.

    Amaç seni ikna etmek değil, tezindeki en zayıf halkayı göstermek.
    Bu iş Opus'a gider: seyrek çalışır ama zorludur."""
    return _sor(
        "tez_elestir",
        SISTEM_ANALIST + "\n\nBu görevde özellikle ŞEYTANIN AVUKATI'sın. "
        "Kullanıcının tezini onaylamak değil, en zayıf noktasını bulmak işin.",
        f"""Bir yatırımcı şu tezi yazdı ve bu hisseyi almak üzere:

TEZ:
{json.dumps(tez_sozluk, ensure_ascii=False, indent=2)}

SİSTEMİN ÖLÇTÜĞÜ GERÇEK RAKAMLAR (bunlar doğrulanmış veridir):
{json.dumps(anlik, ensure_ascii=False, indent=2)}

Şunları yap:
1. Tezin en zayıf 2-3 varsayımını göster. Hangi cümlesi veriyle çelişiyor?
2. Yatırımcının GÖRMEDİĞİ riski söyle.
3. "Yanılma koşulu" yeterince somut mu? Değilse nasıl olmalı?
4. Sonunda tek cümlelik hüküm: bu tez ne kadar sağlam?

Rakamlara atıf yaparak konuş.""", azami=3000)


def finansal_ozet(sembol: str, oranlar: dict, bayraklar: list,
                  carpanlar: dict, sektor: str) -> str | None:
    """Finansal tabloları sade Türkçeye çevir."""
    return _sor("finansal_ozet", SISTEM_ANALIST,
                f"""{sembol} ({sektor}) için hesaplanan rakamlar:

ORANLAR: {json.dumps(oranlar, ensure_ascii=False)}
KIRMIZI BAYRAKLAR: {json.dumps(bayraklar, ensure_ascii=False)}
DEĞERLEME ÇARPANLARI: {json.dumps(carpanlar, ensure_ascii=False)}

Bu şirketi borsayı yeni öğrenen birine anlat:
1. Bu şirket para kazanıyor mu, nasıl?
2. Bilançosu sağlam mı?
3. Bu rakamlarda dikkat çeken en önemli 2 şey ne?
4. Pahalı mı ucuz mu — ve neden bu soru tek başına yeterli değil?

Terim kullanırsan hemen yanında bir cümleyle açıkla.""")


def haber_degerlendir(metin: str, sembol: str = "") -> str | None:
    """Bir haber/söylenti işlem gerekçesi olabilir mi?"""
    return _sor("haber_degerlendir", SISTEM_ANALIST,
                f"""Yatırımcı şu bilgiyi gördü{' (' + sembol + ' hakkında)' if sembol else ''}:

\"\"\"{metin[:3000]}\"\"\"

Değerlendir:
1. Bu bir GERÇEKLEŞMİŞ VERİ mi, BEKLENTİ mi, yoksa YORUM mu?
2. Kaynağı ne kadar güvenilir görünüyor?
3. Bu bilgi fiyata çoktan yansımış olabilir mi?
4. Manipülasyon işareti var mı? ("uçacak", "son şans", hedef fiyat vaadi)
5. Tek cümle: bu bilgiye dayanarak işlem yapılır mı?""")


def sirket_anlat(sembol: str, ad: str, sektor: str, sanayi: str,
                 ozet: str = "") -> str | None:
    """'Ne iş yapıyor?' — temel analizin ilk ve en atlanan adımı."""
    return _sor("sirket_anlat", SISTEM_ANALIST,
                f"""{sembol} — {ad}
Sektör: {sektor} / {sanayi}
{('Şirket özeti: ' + ozet[:1500]) if ozet else ''}

Anlat:
1. Bu şirket parayı tam olarak NASIL kazanıyor?
2. Bu sektörde kâr etmenin anahtarı nedir?
3. Bu sektörde en çok neye bakılmalı? (hangi 2-3 gösterge belirleyici)
4. Bu sektörün Türkiye'ye özgü riski ne?

Bilmediğin şirkete özel detay uydurma; emin değilsen sektör düzeyinde konuş.""")


def gunluk_yorum(tarama: list, makro_ozet: dict, portfoy: list) -> str | None:
    """Günlük tarama sonuçlarını bağlama oturt."""
    return _sor("gunluk_yorum", SISTEM_ANALIST,
                f"""Bugünkü durum:

MAKRO: {json.dumps(makro_ozet, ensure_ascii=False)}
TARAMADA ÖNE ÇIKANLAR: {json.dumps(tarama[:8], ensure_ascii=False)}
AÇIK POZİSYONLAR: {json.dumps(portfoy, ensure_ascii=False)}

Kısa yaz (en fazla 200 kelime):
1. Bugün dikkat edilmesi gereken tek şey ne?
2. Taramadaki adaylarda ortak bir örüntü var mı?
3. Bugün işlem yapmamak da bir seçenek mi?""", azami=600)
