"""Hesap ve bulut yedeği.

NEDEN VAR: telefon yeniden kurulduğunda portföy, tez, karar defteri,
sermaye defteri ve eğitim ilerlemesi gidiyordu. Bunlar yeniden
üretilemeyen veriler — fiyat geçmişi gibi sunucudan yeniden inmiyorlar.

BİLİNÇLİ BİR KARARI DEĞİŞTİRİYOR: `cekirdek/izleme.py` başındaki nota göre
API durumsuzdu ve pozisyonlar yalnızca telefonda yaşıyordu. O karar hâlâ
KARAR AKIŞI için geçerli — sunucu portföyünü okuyup sinyal üretmiyor,
tarama hâlâ durumsuz. Değişen tek şey: sunucu artık telefonun durumunun
bir KOPYASINI saklıyor. Kopya, kaynağı değiştirmez; telefon hâlâ tek
gerçek kaynak, sunucu yalnızca geri yükleme noktası.

GÜVENLİK — küçük ama gerçek bir kimlik doğrulama yüzeyi:

  · PAROLA ÖZETİ scrypt (stdlib hashlib). argon2 tercih edilirdi ama yeni
    bir bağımlılık getirirdi; scrypt OpenSSL destekli, bellek-zor bir KDF
    ve bu iş için fazlasıyla yeterli. Her kullanıcıya rastgele tuz.
  · JETON DEĞİL ÖZETİ saklanır. Veritabanı sızsa bile oturumlar ele
    geçmez — düz jeton yalnızca istemcide durur.
  · SABİT ZAMANLI KARŞILAŞTIRMA (hmac.compare_digest) ve kullanıcı YOKSA
    DA sahte özet hesaplama: ikisi de e-posta sayımını (enumeration)
    engeller. "Bu e-posta kayıtlı mı" sorusu yanıt süresinden okunamaz.
  · KABA KUVVET kilidi: 5 başarısız denemeden sonra 15 dakika.
  · MEVCUT API ANAHTARI KAPISI KALKMIYOR. /hesap uçlarına ulaşmak için
    önce API anahtarı gerekiyor; bu katman onun yerine değil, üstüne.
    Caddy TLS verdiği için parola düz metin gitmiyor.

ÇAKIŞMA: her kullanıcının TEK yedeği var ve her yazma `surum`u artırır.
İstemci elindeki sürümü gönderir; sunucudaki daha yeniyse yazma REDDEDİLİR
ve sunucudaki içerik geri döner. Son yazan kazansaydı, bir hafta açılmamış
ikinci telefon açıldığı anda güncel yedeği sessizce ezerdi.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone

from . import ambar

# scrypt parametreleri. 128*n*r = 16 MB bellek — OpenSSL'in 32 MB
# varsayılan sınırının altında, ARM bulut örneğinde rahat çalışır.
_N, _R, _P, _DK = 2 ** 14, 8, 1, 32

JETON_GUN = 90              # mobil istemci; kısa ömür sürekli giriş demek
AZAMI_DENEME = 5
KILIT_DAKIKA = 15
AZAMI_YEDEK_BAYT = 2 * 1024 * 1024

EPOSTA_KALIBI = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SEMA = """
CREATE TABLE IF NOT EXISTS kullanici (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    eposta        TEXT NOT NULL UNIQUE,
    tuz           BLOB NOT NULL,
    parola_ozet   BLOB NOT NULL,
    olusturma     TEXT NOT NULL,
    son_giris     TEXT,
    basarisiz     INTEGER NOT NULL DEFAULT 0,
    kilit_bitis   TEXT
);

CREATE TABLE IF NOT EXISTS oturum (
    jeton_ozet    TEXT PRIMARY KEY,
    kullanici_id  INTEGER NOT NULL,
    olusturma     TEXT NOT NULL,
    bitis         TEXT NOT NULL,
    cihaz         TEXT
);
CREATE INDEX IF NOT EXISTS ix_oturum_kullanici ON oturum(kullanici_id);

