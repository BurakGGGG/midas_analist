"""Şirket değerleme: 'iyi şirket' ile 'iyi fiyat' ayrı sorulardır.

Mükemmel bir şirketi çok pahalıya almak, vasat bir şirketi ucuza almaktan
daha kötü sonuç verebilir. Bu modül ikinci soruyu cevaplar.

Bütün çarpanlar KUR DÜZELTMELİDİR: piyasa değeri TL, tablo USD olabilir
(bkz. temel_veri.py). Dönüşüm yapılamıyorsa çarpan hesaplanmaz.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .temel_veri import Finansallar
from .temel import BANKA_SEKTOR, _bol


@dataclass
class Carpan:
    ad: str
    deger: float
    yorum: str
    dusuk_ucuz: bool = True      # düşük = ucuz mu?
    gecerli: bool = True
    sektor_ort: float = np.nan

    @property
    def var_mi(self) -> bool:
        return np.isfinite(self.deger)

    @property
    def sektore_gore(self) -> str:
        if not self.var_mi or not np.isfinite(self.sektor_ort) or self.sektor_ort == 0:
            return "—"
        fark = (self.deger / self.sektor_ort - 1) * 100
        ucuz = fark < 0 if self.dusuk_ucuz else fark > 0
        return f"sektör ort.'a göre %{abs(fark):.0f} {'UCUZ' if ucuz else 'PAHALI'}"


def carpanlar(f: Finansallar) -> dict[str, Carpan]:
    """Fiyat çarpanları. TTM (son 12 ay) tercih edilir, yoksa son yıllık."""
    banka = f.sektor in BANKA_SEKTOR
    pd_ = f.piyasa_degeri
    kur = f.kur

    def tl(anahtar: str, tablo: str = "gelir") -> float:
        """Kalemi TL'ye çevirir. Kur bilinmiyorsa NaN — yanlış hesaplama yapma."""
        if not np.isfinite(kur):
            return np.nan
        ttm = f.son_12_ay(anahtar) if tablo == "gelir" else np.nan
        ham = ttm if np.isfinite(ttm) else f.al(anahtar, tablo)
        return ham * kur if np.isfinite(ham) else np.nan

    net_kar = tl("net_kar")
    hasilat = tl("hasilat")
    favok = tl("favok")
    ozsermaye = tl("ozsermaye", "bilanco")
    borc = tl("toplam_borc", "bilanco")
    nakit = tl("nakit", "bilanco")
    fcf = tl("serbest_nakit", "nakit")

    # Firma değeri = piyasa değeri + net borç
    net_borc = (borc - nakit) if np.isfinite(borc) and np.isfinite(nakit) else np.nan
    fd = (pd_ + net_borc) if np.isfinite(pd_) and np.isfinite(net_borc) else np.nan

    c: dict[str, Carpan] = {}
    c["fk"] = Carpan("F/K (Fiyat/Kazanç)", _bol(pd_, net_kar),
        "Şirket bugünkü kârını sürdürürse yatırımını kaç yılda geri alırsın. "
        "Türkiye'de yüksek faiz nedeniyle düşük F/K normaldir.")
    c["pd_dd"] = Carpan("PD/DD (Piyasa/Defter)", _bol(pd_, ozsermaye),
        "Şirketin defter değerinin kaç katına satılıyor. Bankalarda en çok "
        "kullanılan çarpan; 1'in altı 'defterin altında' demektir.")
    c["fd_favok"] = Carpan("FD/FAVÖK", _bol(fd, favok),
        "Borç dahil şirket değeri, nakit kârın kaç katı. Farklı borç yapılarını "
        "kıyaslamayı sağlar. Bankada anlamsızdır.", gecerli=not banka)
    c["fs"] = Carpan("F/S (Fiyat/Satış)", _bol(pd_, hasilat),
        "Zarar eden ya da kârı dalgalanan şirketlerde F/K yerine kullanılır.",
        gecerli=not banka)
    c["fcf_verim"] = Carpan("Serbest nakit verimi", _bol(fcf, pd_) * 100,
        "Şirketin ürettiği serbest nakit, piyasa değerinin yüzde kaçı. "
        "Mevduat faiziyle doğrudan kıyaslanabilir.", dusuk_ucuz=False, gecerli=not banka)

    # Temettü verimi: son 12 ayın nakit temettüsü / fiyat
    tv = np.nan
    if f.temettu is not None and len(f.temettu) > 0:
        try:
            son_yil = f.temettu[f.temettu.index >= (f.temettu.index[-1] - __import__("pandas").Timedelta(days=365))]
            tv = float(son_yil.sum()) / f.fiyat * 100 if np.isfinite(f.fiyat) and f.fiyat > 0 else np.nan
        except Exception:
            tv = np.nan
    c["temettu_verim"] = Carpan("Temettü verimi", tv,
        "Nakit temettünün fiyata oranı. Mevduat/tahvil faiziyle kıyasla — "
        "altındaysa temettü tek başına gerekçe değildir.", dusuk_ucuz=False)

    # PEG: F/K'yı büyümeye böler. 1'in altı klasik olarak 'ucuz' sayılır.
    from .temel import _buyume
    buyume = _buyume(f, "net_kar", 1)
    c["peg"] = Carpan("PEG (F/K ÷ büyüme)",
        _bol(c["fk"].deger, buyume) if np.isfinite(buyume) and buyume > 0 else np.nan,
        "Hızlı büyüyen şirket yüksek F/K hak eder. PEG bunu düzeltir. "
        "Türkiye'de büyümenin ne kadarı enflasyon, ona bak.")
    return c


