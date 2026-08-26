"""Eğitmen motoru: aralıklı tekrar + canlı veriden soru üretimi.

İki tür soru var:
  · SABİT — soru bankasından, aralıklı tekrar takvimine göre
  · CANLI — bugünkü gerçek veriden üretilir ("EREGL'in F/K'sı 1054 çıktı,
    bu şirket pahalı mı?"). Statik bir sınavı gerçek yatırımdan ayıran şey budur.

İlerleme JSON olarak saklanır; CLI dosyada tutar, mobil cihazda tutar.
Motor DURUMSUZDUR: ilerlemeyi parametre alır, güncellenmiş halini döndürür.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from .egitmen_sorular import (TUM_SORULAR, TEMEL, ORTA, USTA, Soru,
                              SIRKET_OKUMA, ALIM_ONCESI, ILKELER)
from .egitmen_dersler import (MODULLER, TUM_DERSLER, DERS_HARITA, MODUL_HARITA,
                              Ders, Modul, ders_modulu)

DOSYA = Path(__file__).resolve().parent.parent / "ilerleme.json"

SORU_HARITA: dict[str, Soru] = {s.kod: s for s in TUM_SORULAR}

# Kendini değerlendirme seçenekleri → SM-2 kalite puanı
DEGERLENDIRME = {
    "bilmiyordum": 1,
    "kismen": 3,
    "biliyordum": 5,
}


@dataclass
class Kayit:
    """Tek bir sorunun öğrenme durumu (SM-2)."""
    kod: str
    tekrar: int = 0
    kolaylik: float = 2.5          # ease factor
    aralik: int = 0                # gün
    son: str = ""                  # son çalışılan tarih
    sonraki: str = ""              # tekrar tarihi
    dogru: int = 0
    yanlis: int = 0

    @property
    def ogrenildi(self) -> bool:
        """En az 3 kez üst üste doğru ve aralık 21 günü geçmiş."""
        return self.tekrar >= 3 and self.aralik >= 21


@dataclass
class DersKaydi:
    """Bir dersin okunma durumu. Sorulardan farklı: ders TEKRAR edilir ama
    unutma eğrisiyle değil, ihtiyaç duyulduğunda."""
    kod: str
    okundu: bool = False
    ilk_okuma: str = ""
    son_okuma: str = ""
    okuma_sayisi: int = 0
    isaretli: bool = False       # kullanıcı "buna dönmem lazım" dedi


def _bugun() -> date:
    return date.today()


def _tarih(s: str) -> date | None:
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None


def ilerleme_yukle(yol: Path | None = None) -> tuple[dict[str, Kayit], dict[str, DersKaydi]]:
    """(soru_ilerlemesi, ders_ilerlemesi) döndürür.

    Eski sürüm dosyaları (sadece soru kaydı içeren düz sözlük) da okunabilir —
    o durumda ders ilerlemesi boş başlar.
    """
    yol = yol or DOSYA
    if not yol.exists():
        return {}, {}
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}

    if "sorular" in ham or "dersler" in ham:
        sorular = {k: Kayit(**v) for k, v in (ham.get("sorular") or {}).items()}
        dersler = {k: DersKaydi(**v) for k, v in (ham.get("dersler") or {}).items()}
        return sorular, dersler

    # eski biçim: düz soru sözlüğü
    try:
        return {k: Kayit(**v) for k, v in ham.items()}, {}
    except Exception:
        return {}, {}


def ilerleme_kaydet(sorular: dict[str, Kayit],
                    dersler: dict[str, DersKaydi] | None = None,
                    yol: Path | None = None) -> None:
    yol = yol or DOSYA
    yol.write_text(
        json.dumps({
            "surum": 2,
            "sorular": {k: asdict(v) for k, v in sorular.items()},
            "dersler": {k: asdict(v) for k, v in (dersler or {}).items()},
        }, ensure_ascii=False, indent=1),
        encoding="utf-8")


def ders_okundu(dersler: dict[str, DersKaydi], kod: str) -> dict[str, DersKaydi]:
    """Dersi okundu olarak işaretler."""
    d = dersler.get(kod) or DersKaydi(kod=kod)
    bugun = _bugun().isoformat()
    dersler[kod] = DersKaydi(
        kod=kod, okundu=True,
        ilk_okuma=d.ilk_okuma or bugun,
        son_okuma=bugun,
        okuma_sayisi=d.okuma_sayisi + 1,
        isaretli=d.isaretli,
    )
    return dersler


def ders_isaretle(dersler: dict[str, DersKaydi], kod: str,
                  isaretli: bool = True) -> dict[str, DersKaydi]:
    d = dersler.get(kod) or DersKaydi(kod=kod)
    d.isaretli = isaretli
    dersler[kod] = d
    return dersler


def guncelle(kayit: Kayit, kalite: int) -> Kayit:
    """SM-2 aralıklı tekrar.

    Kalite < 3 ise sıfırdan başlar — yanlış hatırlanan bilgi, hiç
    hatırlanmayan bilgiden daha tehlikelidir çünkü ona güvenirsin.
    """
    k = Kayit(**asdict(kayit))
    k.son = _bugun().isoformat()

    if kalite < 3:
        k.tekrar = 0
        k.aralik = 1
        k.yanlis += 1
    else:
        k.dogru += 1
        if k.tekrar == 0:
            k.aralik = 1
        elif k.tekrar == 1:
            k.aralik = 6
        else:
            k.aralik = int(round(k.aralik * k.kolaylik))
        k.tekrar += 1

    # kolaylık faktörü: zor bulunan soru daha sık gelir
    k.kolaylik = max(1.3, k.kolaylik + (0.1 - (5 - kalite) * (0.08 + (5 - kalite) * 0.02)))
    k.sonraki = (_bugun() + timedelta(days=max(1, k.aralik))).isoformat()
    return k


def modul_ilerlemesi(dersler: dict[str, DersKaydi]) -> list[dict]:
    """Her modülde kaç ders okundu."""
    cikti = []
    for m in MODULLER:
        okunan = sum(1 for d in m.dersler
                     if dersler.get(d.kod) and dersler[d.kod].okundu)
        cikti.append({
            "kod": m.kod, "ad": m.ad, "aciklama": m.aciklama,
            "seviye": m.seviye,
            "okunan": okunan, "toplam": len(m.dersler),
            "yuzde": round(okunan / len(m.dersler) * 100) if m.dersler else 0,
            "dakika": sum(d.sure for d in m.dersler),
            "bitti": okunan == len(m.dersler),
        })
    return cikti


def seviye_durumu(sorular: dict[str, Kayit],
                  dersler: dict[str, DersKaydi] | None = None) -> dict:
    """Hangi seviyedesin? Artık ana ölçüt OKUNAN DERS, ikincil ölçüt sorular.

    Sebep: bu bir sınav değil, bir müfredat. Seviye, ne kadar öğrendiğinle
    ilerler — ne kadar test edildiğinle değil.
    """
    dersler = dersler or {}
    okunan = sum(1 for d in TUM_DERSLER
                 if dersler.get(d.kod) and dersler[d.kod].okundu)
    toplam_ders = len(TUM_DERSLER)
    ders_yuzde = okunan / toplam_ders * 100 if toplam_ders else 0

    def soru_sayim(liste: list[Soru]) -> tuple[int, int]:
        o = sum(1 for s in liste
                if sorular.get(s.kod) and sorular[s.kod].ogrenildi)
        return o, len(liste)

    t_o, t_n = soru_sayim(TEMEL)
    o_o, o_n = soru_sayim(ORTA)
    u_o, u_n = soru_sayim(USTA)
    soru_yuzde = ((t_o + o_o + u_o) / len(TUM_SORULAR) * 100) if TUM_SORULAR else 0

    # Seviye: dersin ağırlığı 2/3, soruların 1/3
    bilesik = ders_yuzde * (2 / 3) + soru_yuzde * (1 / 3)
    if bilesik >= 70:
        seviye, unvan = 3, "Usta"
    elif bilesik >= 35:
        seviye, unvan = 2, "Kalfa"
    else:
        seviye, unvan = 1, "Çırak"
    if bilesik >= 90:
        unvan = "Usta (tamamlandı)"

    return {
        "seviye": seviye, "unvan": unvan,
        "bilesik_yuzde": round(bilesik, 1),
        "ders": {"okunan": okunan, "toplam": toplam_ders,
                 "yuzde": round(ders_yuzde),
                 "dakika_kalan": sum(d.sure for d in TUM_DERSLER
                                     if not (dersler.get(d.kod)
                                             and dersler[d.kod].okundu))},
        "temel": {"ogrenilen": t_o, "toplam": t_n, "yuzde": round(t_o / t_n * 100)},
        "orta": {"ogrenilen": o_o, "toplam": o_n, "yuzde": round(o_o / o_n * 100)},
        "usta": {"ogrenilen": u_o, "toplam": u_n, "yuzde": round(u_o / u_n * 100)},
        "toplam_calisilan": len(sorular),
        "toplam_soru": len(TUM_SORULAR),
        "moduller": modul_ilerlemesi(dersler),
        "sonraki_seviye": (
            f"Derslerin %{round(ders_yuzde)}'ini okudun. "
            + ("Kalfa olmak için biraz daha ilerle." if seviye == 1 else
               "Usta olmak için müfredatı tamamla." if seviye == 2 else
               "Müfredatı bitirdin — tekrar etmeye devam et.")
        ),
    }


def sonraki_ders(dersler: dict[str, DersKaydi]) -> Ders | None:
    """Müfredat sırasına göre okunmamış ilk ders."""
    for d in TUM_DERSLER:
        k = dersler.get(d.kod)
        if not (k and k.okundu):
            return d
    return None


def gunluk_ders(dersler: dict[str, DersKaydi], adet: int = 1) -> list[Ders]:
    """Bugün okunacak dersler — müfredat sırasıyla."""
    cikti = []
    for d in TUM_DERSLER:
        k = dersler.get(d.kod)
        if not (k and k.okundu):
            cikti.append(d)
            if len(cikti) >= adet:
                break
    return cikti


def isaretli_dersler(dersler: dict[str, DersKaydi]) -> list[Ders]:
    return [DERS_HARITA[k] for k, v in dersler.items()
            if v.isaretli and k in DERS_HARITA]


def gunluk_secim(ilerleme: dict[str, Kayit], adet: int = 5,
                 tohum: int | None = None,
                 dersler: dict[str, DersKaydi] | None = None,
                 sadece_okunanlardan: bool = True) -> list[Soru]:
    """Bugünün soruları: önce vadesi gelen tekrarlar, sonra yeni sorular.

    Karışım bilinçli: tekrar olmadan öğrenme kalıcı olmaz, yeni soru olmadan
    ilerleme olmaz.
    """
    bugun = _bugun()
    rnd = random.Random(tohum if tohum is not None else bugun.toordinal())

    vadesi_gelen, yeni = [], []
    dersler = dersler or {}
    durum = seviye_durumu(ilerleme, dersler)
    acik_seviyeler = list(range(1, durum["seviye"] + 1))

    # Ders okumadan o dersin sorusu sorulmaz — bu bir sınav değil, pekiştirme.
    okunan_sorular: set[str] = set()
    if sadece_okunanlardan:
        for d in TUM_DERSLER:
            k = dersler.get(d.kod)
            if k and k.okundu:
                okunan_sorular.update(d.sorular)

    for s in TUM_SORULAR:
        if sadece_okunanlardan and okunan_sorular and s.kod not in okunan_sorular:
            continue
        k = ilerleme.get(s.kod)
        if k is None:
            if s.seviye in acik_seviyeler:
                yeni.append(s)
        else:
            t = _tarih(k.sonraki)
            if t is None or t <= bugun:
                vadesi_gelen.append(s)

    # Vadesi en çok geçmiş olan önce
    vadesi_gelen.sort(key=lambda s: ilerleme[s.kod].sonraki or "")
    rnd.shuffle(yeni)
    # Kolaydan zora: aynı seviyede kod sırası müfredat sırasıdır
    yeni.sort(key=lambda s: (s.seviye, s.kod))

    # En fazla yarısı tekrar olsun, kalan yeni
    tekrar_payi = min(len(vadesi_gelen), max(1, adet // 2)) if vadesi_gelen else 0
    secim = vadesi_gelen[:tekrar_payi]
    secim += yeni[: adet - len(secim)]
    # Hâlâ boşluk varsa kalan tekrarlarla doldur
    if len(secim) < adet:
        kalan = [s for s in vadesi_gelen if s not in secim]
        secim += kalan[: adet - len(secim)]
    return secim[:adet]


# ═══════════════════════════════════════════ canlı sorular

@dataclass
class CanliSoru:
    kod: str
    kategori: str
    soru: str
    cevap: str
    baglam: dict = field(default_factory=dict)
    seviye: int = 2
    tuzak: str = ""
    canli: bool = True


def _g(d: dict, *yol, vars=None):
    """İç içe sözlükten güvenli okuma."""
    x = d
    for a in yol:
        if not isinstance(x, dict) or a not in x:
            return None
        x = x[a]
    return x


def canli_sorular(tarama: dict | None = None, makro_durum: dict | None = None,
                  sirketler: list[dict] | None = None,
                  pozisyonlar: list[dict] | None = None,
                  azami: int = 3) -> list[CanliSoru]:
    """Bugünkü gerçek veriden soru üretir.

    Bunlar ezber sorusu değil; öğrencinin ELİNDEKİ durumu okumasını ister.
    """
    sorular: list[CanliSoru] = []

    # 1) Taramadan: yüksek skor ama düşük zamanlama
    for a in (tarama or {}).get("adaylar", [])[:12]:
        zam = a.get("zamanlama")
        skor = a.get("skor")
        if zam is not None and skor is not None and skor >= 60 and zam <= 8:
            sorular.append(CanliSoru(
                kod=f"c_zamanlama_{a['sembol']}",
                kategori="teknik",
                soru=(f"{a['sembol']} bugün {skor:.0f} skorla üst sıralarda ama "
                      f"zamanlama puanı 25 üzerinden sadece {zam:.0f} "
                      f"(RSI {a.get('rsi', '?')}). Bu ne anlama gelir, "
                      f"bugün alır mısın?"),
                cevap=("Yüksek toplam skor + düşük zamanlama puanı şu demektir: "
                       "şirket ve trend iyi konumlanmış, ama fiyat şu an giriş için "
                       "pahalı bir noktada. RSI yüksekse hisse kısa vadede uzamıştır.\n\n"
                       "Doğru davranış: bu hisseyi İZLEME listesine al, geri "
                       "çekilmeyi bekle. Kovalayarak alınan pozisyonun stop mesafesi "
                       "büyür, aynı risk bütçesiyle daha az adet alabilirsin — yani "
                       "aynı fikri daha kötü koşullarla oynarsın.\n\n"
                       "Ama dikkat: güçlü trendde 'geri çekilme' hiç gelmeyebilir. "
                       "Bu yüzden karar 'asla alma' değil, 'bugün acele etme'dir."),
                tuzak="Yüksek skoru otomatik 'al' sinyali sanmak. Skor bir sıralama "
                      "aracıdır; giriş zamanı ayrı bir sorudur.",
                baglam={"sembol": a["sembol"], "skor": skor, "zamanlama": zam},
            ))
            break

    # 2) Şirket verisinden: uç değerli çarpan
    for s in (sirketler or []):
        fk = _g(s, "carpanlar", "fk", "deger")
        pd_dd = _g(s, "carpanlar", "pd_dd", "deger")
        kalite = _g(s, "kalite", "skor")
        if fk is not None and fk > 200:
            sorular.append(CanliSoru(
                kod=f"c_fk_{s['sembol']}",
                kategori="carpan",
                soru=(f"{s['sembol']}'in F/K oranı {fk:,.0f} çıkıyor. "
                      f"PD/DD ise {pd_dd:.2f}. Bu şirket pahalı mı? "
                      f"F/K burada ne söylüyor?"),
                cevap=("F/K bu değerde ANLAMSIZDIR. Sebep: net kâr sıfıra çok "
                       "yakın. Sıfıra bölmeye yaklaştıkça oran patlar; bu bir "
                       "bilgi değil, matematiksel artefakttır.\n\n"
                       "Bu durumda F/K'yı bırakıp şunlara bakılır:\n"
                       "· PD/DD — defter değerine göre nerede\n"
                       "· FD/FAVÖK — faaliyet düzeyinde kârlılık var mı\n"
                       "· Serbest nakit verimi — nakit üretiyor mu\n"
                       "· NORMALLEŞTİRİLMİŞ kâr — döngünün dibinde miyiz?\n\n"
                       "Döngüsel bir şirkette kâr dipteyken F/K şişer ve bu bazen "
                       "ALIM zamanıdır. Ama önce kârın neden çöktüğünü bulmalısın: "
                       "geçici döngü mü, kalıcı bozulma mı?"),
                tuzak="Yüksek F/K'yı otomatik 'pahalı' okumak. Kâr sıfıra yakınken "
                      "F/K hiçbir şey ölçmez.",
                baglam={"sembol": s["sembol"], "fk": fk, "pd_dd": pd_dd,
                        "kalite": kalite},
                seviye=3,
            ))
            break

    # 3) Kur uyuşmazlığı olan şirket
    for s in (sirketler or []):
        if s.get("kur_uyusmazligi"):
            sorular.append(CanliSoru(
                kod=f"c_kur_{s['sembol']}",
                kategori="usta",
                soru=(f"{s['sembol']} finansallarını {s.get('tablo_para')} cinsinden "
                      f"açıklıyor ama hissesi {s.get('fiyat_para')} işlem görüyor. "
                      f"Bu durum hangi hataya yol açar ve şirketin büyümesini "
                      f"hangi enflasyonla kıyaslarsın?"),
                cevap=(f"İki ayrı hata doğar:\n\n"
                       f"1) ÇARPAN HATASI — piyasa değeri TL, kâr {s.get('tablo_para')}. "
                       f"İkisini bölen her oran çöp üretir. Bu sistemin ölçtüğü "
                       f"örnek: yfinance THYAO'nun F/S'sini 15,66 gösteriyor, "
                       f"kur düzeltmesiyle gerçeği 0,34 — 43 kat hata.\n\n"
                       f"2) ENFLASYON HATASI — {s.get('tablo_para')} raporlayan bir "
                       f"şirketin büyümesini TÜRKİYE enflasyonuyla kıyaslamak "
                       f"geçersizdir. O şirket dolar dünyasında iş yapar; "
                       f"kıyas ölçütü USD enflasyonu (~%3) olmalıdır. Yanlış "
                       f"referans sağlıklı şirketi 'reel küçülüyor' diye damgalar.\n\n"
                       f"Ek olarak: bu şirket kur riski taşır. Dövizli geliri var "
                       f"ama dövizli borcu da olabilir — net döviz pozisyonuna bak."),
                tuzak="Hazır sitelerdeki oranlara güvenmek. Kur uyuşmazlığını "
                      "düzeltmeyen her kaynak bu hisselerde yanlış sayı verir.",
                baglam={"sembol": s["sembol"], "tablo_para": s.get("tablo_para")},
                seviye=3,
            ))
            break

    # 4) Makro durumdan
    if makro_durum:
        enf = _g(makro_durum, "enflasyon", "yillik")
        reel = makro_durum.get("bist_reel_getiri_1y")
        xu = _g(makro_durum, "gostergeler", "xu100", "g365")
        if enf and reel is not None and xu is not None:
            sorular.append(CanliSoru(
                kod="c_reel",
                kategori="makro",
                soru=(f"BIST 100 son bir yılda %{xu:.1f} getirdi, enflasyon "
                      f"%{enf:.1f}. Bu dönemde borsaya para koyan biri "
                      f"zenginleşti mi?"),
                cevap=(f"Hayır. Reel getiri %{reel:.1f} — yani alım gücü AZALDI.\n\n"
                       f"Nominal getiri seni kandırır çünkü sayı büyür. Ama 100 "
                       f"liralık sepet artık {100 * (1 + enf/100):.0f} lira; "
                       f"senin paran {100 * (1 + xu/100):.0f} lira oldu. Daha az "
                       f"şey alabiliyorsun.\n\n"
                       f"Doğru ölçüm iki katmanlıdır:\n"
                       f"· Enflasyondan arındır (reel getiri)\n"
                       f"· Risksiz alternatifle kıyasla (mevduat faizi)\n\n"
                       f"Bir strateji, mevduat faizini geçemiyorsa aldığın risk "
                       f"karşılıksızdır. Bu sistem `risk` komutunda Sharpe'ı "
                       f"risksiz getiriye göre hesaplar, tam bu yüzden."),
                tuzak="Nominal getiriye bakıp başarılı olduğunu sanmak. "
                      "Türkiye'de bu, en yaygın kendini kandırma biçimidir.",
                baglam={"enflasyon": enf, "reel": reel, "nominal": xu},
            ))

    # 5) Kullanıcının kendi pozisyonundan
    for p in (pozisyonlar or []):
        kar_y = p.get("kar_yuzde")
        if kar_y is not None and kar_y <= -8:
            sorular.append(CanliSoru(
                kod=f"c_poz_{p['sembol']}",
                kategori="psikoloji",
                soru=(f"Portföyündeki {p['sembol']} %{kar_y:.1f} zararda. "
                      f"Şimdi ne yaparsın — ve bu kararı neye dayandırırsın?"),
                cevap=("Doğru cevap bir eylem değil, bir SIRA:\n\n"
                       "1) Tezini aç ve yanılma koşulunu oku. Gerçekleşti mi?\n"
                       "   Yazmadıysan asıl sorun burada — objektif dayanağın yok.\n"
                       "2) Düşüşün sebebini ayır: tüm piyasa mı, sektör mü, "
                       "sadece bu hisse mi? Sadece bu hisseyse şirkete özgü bir şey "
                       "var, bulman gerekir.\n"
                       "3) Tez bozuldu mu — kalite skoru düştü mü, yeni kırmızı "
                       "bayrak çıktı mı, trend kırıldı mı? Sistem bunları ölçer.\n"
                       "4) Baştan yazdığın plana göre hareket et.\n\n"
                       "Ve şu matematiği hatırla: %20 kaybı telafi etmek için %25 "
                       "kazanmak gerekir. Kaybı küçük tutmak, kazancı büyütmekten "
                       "daha değerlidir."),
                tuzak="'Satmam, nasıl olsa çıkar' — bu strateji değil, kayıptan "
                      "kaçınma refleksidir. 'Düşen hisse mutlaka yükselir' diye bir "
                      "kural yoktur.",
                baglam={"sembol": p["sembol"], "kar_yuzde": kar_y},
            ))
            break

    return sorular[:azami]


def ilke_gunun(tohum: int | None = None) -> str:
    rnd = random.Random(tohum if tohum is not None else _bugun().toordinal())
    return rnd.choice(ILKELER)


def istatistik(ilerleme: dict[str, Kayit]) -> dict:
    if not ilerleme:
        return {"calisilan": 0}
    toplam_dogru = sum(k.dogru for k in ilerleme.values())
    toplam_yanlis = sum(k.yanlis for k in ilerleme.values())
    zorlar = sorted([k for k in ilerleme.values() if k.yanlis > 0],
                    key=lambda k: (-k.yanlis, k.kolaylik))[:5]
    bugun = _bugun()
    vadesi = sum(1 for k in ilerleme.values()
                 if (_tarih(k.sonraki) or bugun) <= bugun)
    return {
        "calisilan": len(ilerleme),
        "ogrenilen": sum(1 for k in ilerleme.values() if k.ogrenildi),
        "toplam_cevap": toplam_dogru + toplam_yanlis,
        "dogru_orani": round(toplam_dogru / max(1, toplam_dogru + toplam_yanlis) * 100, 1),
        "bugun_vadesi_gelen": vadesi,
        "en_zorlananlar": [
            {"kod": k.kod,
             "soru": SORU_HARITA[k.kod].soru if k.kod in SORU_HARITA else k.kod,
             "yanlis": k.yanlis, "dogru": k.dogru}
            for k in zorlar
        ],
    }


# ── Bağlamsal ders ─────────────────────────────────────────────────────────
#
# NEDEN VAR: 65 derslik müfredat ayrı bir iş gibi duruyor ve açılmıyor.
# Ölçüldü (2026-08-25): 65 dersten 1'i okunmuş, hiç soru çözülmemiş.
# Sebep içerik değil, akış — kullanıcı "eğitim" için ayrı zaman ayırmıyor.
#
# Çözüm: dersi o günün GERÇEK olayına bağlamak. "Bugün iki sinyal karantinada"
# uyarısının altında "backtest neden yalan söyler" dersi duruyorsa, ders
# ayrı bir iş olmaktan çıkıp o anın açıklaması oluyor.
#
# Sıra önemli: ilk eşleşen kazanır, en özgül durum en üstte.
_BAGLAM_KURALLARI: list[tuple[str, str, str]] = [
    # (durum anahtarı, ders kodu, neden bu ders bugün)
    ("karantina",     "d1202", "Bugün bir strateji karantinaya alındı: canlı "
                               "sicili backtest beklentisinin altında kaldı. "
                               "Bu ders backtestin neden gerçeği olduğundan "
                               "iyi gösterdiğini anlatıyor."),
    ("yogunlasma",    "d804",  "Bugünkü sinyaller birbirine yakın hareket "
                               "ediyor — sayıca çok ama bağımsız bahis olarak "
                               "az. Çeşitlendirme yanılsaması tam olarak bu."),
    ("reel_negatif",  "d601",  "Endeks TL bazında yükselirken reel getirisi "
                               "negatif. Nominal ile reel arasındaki farkı "
                               "görmeden kazanç sanılan şey kayıp olabilir."),
    ("kap_yogun",     "d1101", "Bugün KAP'ta şirket açıklamaları var. En "
                               "güvenilir bilgi kaynağını doğru okumak, "
                               "haberden önce davranmaktan daha değerli."),
    ("sinyal_yok",    "d1004", "Bugün önerilen sinyal yok. Boş günlerde "
                               "işlem üretme dürtüsü en pahalı alışkanlıktır."),
    ("oynaklik",      "d705",  "Bugün oynaklık yüksek. Aynı pozisyon boyutu "
                               "oynak piyasada bambaşka bir risk demektir."),
    ("portfoy_bos",   "d1201", "Henüz açık pozisyonun yok. İlk alımdan önce "
                               "yazılması gereken şey burada anlatılıyor."),
]


def baglamsal_ders(durum: dict, dersler: dict[str, DersKaydi] | None = None) -> dict | None:
    """Bugünün durumuna en uygun dersi seçer.

    `durum` sistemin o anki hâlini taşır (karantinalı strateji var mı,
    sinyaller yoğunlaşmış mı, reel getiri negatif mi...). Eşleşme yoksa
    müfredat sırasındaki bir sonraki okunmamış derse düşer — yani her
    zaman bir cevap verir.

    Okunmuş ders de önerilebilir; o durumda `tekrar` işaretlenir. Bir
    dersi ikinci kez okumak, alakasız bir dersi ilk kez okumaktan iyidir.
    """
    dersler = dersler or {}
    aktif = [k for k, _, _ in _BAGLAM_KURALLARI if durum.get(k)]

    secim, neden = None, ""
    for anahtar, kod, aciklama in _BAGLAM_KURALLARI:
        if not durum.get(anahtar):
            continue
        d = DERS_HARITA.get(kod)
        if d:
            secim, neden = d, aciklama
            break

    if secim is None:
        sirada = gunluk_ders(dersler, adet=1)
        if not sirada:
            return None
        secim = sirada[0]
        neden = "Bugün özel bir durum yok — müfredattan sıradaki ders."

    k = dersler.get(secim.kod)
    return {
        "kod": secim.kod,
        "baslik": secim.baslik,
        "ozet": secim.ozet,
        "sure": secim.sure,
        "neden": neden,
        "tekrar": bool(k and k.okundu),
        "tetikleyen": aktif[0] if aktif else None,
    }


def gunun_durumu(tarama: dict | None = None, karne: dict | None = None,
                 ozet: dict | None = None, portfoy_adet: int = 0) -> dict:
    """API/CLI çıktısından `baglamsal_ders` için durum sözlüğü çıkarır.

    Tek yerde yapılır: mobil, CLI ve zamanlayıcı aynı dersi görsün. İki
    yerde kopyalanırsa biri sessizce geride kalır.
    """
    tarama = tarama or {}
    ozet = ozet or {}
    d: dict = {}

    siniflar = tarama.get("strateji_durumlari") or {}
    d["karantina"] = any(not v.get("onerilir", True) for v in siniflar.values())

    y = tarama.get("yogunlasma") or {}
    if y.get("yeterli_mi"):
        adet = y.get("adet") or 0
        d["yogunlasma"] = bool(adet > 1 and (y.get("bagimsiz_bahis") or adet)
                               < adet * 0.6)

    d["sinyal_yok"] = (tarama.get("onerilen") == 0)

    # gun_ozeti şemasındaki gerçek alan adı
    reel = ozet.get("bist_reel_1y")
    d["reel_negatif"] = bool(reel is not None and reel < 0)

    d["kap_yogun"] = bool((ozet.get("kap_bildirim") or 0) >= 5)
    d["portfoy_bos"] = portfoy_adet == 0
    return d
