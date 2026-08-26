"""Uygulama sözlüğü — ekranlarda geçen terimlerin karşılıkları.

NEDEN AYRI BİR KATMAN: eğitmen (egitmen_dersler.py) bir KONUYU baştan sona
anlatır ve 6-9 dakika sürer. Ama kullanıcı tarama ekranında "GG60" sütununu
gördüğünde ders okumak istemiyor — tek cümlelik karşılığını istiyor.

İkisi birbirinin yerine geçmez ve birbirini tekrarlamaz:
  SÖZLÜK  — bu kelime ne demek, uygulamada nerede karşıma çıkar (30 saniye)
  DERS    — bu neden böyle çalışır, ne zaman yanıltır (6-9 dakika)

Bu yüzden her terimin `ders` alanı var: sözlük merak uyandırır, ders
cevaplar. Sözlüğü ders yerine geçecek kadar uzatmak ikisini de bozar.

DRİFT KORUMASI: `kolonlar` alanı, terimin karşıladığı veri sütunlarını
sayar. testler/test_sozluk.py her göstergenin, her stratejinin ve her
rejim adının sözlükte karşılığı olduğunu doğrular — kod büyürken sözlük
sessizce geride kalamaz. Sessizce eksilen sözlük, sözlük olmamasından
kötüdür: kullanıcı bakar, bulamaz, bir daha bakmaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Terim:
    terim: str
    kisa: str                                   # tek cümlelik karşılık
    aciklama: str = ""                          # mekanizma: neden var
    nerede: str = ""                            # uygulamada nerede görürsün
    ders: str = ""                              # ilgili ders kodu
    kolonlar: list[str] = field(default_factory=list)   # karşıladığı veri sütunları


@dataclass
class Bolum:
    kod: str
    ad: str
    aciklama: str
    terimler: list[Terim] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# 1 — STRATEJİLER
# ═══════════════════════════════════════════════════════════════════

B1 = Bolum("stratejiler", "Stratejiler",
           "Sistemin tanıdığı üç giriş kalıbı. Üçü de t günü KAPANIŞINDA "
           "sinyal üretir, işlem t+1 AÇILIŞINDA yapılır.", [

Terim("trend",
 "Yükselen trendde geri çekilme alımı.",
 """Fiyat uzun vadeli yükselişte (SMA200 üstünde, EMA20 > EMA50) ve trend
güçlüyken (ADX14 > 18), son 3 günde EMA20'ye kadar geri çekilip yükselen
mumla toparlanan hisseyi arar.

Mantığı: yükselen trendde her geri çekilme bir indirimdir. Trendin
kırıldığı yerde değil, nefes aldığı yerde girmeye çalışır.

Stop 2 ATR, hedef 4 ATR, en fazla 20 gün tutulur.""",
 nerede="Tarama ekranında 'sinyal' sütununda ve günlük Telegram özetinde.",
 ders="d703"),

Terim("tepki",
 "Yükseliş trendi içindeki aşırı satım tepkisi.",
 """Uzun vadeli trendi yukarı olan (SMA200 üstünde) bir hissede RSI2 10'un,
Bollinger konumu 0,20'nin altına düştüğünde girer. Ek şart: önceki güne
göre %10'dan fazla çökmemiş olmak — panik satışı ile normal geri çekilme
farklıdır.

SMA200 şartı stratejinin belkemiği: onsuz bu strateji "düşen bıçağı
yakalamaya" dönüşür.

Kısa vadelidir: stop 2,5 ATR, hedef 2,5 ATR, en fazla 6 gün.""",
 nerede="Tarama ekranında 'sinyal' sütununda.",
 ders="d704"),

Terim("kirilim",
 "20 günlük zirvenin hacimle kırılması (breakout).",
 """Kapanış son 20 günün en yükseğinin (DON_ust) üstüne çıktığında, ama
yalnızca hacim son 20 günün ortalamasının 1,4 katından fazlaysa girer.
Ayrıca fiyat SMA200 üstünde ve ADX14 > 20 olmalı.

Hacim şartının sebebi ölçüm: onsuz backtest sonuçları belirgin şekilde
kötüleşiyor. Hacimsiz kırılım çoğunlukla sahtedir.

En uzun soluklu strateji: stop 2,5 ATR, hedef 5 ATR, en fazla 25 gün.""",
 nerede="Tarama ekranında 'sinyal' sütununda. Bu sinyal geldiği gün "
        "günün dersi otomatik olarak retest dersi olur.",
 ders="d1308"),
])


# ═══════════════════════════════════════════════════════════════════
# 2 — SİNYAL VE KARAR
# ═══════════════════════════════════════════════════════════════════

B2 = Bolum("sinyal", "Sinyal ve karar",
           "Bir hissenin ekrana gelene kadar geçtiği eleme ve sonrasında "
           "aldığı işaretler.", [

Terim("evren",
 "Sistemin baktığı hisse listesi (varsayılan: BIST 100).",
 """Tüm BIST'e bakmamanın sebebi likidite: küçük hisselerde emrin kendisi