# İskonto oranı raporlama para birimine göre değişmeli. TL nakit akışını %40 ile,
# USD nakit akışını %11 ile iskonto edersin — ikisini karıştırmak sonucu bozar.
ISKONTO = {"TRY": 40.0, "USD": 11.0, "EUR": 9.0}
SONSUZ_BUYUME = {"TRY": 20.0, "USD": 3.0, "EUR": 2.5}


def ters_dcf(f: Finansallar, iskonto: float | None = None,
             sonsuz_buyume: float | None = None, yil: int = 5) -> dict:
    """Ters DCF: 'bugünkü fiyat hangi büyümeyi ima ediyor?'

    Klasik DCF Türkiye'de neredeyse kullanışsızdır: %40 iskonto oranında
    varsayımın küçük bir değişimi sonucu ikiye katlar. Ters DCF daha dürüsttür —
    tahmin üretmez, piyasanın zaten yaptığı tahmini AÇIĞA ÇIKARIR.

    Sen sadece şunu değerlendirirsin: 'bu büyüme makul mü?'
    """
    if not np.isfinite(f.kur) or f.kur <= 0:
        return {"hata": "kur bilinmiyor, hesaplanamıyor"}

    # Hesabın TAMAMI şirketin raporlama para biriminde yapılır: nakit akışı
    # zaten o birimde, piyasa değerini de oraya çeviriyoruz. Böylece iskonto
    # oranı, enflasyon kıyası ve büyüme aynı dünyada kalır.
    para = f.tablo_para
    iskonto = ISKONTO.get(para, 40.0) if iskonto is None else iskonto
    sonsuz_buyume = SONSUZ_BUYUME.get(para, 20.0) if sonsuz_buyume is None else sonsuz_buyume

    fcf = f.al("serbest_nakit", "nakit")
    temel_kalem = "serbest nakit akışı"
    if not np.isfinite(fcf) or fcf <= 0:
        fcf = f.son_12_ay("net_kar")
        temel_kalem = "net kâr"
    if not np.isfinite(fcf) or fcf <= 0:
        return {"hata": "pozitif nakit akışı yok, ters DCF anlamsız"}
    if not np.isfinite(f.piyasa_degeri):
        return {"hata": "piyasa değeri yok"}
    piyasa_degeri = f.piyasa_degeri / f.kur   # TL -> raporlama para birimi

    i, g_son = iskonto / 100, sonsuz_buyume / 100
    if i <= g_son:
        return {"hata": "iskonto oranı sonsuz büyümenin altında — model geçersiz"}

    def deger(g: float) -> float:
        bugunku = 0.0
        nakit = fcf
        for t in range(1, yil + 1):
            nakit *= (1 + g)
            bugunku += nakit / (1 + i) ** t
        devam = nakit * (1 + g_son) / (i - g_son)
        return bugunku + devam / (1 + i) ** yil

    # ikili arama: hangi g, bugünkü fiyatı verir?
    alt, ust = -0.5, 3.0
    for _ in range(80):
        orta = (alt + ust) / 2
        if deger(orta) < piyasa_degeri:
            alt = orta
        else:
            ust = orta
    ima = (alt + ust) / 2 * 100

    return {
        "ima_edilen_buyume": round(ima, 1),
        "temel_kalem": temel_kalem,
        "para": para,
        "baslangic_nakit": fcf,
        "iskonto": iskonto,
        "sonsuz_buyume": sonsuz_buyume,
        "yil": yil,
        "yorum": (
            f"Bugünkü fiyat, {temel_kalem}nın {yil} yıl boyunca yılda "
            f"%{ima:.1f} ({para}) büyümesini ima ediyor. "
            f"[iskonto %{iskonto:.0f}, sonsuz büyüme %{sonsuz_buyume:.0f}]"
        ),
        "kiyas": (
            f"Enflasyon %{f.enflasyon_referansi():.1f}. İma edilen büyüme bunun "
            f"{'ÜSTÜNDE — piyasa reel büyüme bekliyor' if ima > f.enflasyon_referansi() else 'ALTINDA — piyasa reel daralma fiyatlıyor'}."
        ),
    }


