"""Kalıcı veri ambarı (SQLite).

Neden dosya değil veritabanı: günlük anlık görüntüler, haberler ve sinyal
sonuçları zamanla birikir ve sorgulanması gerekir ("bu hissenin son 30 günü",
"geçen ay verilen sinyallerin kaçı tuttu"). JSON dosyalarla bu ölçeklenmez.

Tablolar:
  gunluk_fiyat   — her hisse, her gün: kapanış, değişim, hacim, göstergeler
  haber          — toplanan haberler
  haber_hisse    — haber ↔ hisse eşleşmeleri (çoktan çoğa)
  sinyal         — sistemin ürettiği her sinyal
  sinyal_sonuc   — o sinyalden 1/5/20 gün sonra ne oldu
  gunluk_ozet    — günün piyasa özeti
  calisma        — iş kaydı (ne zaman çalıştı, ne oldu)
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

VERITABANI = Path(__file__).resolve().parent.parent / "veri" / "ambar.db"

SEMA = """
CREATE TABLE IF NOT EXISTS gunluk_fiyat (
    tarih       TEXT NOT NULL,
    sembol      TEXT NOT NULL,
    kapanis     REAL,
    acilis      REAL,
    yuksek      REAL,
    dusuk       REAL,
    hacim       REAL,
    onceki      REAL,
    degisim     REAL,          -- yüzde
    tl_hacim    REAL,
    rsi         REAL,
    adx         REAL,
    atr_yuzde   REAL,
    sma200_ustu INTEGER,
    skor        REAL,
    PRIMARY KEY (tarih, sembol)
);
CREATE INDEX IF NOT EXISTS ix_fiyat_sembol ON gunluk_fiyat(sembol, tarih);

CREATE TABLE IF NOT EXISTS haber (
    id        TEXT PRIMARY KEY,      -- url hash
    tarih     TEXT NOT NULL,
    kaynak    TEXT,
    baslik    TEXT,
    ozet      TEXT,
    url       TEXT,
    yayin     TEXT
);
CREATE INDEX IF NOT EXISTS ix_haber_tarih ON haber(tarih);

CREATE TABLE IF NOT EXISTS haber_hisse (
    haber_id  TEXT NOT NULL,
    sembol    TEXT NOT NULL,
    ifade     TEXT,
    PRIMARY KEY (haber_id, sembol)
);
CREATE INDEX IF NOT EXISTS ix_hh_sembol ON haber_hisse(sembol);

CREATE TABLE IF NOT EXISTS sinyal (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tarih     TEXT NOT NULL,
    sembol    TEXT NOT NULL,
    strateji  TEXT,
    skor      REAL,
    fiyat     REAL,
    stop      REAL,
    hedef     REAL,
    rsi       REAL,
    adx       REAL,
    sma200_ustu INTEGER,
    alinabilir  INTEGER,
    UNIQUE (tarih, sembol, strateji)
);
CREATE INDEX IF NOT EXISTS ix_sinyal_tarih ON sinyal(tarih);

