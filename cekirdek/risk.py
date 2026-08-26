"""Pozisyon boyutlandırma ve risk yönetimi.

Bu modül sistemin en önemli parçası. Strateji seçimi getiriyi belirler;
risk yönetimi hayatta kalıp kalmayacağını belirler.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


# BIST pay piyasası fiyat adımları (Borsa İstanbul kademe tablosu)
KADEMELER = [(19.90, 0.01), (49.98, 0.02), (99.95, 0.05), (float("inf"), 0.10)]


def fiyat_adimi(fiyat: float) -> float:
    for ust, adim in KADEMELER:
        if fiyat <= ust:
            return adim
    return 0.10


def kademeye_yuvarla(fiyat: float, yukari: bool = False) -> float:
    adim = fiyat_adimi(fiyat)
    n = math.ceil(fiyat / adim) if yukari else math.floor(fiyat / adim)
    return round(n * adim, 2)


@dataclass
class RiskAyarlari:
    sermaye: float = 1000.0
    islem_basi_risk_yuzde: float = 1.5    # tek işlemde sermayenin en fazla %1.5'i riske girer
    azami_pozisyon_yuzde: float = 35.0    # tek hissede sermayenin en fazla %35'i
    azami_es_zamanli: int = 4             # aynı anda en fazla kaç pozisyon
    atr_stop_kat: float = 2.0
    atr_hedef_kat: float = 3.5
    gunluk_kayip_limiti_yuzde: float = 4.0   # gün içi bu kadar kaybettiysen dur


@dataclass
class Pozisyon:
    sembol: str
    adet: int
    giris: float
    stop: float
    hedef: float
    risk_tl: float
    maliyet: float
    sermaye_payi: float
    uyari: str = ""

    @property
    def uygulanabilir(self) -> bool:
        return self.adet >= 1


def pozisyon_hesapla(
    sembol: str,
    fiyat: float,
    atr: float,
    ayar: RiskAyarlari,
    kullanilabilir_nakit: float | None = None,
    stop_kat: float | None = None,
    hedef_kat: float | None = None,
) -> Pozisyon:
    """Kaç adet alınmalı, stop ve hedef nerede?

    İki tavan aynı anda uygulanır:
      1) Risk tavanı  - stop'a düşerse kayıp, risk bütçesini aşmasın
      2) Ağırlık tavanı - tek hisse portföyün çok büyük kısmını kaplamasın
    Küçük sermayede (1000 TL) genellikle 2. tavan bağlayıcıdır, çünkü BIST'te
    kesirli hisse yok - 400 TL'lik bir hisseden 1 adet zaten sermayenin %40'ı.
    """
    nakit = ayar.sermaye if kullanilabilir_nakit is None else kullanilabilir_nakit
    uyarilar: list[str] = []
    # Stop/hedef mesafesi sinyali VEREN stratejinin çarpanlarıyla hesaplanmalı.
    # Aksi halde ekranda gördüğün stop, backtestte ölçülen stop olmaz.
    stop_kat = ayar.atr_stop_kat if stop_kat is None else stop_kat
    hedef_kat = ayar.atr_hedef_kat if hedef_kat is None else hedef_kat

    if atr <= 0 or fiyat <= 0:
        return Pozisyon(sembol, 0, fiyat, 0, 0, 0, 0, 0, "ATR/fiyat geçersiz")

    stop = kademeye_yuvarla(fiyat - stop_kat * atr)
    hedef = kademeye_yuvarla(fiyat + hedef_kat * atr, yukari=True)
    stop_mesafe = fiyat - stop
    if stop_mesafe <= 0:
        return Pozisyon(sembol, 0, fiyat, stop, hedef, 0, 0, 0, "stop mesafesi sıfır")

    risk_butcesi = ayar.sermaye * ayar.islem_basi_risk_yuzde / 100
    adet_risk = risk_butcesi / stop_mesafe
    adet_agirlik = (ayar.sermaye * ayar.azami_pozisyon_yuzde / 100) / fiyat
    adet_nakit = nakit / fiyat

    adet = int(math.floor(min(adet_risk, adet_agirlik, adet_nakit)))

    if adet < 1:
        if fiyat > nakit:
            sebep = f"1 adet {fiyat:.2f} TL, nakit {nakit:.0f} TL - yetmiyor"
        elif fiyat > ayar.sermaye * ayar.azami_pozisyon_yuzde / 100:
            sebep = (f"1 adet = sermayenin %{fiyat / ayar.sermaye * 100:.0f}'i "
                     f"(tavan %{ayar.azami_pozisyon_yuzde:.0f}); "
                     f"~{fiyat / (ayar.azami_pozisyon_yuzde/100):,.0f} TL sermaye gerekir")
        else:
            # Ne gerekirdi? Kullanıcı bilinçli bir seçim yapabilsin diye söyle.
            gereken_risk = stop_mesafe / ayar.sermaye * 100
            sebep = (f"1 adetin riski {stop_mesafe:.2f} TL = sermayenin "
                     f"%{gereken_risk:.1f}'i (bütçen %{ayar.islem_basi_risk_yuzde}); "
                     f"bu hisse için ~{stop_mesafe / (ayar.islem_basi_risk_yuzde/100):,.0f} TL sermaye gerekir")
        return Pozisyon(sembol, 0, fiyat, stop, hedef, 0, 0, 0, sebep)

    if adet_risk < adet_agirlik:
        pass  # risk tavanı bağladı - ideal durum
    else:
        gercek_risk = adet * stop_mesafe
        if gercek_risk > risk_butcesi * 1.05:
            uyarilar.append(
                f"gerçek risk {gercek_risk / ayar.sermaye * 100:.1f}% "
                f"(hedef %{ayar.islem_basi_risk_yuzde})")

    maliyet = adet * fiyat
    pay = maliyet / ayar.sermaye * 100
    if pay > 50:
        uyarilar.append(f"portföyün %{pay:.0f}'i tek hissede")

    return Pozisyon(
        sembol=sembol, adet=adet, giris=fiyat, stop=stop, hedef=hedef,
        risk_tl=round(adet * stop_mesafe, 2), maliyet=round(maliyet, 2),
        sermaye_payi=round(pay, 1), uyari="; ".join(uyarilar),
    )


def kelly_kesri(kazanma_orani: float, ort_kazanc: float, ort_kayip: float) -> float:
    """Kelly kriteri: teorik optimum bahis oranı.

    Pratikte 'yarım Kelly' bile çok agresiftir; buradaki değer üst sınır
    olarak, gerçek risk yüzdesinin makul olup olmadığını denetlemek için var.
    """
    if ort_kayip <= 0 or not 0 < kazanma_orani < 1:
        return 0.0
    b = ort_kazanc / ort_kayip
    k = (kazanma_orani * (b + 1) - 1) / b
    return max(0.0, min(k, 1.0))
