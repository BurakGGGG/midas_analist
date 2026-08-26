"""Push bildirimi için cihaz kaydı.

Jetonlar hesaba bağlı (bkz. cekirdek/hesap.py): bildirim "bu kullanıcının
telefonlarına" gidiyor, "herkese" değil. Hesap katmanı zaten vardı, ayrı
bir kimlik uydurmaya gerek kalmadı.

JETON KALICI DEĞİL: Firebase jetonu uygulama yeniden kurulunca, veriler
temizlenince ya da kendiliğinden yenilenebilir. Bu yüzden:
  · istemci her açılışta jetonu yeniden gönderir (upsert)
  · FCM "UNREGISTERED" derse jeton silinir (bkz. `temizle`)
  · uzun süre görülmeyen jetonlar da silinir (bkz. `eskileri_at`)

Temizlenmezse ölü jetonlar birikir ve her bildirimde boşuna istek atılır;
hata sayısı şişer, gerçek arıza gürültüde kaybolur.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import ambar

# Bu kadar gündür görülmeyen jeton ölü sayılır. Uygulamayı iki ay hiç
# açmadıysan zaten bildirim alacak durumda değilsin.
AZAMI_SESSIZ_GUN = 60

SEMA = """
CREATE TABLE IF NOT EXISTS cihaz (
    jeton         TEXT PRIMARY KEY,
    kullanici_id  INTEGER NOT NULL,
    platform      TEXT,
    olusturma     TEXT NOT NULL,
    son_gorulme   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cihaz_kullanici ON cihaz(kullanici_id);
"""


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def kur(yol=None) -> None:
    with ambar.baglan(yol) as c:
        c.executescript(SEMA)


def kaydet(kullanici_id: int, jeton: str, platform: str = "", yol=None) -> dict:
    """Jetonu kaydeder ya da tazeler.

    Aynı jeton başka bir kullanıcıya geçebilir: telefonda çıkış yapıp
    başka hesapla girildiğinde. O durumda jeton YENİ sahibine taşınır,
    yoksa bildirim eski kullanıcıya gitmeye devam ederdi.
    """
    jeton = (jeton or "").strip()
    if not jeton:
        return {"kayitli": False, "not": "jeton boş"}
    kur(yol)
    with ambar.baglan(yol) as c:
        c.execute(
            "INSERT INTO cihaz (jeton, kullanici_id, platform, olusturma, "
            "son_gorulme) VALUES (?,?,?,?,?) "
            "ON CONFLICT(jeton) DO UPDATE SET kullanici_id=excluded.kullanici_id, "
            "platform=excluded.platform, son_gorulme=excluded.son_gorulme",
            (jeton, kullanici_id, (platform or "")[:40], _simdi(), _simdi()))
    return {"kayitli": True}


def sil(jeton: str, yol=None) -> bool:
    if not jeton:
        return False
    with ambar.baglan(yol) as c:
        return c.execute("DELETE FROM cihaz WHERE jeton=?", (jeton,)).rowcount > 0


def jetonlar(kullanici_id: int | None = None, yol=None) -> list[str]:
    """Bildirim gönderilecek jetonlar. Ambar kurulmamışsa boş liste —
    push yüzünden günlük iş çökmemeli."""
    try:
        kur(yol)
        with ambar.baglan(yol) as c:
            if kullanici_id is None:
                r = c.execute("SELECT jeton FROM cihaz").fetchall()
            else:
                r = c.execute("SELECT jeton FROM cihaz WHERE kullanici_id=?",
                              (kullanici_id,)).fetchall()
        return [x["jeton"] for x in r]
    except Exception:
        return []


def temizle(gecersiz: list[str], yol=None) -> int:
    """FCM'in ölü dediği jetonları siler."""
    gecersiz = [j for j in (gecersiz or []) if j]
    if not gecersiz:
        return 0
    with ambar.baglan(yol) as c:
        n = 0
        for j in gecersiz:
            n += c.execute("DELETE FROM cihaz WHERE jeton=?", (j,)).rowcount
    return n


def eskileri_at(gun: int = AZAMI_SESSIZ_GUN, yol=None) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=gun)).isoformat(
        timespec="seconds")
    with ambar.baglan(yol) as c:
        return c.execute("DELETE FROM cihaz WHERE son_gorulme < ?",
                         (sinir,)).rowcount


def liste(kullanici_id: int, yol=None) -> list[dict]:
    """Hesap ekranında 'kaç cihaza bildirim gidiyor' göstermek için."""
    try:
        kur(yol)
        with ambar.baglan(yol) as c:
            r = c.execute(
                "SELECT platform, olusturma, son_gorulme FROM cihaz "
                "WHERE kullanici_id=? ORDER BY son_gorulme DESC",
                (kullanici_id,)).fetchall()
        return [dict(x) for x in r]
    except Exception:
        return []