fiyatı oynatır ve backtest sonuçları gerçekte tekrarlanamaz.""",
 nerede="Tarama başlığında.",
 ders="d106"),

Terim("filtre",
 "Hissenin değerlendirmeye bile alınıp alınmayacağı.",
 """Dört eşik: günlük ortalama TL hacim en az 20 milyon, ATR'nin fiyata
oranı %0,8 ile %7 arasında, o gün %9'dan fazla artmamış olmak, ve SMA200
için en az 220 günlük geçmiş.

Bu eşikler sinyal DEĞİL, elemedir: geçemeyen hisse hiç puanlanmaz.""",
 nerede="Tarama ekranında 'X hisse filtreyi geçti' satırı ve ELENENLER "
        "listesindeki gerekçeler."),

Terim("skor",
 "0-100 arası birleşik sıralama puanı.",
 """Dört parçadan oluşur: TREND (0-30) fiyat ortalamaların neresinde,
MOMENTUM (0-25) endeksi yeniyor mu, ZAMANLAMA (0-25) şu an girmek için
iyi bir nokta mı, KALİTE (0-20) likidite ve oynaklık uygun mu.

Zamanlama bileşeni aşırı alımı KASITLI olarak cezalandırır — RSI 80
üstünde bu bileşen 0 puandır.

Skor bir kesinlik değil SIRALAMA aracıdır. 85 puanlık hisse 40 puanlıktan
daha iyi konumlanmıştır ama yine de zarar edebilir.""",
 nerede="Tarama ekranında 'skor' sütunu ve alt kırılımları."),

Terim("sinyal",
 "Bir stratejinin giriş şartlarının o gün sağlanması.",
 """Skordan farklıdır: skor sıralar, sinyal karar önerir. Yüksek skorlu bir
hisse sinyal vermiyor olabilir; sinyal veren bir hisse düşük skorlu
olabilir.""",
 nerede="Tarama ekranında 'BUGÜN SİNYAL VEREN HİSSELER' bölümü."),

Terim("alınabilir",
 "Sinyal veren hisse, senin sermayenle gerçekten alınabiliyor mu.",
 """BIST'te kesirli hisse yok — en az 1 adet alabilirsin. 400 TL'lik bir
hisse, 1.000 TL'lik portföyün %40'ıdır ve tek hisse tavanını (%35) aşar.
Bu yüzden sinyal veren her hisse alınabilir değildir.""",
 nerede="Tarama ekranında 'adet' ve 'tutar' sütunları; alınamıyorsa "
        "gerekçe yazar.",
 ders="d101"),

Terim("önerilir",
 "Sinyali üreten stratejinin canlı sicili yeterli mi.",
 """Karantinadaki bir stratejiden gelen sinyal gizlenmez ama 'önerilmez'
olarak işaretlenir. Gizlemek daha kötü olurdu: kullanıcı sinyali başka bir
yerde görüp onaylanmış sanabilir.""",
 nerede="Günlük özet mesajında 'karantinadaki stratejilerden geldi' notu."),

Terim("karantina",
 "Canlı sicili beklentinin altına düşen stratejinin önerilmez olması.",
 """Dört sınıf var ve eşik sabit bir sayı değil, o stratejinin TARİHSEL
dağılımıdır:

· normal     — beklenen aralığın alt çeyreğinin üstünde
· izlemede   — alt %5 ile alt çeyrek arasında; önerilir ama işaretli
· karantina  — beklenenin alt %5'inin altında; ÖNERİLMEZ
· hüküm_yok  — sınıflandırmaya yetecek ay/sinyal birikmemiş

Kritik ayrıntı: karantinadaki strateji KAPATILMAZ, sinyal üretmeye devam
eder ve ambara yazılır. Yoksa hakkında yeni kanıt hiç birikmez ve
karantina kalıcı hapse dönüşür. Bozulan kendiliğinden girer, düzelen
kendiliğinden çıkar.""",
 nerede="Sistemin sicili ekranı ve günlük özet mesajı.",
 ders="d1202"),
])


# ═══════════════════════════════════════════════════════════════════
# 3 — GÖSTERGELER
# ═══════════════════════════════════════════════════════════════════

B3 = Bolum("gostergeler", "Göstergeler",
           "Tarama ve hisse ekranlarındaki sütunlar. Hepsi yalnızca o güne "
           "kadarki veriden hesaplanır — geleceğe bakma yoktur.", [

Terim("Hareketli ortalama (EMA / SMA)",
 "Son N günün ortalama fiyatı; trendin yönünü gürültüden ayırır.",
 """SMA her güne eşit ağırlık verir, EMA son günlere daha çok ağırlık verir