def sektor_ortalamasi(finansallar: dict[str, Finansallar],
                      sektor: str | None = None) -> dict[str, float]:
    """Sektördeki şirketlerin çarpan MEDYANI.

    Ortalama değil medyan: tek bir uç değer (zarar eden şirketin negatif F/K'sı)
    ortalamayı bozar, medyanı bozmaz.
    """
    havuz = [f for f in finansallar.values()
             if (sektor is None or f.sektor == sektor)]
    if not havuz:
        return {}
    toplu: dict[str, list[float]] = {}
    for f in havuz:
        for ad, c in carpanlar(f).items():
            if c.var_mi and c.gecerli and 0 < c.deger < 200:   # uç değerleri ele
                toplu.setdefault(ad, []).append(c.deger)
    return {ad: float(np.median(v)) for ad, v in toplu.items() if len(v) >= 3}


def deger_hukmu(f: Finansallar, c: dict[str, Carpan] | None = None,
                sektor_ort: dict[str, float] | None = None) -> dict:
    """Ucuz mu pahalı mı — ama tek bir çarpana dayanmadan."""
    c = c or carpanlar(f)
    if sektor_ort:
        for ad, v in sektor_ort.items():
            if ad in c:
                c[ad].sektor_ort = v

    puanlar, gerekce = [], []
    for ad, agirlik in [("fk", 3), ("fd_favok", 3), ("pd_dd", 2), ("fs", 1), ("fcf_verim", 2)]:
        ca = c.get(ad)
        if ca is None or not ca.var_mi or not ca.gecerli or not np.isfinite(ca.sektor_ort):
            continue
        if ca.sektor_ort == 0:
            continue
        oran = ca.deger / ca.sektor_ort
        # düşük=ucuz çarpanlarda oran<1 iyi; verimlerde tersi
        p = (1 - oran) if ca.dusuk_ucuz else (oran - 1)
        puanlar.append((float(np.clip(p, -1, 1)), agirlik))
        gerekce.append(f"{ca.ad}: {ca.deger:.2f} vs sektör {ca.sektor_ort:.2f}")

    if not puanlar:
        return {"hukum": "belirsiz", "skor": None,
                "gerekce": ["sektör kıyası için yeterli veri yok"]}

    skor = sum(p * a for p, a in puanlar) / sum(a for _, a in puanlar)
    if skor > 0.25:    hukum = "UCUZ"
    elif skor > 0.08:  hukum = "makul-ucuz"
    elif skor > -0.08: hukum = "adil fiyatlı"
    elif skor > -0.25: hukum = "makul-pahalı"
    else:              hukum = "PAHALI"

    return {"hukum": hukum, "skor": round(float(skor), 3), "gerekce": gerekce,
            "uyari": "Ucuzluk tek başına alım gerekçesi değildir — ucuz şirket "
                     "genellikle bir SEBEPTEN ucuzdur. Kalite skoruyla birlikte oku."}
