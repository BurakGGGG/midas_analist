"""Temel analiz: finansal tablolardan oran üretir ve her oranı YORUMLAR.

Tasarım kuralı: hesaplanamayan oran NaN döner, asla 0 dönmez. Borcu okunamayan
şirketin 'borçsuz' görünmesi, hiç bilgi vermemekten daha tehlikelidir.

Sektör farkı gözetilir: bankada cari oran, borç/özsermaye ve FD/FAVÖK
anlamsızdır — banka için borç bir hammaddedir, kusur değil.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .temel_veri import Finansallar

# Bilançosu yapısal olarak farklı olan sektörler
BANKA_SEKTOR = {"Financial Services", "Financial", "Banks"}
GYO_ANAHTAR = {"REIT", "Real Estate"}


def _bol(a: float, b: float) -> float:
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return a / b


@dataclass
class Oran:
    ad: str
    deger: float
    birim: str = "%"
    iyi_yon: int = 1                 # +1 yüksek iyi, -1 düşük iyi, 0 nötr
    esik_iyi: float = np.nan
    esik_kotu: float = np.nan
    yorum: str = ""
    gecerli: bool = True             # sektöre göre anlamlı mı?

    @property
    def var_mi(self) -> bool:
        return np.isfinite(self.deger)

    @property
    def durum(self) -> str:
        """iyi | orta | kotu | yok"""
        if not self.var_mi or not self.gecerli:
            return "yok"
        if not np.isfinite(self.esik_iyi) or not np.isfinite(self.esik_kotu):
            return "orta"
        if self.iyi_yon > 0:
            return "iyi" if self.deger >= self.esik_iyi else ("kotu" if self.deger <= self.esik_kotu else "orta")
        return "iyi" if self.deger <= self.esik_iyi else ("kotu" if self.deger >= self.esik_kotu else "orta")

    def yaz(self) -> str:
        if not self.gecerli:
            return f"{self.ad}: — (bu sektörde anlamsız)"
        if not self.var_mi:
            return f"{self.ad}: veri yok"
        return f"{self.ad}: {self.deger:,.2f}{self.birim}"


def _buyume(f: Finansallar, anahtar: str, yil: int = 1) -> float:
    """yil kadar önceki döneme göre büyüme (%). CAGR için yil>1."""
    yeni = f.al(anahtar, "gelir", 0)
    eski = f.al(anahtar, "gelir", yil)
    if not np.isfinite(yeni) or not np.isfinite(eski) or eski <= 0:
        return np.nan
    return ((yeni / eski) ** (1 / yil) - 1) * 100


def oranlar(f: Finansallar) -> dict[str, Oran]:
    """Tüm temel oranlar. Hepsi tablodan tabloya — para birimi nötr."""
    banka = f.sektor in BANKA_SEKTOR

    hasilat = f.al("hasilat")
    brut = f.al("brut_kar")
    faaliyet = f.al("faaliyet_kari")
    favok = f.al("favok")
    net = f.al("net_kar")
    faiz = abs(f.al("faiz_gideri")) if np.isfinite(f.al("faiz_gideri")) else np.nan

    varlik = f.al("toplam_varlik", "bilanco")
    ozsermaye = f.al("ozsermaye", "bilanco")
    borc = f.al("toplam_borc", "bilanco")
    nakit = f.al("nakit", "bilanco")
    donen = f.al("donen_varlik", "bilanco")
    kisa = f.al("kisa_borc", "bilanco")
    stok = f.al("stok", "bilanco")

    fnakit = f.al("faaliyet_nakit", "nakit")
    fcf = f.al("serbest_nakit", "nakit")

    net_borc = borc - nakit if np.isfinite(borc) and np.isfinite(nakit) else np.nan
    yatirilan = (ozsermaye + borc) if np.isfinite(ozsermaye) and np.isfinite(borc) else np.nan

    o: dict[str, Oran] = {}

    # ---- KÂRLILIK MARJLARI ----
    o["brut_marj"] = Oran("Brüt kâr marjı", _bol(brut, hasilat) * 100, "%", 1, 35, 15,
        "Ürünün kendi maliyetinden ne kadar üstte satıldığı. Yüksek marj = fiyatlama gücü.",
        gecerli=not banka)
    o["faaliyet_marj"] = Oran("Faaliyet kâr marjı", _bol(faaliyet, hasilat) * 100, "%", 1, 15, 5,
        "Ana işten kâr. Finansman ve tek seferlik kalemler hariç — asıl performans burası.")
    o["favok_marj"] = Oran("FAVÖK marjı", _bol(favok, hasilat) * 100, "%", 1, 20, 8,
        "Amortisman ve faiz öncesi nakit üretimi. Sermaye yoğun sektörlerde kıyas için kullanılır.",
        gecerli=not banka)
    o["net_marj"] = Oran("Net kâr marjı", _bol(net, hasilat) * 100, "%", 1, 10, 2,
        "Her 100 TL satıştan cebe kalan. Kur farkı ve tek seferlik kalemler bunu şişirebilir.")

    # ---- SERMAYE GETİRİSİ ----
    o["roe"] = Oran("ROE (özsermaye kârlılığı)", _bol(net, ozsermaye) * 100, "%", 1, 20, 8,
        "Ortağın koyduğu paranın getirisi. Enflasyonun altındaysa şirket reel olarak değer kaybettiriyor.")
    o["roa"] = Oran("ROA (aktif kârlılığı)", _bol(net, varlik) * 100, "%", 1, 8, 2,
        "Toplam varlıkların getirisi. Bankada doğal olarak düşüktür (kaldıraçlı iş modeli).")
    o["roic"] = Oran("ROIC (yatırılan sermaye getirisi)", _bol(faaliyet, yatirilan) * 100, "%", 1, 15, 6,
        "Borç + özsermayenin toplam getirisi. ROE'den daha dürüst: kaldıraçla şişirilemez.",
        gecerli=not banka)

    # ---- BORÇLULUK ----
    o["borc_ozsermaye"] = Oran("Borç / Özsermaye", _bol(borc, ozsermaye), "x", -1, 0.5, 1.5,
        "1'in üstü borçla büyüyor demek. Faiz yükselince en çok bunlar acı çeker.",
        gecerli=not banka)
    o["net_borc_favok"] = Oran("Net Borç / FAVÖK", _bol(net_borc, favok), "x", -1, 1.5, 3.5,
        "Şirket tüm nakit kârıyla borcunu kaç yılda kapatır. 4'ün üstü tehlike bölgesi.",
        gecerli=not banka)
    o["faiz_karsilama"] = Oran("Faiz karşılama", _bol(faaliyet, faiz), "x", 1, 5, 2,
        "Faaliyet kârı faiz giderinin kaç katı. 2'nin altı = faiz ödemekte zorlanıyor.",
        gecerli=not banka)

    # ---- LİKİDİTE ----
    o["cari_oran"] = Oran("Cari oran", _bol(donen, kisa), "x", 1, 1.5, 1.0,
        "Kısa vadeli borcu ödeyecek dönen varlık var mı. 1'in altı nakit sıkışıklığı sinyali.",
        gecerli=not banka)
    o["asit_test"] = Oran("Asit-test oranı",
        _bol(donen - stok if np.isfinite(stok) else np.nan, kisa), "x", 1, 1.0, 0.7,
        "Stok satılamazsa yine ödeyebilir mi. Stoku ağır sektörlerde cari orandan önemli.",
        gecerli=not banka)

    # ---- NAKİT ve KÂR KALİTESİ ----
    o["fcf_marj"] = Oran("Serbest nakit akışı marjı", _bol(fcf, hasilat) * 100, "%", 1, 8, 0,
        "Yatırım harcamasından sonra gerçekten kalan nakit. Temettü ve borç ödemesi buradan çıkar.",
        gecerli=not banka)
    # Bankada faaliyet nakit akışı mevduat/kredi hareketinden oluşur; kâr
    # kalitesi ölçmez. Sağlıklı bir banka rutin olarak negatif gösterebilir.
    #
    # Ayrıca net kâr sıfıra yakınsa oran patlar: EREGL'de net marj %0.24 iken
    # nakit/net kâr 127x çıkıyor ve "mükemmel kâr kalitesi" gibi görünüyor.
    # Bu bir bölme artefaktıdır, bilgi değildir — geçersiz sayılır.
    net_marj_deger = _bol(net, hasilat)
    kar_anlamli = (np.isfinite(net_marj_deger) and abs(net_marj_deger) >= 0.01
                   and np.isfinite(net) and net > 0)
    o["kar_kalitesi"] = Oran("Nakit / Net kâr", _bol(fnakit, net), "x", 1, 1.0, 0.5,
        "KRİTİK: kâğıt üzerindeki kâr nakde dönüyor mu. Sürekli 1'in altıysa kâr şüphelidir.",
        gecerli=(not banka) and kar_anlamli)

    # ---- BÜYÜME ----
    o["hasilat_buyume"] = Oran("Hasılat büyümesi (yıllık)", _buyume(f, "hasilat", 1), "%", 1, 25, 0,
        "Enflasyonun altındaysa şirket reel olarak KÜÇÜLÜYOR. Türkiye'de bu eşik yüksek.")
    o["hasilat_cagr3"] = Oran("Hasılat büyümesi (3 yıl ort.)", _buyume(f, "hasilat", 3), "%", 1, 25, 0,
        "Tek yılın şansını eler. Uzun vadeli trend burada görünür.")
    o["kar_buyume"] = Oran("Net kâr büyümesi (yıllık)", _buyume(f, "net_kar", 1), "%", 1, 25, -10,
        "Hasılattan hızlı büyüyorsa marj genişliyor demektir — iyi işaret.")

    return o


def kalite_skoru(f: Finansallar, o: dict[str, Oran] | None = None,
                 enflasyon: float | None = None) -> dict:
    """0-100 şirket kalite skoru — 'ucuz mu' değil, 'İYİ Mİ' sorusu.

    Türkiye'ye özgü ayar: ROE ve büyüme eşikleri enflasyona göre kayar.
    %31 enflasyonda %20 ROE, reel olarak para KAYBETTİRİYOR demektir.
    """
    o = o or oranlar(f)
    banka = f.sektor in BANKA_SEKTOR
    # Şirket hangi para biriminde raporluyorsa O dünyanın enflasyonuyla kıyasla
    enflasyon = f.enflasyon_referansi() if enflasyon is None else enflasyon

    def puan(ad: str, agirlik: float, esik_iyi: float, esik_kotu: float, ters=False) -> tuple[float, float]:
        r = o.get(ad)
        if r is None or not r.var_mi or not r.gecerli:
            return 0.0, 0.0          # (alınan, mümkün) — mümkün de 0 ise ortalamadan düşer
        d = r.deger
        if ters:
            p = 1.0 if d <= esik_iyi else (0.0 if d >= esik_kotu else (esik_kotu - d) / (esik_kotu - esik_iyi))
        else:
            p = 1.0 if d >= esik_iyi else (0.0 if d <= esik_kotu else (d - esik_kotu) / (esik_iyi - esik_kotu))
        return float(np.clip(p, 0, 1)) * agirlik, agirlik

    parcalar = []
    # Kârlılık (30)
    parcalar.append(puan("faaliyet_marj", 10, 15, 2))
    parcalar.append(puan("net_marj", 10, 10, 0))
    if not banka:
        parcalar.append(puan("brut_marj", 10, 35, 12))
    # Sermaye getirisi (25) — enflasyona göre kayan eşik
    parcalar.append(puan("roe", 15, enflasyon + 10, enflasyon - 10))
    parcalar.append(puan("roic", 10, enflasyon, enflasyon - 15))
    # Bilanço sağlamlığı (20)
    if not banka:
        parcalar.append(puan("net_borc_favok", 10, 1.5, 4.0, ters=True))
        parcalar.append(puan("cari_oran", 5, 1.5, 0.9))
        parcalar.append(puan("faiz_karsilama", 5, 5, 1.5))
    # Kâr kalitesi (15) — en önemli tek gösterge
    parcalar.append(puan("kar_kalitesi", 15, 1.0, 0.3))
    # Büyüme (10) — enflasyon üstü olmalı
    parcalar.append(puan("hasilat_cagr3", 10, enflasyon + 15, enflasyon - 15))

    alinan = sum(p[0] for p in parcalar)
    mumkun = sum(p[1] for p in parcalar)
    skor = (alinan / mumkun * 100) if mumkun > 0 else np.nan

    return {
        "skor": round(float(skor), 1) if np.isfinite(skor) else None,
        "kapsama": round(mumkun / (100 if not banka else 60) * 100, 0),
        "banka_modu": banka,
        "enflasyon_esigi": enflasyon,
        "veri_eksik": [ad for ad, r in o.items() if r.gecerli and not r.var_mi],
    }


def kirmizi_bayraklar(f: Finansallar, o: dict[str, Oran] | None = None,
                      enflasyon: float | None = None) -> list[str]:
    """Yatırım yapmadan ÖNCE görülmesi gereken uyarılar."""
    o = o or oranlar(f)
    enflasyon = f.enflasyon_referansi() if enflasyon is None else enflasyon
    para = f.tablo_para
    b = []

    def d(ad):
        r = o.get(ad)
        return r.deger if r and r.var_mi and r.gecerli else np.nan

    if np.isfinite(d("kar_kalitesi")) and d("kar_kalitesi") < 0.5:
        b.append(f"Kâr nakde dönmüyor (nakit/net kâr {d('kar_kalitesi'):.2f}) — "
                 "kâğıt üstündeki kâr şüpheli")
    if np.isfinite(d("net_borc_favok")) and d("net_borc_favok") > 4:
        b.append(f"Ağır borç yükü (net borç/FAVÖK {d('net_borc_favok'):.1f}x) — "
                 "faiz artışına çok duyarlı")
    if np.isfinite(d("faiz_karsilama")) and d("faiz_karsilama") < 2:
        b.append(f"Faiz ödemekte zorlanıyor (karşılama {d('faiz_karsilama'):.1f}x)")
    if np.isfinite(d("cari_oran")) and d("cari_oran") < 1:
        b.append(f"Kısa vadeli borç dönen varlığı aşıyor (cari oran {d('cari_oran'):.2f})")
    if np.isfinite(d("roe")) and d("roe") < enflasyon:
        b.append(f"ROE %{d('roe'):.1f}, {para} enflasyonu %{enflasyon:.1f} — "
                 "özsermaye REEL olarak eriyor")
    if np.isfinite(d("hasilat_buyume")) and d("hasilat_buyume") < enflasyon:
        b.append(f"Hasılat %{d('hasilat_buyume'):.1f} büyüdü, {para} enflasyonu "
                 f"%{enflasyon:.1f} — şirket reel olarak küçülüyor")
    if np.isfinite(d("net_marj")) and d("net_marj") < 0:
        b.append("Şirket zarar ediyor")
    if f.kur_uyusmazligi:
        b.append(f"Finansallar {f.tablo_para}, hisse {f.fiyat_para} — "
                 "oranlar kur çevrimiyle hesaplandı, kur riski taşır")
    return b