CREATE TABLE IF NOT EXISTS sinyal_sonuc (
    sinyal_id INTEGER NOT NULL,
    gun       INTEGER NOT NULL,      -- 1, 5, 20
    tarih     TEXT,
    fiyat     REAL,
    getiri    REAL,                  -- ham: N gün sonra kapanış (stop'suz)
    kural_getiri REAL,               -- stop/hedef uygulanmış (backtestle kıyaslanabilir)
    cikis_sebep  TEXT,               -- stop | hedef | sure
    stop_gordu INTEGER,
    hedef_gordu INTEGER,
    PRIMARY KEY (sinyal_id, gun)
);

CREATE TABLE IF NOT EXISTS gunluk_ozet (
    tarih     TEXT PRIMARY KEY,
    veri      TEXT                   -- JSON
);

CREATE TABLE IF NOT EXISTS calisma (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    baslangic TEXT,
    bitis     TEXT,
    durum     TEXT,
    ozet      TEXT
);

CREATE TABLE IF NOT EXISTS ai_harcama (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    zaman     TEXT NOT NULL,
    ay        TEXT NOT NULL,      -- 'YYYY-MM', bütçe bu alandan sayılır
    is_adi    TEXT,
    model     TEXT,
    giris     INTEGER,            -- önbelleksiz giriş tokenı
    cikis     INTEGER,
    onbellek_yazma INTEGER,
    onbellek_okuma INTEGER,
    usd       REAL,
    tl        REAL
);
CREATE INDEX IF NOT EXISTS ix_ai_ay ON ai_harcama(ay);

-- Kullanıcının KARARLARI. `sinyal` tablosundan ayrı tutulur ve öyle
-- kalmalı: sinyal sistemin ne önerdiği, karar kullanıcının ne yaptığı.
-- İkisini aynı tabloda tutmak, "sistem ne dedi" ile "ben ne yaptım"
-- sorularını birbirine karıştırır — oysa aradaki FARK ölçülmek istenen
-- şeyin ta kendisi.
--
-- Değiştirilemez günlük: satır güncellenmez, yalnızca eklenir. Satış da
-- ayrı bir karardır, alımı silmez. "Sonradan ben zaten biliyordum"
-- demeyi imkânsız kılan tek şey budur.
CREATE TABLE IF NOT EXISTS karar (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    zaman     TEXT NOT NULL,        -- ISO, saniye duyarlı
    tarih     TEXT NOT NULL,        -- YYYY-MM-DD (gruplama için)
    tur       TEXT NOT NULL,        -- alim | satim
    sembol    TEXT NOT NULL,
    adet      INTEGER NOT NULL,
    fiyat     REAL NOT NULL,
    kagit     INTEGER DEFAULT 1,    -- 1 = kağıt üzerinde, 0 = gerçek para
    stop      REAL,
    hedef     REAL,
    -- Karar anında sistem ne diyordu? SONRADAN doldurulmaz.
    sinyal_var    INTEGER DEFAULT 0,  -- o gün bu hisseye sinyal var mıydı
    strateji      TEXT,
    onerilir      INTEGER,            -- sinyal karantinada mıydı
    skor          REAL,
    gerekce   TEXT
);
CREATE INDEX IF NOT EXISTS ix_karar_sembol ON karar(sembol, zaman);
CREATE INDEX IF NOT EXISTS ix_karar_tarih ON karar(tarih);
"""


@contextmanager
def baglan(yol: Path | None = None):
    yol = yol or VERITABANI
    yol.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(yol, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        yield con
        con.commit()
    finally:
        con.close()


def kur(yol: Path | None = None) -> None:
    with baglan(yol) as con:
        con.executescript(SEMA)


def _g(x):
    """None/NaN güvenli sayı."""
    try:
        if x is None:
            return None
        f = float(x)
        return None if f != f else f     # NaN kontrolü
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────── fiyat

def fiyat_yaz(satirlar: list[dict], yol: Path | None = None) -> int:
    """Günlük fiyat anlık görüntüsünü yazar. Aynı gün tekrar yazılırsa günceller."""
    if not satirlar:
        return 0
    with baglan(yol) as con:
        con.executemany("""
            INSERT INTO gunluk_fiyat
              (tarih,sembol,kapanis,acilis,yuksek,dusuk,hacim,onceki,degisim,
               tl_hacim,rsi,adx,atr_yuzde,sma200_ustu,skor)
            VALUES (:tarih,:sembol,:kapanis,:acilis,:yuksek,:dusuk,:hacim,:onceki,
                    :degisim,:tl_hacim,:rsi,:adx,:atr_yuzde,:sma200_ustu,:skor)
            ON CONFLICT(tarih,sembol) DO UPDATE SET
              kapanis=excluded.kapanis, acilis=excluded.acilis,
              yuksek=excluded.yuksek, dusuk=excluded.dusuk, hacim=excluded.hacim,
              onceki=excluded.onceki, degisim=excluded.degisim,
              tl_hacim=excluded.tl_hacim, rsi=excluded.rsi, adx=excluded.adx,
              atr_yuzde=excluded.atr_yuzde, sma200_ustu=excluded.sma200_ustu,
              skor=excluded.skor
        """, satirlar)
        return len(satirlar)


def fiyat_gecmis(sembol: str, gun: int = 30, yol: Path | None = None) -> list[dict]:
    with baglan(yol) as con:
        c = con.execute("""SELECT * FROM gunluk_fiyat WHERE sembol=?
                           ORDER BY tarih DESC LIMIT ?""", (sembol.upper(), gun))
        return [dict(r) for r in c.fetchall()]


def gun_fiyatlari(tarih: str | None = None, yol: Path | None = None) -> list[dict]:
    with baglan(yol) as con:
        if tarih is None:
            r = con.execute("SELECT MAX(tarih) t FROM gunluk_fiyat").fetchone()
            tarih = r["t"] if r else None
        if not tarih:
            return []
        c = con.execute("""SELECT * FROM gunluk_fiyat WHERE tarih=?
                           ORDER BY degisim DESC""", (tarih,))
        return [dict(r) for r in c.fetchall()]


def fiyat_tarihleri(yol: Path | None = None) -> list[str]:
    with baglan(yol) as con:
        c = con.execute("SELECT DISTINCT tarih FROM gunluk_fiyat ORDER BY tarih DESC")
        return [r["tarih"] for r in c.fetchall()]


# ─────────────────────────────────────────────── haber

def haber_yaz(haberler: list[dict], eslesmeler: list[dict],
              yol: Path | None = None) -> tuple[int, int]:
    with baglan(yol) as con:
        if haberler:
            con.executemany("""
                INSERT OR IGNORE INTO haber (id,tarih,kaynak,baslik,ozet,url,yayin)
                VALUES (:id,:tarih,:kaynak,:baslik,:ozet,:url,:yayin)""", haberler)
        if eslesmeler:
            con.executemany("""
                INSERT OR IGNORE INTO haber_hisse (haber_id,sembol,ifade)
                VALUES (:haber_id,:sembol,:ifade)""", eslesmeler)
    return len(haberler), len(eslesmeler)


def hisse_haberleri(sembol: str, gun: int = 7, yol: Path | None = None) -> list[dict]:
    with baglan(yol) as con:
        c = con.execute("""
            SELECT h.*, hh.ifade FROM haber h
            JOIN haber_hisse hh ON hh.haber_id = h.id
            WHERE hh.sembol = ? AND h.tarih >= date('now', ?)
            ORDER BY h.tarih DESC, h.yayin DESC LIMIT 40
        """, (sembol.upper(), f"-{gun} days"))
        return [dict(r) for r in c.fetchall()]


def gun_haberleri(tarih: str | None = None, azami: int = 60,
                  yol: Path | None = None) -> list[dict]:
    tarih = tarih or date.today().isoformat()
    with baglan(yol) as con:
        c = con.execute("""SELECT * FROM haber WHERE tarih=?
                           ORDER BY yayin DESC LIMIT ?""", (tarih, azami))
        haberler = [dict(r) for r in c.fetchall()]
        for h in haberler:
            e = con.execute("SELECT sembol, ifade FROM haber_hisse WHERE haber_id=?",
                            (h["id"],)).fetchall()
            h["hisseler"] = [x["sembol"] for x in e]
            h["ifadeler"] = {x["sembol"]: x["ifade"] for x in e}
        return haberler


# ─────────────────────────────────────────────── AI harcaması

def ai_harcama_yaz(kayit: dict, yol: Path | None = None) -> None:
    with baglan(yol) as con:
        con.execute("""
            INSERT INTO ai_harcama
              (zaman,ay,is_adi,model,giris,cikis,onbellek_yazma,
               onbellek_okuma,usd,tl)
            VALUES (:zaman,:ay,:is_adi,:model,:giris,:cikis,:onbellek_yazma,
                    :onbellek_okuma,:usd,:tl)""", kayit)


def ai_ay_toplami(ay: str | None = None, yol: Path | None = None) -> float:
    """Bu ayki toplam harcama (TL). Bütçe tavanı buna bakar."""
    ay = ay or datetime.now().strftime("%Y-%m")
    with baglan(yol) as con:
        r = con.execute("SELECT COALESCE(SUM(tl),0) t FROM ai_harcama WHERE ay=?",
                        (ay,)).fetchone()
        return float(r["t"] or 0.0)


def ai_dokum(ay: str | None = None, yol: Path | None = None) -> list[dict]:
    """İş bazında döküm — parayı nerede harcadığımız görünsün."""
    ay = ay or datetime.now().strftime("%Y-%m")
    with baglan(yol) as con:
        c = con.execute("""SELECT is_adi, model, COUNT(*) adet,
                                  SUM(giris) giris, SUM(cikis) cikis,
                                  SUM(onbellek_okuma) onb, SUM(tl) tl
                           FROM ai_harcama WHERE ay=?
                           GROUP BY is_adi, model ORDER BY tl DESC""", (ay,))
        return [dict(r) for r in c.fetchall()]


# ─────────────────────────────────────────────── sinyal ve sonuç

def sinyal_yaz(sinyaller: list[dict], yol: Path | None = None) -> int:
    if not sinyaller:
        return 0
    with baglan(yol) as con:
        con.executemany("""
            INSERT OR IGNORE INTO sinyal
              (tarih,sembol,strateji,skor,fiyat,stop,hedef,rsi,adx,
               sma200_ustu,alinabilir)
            VALUES (:tarih,:sembol,:strateji,:skor,:fiyat,:stop,:hedef,:rsi,:adx,
                    :sma200_ustu,:alinabilir)""", sinyaller)
        return len(sinyaller)


def sonuclanmamis_sinyaller(gun: int, yol: Path | None = None) -> list[dict]:
    """Belirli bir vade için henüz sonucu ölçülmemiş sinyaller."""
    with baglan(yol) as con:
        c = con.execute("""
            SELECT s.* FROM sinyal s
            LEFT JOIN sinyal_sonuc r ON r.sinyal_id = s.id AND r.gun = ?
            WHERE r.sinyal_id IS NULL
              AND s.tarih <= date('now', ?)
            ORDER BY s.tarih
        """, (gun, f"-{gun + 2} days"))
        return [dict(r) for r in c.fetchall()]


def sonuc_yaz(sonuclar: list[dict], yol: Path | None = None) -> int:
    if not sonuclar:
        return 0
    with baglan(yol) as con:
        con.executemany("""
            INSERT OR REPLACE INTO sinyal_sonuc
              (sinyal_id,gun,tarih,fiyat,getiri,kural_getiri,cikis_sebep,
               stop_gordu,hedef_gordu)
            VALUES (:sinyal_id,:gun,:tarih,:fiyat,:getiri,:kural_getiri,:cikis_sebep,
                    :stop_gordu,:hedef_gordu)
        """, sonuclar)
        return len(sonuclar)


def sinyal_karnesi(gun: int = 20, strateji: str | None = None,
                   yol: Path | None = None) -> dict:
    """Sistemin kendi sinyallerinin gerçek performansı."""
    with baglan(yol) as con:
        sorgu = """
            SELECT s.strateji, r.getiri, r.kural_getiri, r.cikis_sebep,
                   r.stop_gordu, r.hedef_gordu
            FROM sinyal s JOIN sinyal_sonuc r ON r.sinyal_id = s.id
            WHERE r.gun = ?"""
        p = [gun]
        if strateji:
            sorgu += " AND s.strateji = ?"
            p.append(strateji)
        satirlar = [dict(r) for r in con.execute(sorgu, p).fetchall()]

    if not satirlar:
        return {"sinyal": 0, "vade_gun": gun}

    def ozet(anahtar: str) -> dict:
        g = [r[anahtar] for r in satirlar if r[anahtar] is not None]
        if not g:
            return {}
        kaz = [x for x in g if x > 0]
        kay = [x for x in g if x <= 0]
        return {
            "sinyal": len(g),
            "kazanma_orani": round(len(kaz) / len(g) * 100, 1),
            "ortalama_getiri": round(sum(g) / len(g), 2),
            "ort_kazanc": round(sum(kaz) / len(kaz), 2) if kaz else 0.0,
            "ort_kayip": round(sum(kay) / len(kay), 2) if kay else 0.0,
            "en_iyi": round(max(g), 2), "en_kotu": round(min(g), 2),
        }

    ham = ozet("getiri")
    kural = ozet("kural_getiri")
    from collections import Counter
    sebepler = Counter(r["cikis_sebep"] for r in satirlar if r["cikis_sebep"])
    return {
        **kural,                              # varsayılan: KURAL bazlı (kıyaslanabilir)
        "vade_gun": gun,
        "ham": ham,                           # stop'suz tutma
        "cikis_dagilimi": dict(sebepler),
        "stop_goren": sum(1 for r in satirlar if r["stop_gordu"]),
        "hedef_goren": sum(1 for r in satirlar if r["hedef_gordu"]),
    }


# ─────────────────────────────────────────────── özet ve iş kaydı

def ozet_yaz(tarih: str, veri: dict, yol: Path | None = None) -> None:
    with baglan(yol) as con:
        con.execute("INSERT OR REPLACE INTO gunluk_ozet (tarih,veri) VALUES (?,?)",
                    (tarih, json.dumps(veri, ensure_ascii=False)))


def ozet_oku(tarih: str | None = None, yol: Path | None = None) -> dict | None:
    with baglan(yol) as con:
        if tarih:
            r = con.execute("SELECT veri FROM gunluk_ozet WHERE tarih=?",
                            (tarih,)).fetchone()
        else:
            r = con.execute(
                "SELECT veri FROM gunluk_ozet ORDER BY tarih DESC LIMIT 1").fetchone()
        return json.loads(r["veri"]) if r else None


def ozet_tarihleri(azami: int = 30, yol: Path | None = None) -> list[str]:
    with baglan(yol) as con:
        c = con.execute("SELECT tarih FROM gunluk_ozet ORDER BY tarih DESC LIMIT ?",
                        (azami,))
        return [r["tarih"] for r in c.fetchall()]


def calisma_basla(yol: Path | None = None) -> int:
    with baglan(yol) as con:
        c = con.execute("INSERT INTO calisma (baslangic,durum) VALUES (?,?)",
                        (datetime.now().isoformat(timespec="seconds"), "çalışıyor"))
        return c.lastrowid


def calisma_bitir(is_id: int, durum: str, ozet: str = "",
                  yol: Path | None = None) -> None:
    with baglan(yol) as con:
        con.execute("UPDATE calisma SET bitis=?, durum=?, ozet=? WHERE id=?",
                    (datetime.now().isoformat(timespec="seconds"), durum,
                     ozet[:2000], is_id))


def son_calismalar(azami: int = 10, yol: Path | None = None) -> list[dict]:
    with baglan(yol) as con:
        c = con.execute("SELECT * FROM calisma ORDER BY id DESC LIMIT ?", (azami,))
        return [dict(r) for r in c.fetchall()]


def istatistik(yol: Path | None = None) -> dict:
    with baglan(yol) as con:
        def say(t):
            return con.execute(f"SELECT COUNT(*) n FROM {t}").fetchone()["n"]
        r = con.execute("SELECT MIN(tarih) a, MAX(tarih) b FROM gunluk_fiyat").fetchone()
        return {
            "fiyat_kaydi": say("gunluk_fiyat"),
            "haber": say("haber"),
            "haber_eslesme": say("haber_hisse"),
            "sinyal": say("sinyal"),
            "sinyal_sonuc": say("sinyal_sonuc"),
            "gunluk_ozet": say("gunluk_ozet"),
            "ilk_tarih": r["a"], "son_tarih": r["b"],
            "boyut_kb": round(VERITABANI.stat().st_size / 1024, 1)
                        if VERITABANI.exists() else 0,
        }