ve bu yüzden daha hızlı tepki gösterir.

Sistemde dördü kullanılır: EMA10, EMA20, EMA50 (kısa/orta vade) ve SMA200
(uzun vadeli trend hakemi). "Fiyat SMA200 üstünde mi" sorusu üç stratejinin
de ortak şartıdır.

Yatay piyasada hepsi yanıltır: fiyat ortalamanın etrafında gidip gelirken
sürekli sahte sinyal üretirler.""",
 nerede="Hisse ekranında fiyat grafiğinin üstünde; taramada '200g' sütunu.",
 ders="d703",
 kolonlar=["EMA10", "EMA20", "EMA50", "SMA200"]),

Terim("RSI",
 "0-100 arası momentum ölçer: son hareketler ne kadar tek yönlü olmuş.",
 """Yükseliş günlerinin ortalama büyüklüğünü düşüş günlerininkine oranlar.
70 üstü genelde 'aşırı alım', 30 altı 'aşırı satım' sayılır.

Sistemde iki periyot var ve işleri farklıdır:
· RSI14 — genel momentum, skorun zamanlama bileşeninde kullanılır
· RSI2  — çok kısa vadeli aşırılık; `tepki` stratejisinin tetiği (< 10)

En sık yapılan hata: 'RSI 70 geçti, sat.' Güçlü bir trendde RSI haftalarca
70 üstünde kalabilir ve fiyat yükselmeye devam eder.""",
 nerede="Taramada 'RSI' sütunu, hisse ekranında ayrı panel.",
 ders="d704",
 kolonlar=["RSI14", "RSI2"]),

Terim("ATR",
 "Ortalama gerçek aralık: hissenin bir günde tipik olarak kaç lira oynadığı.",
 """Yön söylemez, MESAFE söyler. Gerçek aralık, günün en yüksek-en düşük
farkı ile önceki kapanışa olan boşluğun büyüğüdür — yani gap'i de sayar.

Sistemde iki iş yapar:
· STOP MESAFESİ — stop, girişin 2 ile 2,5 ATR altına konur. Böylece stop
  hissenin normal gürültüsünün dışında kalır.
· POZİSYON BOYUTU — risk bütçesi ATR'ye bölünür. Oynak hisseden daha az
  adet alınır.

ATR_yuzde, ATR'nin fiyata oranıdır. Filtre bunu kullanır (%0,8-%7) çünkü
'3 lira oynaklık' 20 liralık hissede başka, 300 liralıkta başka bir şeydir.""",
 nerede="Taramada 'ATR%' sütunu; stop ve hedef bu sayıdan üretilir.",
 ders="d705",
 kolonlar=["ATR14", "ATR_yuzde"]),

Terim("MACD",
 "İki hareketli ortalamanın farkı; trendin hızlanıp yavaşladığını gösterir.",
 """12 günlük EMA eksi 26 günlük EMA. Bunun 9 günlük EMA'sı 'sinyal çizgisi',
ikisinin farkı 'histogram'dır.

Gecikmeli bir göstergedir: dönüşü fiyat döndükten sonra teyit eder. Erken
uyarı beklemek en yaygın yanlış kullanımıdır.""",
 nerede="Hisse ekranında gösterge panelinde.",
 ders="d704",
 kolonlar=["MACD", "MACD_sinyal", "MACD_fark"]),

Terim("Bollinger bantları",
 "Ortalamanın etrafında oynaklığa göre genişleyip daralan bir zarf.",
 """Orta bant 20 günlük ortalama; üst ve alt bantlar bunun 2 standart sapma
uzağıdır. Oynaklık artınca bantlar açılır, azalınca daralır.

BB_konum bu üçünü tek sayıya indirir: fiyat alt bantta 0, üst bantta 1.
`tepki` stratejisi 0,20 altını arar.

Yanılgı: 'üst banda değdi, pahalı.' Güçlü trendde fiyat üst bant boyunca
yürüyebilir — banda değmek bir dönüş sinyali değildir.""",
 nerede="Hisse ekranında fiyat grafiğinde; 'BB_alt' / 'BB_ust' etiketleri.",
 ders="d705",
 kolonlar=["BB_alt", "BB_orta", "BB_ust", "BB_konum"]),

Terim("ADX",
 "Trendin GÜCÜNÜ ölçer — yönünü değil.",
 """Düşük ADX yatay piyasa demektir; yüksek ADX güçlü bir trend (yukarı ya
da aşağı olabilir) demektir.

