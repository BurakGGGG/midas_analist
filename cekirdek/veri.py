"""Veri katmanı: yfinance'ten OHLCV çek, diske önbellekle, temiz DataFrame döndür.

Not: Borsa İstanbul verisi yfinance üzerinde ~15 dk gecikmelidir. Bu sistem
gün sonu (EOD) kararları için tasarlandı, saniyelik scalping için değil.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from .evren import yf_kodu, sade_kod

ONBELLEK = Path(__file__).resolve().parent.parent / "veri"
ONBELLEK.mkdir(exist_ok=True)

def _onarim_mumkun_mu() -> bool:
    """yfinance repair=True scikit-learn ister. DOĞRUDAN sor.

    Eskiden bu, 'boş sonuç geldiyse sklearn yoktur' diye tahmin ediliyordu.
    Boş sonucun ikinci bir sebebi var: hisse borsadan çıkmış olabilir.
    BIST 100 listesinde böyle 4 kod var; biri çekilince onarım TÜM çalıştırma
    için kapanıyordu ve geri kalan ~96 hisse onarımsız iniyordu — yani
    düzeltilmiş sayılan bedelsiz/bölünme hatası sessizce geri geliyordu.
    """
    import importlib.util
    return importlib.util.find_spec("sklearn") is not None


_ONARIM = _onarim_mumkun_mu()
if not _ONARIM:
    print("  uyarı: scikit-learn kurulu değil — yfinance fiyat onarımı kapalı")


SUTUNLAR = ["Open", "High", "Low", "Close", "Volume"]


def _onbellek_yolu(sembol: str, aralik: str) -> Path:
    return ONBELLEK / f"{sade_kod(sembol)}_{aralik}.pkl"


def _taze_mi(yol: Path, azami_saat: float, gerekli_baslangic: datetime | None = None) -> bool:
    """Önbellek hem YETERİNCE YENİ hem de YETERİNCE GERİYE gidiyor olmalı.

    İkinci koşul şart: 400 günlük istekle doldurulmuş bir dosya, 1200 günlük
    istek için sessizce kullanılırsa backtest kısa geçmişle çalışır ve sonuç
    farkında olmadan yanlış çıkar.
    """
    if not yol.exists():
        return False
    if time.time() - yol.stat().st_mtime >= azami_saat * 3600:
        return False
    if gerekli_baslangic is None:
        return True
    try:
        df = pd.read_pickle(yol)
    except Exception:
        return False
    if df is None or df.empty:
        return False
    # 10 günlük tolerans: hisse o tarihte henüz işlem görmüyor olabilir
    return df.index[0] <= pd.Timestamp(gerekli_baslangic) + pd.Timedelta(days=10)


def fiyat_cek(
    sembol: str,
    gun: int = 750,
    aralik: str = "1d",
    onbellek_saat: float = 6.0,
    zorla: bool = False,
    ham: bool = False,
) -> pd.DataFrame:
    """Tek hisse için OHLCV. Boş DataFrame dönebilir - çağıran kontrol etmeli.

    ham=True: sembole '.IS' ekleme. BIST dışı kodlar (EEM, AAPL gibi harf-only
    ABD sembolleri) için şart - yoksa 'EEM.IS' aranır ve 404 döner."""
    yol = _onbellek_yolu(sembol, aralik)
    baslangic = datetime.now() - timedelta(days=gun)

    if not zorla and _taze_mi(yol, onbellek_saat, baslangic):
        try:
            return pd.read_pickle(yol)
        except Exception:
            pass  # bozuk önbellek -> yeniden çek

    try:
        kod = sembol.strip().upper() if ham else yf_kodu(sembol)
        t = yf.Ticker(kod)

        def _gecmis(**kw):
            """repair=True kaçırılmış bedelsiz/bölünmeleri onarır (EUREN'de
            2024-12-02'de olmayan bir -%63,6 düşüş üretiyordu).

            Boş sonuç gelirse onarımı KAPATMAYIZ — boş sonuç çoğu zaman
            hissenin borsadan çıkmış olması demektir, sklearn eksikliği değil.
            Yalnızca bu çağrı için onarımsız bir kez daha denenir."""
            d = t.history(auto_adjust=True, raise_errors=False,
                          repair=_ONARIM, **kw)
            if _ONARIM and (d is None or d.empty):
                d = t.history(auto_adjust=True, raise_errors=False,
                              repair=False, **kw)
            return d

        ham_veri = _gecmis(start=baslangic.strftime("%Y-%m-%d"), interval=aralik)
        # yfinance tuhaflığı: bazı semboller (BIST sektör endeksleri gibi)
        # start= ile tek satır döner ama period= ile tam geçmişi verir.
        # Az veri geldiyse period= ile yeniden dene.
        if ham_veri is None or len(ham_veri) < min(30, gun // 5):
            try:
                p_kod = "max" if gun > 1800 else ("5y" if gun > 730 else
                        ("2y" if gun > 365 else "1y"))
                yedek = _gecmis(period=p_kod, interval=aralik)
                if yedek is not None and len(yedek) > len(ham_veri or []):
                    ham_veri = yedek[yedek.index >= baslangic.strftime("%Y-%m-%d")] \
                        if len(yedek) else yedek
            except Exception:
                pass
    except Exception:
        ham_veri = pd.DataFrame()

    if ham_veri is None or ham_veri.empty:
        # ağ hatasında bayat önbellek, hiç yoktan iyidir
        if yol.exists():
            try:
                return pd.read_pickle(yol)
            except Exception:
                pass
        return pd.DataFrame(columns=SUTUNLAR)

    df = ham_veri[[c for c in SUTUNLAR if c in ham_veri.columns]].copy()
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Tarih"

    try:
        df.to_pickle(yol)
    except Exception:
        pass
    return df


def toplu_cek(
    semboller: list[str],
    gun: int = 750,
    aralik: str = "1d",
    onbellek_saat: float = 6.0,
    zorla: bool = False,
    sessiz: bool = False,
) -> dict[str, pd.DataFrame]:
    """Çok sayıda hisseyi çeker. Ağı yormamak için önbelleği olanları atlar."""
    sonuc: dict[str, pd.DataFrame] = {}
    eksik: list[str] = []
    baslangic = datetime.now() - timedelta(days=gun)

    for s in semboller:
        yol = _onbellek_yolu(s, aralik)
        if not zorla and _taze_mi(yol, onbellek_saat, baslangic):
            try:
                sonuc[sade_kod(s)] = pd.read_pickle(yol)
                continue
            except Exception:
                pass
        eksik.append(s)

    if eksik:
        if not sessiz:
            print(f"  {len(eksik)} hisse indiriliyor ({len(sonuc)} önbellekten)...")
        # yfinance toplu indirme tek istekte çok daha hızlı
        kodlar = [yf_kodu(s) for s in eksik]
        def _indir(onar: bool):
            return yf.download(
                kodlar,
                start=baslangic.strftime("%Y-%m-%d"),
                interval=aralik,
                auto_adjust=True,
                group_by="ticker",
                progress=False,
                threads=True,
                repair=onar,
            )

        try:
            toplu = _indir(_ONARIM)
            # Boş çerçeve gelirse onarımsız bir kez daha dene — ama onarımı
            # kalıcı olarak kapatma. Listede borsadan çıkmış tek bir kod bile
            # boş sonuç üretebilir; bunun cezasını diğer 99 hisse çekmemeli.
            if _ONARIM and (toplu is None or toplu.empty):
                toplu = _indir(False)
        except Exception:
            toplu = None

        for s in eksik:
            df = pd.DataFrame(columns=SUTUNLAR)
            if toplu is not None and not toplu.empty:
                try:
                    alt = toplu[yf_kodu(s)] if isinstance(toplu.columns, pd.MultiIndex) else toplu
                    alt = alt[[c for c in SUTUNLAR if c in alt.columns]].dropna(subset=["Close"])
                    if not alt.empty:
                        df = alt[alt["Close"] > 0].copy()
                        if df.index.tz is not None:
                            df.index = df.index.tz_localize(None)
                        df.index.name = "Tarih"
                        df.to_pickle(_onbellek_yolu(s, aralik))
                except Exception:
                    df = pd.DataFrame(columns=SUTUNLAR)
            if df.empty:   # toplu indirme tutmadıysa tek tek dene
                df = fiyat_cek(s, gun, aralik, onbellek_saat, zorla)
            sonuc[sade_kod(s)] = df

    return {k: v for k, v in sonuc.items() if v is not None and not v.empty}


def usd_try() -> float:
    """Güncel USD/TRY. Başarısız olursa 0 döner."""
    try:
        d = yf.Ticker("TRY=X").history(period="5d")
        return float(d["Close"].iloc[-1])
    except Exception:
        return 0.0