CREATE TABLE IF NOT EXISTS yedek (
    kullanici_id  INTEGER PRIMARY KEY,
    icerik        TEXT NOT NULL,
    surum         INTEGER NOT NULL DEFAULT 1,
    guncelleme    TEXT NOT NULL,
    cihaz         TEXT
);
"""


def _simdi() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def kur(yol=None) -> None:
    with ambar.baglan(yol) as c:
        c.executescript(SEMA)


def _ozet(parola: str, tuz: bytes) -> bytes:
    return hashlib.scrypt(parola.encode("utf-8"), salt=tuz,
                          n=_N, r=_R, p=_P, dklen=_DK)


def _jeton_ozeti(jeton: str) -> str:
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def _eposta_duzelt(e: str) -> str:
    return (e or "").strip().lower()


class HesapHata(Exception):
    """Kullanıcıya gösterilebilir hata. Mesaj bilerek genel tutulur."""


# ── kayıt ve giriş ─────────────────────────────────────────────────────────

def kayit(eposta: str, parola: str, cihaz: str = "", yol=None) -> dict:
    eposta = _eposta_duzelt(eposta)
    if not EPOSTA_KALIBI.match(eposta):
        raise HesapHata("Geçerli bir e-posta adresi gir.")
    if len(parola or "") < 8:
        raise HesapHata("Parola en az 8 karakter olmalı.")

    kur(yol)
    tuz = secrets.token_bytes(16)
    with ambar.baglan(yol) as c:
        var = c.execute("SELECT 1 FROM kullanici WHERE eposta=?",
                        (eposta,)).fetchone()
        if var:
            raise HesapHata("Bu e-posta zaten kayıtlı.")
        c.execute(
            "INSERT INTO kullanici (eposta, tuz, parola_ozet, olusturma) "
            "VALUES (?,?,?,?)",
            (eposta, tuz, _ozet(parola, tuz), _iso(_simdi())))
        kid = c.execute("SELECT id FROM kullanici WHERE eposta=?",
                        (eposta,)).fetchone()["id"]
    return _oturum_ac(kid, eposta, cihaz, yol)


def giris(eposta: str, parola: str, cihaz: str = "", yol=None) -> dict:
    """E-posta + parola ile oturum açar.

    DİKKAT — istisna `with` bloğunun DIŞINDA fırlatılıyor ve bu bilinçli.
    `ambar.baglan()` yalnızca istisnasız çıkışta commit eder; içeride
    `raise` edilirse başarısız deneme sayacı geri alınır ve kaba kuvvet
    kilidi hiç çalışmaz. Sessiz bir arıza: her şey doğru görünür, koruma
    yoktur. Bu yüzden önce karar verilir, blok kapanıp yazma commit olur,
    hata en sonda fırlatılır."""
    eposta = _eposta_duzelt(eposta)
    kur(yol)

    hata: str | None = None
    kid: int | None = None

    with ambar.baglan(yol) as c:
        k = c.execute("SELECT * FROM kullanici WHERE eposta=?",
                      (eposta,)).fetchone()

        if k is None:
            # Kullanıcı yokken de scrypt çalıştır: aksi halde yanıt süresi
            # "bu e-posta kayıtlı değil" bilgisini sızdırır.
            _ozet(parola or "", b"sahte-tuz-16byt")
            hata = "E-posta ya da parola hatalı."
        else:
            kilitli = False
            if k["kilit_bitis"]:
                bitis = datetime.fromisoformat(k["kilit_bitis"])
                if bitis > _simdi():
                    kalan = int((bitis - _simdi()).total_seconds() // 60) + 1
                    hata = (f"Çok fazla hatalı deneme. "
                            f"{kalan} dakika sonra dene.")
                    kilitli = True

            if not kilitli:
                if hmac.compare_digest(_ozet(parola or "", k["tuz"]),
                                       k["parola_ozet"]):
                    c.execute("UPDATE kullanici SET basarisiz=0, "
                              "kilit_bitis=NULL, son_giris=? WHERE id=?",
                              (_iso(_simdi()), k["id"]))
                    kid = int(k["id"])
                else:
                    sayi = int(k["basarisiz"]) + 1
                    kilit = (_iso(_simdi() + timedelta(minutes=KILIT_DAKIKA))
                             if sayi >= AZAMI_DENEME else None)
                    c.execute("UPDATE kullanici SET basarisiz=?, "
                              "kilit_bitis=? WHERE id=?",
                              (0 if kilit else sayi, kilit, k["id"]))
                    hata = "E-posta ya da parola hatalı."

    if hata:
        raise HesapHata(hata)
    return _oturum_ac(kid, eposta, cihaz, yol)


def _oturum_ac(kullanici_id: int, eposta: str, cihaz: str, yol=None) -> dict:
    jeton = secrets.token_urlsafe(32)
    bitis = _simdi() + timedelta(days=JETON_GUN)
    with ambar.baglan(yol) as c:
        # Süresi geçmiş oturumları fırsat buldukça temizle; ayrı bir
        # bakım işi kurmaya değmeyecek kadar küçük bir tablo.
        c.execute("DELETE FROM oturum WHERE bitis < ?", (_iso(_simdi()),))
        c.execute("INSERT INTO oturum (jeton_ozet, kullanici_id, olusturma, "
                  "bitis, cihaz) VALUES (?,?,?,?,?)",
                  (_jeton_ozeti(jeton), kullanici_id, _iso(_simdi()),
                   _iso(bitis), (cihaz or "")[:80]))
    return {"jeton": jeton, "bitis": _iso(bitis), "eposta": eposta,
            "kullanici_id": kullanici_id}


def jeton_dogrula(jeton: str, yol=None) -> int | None:
    """Geçerliyse kullanıcı id'si, değilse None. Asla istisna atmaz."""
    if not jeton:
        return None
    try:
        kur(yol)
        with ambar.baglan(yol) as c:
            o = c.execute("SELECT kullanici_id, bitis FROM oturum "
                          "WHERE jeton_ozet=?", (_jeton_ozeti(jeton),)).fetchone()
            if o is None:
                return None
            if datetime.fromisoformat(o["bitis"]) <= _simdi():
                c.execute("DELETE FROM oturum WHERE jeton_ozet=?",
                          (_jeton_ozeti(jeton),))
                return None
            return int(o["kullanici_id"])
    except Exception:
        return None