Sistemde bir filtre olarak kullanılır: `trend` stratejisi 18, `kirilim`
20 üstü ister. Sebep basit — trend takip eden kurallar yatay piyasada
para kaybettirir. ADX o piyasayı eler.""",
 nerede="Taramada 'ADX' sütunu.",
 ders="d701",
 kolonlar=["ADX14"]),

Terim("Donchian kanalı",
 "Son N günün en yükseği ve en düşüğü.",
 """Sistemde N = 20. DON_ust son 20 günün zirvesi, DON_alt dibi.

`kirilim` stratejisinin giriş şartı doğrudan budur: kapanış DON_ust'ün
üstüne çıkması. Çıkış tarafında ise 10 günlük dip kullanılır.

Destek/direnç çizmenin öznelliği olmayan hali: kimsenin yorumuna bağlı
değil, tek bir doğru cevabı var.""",
 nerede="Doğrudan görünmez; `kirilim` sinyalinin arkasındaki sayıdır.",
 ders="d706",
 kolonlar=["DON_ust", "DON_alt"]),

Terim("Hacim oranı",
 "Bugünkü hacim, son 20 günün ortalamasının kaç katı.",
 """1,0 normal gün demektir; 2,0 hacmin iki katına çıktığı gün.

`kirilim` stratejisi 1,4 üstü ister. Hacim, bir fiyat hareketinin kaç
kişiyi ilgilendirdiğini söyler: hacimsiz kırılım çoğunlukla sahtedir.""",
 nerede="Skorun kalite bileşeninde ve `kirilim` sinyalinde.",
 ders="d702",
 kolonlar=["Hacim_orani"]),

Terim("Göreli güç (GG)",
 "Hissenin endeksten ne kadar iyi/kötü performans gösterdiği.",
 """GG60 = hissenin 60 günlük getirisi eksi XU100'ün 60 günlük getirisi.
Pozitifse hisse endeksi yeniyor.

Neden önemli: BIST %30 yükselirken %20 yükselen hisse KAZANDIRMADI —
endeks fonu alsan daha iyiydin. Göreli güç bu soruyu sorar.

Sistemde skorun momentum bileşeninin ana girdisi ve aynı gün birden çok
sinyal geldiğinde sıralama ölçütüdür.""",
 nerede="Taramada 'GG60' sütunu.",
 ders="d903",
 kolonlar=["GG20", "GG60"]),

Terim("Oynaklık",
 "Günlük getirilerin standart sapması — fiyatın ne kadar zıpladığı.",
 """20 günlük gerçekleşen oynaklık. ATR'ye benzer ama yüzde getiriler
üzerinden hesaplanır, bu yüzden hisseler arası kıyaslanabilir.

Risk hesaplarında ve Sharpe'ın paydasında kullanılır.""",
 nerede="Risk matematiği ekranında.",
 ders="d705",
 kolonlar=["Oynaklik"]),

Terim("Zirveden",
 "Fiyatın kendi en yüksek seviyesinden yüzde kaç aşağıda olduğu.",
 """Tek bir hisse için 'düşüşten kayıp' ölçüsü. Portföy düzeyindeki
karşılığı azami düşüştür.""",
 nerede="Hisse ekranında.",
 ders="d801",
 kolonlar=["Zirveden"]),

Terim("Getiri (5 / 20 / 60 gün)",
 "Fiyatın N gün önceye göre yüzde değişimi.",
 """Momentum ölçmenin en doğrudan hali. Skorun momentum bileşeninde ve
göreli güç hesabında kullanılır.""",
 nerede="Hisse ekranında ve skor kırılımında.",
 kolonlar=["Getiri_5g", "Getiri_20g", "Getiri_60g"]),

Terim("TL hacim",
 "Adet değil, o gün el değiştiren PARA (fiyat × adet).",
 """Likiditenin doğru ölçüsü budur. 1 milyon adet, 2 liralık hissede 2
milyon TL; 200 liralık hissede 200 milyon TL demektir — ikisi bambaşka
likiditedir.

TL_hacim_ort20 son 20 günün ortalamasıdır ve filtre bunu kullanır
(en az 20 milyon TL).""",
 nerede="Taramada 'hacim(M₺)' sütunu.",
 ders="d102",
 kolonlar=["TL_hacim", "TL_hacim_ort20"]),
])


# ═══════════════════════════════════════════════════════════════════
# 4 — RİSK VE POZİSYON
# ═══════════════════════════════════════════════════════════════════

