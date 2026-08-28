"""Alıştırma görevleri — sırayla yapılan uygulamalı egzersizler.

TASARIM KURALI (egitmen_dersler.py'den devralındı): her görev bir
MEKANİZMA uygulatır, terim sormaz. "Stop nedir?" diye sormak bir tanım
ister ve hiçbir şey öğretmez. "Bu hissede ATR 3,70; stopu nereye
koyarsın?" diye sormak karar aldırır.

SIRA ÖNEMLİ: tutar → stop → hedef → adet → gerçek alım → sonucu görmek.
Her görev bir öncekinin cevabını kullanıyor. Adet hesabını stop'tan önce
öğretmek imkânsız, çünkü adedi stop belirliyor.

SENARYO SAYILARI GÖREVİN İÇİNDE: telefon internetsizken de kontrol
edebilsin diye. Canlı fiyat gerektiren şeyler `islem` ve `ilerlet`
türlerinde, onlar zaten kum havuzunda çalışıyor.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Gorev:
    kod: str
    baslik: str
    amac: str                       # bitirince ne bileceksin
    anlatim: str                    # görevden önce okunan kısa açıklama
    tur: str                        # secim | sayi | islem | ilerlet
    soru: str = ""
    senaryo: dict = field(default_factory=dict)
    secenekler: list = field(default_factory=list)   # tur=secim
    dogru: object = None            # secim: index · sayi: değer
    tolerans: float = 0.0           # sayı cevabında kabul payı (mutlak)
    birim: str = ""
    aciklama: str = ""              # cevaptan sonra: NEDEN böyle
    ipucu: str = ""
    ders: str = ""


GOREVLER: list[Gorev] = [

Gorev(
    "g01", "Emir verince ne oluyor",
    "Alım düğmesine bastığında arka planda ne olduğunu bilmek.",
    """Bir hisseyi "satın almak" aslında şu demek: emir defterine bir
alış emri koyuyorsun ve karşısında satmaya razı biri çıkınca işlem
oluyor.

İki tür emir var ve farkları para kaybettirecek kadar önemli:

PİYASA EMRİ — "kaç liraya olursa olsun al". Hemen gerçekleşir ama
fiyatını sen belirlemezsin. Likit olmayan hissede beklediğinden çok
yukarıdan alabilirsin.

LİMİT EMRİ — "en fazla şu fiyattan al". Fiyatı sen belirlersin ama
gerçekleşmeyebilir; fiyat sana hiç gelmezse emir asılı kalır.""",
    tur="secim",
    soru="1.000 TL'lik hesabınla, günde 20 milyon TL işlem gören bir "
         "hisseden 3 adet alacaksın. Hangi emri kullanırsın?",
    secenekler=[
        "Limit emri — fiyatı ben belirleyeyim",
        "Piyasa emri — hemen olsun, fiyat önemli değil",
        "Fark etmez, ikisi de aynı sonucu verir",
    ],
    dogru=0,
    aciklama="""Limit. Sebep büyüklük değil ALIŞKANLIK: piyasa emri
"fiyatı umursamıyorum" demektir ve bu alışkanlık likit olmayan bir
hissede ya da açılışın ilk dakikalarında pahalıya patlar.

Bu sistemin backtesti işlemi açılış fiyatından + kayma ile modelliyor.
Kaymayı küçük tutmanın yolu limit emri.""",
    ders="d103"),

Gorev(
    "g02", "Tutar: ne kadar para çıkacak",
    "Adet ile fiyattan maliyeti hesaplamak ve BIST'in kesirli hisse "
    "kısıtını görmek.",
    """TUTAR (ya da maliyet) basit bir çarpım: adet × fiyat.

Ama BIST'te bir kısıt var: KESİRLİ HİSSE YOKTUR. En az 1 adet
alabilirsin. ABD'de 100 dolarlık hissenin 10 dolarlık parçasını
alabilirsin, burada alamazsın.

Bu küçük sermayede gerçek bir sorun: 400 TL'lik bir hisseden 1 adet,
1.000 TL'lik portföyün %40'ıdır. Yani "biraz alayım" diye bir şey yok.""",
    tur="sayi",
    soru="GESAN 92,20 ₺. 3 adet alırsan hesabından ne kadar çıkar?",
    senaryo={"sembol": "GESAN", "fiyat": 92.20, "adet": 3},
    dogru=276.60, tolerans=0.05, birim="₺",
    ipucu="adet × fiyat",
    aciklama="""3 × 92,20 = 276,60 ₺.

