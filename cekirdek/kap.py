"""KAP bildirimleri — Kamuyu Aydınlatma Platformu'ndan günlük şirket açıklamaları.

Neden önemli: `psikoloji.KAYNAKLAR` ölçeğinde KAP en tepede (güvenilirlik 5) —
yasal zorunlulukla açıklanır, yanlışsa yaptırımı vardır. RSS haber kaynakları
BIST şirket haberi taşımadığı için haber katmanı değer üretmiyordu; eksik olan
buydu.

Uç nokta resmi olarak belgelenmiş DEĞİL. KAP'ın Next.js uygulamasının
kullandığı JSON ucu:

    GET https://www.kap.org.tr/tr/api/disclosure/list/light

2026-08-25'te doğrulandı: 200, ~213 kayıt/gün. Belgelenmemiş olduğu için
kırılabilir; bu modülün tamamı hata durumunda boş liste döner ve günlük iş
KAP'sız çalışmaya devam eder. Sessizce yanlış veri üretmez.

İki sınır, bilerek kabul edildi:

1) Uç YALNIZCA bugünü döndürür (geçmiş sorgusu yok). Günlük iş 18:00
   kapanışından sonra çalıştığı için tam günü yakalar; ama bir gün iş
   çalışmazsa o günün bildirimleri geri getirilemez. Bu yüzden kayıtlar
   ambar'a yazılır — ambar tek kalıcı hafıza.

2) Bildirimde hisse kodu YOK, yalnızca şirket unvanı var. Kod eşlemesi
   /tr/bist-sirketler sayfasındaki gömülü veriden çıkarılır ve
   veri/kap_sirketler.json'da önbelleğe alınır.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

ONBELLEK = Path(__file__).resolve().parent.parent / "veri" / "kap_sirketler.json"
LISTE_UCU = "https://www.kap.org.tr/tr/api/disclosure/list/light"
SIRKET_SAYFASI = "https://www.kap.org.tr/tr/bist-sirketler"
BILDIRIM_URL = "https://www.kap.org.tr/tr/Bildirim/{}"

# Sunucu tarayıcı bekliyor; User-Agent'sız istek engellenebilir.
_BASLIK = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"),
    "Accept": "application/json",
}

# Şirket listesi ayda bir bile değişmez; sayfayı her gün çekmenin anlamı yok.
HARITA_OMRU_GUN = 30

# ── Bildirim konusunun ağırlığı ────────────────────────────────────────────
# Gerçek bir günün (2026-08-25) 67 şirket bildirimi üzerinden çıkarıldı.
# Konu metinleri uzun ve değişken; tam eşleşme yerine anahtar sözcük aranır.
# Sıra önemli: ilk eşleşen kazanır, en belirleyici desenler üstte.
_ONEM_DESENLERI: list[tuple[str, int]] = [
    # 3 = fiyatı doğrudan hareket ettirebilecek açıklamalar
    (r"özel durum açıklaması", 3),
    (r"olağan dışı fiyat", 3),
    (r"kar payı dağıtım|kâr payı dağıtım", 3),
    (r"sermaye artırımı|sermaye azaltımı", 3),
    (r"birleşme|devralma|bölünme", 3),
    (r"geleceğe dönük değerlendirme", 3),
    (r"pay alım satım", 3),
    (r"kredi derecelendirme", 3),
    (r"halka arz", 3),
    (r"esas sözleşme tadili", 3),
    # 2 = bağlam taşır, tek başına nadiren fiyat hareketi
    (r"genel kurul", 2),
    (r"finansal rapor|faaliyet raporu|yatırımcı raporu", 2),
    (r"bağımsız denetim", 2),
    (r"fiyat tespit raporu", 2),
    (r"sürdürülebilirlik raporu", 2),
    # 1 = rutin/mekanik bildirimler (tahvil ihracı, form güncellemesi)
    (r"pay dışında sermaye piyasası aracı", 1),
    (r"ihraç belgesi|ihraç tavanı|tertip ihraç", 1),
    (r"şirket genel bilgi formu|kurumsal yönetim bilgi formu", 1),
    (r"piyasa yapıcılığı", 1),
    (r"varant|sertifika", 1),
    (r"fon sürekli bilgilendirme", 1),
    (r"repo", 1),
    (r"devre kesici", 1),
]
_ONEM_DERLI = [(re.compile(d, re.IGNORECASE), o) for d, o in _ONEM_DESENLERI]


def onem(konu: str) -> int:
    """Bildirim konusunun önem derecesi: 3 yüksek, 2 orta, 1 rutin."""
    for desen, o in _ONEM_DERLI:
        if desen.search(konu or ""):
            return o
    return 2  # tanımadığımız konu: ortada bırak, sessizce eleme


def _istek(url: str, zaman_asimi: float = 25.0) -> str | None:
    try:
        import requests
        c = requests.get(url, headers=_BASLIK, timeout=zaman_asimi)
        c.raise_for_status()
        return c.text
    except Exception:
        return None


# ── Şirket unvanı ↔ hisse kodu ─────────────────────────────────────────────

def _haritayi_cek() -> dict[str, list[str]]:
    """bist-sirketler sayfasından {unvan(BÜYÜK): [kodlar]} çıkarır.

    HER KOD TUTULUYOR. Önceki hâli unvan başına yalnızca ilk kodu
    saklıyordu (`setdefault(unvan, kod)`) ve çok gruplu paylarda geri
    kalanlar sessizce düşüyordu: İş Bankası'nın beş kodundan
    ISATR kazanıp ISCTR kayboluyordu. Evrende kaybolan altı hisse
    bu yüzden KAP bildirimi almıyordu — ISCTR, KRDMD, SKBNK, TSKB,
    VAKBN, YKBNK.
    """
    h = _istek(SIRKET_SAYFASI, zaman_asimi=40.0)
    if not h:
        return {}
    # Next.js App Router flight verisi: alanlar \"anahtar\":\"değer\" biçiminde
    # kaçışlı gömülü. Bu yüzden düz JSON ayrıştırıcısı işe yaramıyor.
    ciftler = re.findall(
        r'\\"kapMemberTitle\\":\\"(.*?)\\".*?\\"stockCode\\":\\"(.*?)\\"', h)
    harita: dict[str, list[str]] = {}
    for unvan, kodlar in ciftler:
        unvan = unvan.strip()
        if not unvan or not kodlar or kodlar == "null":
            continue
        # Tek şirketin birden fazla kodu olabilir (A/B grubu payları).
        temiz = [k.strip().upper() for k in kodlar.split(",") if k.strip()]
        if temiz:
            harita.setdefault(unvan.upper(), temiz)
    return harita


def sirket_haritasi(yenile: bool = False, sessiz: bool = True) -> dict[str, str]:
    """{unvan(BÜYÜK): hisse kodu}. Önbellekten okur, gerekirse tazeler.

    Ağ hatasında bayat önbellek kullanılır: eski eşleme, hiç eşleme
    olmamasından iyidir — unvanlar zaten yıllarca değişmiyor.

    Çok kodlu şirkette EVRENDEKİ kod seçilir (bkz. `_tercih_edilen`):
    bildirim İş Bankası'na aitse onu ISATR'ye değil, bizim takip
    ettiğimiz ISCTR'ye bağlamak gerekiyor.
    """
    ham = _ham_harita(yenile=yenile, sessiz=sessiz)
    return {unvan: _tercih_edilen(kodlar) for unvan, kodlar in ham.items()
            if kodlar}


def kod_haritasi(yenile: bool = False, sessiz: bool = True) -> dict[str, str]:
    """{hisse kodu: unvan(BÜYÜK)} — ters yön, HER kod ayrı satır.

    Sembol araması bunu kullanıyor: kullanıcı "iş bankası" yazdığında
    ISCTR çıkmalı, ve ISATR de ayrı bir satır olarak durmalı.
    """
    cikti: dict[str, str] = {}
    for unvan, kodlar in _ham_harita(yenile=yenile, sessiz=sessiz).items():
        for k in kodlar:
            cikti.setdefault(k, unvan)
    return cikti


def _tercih_edilen(kodlar: list[str]) -> str:
    """Çok kodlu şirkette hangi kod. Evrendekiler öncelikli."""
    if not kodlar:
        return ""
    try:
        from . import evren as _e
        izlenen = set(_e.evren_getir("hepsi"))
        for k in kodlar:
            if k in izlenen:
                return k
    except Exception:
        pass
    return kodlar[0]


def _ham_harita(yenile: bool = False,
                sessiz: bool = True) -> dict[str, list[str]]:
    """{unvan: [kodlar]} — önbellekli ham veri. İki yönün de kaynağı."""
    bayat: dict[str, list[str]] = {}
    if ONBELLEK.exists():
        try:
            k = json.loads(ONBELLEK.read_text(encoding="utf-8"))
            bayat = _bicime_getir(k.get("esleme", {}))
            yas = (date.today() - date.fromisoformat(k["guncelleme"])).days
            # `bicim` alanı yoksa kayıt ESKİ tek-kodlu hâlde. Yaşı ne
            # olursa olsun tazelenmeli, yoksa kaybolan kodlar 30 gün
            # daha kayıp kalır.
            eski_bicim = int(k.get("bicim", 1)) < 2
            if not yenile and not eski_bicim and yas < HARITA_OMRU_GUN and bayat:
                return bayat
        except Exception:
            pass

    yeni = _haritayi_cek()
    if not yeni:
        if not sessiz:
            print(f"    KAP şirket listesi çekilemedi; önbellek kullanılıyor "
                  f"({len(bayat)} kayıt)")
        return bayat
    ONBELLEK.parent.mkdir(parents=True, exist_ok=True)
    ONBELLEK.write_text(json.dumps(
        {"guncelleme": date.today().isoformat(), "bicim": 2, "esleme": yeni},
        ensure_ascii=False, indent=1), encoding="utf-8")
    if not sessiz:
        kod_sayisi = sum(len(v) for v in yeni.values())
        print(f"    KAP şirket listesi tazelendi: {len(yeni)} unvan, "
              f"{kod_sayisi} kod")
    return yeni


def _bicime_getir(esleme: dict) -> dict[str, list[str]]:
    """Eski {unvan: kod} kaydını yeni {unvan: [kod]} biçimine çevirir.

    Sürüm yükselten kurulumda önbellek eski biçimde. Okuyamamak, o gün
    hiç eşleme olmaması demek olurdu.
    """
    cikti: dict[str, list[str]] = {}
    for unvan, deger in (esleme or {}).items():
        if isinstance(deger, str):
            cikti[unvan] = [deger]
        elif isinstance(deger, list):
            cikti[unvan] = [str(x) for x in deger if x]
    return cikti


# ── Günün bildirimleri ─────────────────────────────────────────────────────

def _zaman(metin: str) -> tuple[str, str]:
    """'25.08.2026 16:52:07' → (gün, ISO zaman)."""
    try:
        dt = datetime.strptime(metin.strip(), "%d.%m.%Y %H:%M:%S")
        return dt.date().isoformat(), dt.isoformat(timespec="seconds")
    except Exception:
        b = date.today()
        return b.isoformat(), datetime.now().isoformat(timespec="seconds")


def topla(evren_kodlari: set[str] | None = None,
          asgari_onem: int = 1,
          sessiz: bool = True) -> tuple[list[dict], list[dict]]:
    """Bugünün KAP bildirimlerini ambar biçiminde döndürür.

    (kayitlar, eslesmeler) — kayıtlar ambar.haber_yaz() biçiminde, ek olarak
    "_onem" taşır; yazmadan önce çıkarılmalıdır. KAP
    kayıtları normal haberlerle aynı tabloda yaşar, böylece hisse_haberleri()
    ve gun_haberleri() ek iş yapmadan bildirimleri de gösterir.

    evren_kodlari verilirse yalnızca o hisselere ait bildirimler alınır.
    """
    ham = _istek(LISTE_UCU)
    if not ham:
        if not sessiz:
            print("    KAP ucu yanıt vermedi — bildirimler atlandı")
        return [], []
    try:
        liste = json.loads(ham)
    except Exception:
        if not sessiz:
            print("    KAP yanıtı JSON değil — uç değişmiş olabilir")
        return [], []
    if not isinstance(liste, list):
        return [], []

    harita = sirket_haritasi(sessiz=sessiz)
    if not harita:
        if not sessiz:
            print("    KAP şirket eşlemesi yok — bildirimler hisseye bağlanamaz")
        return [], []

    kayitlar, eslesmeler, gorulen = [], [], set()
    atlanan_kod, atlanan_onem = 0, 0
    for b in liste:
        try:
            indeks = b.get("disclosureIndex")
            unvan = (b.get("title") or "").strip()
            konu = (b.get("subject") or "").strip()
            if not indeks or not unvan:
                continue
            kod = harita.get(unvan.upper())
            if not kod:
                # Fon, BIST duyurusu, MKK, borsada işlem görmeyen kuruluş.
                atlanan_kod += 1
                continue
            if evren_kodlari is not None and kod not in evren_kodlari:
                continue
            o = onem(konu)
            if o < asgari_onem:
                atlanan_onem += 1
                continue

            kid = f"kap-{indeks}"
            if kid in gorulen:
                continue
            gorulen.add(kid)
            gun, yayin = _zaman(b.get("publishDate") or "")
            kayitlar.append({
                "id": kid, "tarih": gun, "kaynak": "KAP",
                # Başlık tek başına anlamlı olsun: rapor ekranında konu
                # yalnız başına ("Özel Durum Açıklaması") kime ait belli olmaz.
                "baslik": f"{unvan} — {konu}" if konu else unvan,
                "ozet": (b.get("summary") or "")[:600],
                "url": BILDIRIM_URL.format(indeks),
                "yayin": yayin,
                # haber tablosunda önem sütunu yok; çağıran bunu okuyup
                # yazmadan önce çıkarır (bkz. gunluk.calistir).
                "_onem": o,
            })
            eslesmeler.append({"haber_id": kid, "sembol": kod, "ifade": unvan})
        except Exception:
            continue

    if not sessiz:
        print(f"    KAP: {len(kayitlar)} bildirim "
              f"({atlanan_kod} kurum dışı, {atlanan_onem} önemsiz elendi)")
    return kayitlar, eslesmeler