B4 = Bolum("risk", "Risk ve pozisyon",
           "Ne kadar alacağın ve nerede çıkacağın. Sistemin en çok "
           "önemsediği bölüm — burada yapılan hata geri alınmaz.", [

Terim("stop",
 "Tezinin bozulduğunu kabul ettiğin fiyat.",
 """Girişin 2 ile 2,5 ATR altına konur (stratejiye göre değişir). ATR'ye
bağlanmasının sebebi: stop hissenin normal gürültüsünün DIŞINDA olmalı,
yoksa haklı olduğun işlemlerden bile gürültüyle atılırsın.

Stop bir tahmin değil, önceden verilmiş bir karardır. Değeri de tam olarak
bundan gelir: fiyat oraya geldiğinde artık düşünmek zorunda kalmazsın.""",
 nerede="Taramada 'stop' sütunu; Telegram stop alarmında.",
 ders="d805"),

Terim("hedef",
 "Kârı realize etmeyi planladığın fiyat.",
 """Girişin 2,5 ile 5 ATR üstüne konur. Stop ile hedef arasındaki oran
ÖDÜL/RİSK oranıdır: `kirilim` stratejisinde 5/2,5 = 2, yani kazandığında
kaybettiğinin iki katını hedefler.""",
 nerede="Taramada 'hedef' sütunu.",
 ders="d803"),

Terim("işlem başına risk",
 "Tek bir işlemde kaybetmeyi göze aldığın sermaye yüzdesi.",
 """Varsayılan %1,5. 1.000 TL'de 15 TL demektir.

Adet buradan çıkar: risk bütçesi ÷ (giriş − stop). Yani pozisyon boyutunu
'içime sinen miktar' değil, stop mesafesi belirler. Stop uzaksa daha az
adet alırsın.""",
 nerede="Ayarlar ekranında; her sinyalin adet hesabında.",
 ders="d802"),

Terim("azami pozisyon",
 "Tek bir hisseye koyabileceğin en yüksek sermaye oranı.",
 """Varsayılan %35. Küçük sermayede genelde BAĞLAYICI olan tavan budur:
BIST'te kesirli hisse olmadığı için 400 TL'lik bir hisseden 1 adet zaten
1.000 TL'nin %40'ıdır.""",
 nerede="Ayarlar ekranında; 'alınamıyor' gerekçesinde.",
 ders="d802"),

Terim("kayma (slippage)",
 "Emrin göründüğü fiyattan değil, biraz kötüsünden gerçekleşmesi.",
 """Alışta biraz yukarıdan, satışta biraz aşağıdan. Sebebi spread ve emir
defterinin derinliği.

Midas'ta BIST komisyonu sıfır — ama kayma sıfır değildir. Backtest bunu
modeller; etmeyen backtestler sonucu olduğundan iyi gösterir. Sistem
ayrıca canlı sinyallerde gerçek kaymayı ÖLÇER.""",
 nerede="Sistemin sicili ekranında 'kayma' bölümü.",
 ders="d102"),

Terim("tavan / taban",
 "BIST'te bir hissenin bir günde çıkabileceği/inebileceği sınır.",
 """Ana pazarda yaklaşık ±%20. İki yerde karşına çıkar:

· FİLTRE — o gün %9'dan fazla artmış hisse elenir; ertesi gün alım riskli.
· BACKTEST — ertesi gün önceki kapanışın %19,5 üstünde AÇAN hisse
  alınamaz sayılır. Gerçekte de alamazsın: tavanda satıcı yoktur.""",
 nerede="Elenenler listesinde 'tavana yakın' gerekçesi.",
 ders="d104"),

Terim("boşluk (gap)",
 "İki günün fiyat aralıklarının hiç kesişmemesi.",
 """Seans 18:00'de kapanır, haber gece KAP'a düşer, sabah 10:00'da fiyat
bambaşka bir yerden açar. Aradaki fiyatlardan hiç işlem geçmemiştir.

Stop açısından kritik: boşluklu açılışta stop, stop fiyatından DEĞİL
açılıştan çalışır. Stopun 100'dü ama hisse 92'den açtıysa 92'den çıkarsın.
Backtest bunu böyle modeller.""",
 nerede="Backtest varsayımlarında; stop alarmında.",
 ders="d1305"),
])


# ═══════════════════════════════════════════════════════════════════
# 5 — ÖLÇÜM VE SİCİL
# ═══════════════════════════════════════════════════════════════════