10.000 TL'lik alıştırma hesabında bu %2,8 — rahat. Ama gerçek 1.000
TL'lik hesabında %27,7 olurdu ve tek hisse tavanına (%35) yaklaşırdın.

Aynı işlem, sermaye değişince bambaşka bir risk demek.""",
    ders="d101"),

Gorev(
    "g03", "Stop: nereden çıkacağını önceden söylemek",
    "Stopu duyguya değil oynaklığa göre koymayı öğrenmek.",
    """STOP, "buraya gelirse yanıldığımı kabul ediyorum" dediğin fiyat.
Alımdan ÖNCE konur, çünkü sonra konamaz: fiyat düşerken her seviye
"biraz daha bekleyeyim" gibi görünür.

Nereye konur? "Kaybetmeye razı olduğum yer" YANLIŞ cevap — o keyfi bir
sayı. Doğru cevap: hissenin NORMAL GÜNLÜK DALGALANMASININ DIŞINA.

Bunu ölçen sayı ATR: hissenin bir günde tipik olarak kaç lira oynadığı.
Bu sistem stopu girişin 2 ATR altına koyuyor. Daha yakın koyarsan
hissenin normal nefes alışı seni dışarı atar — haklı olduğun işlemden
bile gürültüyle çıkarsın.""",
    tur="sayi",
    soru="GESAN 92,20 ₺'den aldın. ATR 3,70 ₺. Stopu 2 ATR altına "
         "koyarsan kaç lira olur?",
    senaryo={"sembol": "GESAN", "fiyat": 92.20, "atr": 3.70, "kat": 2},
    dogru=84.80, tolerans=0.10, birim="₺",
    ipucu="giriş − (2 × ATR)",
    aciklama="""92,20 − (2 × 3,70) = 92,20 − 7,40 = 84,80 ₺.

Dikkat: bu stop "%8 kaybederim" diye seçilmedi. Yüzde tesadüfen çıktı.
Seçilen şey ORANTI: hissenin iki günlük normal hareketi kadar boşluk.

Oynak bir hissede aynı 2 ATR daha geniş bir stop demektir — ve doğrusu
budur. Sabit yüzde kullansaydın oynak hisseden sürekli atılırdın.""",
    ders="d805"),

Gorev(
    "g04", "Hedef ve ödül/risk oranı",
    "Bir işlemin 'değer mi' sorusunu sayıyla cevaplamak.",
    """HEDEF, kârı realize etmeyi planladığın fiyat. O da ATR'den çıkar.

Asıl mesele hedefin kendisi değil, stop ile arasındaki ORAN:

    ödül / risk = (hedef − giriş) / (giriş − stop)

Bu oran 1'in altındaysa, kazandığında kaybettiğinden az kazanıyorsun —
kârlı olman için isabet oranının çok yüksek olması gerekir. 2 ise,
işlemlerin üçte biri tutsa bile başabaşı geçersin.

Bu yüzden "bu hisse yükselir mi" sorusundan önce "yükselirse ne kadar
kazanırım, yükselmezse ne kadar kaybederim" sorusu gelir.""",
    tur="sayi",
    soru="Giriş 92,20 · stop 84,80 · hedef 110,70. Ödül/risk oranı kaç?",
    senaryo={"giris": 92.20, "stop": 84.80, "hedef": 110.70},
    dogru=2.5, tolerans=0.15, birim="",
    ipucu="(hedef − giriş) ÷ (giriş − stop)",
    aciklama="""(110,70 − 92,20) ÷ (92,20 − 84,80) = 18,50 ÷ 7,40 = 2,5.

Yani kazandığında kaybettiğinin 2,5 katını hedefliyorsun. Bu oranla
işlemlerin %29'u tutsa başabaşsın:
    başabaş isabet = 1 / (1 + 2,5) = %28,6

Sistemin canlı kazanma oranı %35 civarında. 2,5 ödül/risk ile bu oran
kâr üretir; 1,0 ile üretmezdi. İşte bu yüzden isabet oranı tek başına
hiçbir şey söylemiyor.""",
    ders="d803"),