def cikis(jeton: str, yol=None) -> bool:
    if not jeton:
        return False
    with ambar.baglan(yol) as c:
        n = c.execute("DELETE FROM oturum WHERE jeton_ozet=?",
                      (_jeton_ozeti(jeton),)).rowcount
    return n > 0


def bilgi(kullanici_id: int, yol=None) -> dict:
    with ambar.baglan(yol) as c:
        k = c.execute("SELECT eposta, olusturma, son_giris FROM kullanici "
                      "WHERE id=?", (kullanici_id,)).fetchone()
        y = c.execute("SELECT surum, guncelleme, cihaz, length(icerik) AS boyut "
                      "FROM yedek WHERE kullanici_id=?", (kullanici_id,)).fetchone()
        o = c.execute("SELECT COUNT(*) AS n FROM oturum WHERE kullanici_id=?",
                      (kullanici_id,)).fetchone()
    if k is None:
        raise HesapHata("Kullanıcı yok.")
    return {
        "eposta": k["eposta"], "olusturma": k["olusturma"],
        "son_giris": k["son_giris"], "acik_oturum": int(o["n"]),
        "yedek": (None if y is None else
                  {"surum": y["surum"], "guncelleme": y["guncelleme"],
                   "cihaz": y["cihaz"], "boyut": y["boyut"]}),
    }


# ── yedek ──────────────────────────────────────────────────────────────────

def yedek_oku(kullanici_id: int, yol=None) -> dict | None:
    with ambar.baglan(yol) as c:
        y = c.execute("SELECT * FROM yedek WHERE kullanici_id=?",
                      (kullanici_id,)).fetchone()
    if y is None:
        return None
    try:
        icerik = json.loads(y["icerik"])
    except Exception:
        return None
    return {"icerik": icerik, "surum": y["surum"],
            "guncelleme": y["guncelleme"], "cihaz": y["cihaz"]}


def yedek_yaz(kullanici_id: int, icerik: dict, cihaz: str = "",
              beklenen_surum: int | None = None, yol=None) -> dict:
    """Yedeği yazar. `beklenen_surum` verildiyse ve sunucudaki daha yeniyse
    yazmaz — çakışma bilgisiyle birlikte sunucudaki içeriği döndürür."""
    if not isinstance(icerik, dict):
        raise HesapHata("Yedek içeriği bir nesne olmalı.")
    metin = json.dumps(icerik, ensure_ascii=False, separators=(",", ":"))
    if len(metin.encode("utf-8")) > AZAMI_YEDEK_BAYT:
        raise HesapHata(f"Yedek çok büyük (üst sınır "
                        f"{AZAMI_YEDEK_BAYT // 1024 // 1024} MB).")

    kur(yol)
    with ambar.baglan(yol) as c:
        mevcut = c.execute("SELECT surum FROM yedek WHERE kullanici_id=?",
                           (kullanici_id,)).fetchone()
        su_anki = int(mevcut["surum"]) if mevcut else 0

        if (beklenen_surum is not None and mevcut is not None
                and beklenen_surum < su_anki):
            sunucudaki = yedek_oku(kullanici_id, yol)
            return {"yazildi": False, "cakisma": True, "surum": su_anki,
                    "sunucudaki": sunucudaki}

        yeni = su_anki + 1
        c.execute(
            "INSERT INTO yedek (kullanici_id, icerik, surum, guncelleme, cihaz) "
            "VALUES (?,?,?,?,?) ON CONFLICT(kullanici_id) DO UPDATE SET "
            "icerik=excluded.icerik, surum=excluded.surum, "
            "guncelleme=excluded.guncelleme, cihaz=excluded.cihaz",
            (kullanici_id, metin, yeni, _iso(_simdi()), (cihaz or "")[:80]))
    return {"yazildi": True, "cakisma": False, "surum": yeni,
            "guncelleme": _iso(_simdi()), "boyut": len(metin)}


def parola_degistir(kullanici_id: int, eski: str, yeni: str, yol=None) -> bool:
    if len(yeni or "") < 8:
        raise HesapHata("Yeni parola en az 8 karakter olmalı.")
    with ambar.baglan(yol) as c:
        k = c.execute("SELECT tuz, parola_ozet FROM kullanici WHERE id=?",
                      (kullanici_id,)).fetchone()
        if k is None:
            raise HesapHata("Kullanıcı yok.")
        if not hmac.compare_digest(_ozet(eski or "", k["tuz"]), k["parola_ozet"]):
            raise HesapHata("Mevcut parola hatalı.")
        tuz = secrets.token_bytes(16)
        c.execute("UPDATE kullanici SET tuz=?, parola_ozet=? WHERE id=?",
                  (tuz, _ozet(yeni, tuz), kullanici_id))
        # Parola değişince diğer cihazlardaki oturumlar düşer. Parola
        # değiştirmenin sebebi genelde "başkası girmiş olabilir"dir.
        c.execute("DELETE FROM oturum WHERE kullanici_id=?", (kullanici_id,))
    return True