B5 = Bolum("olcum", "Ölçüm ve sicil",
           "Bir kuralın gerçekten işe yarayıp yaramadığını söyleyen "
           "sayılar. Sistemin sicili ekranının dili budur.", [

Terim("backtest",
 "Bir stratejiyi geçmiş veride, gün gün çalıştırarak sınamak.",
 """Bu motorun amacı stratejiyi güzel göstermek değil, dürüstçe ölçmektir.
Bu yüzden bilerek modellenenler: sinyal t kapanışında üretilir işlem t+1
açılışında yapılır, alışta yukarı satışta aşağı kayma uygulanır, tavanda
açan hisse alınamaz, boşluklu açılışta stop açılıştan çalışır, aynı gün
hem stop hem hedef görüldüyse kötümser varsayım (stop çalıştı), nakit
sınırlıdır.

Backtest GEÇMİŞTİR ve geçmişe uydurulmuş olabilir. Bu yüzden tek başına
yeterli değildir — karantina onun sınavıdır.""",
 nerede="Backtest ekranı ve sistemin sicili karşılaştırması.",
 ders="d1202"),

Terim("canlı sicil",
 "Sistemin gerçek zamanda ürettiği sinyallerin gerçekte ne yaptığı.",
 """Backtestten farkı: bu sinyaller üretildiği anda kaydedildi, sonuç
sonradan ölçüldü. Yani geçmişe uydurma imkânı yok.

Canlı sicil ile backtest arasındaki fark, karantina kararının girdisidir.""",
 nerede="Sistemin sicili ekranı — 'Canlı vs backtest'.",
 ders="d1203"),

Terim("kazanma oranı",
 "İşlemlerin yüzde kaçının kârla kapandığı.",
 """Tek başına neredeyse hiçbir şey söylemez. %35 kazanma oranlı bir trend
stratejisi, kazandığında çok kazanıyorsa kârlıdır; %90 kazanma oranlı bir
strateji, kaybettiği %10'da her şeyi geri veriyorsa batırır.

Doğru soru kazanma oranı değil, beklenen değerdir.""",
 nerede="Sistemin sicili ekranı.",
 ders="o16"),

Terim("beklenen değer",
 "İşlem başına ortalama olarak ne kazandırdığı.",
 """(kazanma oranı × ortalama kazanç) − (kayıp oranı × ortalama kayıp).

Bir kuralın tek gerçek ölçüsü budur. Pozitif değilse, kazanma oranı ne
olursa olsun o kural para kaybettirir.""",
 nerede="Risk matematiği ekranı.",
 ders="d803"),

Terim("kâr faktörü",
 "Toplam kazancın toplam kayba oranı.",
 """1,0 başabaş demektir. 1,5 üstü genelde sağlıklı sayılır. Beklenen
değerin işlem sayısından bağımsız hali.""",
 nerede="Sistemin sicili ekranı."),

Terim("Sharpe oranı",
 "Aldığın risk başına ne kadar getiri elde ettiğin.",
 """(Yıllık getiri − RİSKSİZ GETİRİ) ÷ yıllık oynaklık.

Risksiz getiriyi çıkarmak Türkiye'de belirleyicidir: mevduat %45 verirken
%40 kazanan bir strateji para kazanmış görünür ama aslında kaybetmiştir.
Bu yüzden sistemin Sharpe'ı çoğu zaman negatiftir — ve bu doğru olandır.

Negatif Sharpe 'strateji bozuk' demek değil, 'riski alacağına mevduatta
otursaydın daha iyiydin' demektir.""",
 nerede="Sistemin sicili ve backtest ekranları.",
 ders="d903"),

Terim("Sortino oranı",
 "Sharpe'ın yalnızca AŞAĞI yönlü oynaklığa bakan hali.",
 """Sharpe yukarı zıplamaları da risk sayar — halbuki kimse kazanmaktan
şikâyetçi değildir. Sortino yalnızca kayıpların oynaklığını paydaya koyar.""",
 nerede="Backtest ekranı.",
 ders="d903"),

Terim("azami düşüş",
 "Zirveden dibe en büyük sermaye kaybı.",
 """Getiriden daha önemli bir sayıdır, çünkü dayanabileceğin şeyi ölçer.
%50 düşen bir portföyün başabaşa dönmesi için %100 kazanması gerekir —
kayıp asimetrisi budur.

Ayrıca psikolojik sınır: çoğu kişi %30 düşüşte stratejiyi terk eder ve
tam dipte satar.""",
 nerede="Sistemin sicili ve backtest ekranları.",
 ders="d801"),

Terim("Calmar oranı",
 "Yıllık getirinin azami düşüşe oranı.",
 """'Bu acıya katlanmaya değdi mi' sorusunun tek sayılık cevabı.""",
 nerede="Backtest ekranı."),

Terim("kaçırılan sinyal",
 "Nakit ya da pozisyon slotu olmadığı için alınamayan sinyal.",
 """Backtest bunu sayar, çünkü gerçek hayatta da olur: dört pozisyonun
doluysa beşinci sinyali alamazsın. Saymayan backtestler sınırsız para
varsayar ve sonucu şişirir.""",
 nerede="Backtest sonucunda."),

Terim("taban oran",
 "Hiçbir şey yapmasan / rastgele seçsen ne çıkardı.",
 """Her ölçümün kıyas noktası. 'Bu kural %58 tutturuyor' cümlesi, aynı
hisselerde rastgele günlerde %56 çıkıyorsa hiçbir şey ifade etmez.

En sık atlanan adım budur ve atlandığında ölçüm ölçüm olmaktan çıkar.""",
 nerede="Sicil yorumlarında; d1310 dersinin konusu.",
 ders="d1310"),
])