Gorev(
    "g05", "Adet: stop belirler, cüzdan değil",
    "Pozisyon boyutunu hesaplamak — sistemin en önemli tek kuralı.",
    """Şimdi hepsini birleştiriyoruz.

Sıradan yaklaşım: "1.000 lira var, 300 lirasını bu hisseye koyayım."
Bu yaklaşımda ne kadar RİSK aldığın belirsizdir.

Doğru yaklaşım tersten çalışır:
  1. Bu işlemde en fazla ne kaybedebilirim?  (risk bütçesi)
  2. Stop çalışırsa hisse başına kaç lira kaybederim?
  3. Adet = risk bütçesi ÷ hisse başına risk

Bu sistemde risk bütçesi sermayenin %1,5'i. Neden bu kadar küçük:
üst üste altı işlem kaybetsen sermayenin ancak %9'unu kaybedersin ve
oyunda kalırsın. %10 riskle aynı seri seni yarı yarıya bitirirdi.""",
    tur="sayi",
    soru="10.000 ₺ alıştırma bakiyen var, işlem başına risk %1,5. "
         "GESAN 92,20 ₺, stop 84,80 ₺. Kaç adet alırsın?",
    senaryo={"bakiye": 10000, "risk_yuzde": 1.5, "fiyat": 92.20,
             "stop": 84.80},
    dogru=20, tolerans=1, birim="adet",
    ipucu="risk bütçesi = 10.000 × %1,5 · hisse başına risk = 92,20 − 84,80",
    aciklama="""Risk bütçesi: 10.000 × 0,015 = 150 ₺
Hisse başına risk: 92,20 − 84,80 = 7,40 ₺
Adet: 150 ÷ 7,40 = 20,3 → 20 adet
Maliyet: 20 × 92,20 = 1.844 ₺

Dikkat et: 1.844 ₺ harcıyorsun ama RİSKİN 150 ₺. İkisi çok farklı
şeyler ve karıştırılması en pahalı hatalardan biri.

Bir de şu: stop 88,50 olsaydı (daha yakın), hisse başına risk 3,70 ₺
olur ve 40 adet alırdın. Aynı 150 ₺ riskle iki katı hisse. Adedi
belirleyen şey cüzdanın değil, stop mesafesi.""",
    ders="d802"),

Gorev(
    "g06", "İlk alımını yap",
    "Öğrendiğin dört sayıyı gerçek bir emirde birleştirmek.",
    """Şimdi kum havuzunda gerçekten alım yapacaksın. Sanal para, gerçek
fiyat, gerçek kurallar.

Dört sayıyı da kendin gireceksin: adet, giriş, stop, hedef. Sistem
hesaplayıp sana vermiyor — çünkü gerçek işlemde de vermeyecek.

Bir şeyi unutma: alımdan önce TEZİNİ yaz. "Neden alıyorum" ve "hangi
durumda yanıldığımı kabul ederim". İkincisi stopun kendisi zaten; ama
birincisini yazmadan alırsan, fiyat düştüğünde tutunacak bir şeyin
olmaz ve gerekçeyi sonradan uydurursun.""",
    tur="islem",
    soru="Kum havuzunda bir alım yap: adet, stop ve hedefi sen belirle.",
    aciklama="""Alım kaydedildi. Şimdi önemli olan kısım: bu işlemi
kapatana kadar stopu DEĞİŞTİRME.

Stopu aşağı çekmek ("biraz daha alan vereyim") en yaygın ve en pahalı
alışkanlıktır. Stopu yukarı çekmek serbest — kârı korur. Aşağı çekmek
ise kaybı büyütür ve bir kere yapan bir daha yapar.""",
    ders="d1201"),