# ═══════════════════════════════════════════════════════════════════
# 6 — PORTFÖY VE KAYIT
# ═══════════════════════════════════════════════════════════════════

B6 = Bolum("portfoy", "Portföy ve kayıt",
           "Birden çok pozisyonu birlikte yönetmek ve kendi kararlarını "
           "kayda geçirmek.", [

Terim("korelasyon",
 "İki hissenin birlikte hareket etme derecesi (-1 ile +1).",
 """+1 tamamen birlikte, 0 ilgisiz, -1 tam ters. Beş banka hissesi almak
çeşitlendirme değildir: ortalama korelasyon 0,7 üstündeyse portföy tek
hisse gibi hareket eder.""",
 nerede="Risk matematiği ekranı.",
 ders="d804"),

Terim("etkin hisse sayısı",
 "Korelasyon hesaba katıldığında gerçekte kaç hisseye sahipsin.",
 """4 hissen olabilir ama hepsi birlikte hareket ediyorsa etkin sayı 1,2
olabilir. 'Kaç hisse aldım' değil, 'kaç BAĞIMSIZ bahis yaptım' sorusunun
cevabı.""",
 nerede="Risk matematiği ekranı; yoğunlaşma uyarısı.",
 ders="d804"),

Terim("bağımsız bahis",
 "Portföyünün gerçekte kaç ayrı fikre dayandığı.",
 """Etkin hisse sayısının karar diline çevrilmiş hali. Bu sayı hisse
sayının belirgin altındaysa sistem uyarır ve günün dersini çeşitlendirme
dersine çevirir.""",
 nerede="Tarama ekranında yoğunlaşma uyarısı.",
 ders="d804"),

Terim("kâğıt portföy",
 "Gerçek para koymadan yapılan kayıtlı işlem.",
 """Varsayılan budur. Karar defterine kaydedilir ve gerçek işlemle aynı
şekilde ölçülür — ama para riske girmez. Amaç: sicil biriktirmeden gerçek
para koymamak.""",
 nerede="Alım kaydederken 'kâğıt' işareti.",
 ders="d1203"),

Terim("karar defteri",
 "Senin verdiğin kararların ve gerekçelerinin kaydı.",
 """Sistemin sicilinden farklı bir şeydir ve daha önemlidir: sistem ne
önerdi, sen ne yaptın, neden. Sistemi takip mi ettin yoksa kendi fikrinle
mi gittin — ve hangisi daha iyi sonuç verdi?

Kaydedilmeyen karar öğrenilmez: sonucu bildiğin an, kararı verdiğin
andaki düşünceni hatırladığını sanırsın. Hatırlamazsın.""",
 nerede="Daha → Karar defterin.",
 ders="d1203"),

Terim("tez",
 "Alımdan ÖNCE yazılan gerekçe ve yanılma koşulu.",
 """İki şeyi içerir: neden alıyorum, ve hangi durumda yanıldığımı kabul
ederim. İkincisi alımdan sonra tanımlanamaz — o noktada her düşüş
'geçici' görünür ve beynin gerekçe üretir.""",
 nerede="Tez yaz ekranı.",
 ders="d1201"),

Terim("sermaye defteri",
 "Yatırdığın para ile kazandığın paranın ayrı tutulması.",
 """Portföyün 1.300 TL ise ve 1.200 TL yatırdıysan kazancın 100 TL'dir,
%30 değil. Para yatırıp çekince getiri hesabı bozulur; bu defter onu
düzeltir.""",
 nerede="Daha → Sermaye.",
 ders="d903"),
])


# ═══════════════════════════════════════════════════════════════════
# 7 — PİYASA VE MAKRO
# ═══════════════════════════════════════════════════════════════════

B7 = Bolum("piyasa", "Piyasa ve makro",
           "Tek tek hisselerin üstündeki katman: piyasanın genel hâli ve "
           "BIST'in kendi kuralları.", [

Terim("rejim",
 "Piyasanın genel risk iştahı — dört kademe.",
 """Faiz, kur, enflasyon, gelişen piyasalar ve ABD 10 yıllık faizi
puanlanarak belirlenir:

· RİSK AÇIK — momentum ve kırılım stratejileri için elverişli
· ılımlı     — normal işlem, pozisyon boyutunu abartma
· temkinli   — filtreleri sıkılaştır, daha az pozisyon taşı
· SAVUNMA    — nakit oranını yükselt; bu rejimde kaybetmemek kazanmaktır

Trend takip eden stratejiler risk iştahı açıkken çalışır. Savunma
rejiminde nakitte beklemek bir pozisyondur.""",
 nerede="Daha → Makro; günlük özet mesajında.",
 ders="d605"),

Terim("XU100",
 "BIST 100 endeksi — piyasanın geneli.",
 """Göreli güç hesabının kıyas noktası. Endeksi yenemeyen bir hisse, o
dönem için kaybettirmiştir — endeks fonu daha iyiydi.""",
 nerede="Günlük özet mesajının ilk satırı.",
 ders="d106"),

Terim("reel getiri",
 "Enflasyondan arındırılmış getiri.",
 """Türkiye'de en pahalı yanılgı buradadır. BIST'in TL bazında %222 kazandığı
bir dönemde USD bazında kazancı %32'ydi ve enflasyon düşüldüğünde reel
getiri negatif olabilir.

Nominal rakama sevinmek, kaybettiğini kazanç sanmaktır.""",
 nerede="Günlük özet mesajında 'BIST 1 yıl reel getirisi' satırı.",
 ders="d601"),

Terim("T+2 / takas",
 "Sattığın hissenin parasının hesabına geçme süresi.",
 """İşlem günü + 2 iş günü. Sattığın gün parayı çekemezsin, ama o parayla
aynı gün başka hisse alabilirsin.""",
 nerede="Portföy ekranı.",
 ders="d105"),

Terim("KAP",
 "Kamuyu Aydınlatma Platformu — şirketlerin resmî bildirim adresi.",
 """Bilanço, sermaye artırımı, temettü, yönetim değişikliği: hepsi önce
buraya düşer. Haber sitesinden okuduğun her şeyin kaynağı burasıdır ve
aradaki gecikmede fiyat çoktan hareket etmiş olur.""",
 nerede="Gün özeti ekranında KAP bildirimleri.",
 ders="d1101"),

Terim("seans",
 "BIST'in işlem saatleri.",
 """Sürekli işlem 10:00-18:00. Sistemin günlük işi 18:10'da, kapanış
verisi kesinleştikten sonra çalışır. Gün içi veri 15 dakika gecikmeli
geldiği için sistem gün içi karar vermez.""",
 nerede="Günlük işin çalışma saati.",
 ders="d104"),

Terim("emir defteri",
 "Bekleyen alış ve satış emirlerinin listesi; fiyat burada oluşur.",
 """En yüksek alış ile en düşük satış arasındaki farka SPREAD denir ve bu,
komisyon sıfır olsa bile ödediğin görünmeyen maliyettir.""",
 nerede="Midas uygulamasında; bu sistemde kayma olarak modellenir.",
 ders="d102"),
])


BOLUMLER = [B1, B2, B3, B4, B5, B6, B7]
TUM_TERIMLER = [t for b in BOLUMLER for t in b.terimler]
TERIM_HARITA = {t.terim.lower(): t for t in TUM_TERIMLER}
BOLUM_HARITA = {b.kod: b for b in BOLUMLER}

# Hangi veri sütununu hangi terim açıklıyor — tarama ekranı bir sütun
# başlığına dokunulduğunda bunu kullanır.
KOLON_HARITA = {k: t for t in TUM_TERIMLER for k in t.kolonlar}


# Sütun adları büyük/küçük harf duyarlı yazılmış ("ATR_yuzde", "GG60");
# kullanıcı ise küçük harfle arar. Tek bir küçük harfli haritada buluşturulur.
_KOLON_KUCUK = {k.lower(): t for k, t in KOLON_HARITA.items()}


def terim_getir(ad: str) -> Terim | None:
    """Terim adı ya da veri sütunu adıyla arar; ikisi de büyük/küçük harf
    duyarsızdır."""
    q = (ad or "").lower().strip()
    return TERIM_HARITA.get(q) or _KOLON_KUCUK.get(q)


def bolum_getir(kod: str) -> Bolum | None:
    return BOLUM_HARITA.get((kod or "").lower().strip())


def ara(sorgu: str) -> list[Terim]:
    """Terim adında ya da kısa karşılığında geçenler.

    Açıklama gövdesinde aramaz: 'stop' kelimesi on farklı terimin
    gövdesinde geçiyor ve hepsini döndürmek arama olmaz, gürültü olur.
    """
    q = (sorgu or "").lower().strip()
    if not q:
        return []
    return [t for t in TUM_TERIMLER
            if q in t.terim.lower() or q in t.kisa.lower()
            or any(q == k.lower() for k in t.kolonlar)]