Gorev(
    "g07", "Stop çalışınca ne oluyor",
    "Kaybın önceden hesapladığın rakam olduğunu gözle görmek.",
    """Şimdi günleri ilerleteceksin. Fiyat stopa gelirse pozisyon
kapanacak ve kaybın ekranda çıkacak.

Bakmanı istediğim şey: o kayıp, alımdan önce hesapladığın risk
bütçesine ne kadar yakın?

Bir uyarı: her zaman tam tutmaz. Hisse stopun ALTINDA açarsa (boşluklu
açılış) çıkış stop fiyatından değil AÇILIŞTAN olur ve kaybın planından
büyük çıkar. Bu sistemin backtesti bunu böyle modelliyor, alıştırma da
öyle — çünkü gerçekte de böyle oluyor.

Stop bir garanti değil, bir DİSİPLİN aracıdır.""",
    tur="ilerlet",
    soru="Pozisyon kapanana kadar günleri ilerlet.",
    aciklama="""Gördüğün kayıp, alımdan önce kabul ettiğin rakamdı. Sürpriz
yok — stopun tek işi bu.

Şimdi asıl soruyu sor: bu işlemde yanlış bir şey yaptın mı? Muhtemelen
hayır. Kural işledi, kayıp planlanan büyüklükte kaldı.

İYİ KARAR + KÖTÜ SONUÇ diye bir kombinasyon var ve tekrarlanması
gereken şey odur. Sonuca bakıp kararı yargılamak (sonuç yanılgısı) en
tehlikeli düşünce hatasıdır.""",
    ders="d805"),

Gorev(
    "g08", "Tavanda açan hisseyi geç",
    "Alınamayacak bir sinyali tanımak.",
    """BIST'te bir hisse günde en fazla ~%20 hareket edebilir. Tavana
vurmuş bir hissede SATICI YOKTUR — emir girersin, gerçekleşmez.

Bu yüzden sistemin backtesti şunu varsayıyor: ertesi gün önceki
kapanışın %19,5 üstünde AÇAN hisse alınamaz sayılır. Sabah
hatırlatıcısı da bu eşiği söylüyor.

Bunu modellemeyen bir backtest, gerçekte giremeyeceğin işlemlerden kâr
sayar ve sonucu olduğundan iyi gösterir.""",
    tur="secim",
    soru="Dün 100,00 ₺'den kapanan bir hisse bugün 121,00 ₺'den açtı. "
         "Sinyal listesindeydi. Ne yaparsın?",
    secenekler=[
        "Bu emri geçerim — tavanda satıcı yok, zaten alamam",
        "Piyasa emriyle hemen alırım, güçlü hareket kaçmasın",
        "Stopu yukarı taşıyıp yine alırım",
    ],
    dogru=0,
    aciklama="""121,00 ÷ 100,00 = 1,21 → %21 yukarıda açmış, tavan
sınırının üstünde. Emir girsen de gerçekleşmez.

Gerçekleşse bile alma: sinyalin hesapladığı giriş fiyatı ~100 TL'ydi.
121'den girersen stop mesafesi, adet ve ödül/risk oranı — hepsi
bozulur. Aynı işlem değil artık.

Kaçırılan işlem maliyetsizdir. Kötü fiyattan girilen işlem değildir.""",
    ders="d104"),
]

GOREV_HARITA = {g.kod: g for g in GOREVLER}


def gorev_getir(kod: str) -> Gorev | None:
    return GOREV_HARITA.get((kod or "").lower().strip())


def kontrol(kod: str, cevap) -> dict:
    """Cevabı doğrular. `islem` ve `ilerlet` türleri kum havuzunda
    yapıldığı için burada her zaman doğru sayılır — onların kontrolü
    işlemin gerçekleşmiş olması."""
    g = gorev_getir(kod)
    if g is None:
        return {"dogru": False, "not": "görev yok"}

    if g.tur in ("islem", "ilerlet"):
        return {"dogru": True, "aciklama": g.aciklama}

    if g.tur == "secim":
        dogru = (cevap == g.dogru)
        return {"dogru": dogru, "aciklama": g.aciklama if dogru else "",
                "dogru_secenek": g.dogru}

    if g.tur == "sayi":
        try:
            v = float(str(cevap).replace(",", "."))
        except Exception:
            return {"dogru": False, "not": "sayı girilmeli"}
        dogru = abs(v - float(g.dogru)) <= g.tolerans
        return {"dogru": dogru, "aciklama": g.aciklama if dogru else "",
                "beklenen": g.dogru}

    return {"dogru": False, "not": f"bilinmeyen tür: {g.tur}"}
