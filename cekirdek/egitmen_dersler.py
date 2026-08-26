"""Müfredat: okunacak dersler.

Tasarım kuralı: her ders bir MEKANİZMA anlatır, terim listelemez. "F/K fiyat
bölü kazançtır" bir tanımdır ve hiçbir şey öğretmez. "F/K'yı mevduat faiziyle
kıyasla, çünkü ikisi de aynı soruyu cevaplar: paramı buraya koyarsam yılda
yüzde kaç kazanırım" bir mekanizmadır ve karar aldırır.

Her dersin bölümleri:
  icerik  — ana anlatım
  bist    — Türkiye/BIST/Midas özeli (genel finans kitaplarında olmayan kısım)
  tuzak   — bu konuda en sık yapılan hata ve NEDEN yapıldığı
  ornek   — gerçek sayılarla işlenmiş örnek
  sorular — pekiştirme için ilgili soru kodları
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Ders:
    kod: str
    baslik: str
    ozet: str                       # tek cümle: bu derste ne öğreneceksin
    icerik: str
    bist: str = ""
    tuzak: str = ""
    ornek: str = ""
    sorular: list[str] = field(default_factory=list)
    sure: int = 6                   # tahmini okuma dakikası


@dataclass
class Modul:
    kod: str
    ad: str
    aciklama: str
    seviye: int                     # 1 giriş · 2 orta · 3 ileri
    dersler: list[Ders] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# MODÜL 1 — PİYASANIN MEKANİĞİ
# ═══════════════════════════════════════════════════════════════════

M1 = Modul("m1", "Piyasanın mekaniği",
           "Borsa fiziksel olarak nasıl çalışır: emir defteri, fiyat oluşumu, "
           "seanslar, takas. Buradaki her şey kuraldır, yorum değil.", 1, [

Ders("d101", "Hisse senedi gerçekte nedir",
 "Bir kâğıt değil, bir şirketin bölünmüş mülkiyeti aldığını anlamak.",
 """Bir şirket kurulurken sermayesi paylara bölünür. THYAO'nun sermayesi
1.380.000.000 paya bölünmüştür. Sen 1 adet aldığında, şirketin
1.380.000.000'da birine ortak olursun.

Bu ortaklık sana üç hak verir:
· KÂR PAYI — şirket kâr dağıtmaya karar verirse payın kadar alırsın
· OY — genel kurulda payın kadar oy kullanırsın (pratikte küçük yatırımcı için
  etkisiz, ama hak vardır)
· TASFİYE PAYI — şirket kapanırsa, tüm borçlar ödendikten SONRA kalan varlıktan
  payını alırsın

Ve bir sınır koyar: SINIRLI SORUMLULUK. Şirket 10 milyar borçla batarsa senden
kimse para istemez. Kaybedebileceğin en fazla şey, ödediğin paradır. Bu, modern
şirketler hukukunun en önemli buluşudur — insanların riskli işlere sermaye
koymasını mümkün kılan şey budur.

Şimdi kritik sonuç: hisse senedi bir "yükselmesi beklenen kâğıt" değildir. Bir
İŞLETMENİN parçasıdır. Fiyatı, o işletmenin gelecekte üreteceği nakit hakkındaki
kolektif kanaatin bugünkü yansımasıdır.

Bu ayrımı içselleştirmek her şeyi değiştirir. "THYAO 300 lira, ucuz mu?" sorusu
anlamsızdır. "Türk Hava Yolları'nın tamamı 412 milyar lira eder mi?" sorusu
anlamlıdır — ve cevaplanabilir.""",
 bist="""BIST'te KESİRLİ HİSSE YOKTUR. En az 1 adet alabilirsin. ABD'de 100
dolarlık hissenin 10 dolarlık parçasını alabilirsin, burada alamazsın. Bu,
küçük sermaye için gerçek bir kısıttır: 400 TL'lik bir hisseden 1 adet, 1.000
TL'lik portföyün %40'ıdır.

Pay grupları: A, B, C, D. Fiili dolaşımdaki pay değerine göre belirlenir ve
hangi pazarda işlem göreceğini etkiler. BIST 100 endeksine sadece A ve B
grubundakiler girer.""",
 tuzak=""""Fiyatı düşük olan hisse ucuzdur" — en yaygın ve en pahalı başlangıç
hatası. 3 liralık hisse 400 liralıktan ucuz DEĞİLDİR. Şirketin toplam değeri,
fiyat × adet'tir. Bedelsiz sermaye artırımında adet ikiye katlanır ve fiyat
yarıya iner; hiçbir şey değişmez. Fiyat tek başına bir bilgi taşımaz.""",
 ornek="""EREGL 38,36 TL, THYAO 300,25 TL. Hangisi büyük şirket?
EREGL: 38,36 × 6,72 milyar adet = 258 milyar TL
THYAO: 300,25 × 1,38 milyar adet = 412 milyar TL
Fiyatı 8 kat düşük olan şirket, değerinin yarısından fazlası kadar büyük.
Fiyat sana şirket hakkında hiçbir şey söylemedi.""",
 sorular=["t01", "t05"], sure=7),

Ders("d102", "Fiyat nasıl oluşur: emir defteri",
 "Fiyatı kimsenin 'belirlemediğini', alıcı ve satıcının eşleşmesinden doğduğunu görmek.",
 """Borsada bir "fiyat belirleyici" yoktur. Fiyat, EMİR DEFTERİNDE oluşur.

Emir defteri iki taraflıdır:
· ALIŞ tarafı — almak isteyenler, ödemeye razı oldukları fiyatlarla
· SATIŞ tarafı — satmak isteyenler, kabul ettikleri fiyatlarla

Örnek defter (THYAO):
    SATIŞ    299,75 → 4.200 adet
    SATIŞ    299,50 → 1.800 adet
    ─────────────────────────────  ← makas (spread)
    ALIŞ     299,25 → 2.500 adet
    ALIŞ     299,00 → 6.100 adet

En iyi alış 299,25; en iyi satış 299,50. Aradaki 0,25 TL'ye MAKAS (spread) denir.
Şu an işlem YOKTUR — kimse karşı tarafın fiyatını kabul etmiyor.

İşlem nasıl olur: biri sabırsızlanır. Bir alıcı "299,50'yi kabul ediyorum" derse,
işlem 299,50'den gerçekleşir ve "son fiyat" o olur. Fiyat YÜKSELMİŞ olur.

Buradan çıkan en önemli sezgi: fiyat yükseliyorsa, alıcılar satıcılardan daha
sabırsız demektir. Fiyat düşüyorsa satıcılar daha sabırsız. "Alıcı çok" ya da
"satıcı çok" değil — her işlemde bir alıcı ve bir satıcı vardır, sayıları
eşittir. Belirleyici olan SABIRSIZLIKTIR.

DERİNLİK, her fiyat seviyesindeki emir miktarıdır. Derin bir defterde büyük
emirler fiyatı oynatmaz. Sığ bir defterde küçük bir emir fiyatı uçurur — BIST'te
küçük şirketlerde manipülasyonun teknik zemini budur.""",
 bist="""BIST'te FİYAT ADIMI (kademe) vardır — fiyat istediğin her değeri
alamaz:
    0,01 – 19,90 TL  →  adım 0,01
   20,00 – 49,98 TL  →  adım 0,02
   50,00 – 99,95 TL  →  adım 0,05
  100,00 TL ve üstü  →  adım 0,10

Yani 100 TL'lik bir hissede en dar makas 0,10 TL = %0,1'dir. Bu, işlem başına
görünmez bir maliyettir ve sık işlem yapanı yer.

Midas'ta BIST komisyonu SIFIR — ama makas sıfır değildir. "Bedava işlem" diye
bir şey yoktur.""",
 tuzak=""""Hacim yüksek, demek ki alan çok" — hayır. Her işlemde alıcı ve satıcı
BİRER tanedir. Hacim, el değiştiren miktarı gösterir, yönü değil. Yükselirken
yüksek hacim alıcı iştahını, düşerken yüksek hacim satıcı paniğini gösterir —
ama hacmin kendisi yön bilgisi taşımaz.""",
 ornek="""Günlük 20 milyon TL işlem gören bir hissede 1.000 TL'lik emrin
defterin en üst kademesinde bile kaybolur — fiyata etkisi yoktur.
Günlük 500 bin TL işlem gören bir hissede aynı emir, kademeleri süpürüp fiyatı
%1-2 oynatabilir. Alması kolay, satması zordur. Bu sistemin 20 milyon TL hacim
filtresi tam bu yüzden var.""",
 sorular=["t02"], sure=8),

Ders("d103", "Emir türleri ve hangisi ne zaman",
 "Doğru emir türünü seçmenin, doğru hisseyi seçmek kadar para kazandırdığını anlamak.",
 """PİYASA EMRİ — "ne olursa olsun şimdi al/sat". Defterdeki en iyi fiyattan
başlayarak kademeleri süpürür. Kesin gerçekleşir ama FİYATI SEN BELİRLEMEZSİN.
Likit olmayan hissede beklediğinden çok kötü fiyat alabilirsin.

LİMİT EMRİ — "en fazla 300,00'dan al" ya da "en az 305,00'a sat". Fiyatı
kontrol edersin, ama emrin gerçekleşmeyebilir. Fiyat hiç o seviyeye gelmezse
emrin bekler.

Küçük sermayede neredeyse her zaman LİMİT kullan. Sebep: piyasa emriyle
kaybedeceğin 0,25 TL, 100 TL'lik pozisyonda %0,25'tir — bir yılda 50 işlem
yaparsan %12,5 eder.

STOP (ZARAR DURDUR) — "fiyat 285'e düşerse sat" demektir. Fiyat o seviyeye
değdiğinde emir AKTİFLEŞİR ve piyasa emrine dönüşür. Zararı sınırlamak için
kullanılır.

STOP-LİMİT — stop tetiklendiğinde piyasa değil LİMİT emri girer. "285'e
düşerse, ama 280'in altına satma" der. Kötü fiyattan satılmayı engeller, ama
hızlı çöküşte hiç satamama riski taşır.

Hangi durumda hangisi:
· Normal alım → limit
· Acil çıkış (haber çıktı, tez bozuldu) → piyasa
· Zarar koruması → stop
· Çok oynak hissede zarar koruması → stop-limit (ama boşluk riskini bil)""",
 bist="""Midas'ta 4 emir türü var. İZ SÜREN (trailing) STOP YOKTUR — yani
"fiyat yükseldikçe stop'u otomatik yukarı çek" diyemezsin. Bu işi elle yapman
gerekir; bu sistemin `portfoy` komutu her gün "stop'u 36,38 → 38,10 yukarı çek"
diye hatırlatır.

KAPANIŞ SEANSI: 18:00-18:10 arası tek fiyat seansı vardır ve fiyat sınırı
±%3'tür. Gün içindeki son fiyat ile kapanış fiyatı farklı olabilir; endeksler
kapanış fiyatından hesaplanır.""",
 tuzak="""STOP GARANTİ DEĞİLDİR ve bu, yeni yatırımcının en pahalı yanılgısıdır.

Hisse stop seviyenin ALTINDA açılırsa (gece gelen kötü haber), emrin o düşük
fiyattan gerçekleşir. Bu sistemin backtestinde en kötü işlemler tam olarak
bunlar: %12-20 kayıp, stop 2×ATR (~%5) olmasına rağmen.

BIST'te günlük tavan/taban ±%20. Bir gecede bu kadar boşluk gerçektir.
"Stop koydum, riskim %2" cümlesi yanlıştır. Doğrusu: "normal koşullarda %2".""",
 ornek="""Stop'un 285,00. Gece şirketle ilgili kötü haber çıktı.
Ertesi gün hisse 258,00'den açtı. Stop emrin 285'te bekliyordu ama fiyat oraya
uğramadı — 258'den aktifleşip 258 civarında gerçekleşti.
Beklediğin kayıp: %5. Gerçekleşen: %14.
Bu yüzden pozisyon boyutu, stop mesafesine göre değil, DAYANABİLECEĞİN EN KÖTÜ
senaryoya göre ayarlanır.""",
 sorular=["t02"], sure=8),

Ders("d104", "Seanslar, tavan-taban ve tedbirler",
 "BIST'in gün içi ritmini ve fiyatın hangi kurallarla sınırlandığını öğrenmek.",
 """BIST Pay Piyasası günü:

09:40-09:55  Açılış emir toplama — emirler girilir, işlem OLMAZ
09:55-10:00  Açılış eşleştirme — tek fiyat hesaplanır
10:00-18:00  Sürekli işlem — normal alım satım
18:00-18:10  Kapanış seansı — tek fiyat, ±%3 sınır
18:10-18:15  Kapanış fiyatından işlemler

TEK FİYAT (açılış/kapanış) nasıl çalışır: tüm emirler toplanır, en çok işlemi
gerçekleştirecek TEK fiyat hesaplanır ve o fiyattan hepsi eşleşir. Bu yüzden
açılış fiyatı, önceki kapanıştan çok uzak olabilir — gece biriken emirler tek
seferde boşalır.

FİYAT SINIRLARI (tavan-taban): bir hisse gün içinde referans fiyatının belirli
bir yüzdesinden fazla oynayamaz.
· Yıldız Pazar ve Ana Pazar Grup 1 → ±%20
· Ana Pazar Grup 2, GİP, YİP → ±%10
· Kapanış seansında → ±%3

Referans fiyat genelde önceki gün ağırlıklı ortalama fiyattır.

VBTS (Volatilite Bazlı Tedbir Sistemi): anormal fiyat/hacim hareketi görülen
hisselere otomatik tedbir uygulanır. Kademeli olarak:
· Açığa satış ve kredili işlem yasağı
· Brüt takas (aşağıda anlatılıyor)
· Emir iptalinin yasaklanması
· Tek fiyat işlem (sürekli işlem kapatılır)

Tedbirler genelde 1 ay sürer ve KAP'ta duyurulur.""",
 bist="""BRÜT TAKAS en çok atlanan kuraldır ve seni doğrudan etkiler.

Normal koşulda: gün içinde bir hisse satarsan, gelen parayla AYNI GÜN başka
hisse alabilirsin. Midas bunu açıkça belirtir.

Brüt takas uygulanan hissede: satıştan gelen para en erken T+1'de kullanılabilir.
Yani paran bir gün bloke kalır.

Sinsi tarafı şu: brüt takasa alınan hisseler tam da yüksek oynaklıklı,
"hareketli" hisselerdir — yani bir botun ya da acemi yatırımcının seçmeye
meyilli olduğu hisseler. Bu sistemin ATR %7 filtresi çoğunu eler, ama emir
girmeden önce hissenin tedbirli olup olmadığını KAP'tan kontrol etmelisin.""",
 tuzak=""""Tavan yaptı, yarın da yapar" — tavan bir momentum göstergesi değil,
bir SINIRDIR. Tavanda alıcı kuyruğu birikmişse ertesi gün açılış boşluklu
gelir ve senin emrin gerçekleşmez; gerçekleşirse de zirveden almış olursun.

Bu sistem, gün içi +%9 üstü kapanan hisseleri ertesi gün ALMAZ. Sebebi ölçüm:
tavana yakın kapanışlarda ertesi günkü giriş fiyatı öngörülemez.""",
 ornek="""Bir hisse gün içi %19,5 yükselerek kapandı (tavana yakın).
Ertesi gün açılış tek fiyat seansında %12 yukarıdan açtı.
Senin "dünkü kapanıştan alırım" planın çöktü — %12 daha pahalıya aldın ve
stop mesafen aynı kaldı. Aynı risk bütçesiyle çok daha az adet alabildin.""",
 sure=8),

Ders("d105", "Takas, T+2 ve paranın gerçekte ne zaman senin olduğu",
 "Sattığın paranın ne zaman kullanılabilir, ne zaman çekilebilir olduğunu bilmek.",
 """Borsada işlem anında el değiştirmez. TAKAS süreci vardır.

BIST Pay Piyasası'nda takas T+2'dir: bugün yaptığın işlemin hisse ve para
transferi 2 iş günü sonra tamamlanır.

Ama pratikte üç ayrı "kullanılabilirlik" vardır ve karıştırılır:

1) YENİ ALIM İÇİN — gün içinde sattığın hissenin parasıyla aynı gün başka
   hisse alabilirsin. (Brüt takas hisseleri hariç.)
2) PARA ÇEKME İÇİN — T+2 beklemen gerekir. Satış parası hesabında görünse bile
   çekemezsin.
3) DÖVİZ/FON ALIMI İÇİN — genelde çekme ile aynı kurala tabidir.

Midas'ın "Anında Nakit" hizmeti, takasta bekleyen bakiyeyi hemen kullanılabilir
hale getirir. Bedeli: günlük %0,25 + BSMV. Takasa 2 gün kaldıysa %0,5 civarı
bir maliyet demektir — bu, kısa vadeli bir işlemin tüm kârını yiyebilir.""",
 bist="""Bu kural, "günde %5 kazanırım" hayalinin teknik duvarlarından biridir.

Sermayeni her gün tam olarak döndüremezsin: sattığın parayla aynı gün alım
yapabilirsin ama brüt takas hisselerinde yapamazsın, ve para çekmek istersen
2 gün beklersin.

Ayrıca temettü hakkı takas tarihine göre belirlenir: temettü hak kullanım
tarihinde hisseyi TAKASINDA bulundurman gerekir, sadece o gün almış olman
yetmeyebilir.""",
 tuzak=""""Hesabımda para görünüyor, çekebilirim" — görünen bakiye ile
çekilebilir bakiye farklıdır. Midas'ta bu iki rakam ayrı gösterilir; karıştırıp
ödeme planı yapmak sıkıntı yaratır.""",
 sure=5),

Ders("d106", "Endeksler nasıl hesaplanır",
 "BIST 100'ün ne ölçtüğünü ve neden 'piyasa' ile aynı şey olmadığını anlamak.",
 """BIST 100, en yüksek fiili dolaşım piyasa değerine sahip 100 şirketin
PİYASA DEĞERİ AĞIRLIKLI endeksidir.

"Ağırlıklı" ne demek: her hissenin endekse etkisi, büyüklüğüyle orantılıdır.
Endeksin %8'ini oluşturan bir hisse %10 yükselirse endeksi %0,8 yukarı taşır.
Endeksin %0,3'ünü oluşturan bir hisse %10 yükselirse etkisi %0,03'tür.

"Fiili dolaşım" (free float) ne demek: şirketin tamamı değil, borsada gerçekten
işlem gören kısmı sayılır. Ana ortakların elindeki bloke paylar hariç tutulur.
Sebep: o paylar alınıp satılamadığı için piyasa fiyatını temsil etmezler.

Endeks dönemleri: Ocak-Mart, Nisan-Haziran, Temmuz-Eylül, Ekim-Aralık. Her
dönem başında bileşenler revize edilir — bazı hisseler girer, bazıları çıkar.

Kritik sonuç: BIST 100 "piyasa" demek değildir. En büyük 10 şirket endeksin
yarısına yakınını oluşturur. Endeks %2 yükselirken hisselerin çoğu düşmüş
olabilir — birkaç dev yukarı çekiyordur.

Sektör endeksleri (XBANK, XUSIN...) aynı mantıkla, o sektördeki şirketlerden
hesaplanır.""",
 bist="""Bu sistem sektör endekslerini BİLEŞENLERDEN kendisi kurar. Sebep
teknik: veri sağlayıcı (yfinance) BIST sektör endekslerinin sadece 1 günlük
geçmişini taşıyor — XUTEK, XGIDA, XKMYA gibi 14 endeksin geçmişi YOK. Sadece
XU100 ve XBANK gerçek geçmişe sahip.

Bu yüzden 99 hissenin fiyatı sektörlerine göre gruplanıp piyasa değeri
ağırlıklı seri kuruluyor. Sonuç aynı mantıkla üretiliyor, ama ağırlıklandırma
şeffaf.""",
 tuzak=""""Endeks yükseldi, portföyüm de yükselmeli" — endeks birkaç büyük
hissenin ortalamasıdır. Sen küçük ve orta ölçekli hisse tutuyorsan endeksle
ilgin sınırlıdır.

Ayrıca: "BIST 100 yılda %28 getirdi" cümlesi, enflasyon %31,8 iken bir başarı
DEĞİLDİR. Endeksi mutlaka reel olarak oku.""",
 ornek="""BIST 100 son 1 yılda %28,1 arttı. Enflasyon %31,8.
Reel getiri: -%3,5. Endekse yatırım yapan biri, alım gücü olarak fakirleşti.
Nominal sayı büyüdüğü için bunu fark etmek zordur — bu sistemin `makro`
komutu her seferinde reel rakamı yazar, tam bu yüzden.""",
 sure=6),

Ders("d107", "Halka arz, bedelli ve bedelsiz",
 "Şirketin sermaye hareketlerinin senin payını nasıl değiştirdiğini anlamak.",
 """HALKA ARZ (IPO): şirket ilk kez halka pay satar. İki türü var:
· Sermaye artırımı yoluyla — yeni pay çıkarılır, para ŞİRKETE girer
· Ortak satışı yoluyla — mevcut ortak payını satar, para ORTAĞA gider

Fark önemlidir: birincisinde şirket yatırım için para toplar, ikincisinde ana
ortak nakde çıkar. İkincisi her zaman kötü değildir ama sorulması gereken soru
şudur: içeriden bilgisi olan biri neden satıyor?

İKİNCİL HALKA ARZ: zaten borsada olan şirketin yeni pay satması.

BEDELSİZ SERMAYE ARTIRIMI: şirket iç kaynaklarını (geçmiş yıl kârları, yeniden
değerleme fonu) sermayeye ekler. Elindeki adet artar, fiyat aynı oranda düşer.
Toplam değerin DEĞİŞMEZ.
  100 TL'lik 1 hisse → %100 bedelsiz → 50 TL'lik 2 hisse
Zenginleşmedin. Tek gerçek faydası likidite artışı ve psikolojik algı.

BEDELLİ SERMAYE ARTIRIMI: şirket yeni pay çıkarır ve SATAR. Mevcut ortaklara
öncelik hakkı (rüçhan) verilir.
· Katılırsan: para koyarsın, payın korunur
· Katılmazsan: payın SULANIR (dilution)

Bedellide sorulacak tek soru: bu para NEREYE gidecek?
· Yeni fabrika, kapasite, satın alma → yatırım, getirisi olabilir
· Borç kapatma, işletme sermayesi açığı → tehlike sinyali""",
 bist="""BIST'te bedelsiz duyuruları hisseleri sert hareket ettirir ve bu,
mekanik olarak anlamsızdır. Sebep davranışsal: yatırımcı "hisse ucuzladı" diye
algılar. Fiyat düştü ama sende iki katı adet var — hiçbir şey değişmedi.

Bu sistem geçmiş fiyatları `auto_adjust=True` ile çeker: bedelsiz ve temettü
düzeltmesi yapılmış fiyat kullanılır. Yapılmasaydı backtest, bedelsiz günlerini
%50'lik çöküş sanardı.""",
 tuzak=""""Bedelsiz veriyor, alalım" — bedelsiz hiçbir değer yaratmaz. Muhasebe
kalemleri arasında transferdir. Şirket bedelsiz verebiliyor diye daha iyi
olmuş olmaz.

"Bedelli var, kaçalım" da yanlış. Bedellinin iyi mi kötü mü olduğunu paranın
kullanım amacı belirler.""",
 ornek="""Şirket %100 bedelsiz + %50 bedelli açıkladı.
100 adet hissen var, fiyat 40 TL. Toplam 4.000 TL.
Bedelsiz sonrası: 200 adet, 20 TL. Toplam yine 4.000 TL.
Bedelli: 200 adedin %50'si = 100 yeni pay, 1 TL nominalden. 100 TL ödersin.
Sonuç: 300 adet, 4.100 TL yatırım. Payın korundu.
Katılmasaydın: 200 adet kalırdı, şirketin toplam payı 300'e çıktığı için
oransal payın üçte bir azalırdı.""",
 sure=8),

Ders("d108", "Temettü mekanizması",
 "Temettünün neden 'bedava para' olmadığını ve ne zaman değerli olduğunu anlamak.",
 """Şirket kâr eder. Yönetim iki seçenekle karşı karşıyadır:
1) Kârı şirkette tut ve yatırıma çevir
2) Ortaklara nakit dağıt (temettü)

Doğru seçim şuna bağlıdır: şirket o parayı, ortağın kendisinden DAHA İYİ
değerlendirebilir mi? Yatırımın getirisi sermaye maliyetinin üstündeyse
tutmalı; değilse dağıtmalı.

Mekanik: temettü dağıtım gününde hisse fiyatı temettü kadar DÜŞER. Şirketin
kasasından çıkan para, şirketin değerinden de çıkar. Elindeki toplam değer
değişmez — bir kısmı hisseden nakde dönmüştür.

Peki neden önemli:
· DİSİPLİN — nakdi dağıtan yönetim, onu kötü satın almalara harcayamaz
· SİNYAL — düzenli nakit temettü, kârın gerçek ve nakit olduğunun kanıtıdır.
  Kâğıt üstünde kâr yazan ama nakit üretmeyen şirket temettü ödeyemez.
· ÖNGÖRÜLEBİLİRLİK — düzenli gelir isteyen yatırımcı için

Temettü verimi = yıllık temettü / hisse fiyatı. Bu oran MEVDUAT FAİZİYLE
kıyaslanmalıdır — ikisi de aynı soruyu cevaplar.""",
 bist="""Türkiye'de vergi asimetrisi vardır:
· Hisse ALIM-SATIM kazancı → bireysel yatırımcı için stopaj %0
· TEMETTÜ → stopaj vardır

Yani vergi açısından temettü dezavantajlıdır. Bu, yüksek temettü stratejisinin
Türkiye'de gelişmiş ülkelerdeki kadar cazip olmamasının bir sebebidir.

İkinci ve daha büyük sebep: mevduat faizi %40 civarındayken %3'lük temettü
verimi bir çekicilik değildir. Temettü hisselerinin cazip olduğu ortam, düşük
faiz ortamıdır.""",
 tuzak=""""Yüksek temettü verimi = iyi hisse" — verim bir KESİRDİR ve paydası
fiyattır. Fiyat çöktüğü için verim yükselmiş olabilir. Şirket temettüyü
sürdüremeyecekse, yüksek verim bir tuzaktır.

Kontrol edilecek: dağıtım oranı (payout ratio). Şirket kârının %100'ünden
fazlasını dağıtıyorsa, bunu borçlanarak yapıyordur ve sürdürülemez.""",
 ornek="""Hisse 100 TL, şirket 5 TL temettü dağıttı.
Dağıtım günü hisse 95 TL'ye düşer. Elinde 95 TL hisse + 5 TL nakit = 100 TL.
Kazanmadın. Ama 5 TL artık senin kontrolünde — istersen başka yere koyarsın.
Değeri buradadır: sermaye dağıtım kararı yönetimden sana geçti.""",
 sorular=["t12", "u11"], sure=7),

Ders("d109", "Açığa satış, kredili işlem ve kaldıraç",
 "Kaldıracın neden asimetrik olduğunu ve küçük sermayede neden ölümcül olduğunu görmek.",
 """AÇIĞA SATIŞ: sahip olmadığın hisseyi ödünç alıp satmak, sonra daha ucuza
geri alıp iade etmek. Düşüşten kazanmanın yoludur.

Risk asimetriktir ve bu kritiktir:
· Alımda en fazla %100 kaybedersin (hisse sıfırlanır)
· Açığa satışta kayıp SINIRSIZDIR — hisse %300 yükselirse %300 kaybedersin

Ayrıca ödünç maliyeti, temettü yükümlülüğü ve "çağrı" riski vardır: ödünç veren
hisseyi geri isterse pozisyonu kapatmak zorunda kalırsın — hem de en kötü anda.

KREDİLİ İŞLEM (margin): aracı kurumdan borç alıp daha fazla hisse almak.
Kaldıraç kârı da zararı da çarpar.

2 kat kaldıraçta hisse %10 düşerse sen %20 kaybedersin. Ve teminat oranın
belirli seviyenin altına inerse TEMİNAT TAMAMLAMA ÇAĞRISI gelir: ya para
yatırırsın ya da pozisyonun zorla kapatılır — genelde tam dipte.

Kaldıracın gerçek tehlikesi buradadır: haklı olsan bile, YOLDA ZORLA
ÇIKARILABİLİRSİN.""",
 bist="""BIST'te açığa satış izne ve teminata tabidir; VBTS tedbiri olan
hisselerde tamamen yasaklanır. Midas'ta bireysel açığa satış pratikte yoktur.

Kredili işlem faizi Midas'ta 250.000 TL'ye kadar yıllık %66,5 civarındadır.
Bu, kredinin getirmesi gereken minimum getiriyi düşün: %66,5'i geçmeyen her
kredili işlem, matematiksel olarak zarardır.

Bu sistem SADECE uzun taraf çalışır. Düşüşte kazanmaz — nakde geçer.""",
 tuzak=""""Bu hisse çok şişti, kesin düşer, açığa satayım" — piyasa, senin
ödeme gücünün tükendiğinden daha uzun süre mantıksız kalabilir. Keynes'e
atfedilen bu söz, açığa satışta ölümcül derecede doğrudur.

Küçük sermayede kaldıraç kullanmak, hayatta kalma süreni kısaltır. Öğrenme
sermayeni korumak, kazanç kovalamaktan önemlidir.""",
 sure=7),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 2 — FİNANSAL TABLOLARI OKUMAK
# ═══════════════════════════════════════════════════════════════════

M2 = Modul("m2", "Finansal tabloları okumak",
           "Üç tablo, hangi soruyu cevapladıkları ve nerede yalan söyleyebildikleri. "
           "Analistliğin gerçek zemini burasıdır.", 1, [

Ders("d201", "Üç tablo ve hangi soruyu cevapladıkları",
 "Gelir tablosu, bilanço ve nakit akışının farklı sorulara cevap verdiğini görmek.",
 """Bir şirketi anlamak için üç tablo vardır ve her biri FARKLI bir soru
cevaplar. Karıştırmak, analizin en sık kaynağıdır.

GELİR TABLOSU — "bu dönemde ne kadar kazandı?"
Bir ZAMAN ARALIĞINI anlatır (çeyrek ya da yıl). Satış yapıldığında gelir
yazılır — para tahsil edilmese bile. Bu yüzden kâr, bir muhasebe kavramıdır.

BİLANÇO — "şu ANDA neye sahip, ne borçlu?"
Belirli bir TARİHTEKİ fotoğraftır. Temel denklem her zaman geçerlidir:
    Varlıklar = Borçlar + Özsermaye
Sol taraf "neye sahibim", sağ taraf "bunu kimin parasıyla aldım".

NAKİT AKIŞ TABLOSU — "para gerçekte nereye gitti?"
Üç bölümü vardır:
· FAALİYETLERDEN — ana işten gelen/giden nakit
· YATIRIMDAN — fabrika, makine, şirket alımı (genelde negatif)
· FİNANSMANDAN — borç alma/ödeme, temettü, sermaye artırımı

En zor manipüle edilen tablo budur. Kâr bir karardır; nakit ya vardır ya yoktur.

Nasıl birlikte okunur: gelir tablosu performansı, bilanço sağlamlığı, nakit
akışı gerçekliği gösterir. Üçü çelişiyorsa, nakde güven.""",
 bist="""BIST şirketleri finansallarını KAP'ta yayınlar. Dönemler:
· 1. çeyrek → Mayıs başı
· 2. çeyrek (6 aylık) → Ağustos başı
· 3. çeyrek (9 aylık) → Kasım başı
· Yıllık → Mart başı

Çeyrek raporlar SINIRLI DENETİMDEN geçer, yıllık rapor TAM DENETİMDEN. Yani
yıllık rapor daha güvenilirdir ve bazen çeyreklerde yazılan rakamlar yıl
sonunda düzeltilir.

Ayrıca ENFLASYON MUHASEBESİ: 2023'ten itibaren yüksek enflasyon nedeniyle
TMS-29 uygulanıyor. Geçmiş dönem rakamları bugünkü satın alma gücüne göre
düzeltiliyor. Bu, yıllar arası karşılaştırmayı ANLAMLI hale getirir ama
düzeltme öncesi rakamlarla kıyaslama yaparsan saçmalarsın.""",
 tuzak=""""Kâr açıkladı, iyi şirket" — hangi tablodan baktığını sor. Net kâr
tek başına en yanıltıcı satırdır: kur farkı, iştirak kârı, değerleme kârı,
tek seferlik satışlar hepsi oraya girer.

Bir analist önce FAALİYET KÂRINA bakar (ana işin performansı), sonra NAKİT
AKIŞINA (gerçek mi).""",
 sure=7),

Ders("d202", "Gelir tablosu: yukarıdan aşağı",
 "Cirodan net kâra inen merdiveni ve her basamağın ne anlattığını öğrenmek.",
 """Gelir tablosu bir merdivendir. Her basamakta bir şey düşülür:

HASILAT (ciro) — satılan mal/hizmetin toplam tutarı
  − Satılan Malın Maliyeti (SMM)
BRÜT KÂR — ürünün kendi maliyetinin üstünde ne kadar satabildiğin
  Brüt marj = brüt kâr / hasılat. Yüksekse FİYATLAMA GÜCÜ var demektir.
  − Pazarlama, satış, dağıtım giderleri
  − Genel yönetim giderleri
  − Ar-Ge giderleri
FAALİYET KÂRI — ANA İŞİN performansı. En dürüst satır burasıdır.
  + Diğer faaliyet gelirleri / − giderleri
  + Yatırım faaliyetlerinden gelirler (iştirak, satış kârı)
  + Finansman geliri / − finansman gideri (faiz, KUR FARKI)
VERGİ ÖNCESİ KÂR
  − Vergi
NET KÂR

FAVÖK (EBITDA) = Faaliyet kârı + Amortisman + İtfa payları
Nakit çıkışı olmayan kalemleri geri ekler. Sermaye yoğun sektörlerde işletme
performansını görmek için kullanılır — ama nakit akışı DEĞİLDİR.

Okuma sırası: önce marjların TRENDİNE bak (3 yıl), sonra hangi basamakta
bozulma olduğunu bul. Bozulma brüt marjda ise fiyatlama/maliyet sorunu
(kalıcı olma ihtimali yüksek). Faaliyet giderlerinde ise yatırım olabilir.""",
 bist="""Türkiye'de FİNANSMAN GİDERİ satırı, gelişmiş ülkelere göre çok daha
belirleyicidir. İki sebep:
· Faiz yüksek — borçlanma maliyeti ağır
· KUR FARKI bu satıra girer — dövizli borcu olan şirkette TL değer kaybederse
  buraya devasa bir zarar yazılır

Sonuç: BIST'te bir şirketin faaliyet kârı mükemmel olup net kârı negatif
olabilir. Bunun tersi de olur: ana işi kötüyken kur farkı GELİRİ ile net kâr
patlar.

Bu yüzden BIST'te faaliyet kârı, net kârdan daha güvenilir bir performans
göstergesidir.""",
 tuzak=""""Net kâr %80 arttı" manşetine atlamak. Nereden geldiğini sor:
· Faaliyet kârı da arttı mı? → gerçek
· Sadece net kâr arttı mı? → kur farkı, tek seferlik satış, iştirak kârı

Faaliyet kârı düşerken net kâr artıyorsa, artış ana işten GELMİYOR demektir ve
gelecek yıl tekrarlanmayabilir.""",
 ornek="""Bir şirketin cirosu %50 arttı, net kârı %10.
Merdiveni in:
· Brüt marj %35 → %28 düştü mü? Girdi maliyeti fiyata geçirilememiş.
· Brüt marj sabit ama faaliyet marjı düştü mü? Pazarlama/personel gideri artmış.
· İkisi de sabit ama net kâr düşük mü? Finansman gideri veya kur farkı.
Her senaryo farklı bir hikâye anlatır ve farklı karar gerektirir.""",
 sorular=["t10", "o01", "o05"], sure=9),

Ders("d203", "Bilanço: neye sahip, ne borçlu",
 "Bilançonun iki tarafını ve hangi kalemlerin tehlike sinyali olduğunu okumak.",
 """Bilanço iki taraflıdır ve her zaman eşittir:

VARLIKLAR (ne var)            KAYNAKLAR (kimin parasıyla)
─────────────────────         ─────────────────────────────
Dönen varlıklar               Kısa vadeli yükümlülükler
  Nakit ve benzerleri           Ticari borçlar
  Ticari alacaklar              Kısa vadeli finansal borç
  Stoklar                     Uzun vadeli yükümlülükler
Duran varlıklar                 Uzun vadeli finansal borç
  Maddi duran varlık          ÖZSERMAYE
  Maddi olmayan (şerefiye)      Ödenmiş sermaye
  İştirakler                    Geçmiş yıl kârları

Okurken bakılacaklar:

1) ALACAKLAR ciroya göre hızlı büyüyor mu? Şirket satıyor ama tahsil edemiyor
   olabilir. Alacak devir hızı = hasılat / ortalama ticari alacak.
2) STOKLAR ciroya göre hızlı büyüyor mu? Mal satılmıyor olabilir; ileride
   değer düşüklüğü yazılır.
3) ŞEREFİYE (goodwill) büyük mü? Şirket pahalıya satın alma yapmış demektir.
   İşler kötüleşirse tek kalemde silinir ve özsermaye çöker.
4) KISA VADELİ BORÇ, dönen varlıkları aşıyor mu? Cari oran < 1 = nakit
   sıkışıklığı riski.
5) ÖZSERMAYE eriyor mu? Zarar eden şirkette özsermaye her yıl azalır.

Ve en önemlisi: BORCUN PARA BİRİMİ ve VADESİ. Bu bilgi bilançonun kendisinde
değil, DİPNOTLARDA yazar.""",
 bist="""Türkiye'de dipnotlar, bilançonun kendisinden daha kritiktir. Orada
şunlar yazar:
· Net döviz pozisyonu (dövizli varlık − dövizli yükümlülük)
· Borcun vade dağılımı
· Faiz tipi (sabit/değişken)
· İlişkili taraf işlemleri (ana ortakla yapılan alışverişler)
· Teminat, rehin, kefaletler

"Net döviz pozisyonu" kalemi, kur hareketinde şirketin ne kadar etkileneceğini
söyleyen TEK sayıdır ve bilançonun ön yüzünde görünmez.

Otomatik veri sağlayıcılar (bu sistem dahil) dipnotları okumaz. O kısım senin
işindir — KAP'tan tam rapora bakman gerekir.""",
 tuzak=""""Şirketin çok varlığı var, sağlam" — varlıkların NASIL finanse
edildiğine bakmadan bu söylenemez. 10 milyar varlığı olan şirketin 9 milyar
borcu varsa, özsermayesi 1 milyardır ve küçük bir değer kaybı onu silebilir.

Ayrıca varlıkların KALİTESİ: nakit ile şerefiye aynı şey değildir. Şerefiye
satılamaz, teminat gösterilemez, kriz anında işe yaramaz.""",
 sorular=["o03", "o04", "t09"], sure=9),

Ders("d204", "Nakit akış tablosu: en zor yalan söyleyen tablo",
 "Kârın nakde dönüp dönmediğini görmeyi ve kâr kalitesini ölçmeyi öğrenmek.",
 """Nakit akış tablosu üç bölümdür:

1) FAALİYETLERDEN NAKİT AKIŞI
   Net kârdan başlar, nakit olmayan kalemleri geri ekler (amortisman,
   karşılıklar), işletme sermayesi değişimini düzeltir.
   Sağlıklı şirkette bu POZİTİF ve net kâra yakın olmalıdır.

2) YATIRIM FAALİYETLERİNDEN
   Capex (fabrika, makine), şirket alımları, finansal yatırımlar.
   Büyüyen şirkette NEGATİF olur — bu normaldir, hatta iyidir.

3) FİNANSMAN FAALİYETLERİNDEN
   Borç alma/ödeme, sermaye artırımı, temettü ödemesi.

SERBEST NAKİT AKIŞI (FCF) = Faaliyetlerden nakit − Capex
Şirketin işini sürdürdükten sonra elinde GERÇEKTEN kalan para. Temettü buradan
ödenir, borç buradan kapatılır.

KÂR KALİTESİ ORANI = Faaliyetlerden nakit / Net kâr
· 1'in üstü → kâr nakde dönüyor, sağlıklı
· Sürekli 1'in altı → kâr kâğıt üstünde kalıyor, ŞÜPHELİ

Neden bu oran bu kadar önemli: muhasebe kârını şişirmenin yasal yolları vardır
(gelir tanıma zamanlaması, karşılık ayırma, amortisman yöntemi). Ama bankadaki
parayı şişiremezsin.

Şirketler zarar ettiği için değil, NAKİTSİZ kaldığı için batar.""",
 bist="""BANKADA BU ORAN ANLAMSIZDIR ve bu, otomatik analiz araçlarının sık
düştüğü tuzaktır.

Bankada faaliyet nakit akışı, mevduat ve kredi hareketlerinden oluşur. Banka
kredi verdiğinde nakit çıkışı, mevduat topladığında nakit girişi olur — bunlar
kârlılıkla ilgili değil, bilanço büyümesiyle ilgilidir.

Sağlıklı ve kârlı bir banka rutin olarak negatif faaliyet nakit akışı
gösterebilir. Bu sistem, banka sektöründe kâr kalitesi oranını KAPATIR.

İkinci istisna: net kâr sıfıra çok yakınsa oran patlar. EREGL örneğinde net
marj %0,24 iken oran 127x çıkıyor — bu bilgi değil, sıfıra bölme artefaktıdır.
Sistem bu durumda da oranı geçersiz sayar.""",
 tuzak=""""FAVÖK nakit akışıdır" — HAYIR. FAVÖK şunları içermez:
· Capex (yatırım harcaması)
· İşletme sermayesi değişimi
· Vergi
· Faiz ödemesi

Sermaye yoğun bir şirkette FAVÖK yüksek, serbest nakit akışı NEGATİF olabilir.
FAVÖK bir kârlılık ölçüsüdür, nakit ölçüsü değil.""",
 ornek="""Şirket 3 yıl üst üste:
  Net kâr:              800 mn → 1.100 mn → 1.400 mn  (harika görünüyor)
  Faaliyetlerden nakit: 600 mn →   500 mn →   300 mn  (çöküyor)
  Oran:                 0,75  →  0,45   →   0,21

Kâr artıyor, nakit azalıyor. Muhtemel sebep: alacaklar şişiyor (satıyor ama
tahsil edemiyor) ya da kâr nakit olmayan kalemlerden geliyor.
Bu tablo bir ALARM'dır ve net kâra bakan biri onu hiç görmez.""",
 sorular=["t11", "o02", "o15"], sure=9),

Ders("d205", "İşletme sermayesi: sessiz nakit yiyici",
 "Büyümenin neden nakit yaktığını ve devir hızlarının ne anlattığını görmek.",
 """İŞLETME SERMAYESİ = Dönen varlıklar − Kısa vadeli yükümlülükler

Daha kullanışlı tanımı: şirketin günlük işini döndürmek için bağladığı para.

NAKİT DÖNÜŞÜM DÖNGÜSÜ üç parçadan oluşur:
· STOK DEVİR SÜRESİ — malı kaç günde satıyorsun
· ALACAK DEVİR SÜRESİ — sattıktan sonra kaç günde tahsil ediyorsun
· BORÇ DEVİR SÜRESİ — tedarikçine kaç günde ödüyorsun

Nakit döngüsü = Stok gün + Alacak gün − Borç gün

Bu sayı ne kadar KÜÇÜKSE o kadar iyi. Negatifse mükemmeldir: müşteriden parayı
tedarikçiye ödemeden önce alıyorsun demektir — tedarikçi seni finanse ediyor.

Neden büyüme nakit yakar: ciro %50 artarsa, stok ve alacak da yaklaşık %50
artar. Bu artış NAKİT gerektirir. Şirket kâr ediyor olsa bile nakit sıkışabilir.

Bu yüzden hızlı büyüyen şirketler sürekli finansmana muhtaçtır ve finansman
kapandığında büyüme onları öldürür.""",
 bist="""Perakendecilerin (BIM, Şok, Migros) iş modelinin sırrı buradadır:
müşteriden PEŞİN alır, tedarikçiye VADELİ öder. Nakit döngüleri negatiftir.

Bu, düşük net marjla (%2-3) çalışabilmelerinin sebebidir — sermaye devir hızları
çok yüksektir. Marja bakıp "kötü şirket" demek yanlış olur; ROIC'e bakmak gerekir.

Enflasyonist ortamda bu model ekstra avantajlıdır: eski maliyetle aldığın malı
yeni fiyattan satarsın ve tedarikçiye erimiş parayla ödersin.""",
 tuzak=""""Cari oran yüksek, likidite iyi" — cari oranın yüksek olması, dönen
varlıkların STOK ve ALACAKTAN oluşması durumunda iyi haber değildir. Satılamayan
stok ve tahsil edilemeyen alacak, cari oranı yükseltir ama şirketi kurtarmaz.

Bu yüzden ASİT-TEST (stoku düşerek hesaplanan) oranına da bakılır.""",
 ornek="""İki şirket, aynı ciro, aynı kâr:
A: stok 30 gün, alacak 20 gün, borç 60 gün → döngü −10 gün
B: stok 90 gün, alacak 75 gün, borç 30 gün → döngü +135 gün

B, işini döndürmek için 135 günlük ciro kadar parayı bağlamak zorundadır.
Büyüdükçe daha çok para bağlar. A ise büyüdükçe nakit ÜRETİR.
Aynı kârlılıkta iki şirket, tamamen farklı yatırımlardır.""",
 sure=8),

Ders("d206", "Muhasebe kırmızı bayrakları",
 "Rakamların 'teknik olarak doğru ama gerçeği gizliyor' olduğu durumları tanımak.",
 """Muhasebe hilesi genellikle yasadışı değildir — takdir yetkisinin sınırında
kullanılmasıdır. Tanınacak işaretler:

1) KÂR ARTARKEN NAKİT AZALIYOR
   En güçlü tek sinyal. Faaliyetlerden nakit / net kâr oranı sürekli düşüyorsa.

2) ALACAKLAR CİRODAN HIZLI BÜYÜYOR
   Ciro %20, alacak %60 büyüdüyse: ya vadeler uzatılarak satış zorlanmış, ya
   tahsilat bozulmuş.

3) STOKLAR CİRODAN HIZLI BÜYÜYOR
   Satılamayan mal birikiyor. İleride değer düşüklüğü karşılığı gelir.

4) SÜREKLİ "TEK SEFERLİK" KALEMLER
   Her yıl tek seferlik gider yazan şirkette o giderler artık tek seferlik
   değildir; ana işin parçasıdır.

5) MUHASEBE POLİTİKASI DEĞİŞİKLİĞİ
   Amortisman süresinin uzatılması, gelir tanıma yönteminin değişmesi. Kârı
   anında artırır. Dipnotlarda açıklanmak zorundadır.

6) AKTİFLEŞTİRME
   Gider yazılması gereken harcamanın (Ar-Ge, faiz) varlık olarak
   kaydedilmesi. Bugünkü kârı artırır, geleceğe amortisman yükü bırakır.

7) ŞEREFİYE BÜYÜYOR AMA KÂR BÜYÜMÜYOR
   Pahalı satın almalar yapılmış ve beklenen sinerji gelmemiş.

8) DENETÇİ DEĞİŞİKLİĞİ veya ŞARTLI GÖRÜŞ
   Bağımsız denetim raporunda "şartlı görüş" varsa mutlaka okunmalıdır.

9) İLİŞKİLİ TARAF İŞLEMLERİ BÜYÜK
   Şirket, ana ortağın diğer şirketleriyle çok iş yapıyorsa, fiyatların piyasa
   koşullarında olup olmadığı sorgulanır.""",
 bist="""BIST'te en sık görülen üç işaret:
· Kur farkı gelirinin net kârı taşıması (ana iş kötüyken kâr açıklama)
· Yatırım amaçlı gayrimenkul değerleme kârı (özellikle GYO'larda)
· İlişkili taraf işlemlerinin ağırlığı (holding yapılarında)

Ayrıca ENFLASYON MUHASEBESİ (TMS-29) geçişi, 2023 öncesi ve sonrası rakamları
doğrudan kıyaslanamaz hale getirdi. Büyüme hesaplarken hangi bazda olduğuna
dikkat et.""",
 tuzak=""""Denetimden geçmiş, o zaman doğrudur" — bağımsız denetim, tabloların
muhasebe standartlarına UYGUN olduğunu söyler. Şirketin iyi olduğunu değil,
rakamların gerçeği yansıttığını da tam olarak garanti etmez. Tarihteki büyük
muhasebe skandallarının hepsi denetimden geçmişti.""",
 sorular=["o02", "o04"], sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 3 — ORAN ANALİZİ
# ═══════════════════════════════════════════════════════════════════

M3 = Modul("m3", "Oran analizi",
           "Ham rakamları karşılaştırılabilir hale getirmek. Hangi oran hangi "
           "soruyu cevaplar ve hangi sektörde anlamsızlaşır.", 2, [

Ders("d301", "Kârlılık marjları ve ne anlattıkları",
 "Dört marjın farklı şeyler ölçtüğünü ve hangisinin ne zaman önemli olduğunu bilmek.",
 """Marj = kâr / hasılat. Dört basamak, dört farklı bilgi:

BRÜT MARJ = brüt kâr / hasılat
Ürünün kendi maliyetinin ne kadar üstünde satıldığı. Bu oran FİYATLAMA GÜCÜNÜN
doğrudan ölçüsüdür. Yüksekse: marka, teknoloji, konum ya da tekel avantajın var.
Düşükse: emtia gibi satıyorsun, fiyatı piyasa belirliyor.
En önemli özelliği: TRENDİ. Daralan brüt marj, rekabetin arttığının ilk
işaretidir ve genelde kalıcıdır.

FAALİYET MARJI = faaliyet kârı / hasılat
Ana işin performansı. Finansman ve tek seferlik kalemler hariç. Şirketi
şirket olarak değerlendiren en dürüst marj budur.

FAVÖK MARJI = FAVÖK / hasılat
Amortisman ve faiz öncesi nakit üretimi. Sermaye yoğun sektörlerde (sanayi,
telekom, havacılık) kıyaslama için kullanılır, çünkü amortisman politikası
şirketler arasında farklı olabilir.

NET MARJ = net kâr / hasılat
Cebe kalan. En çok dalgalanan ve en çok yanıltan marj. Kur farkı, tek seferlik
satış, vergi avantajı hepsi buraya girer.

Okuma kuralı: TEK BİR YILA BAKMA. Üç yıllık trende bak ve sektör medyanıyla
kıyasla. %3 net marj perakendede normal, yazılımda felakettir.""",
 bist="""Türkiye'de net marj, kur hareketleri yüzünden çeyrekten çeyreğe
uçar. Bir çeyrek %15, sonraki −%5 olabilir ve şirketin işi hiç değişmemiştir.

Bu yüzden BIST'te FAALİYET MARJI, net marjdan çok daha güvenilirdir.

Enflasyonist ortamda ikinci bir etki: nominal ciro şişer. Marj sabit görünse
bile REEL olarak daralmış olabilir. Marjı her zaman reel büyüme ile birlikte
oku.""",
 tuzak=""""Düşük marj = kötü şirket" — yanlış. Marj tek başına değil, DEVİR HIZI
ile birlikte anlam kazanır.

BIM'in net marjı ~%2,6'dır ve bu şirket son 10 yılın en başarılı BIST
hikâyelerinden biridir. Sebep: sermayeyi çok hızlı döndürür. ROIC'i yüksektir.

Formül: Getiri = Marj × Devir hızı. İkisinden biri yüksekse iş yürür.""",
 ornek="""EREGL (çelik): brüt marj %8,89 · faaliyet marjı %4,25 · net marj %0,24
Bir emtia üreticisinin marjları böyledir — fiyatı dünya piyasası belirler.
Net marjın %0,24 olması, bu şirketin döngünün DİBİNDE olduğunu söyler.
Bu bir "kötü şirket" bilgisi değil, "kötü zaman" bilgisidir. İkisini ayırmak
döngüsel sektör analizinin kalbidir.""",
 sorular=["t10", "o05", "t17"], sure=8),

Ders("d302", "ROE, ROA, ROIC ve DuPont",
 "Sermayenin ne kadar verimli çalıştığını ölçmeyi ve ROE'nin nasıl şişirildiğini görmek.",
 """ROE (Özsermaye Kârlılığı) = Net kâr / Özsermaye
Ortağın koyduğu paranın getirisi. Doğrudan senin getirin gibi düşünülebilir.

ROA (Aktif Kârlılığı) = Net kâr / Toplam varlık
Tüm varlıkların getirisi. Bankada doğal olarak düşüktür (kaldıraçlı iş modeli).

ROIC (Yatırılan Sermaye Getirisi) = Faaliyet kârı (vergi sonrası) /
                                     (Özsermaye + Net borç)
Borç dahil, işe yatırılan tüm sermayenin getirisi. ROE'den daha dürüsttür
çünkü KALDIRAÇLA ŞİŞİRİLEMEZ.

DUPONT AYRIŞTIRMASI — ROE'nin nereden geldiğini gösterir:

  ROE = Net Marj × Aktif Devir Hızı × Finansal Kaldıraç
        (kârlılık)  (verimlilik)      (borçluluk)

Bu formül neden önemli: iki şirketin ROE'si %25 olabilir ama biri yüksek
marjdan, diğeri yüksek borçtan geliyordur. İkincisi çok daha kırılgandır —
faiz yükseldiğinde ROE'si çöker.

DEĞER YARATMANIN TEK KOŞULU: ROIC > Sermaye maliyeti.
Bu koşul sağlanmıyorsa şirket büyüdükçe DEĞER YOK EDER — her yatırdığı lira,
geri getirdiğinden az kazandırır.""",
 bist="""Türkiye'de eşik çok yüksektir ve bu, gelişmiş ülke kitaplarından
öğrenilen sezgileri geçersiz kılar.

Enflasyon %31,8, mevduat faizi ~%40. Sermaye maliyeti bunların üstündedir.
Yani %25 ROIC ile büyüyen bir şirket, ABD'de yıldızdır — burada REEL OLARAK
DEĞER YAKIYOR olabilir.

Bu sistem kalite skorunda ROE ve ROIC eşiklerini enflasyona göre KAYDIRIR.
Ve şirket hangi para biriminde raporluyorsa o para biriminin enflasyonunu
kullanır: THYAO USD raporladığı için USD enflasyonuyla (~%3) kıyaslanır,
TL enflasyonuyla değil.""",
 tuzak=""""Yüksek ROE = iyi şirket" — ROE üç şekilde şişirilebilir:
1) BORÇLA — kaldıraç ROE'yi mekanik olarak yükseltir
2) HİSSE GERİ ALIMIYLA — özsermaye küçülür, payda düşer
3) ÖZSERMAYE ERİYEREK — zarar eden şirkette bir yıl kâr edilirse ROE patlar

Bu yüzden ROE'yi her zaman ROIC ile birlikte oku. Aralarındaki fark, kaldıracın
katkısıdır.""",
 ornek="""İki şirket, ikisi de ROE %24:
A: net marj %12 × devir 1,0 × kaldıraç 2,0
B: net marj %4  × devir 1,2 × kaldıraç 5,0

B'nin ROE'si tamamen borçtan geliyor. Faiz 5 puan yükselirse A'nın kârı biraz
düşer, B'nin kârı silinir. Aynı ROE, tamamen farklı risk.""",
 sorular=["t17", "u06"], sure=9),

Ders("d303", "Borçluluk ve ödeme gücü oranları",
 "Bir şirketin borcunun ne zaman tehlikeli hale geldiğini sayıyla belirlemek.",
 """Borç kendiliğinden kötü değildir; ÖDENEMEZ borç kötüdür. Ölçüler:

BORÇ / ÖZSERMAYE = Toplam finansal borç / Özsermaye
Statik bir orandır. 1'in üstü "borçla büyüyor" demektir. Ama tek başına
yetersizdir çünkü ödeme gücünü göstermez.

NET BORÇ / FAVÖK = (Finansal borç − Nakit) / FAVÖK
En kullanışlı borç oranı. "Şirket tüm nakit kârıyla borcunu kaç yılda kapatır?"
· 0-1,5 → rahat
· 1,5-3 → normal
· 3-4 → dikkat
· 4+ → tehlike bölgesi

FAİZ KARŞILAMA = Faaliyet kârı / Faiz gideri
"Faaliyet kârı, faiz giderinin kaç katı?"
· 5+ → rahat
· 2-5 → izlenmeli
· 2 altı → şirket faizini zor ödüyor
· 1 altı → faaliyet kârı faizi karşılamıyor, borçla borç ödeniyor

CARİ ORAN = Dönen varlık / Kısa vadeli yükümlülük
1'in altı: kısa vadeli borç, dönen varlıkları aşıyor. Nakit sıkışıklığı riski.

ASİT-TEST = (Dönen varlık − Stok) / Kısa vadeli yükümlülük
Stok satılamazsa yine ödeyebilir mi? Stoku ağır sektörlerde cari orandan
önemlidir.""",
 bist="""BANKADA BU ORANLARIN HİÇBİRİ ANLAMLI DEĞİLDİR ve bu, en sık yapılan
otomatik analiz hatasıdır.

Bankada mevduat bir "borç"tur ama bu, bankanın HAMMADDESİDİR. Bir bankanın
borç/özsermaye oranı 8-10 olabilir ve bu tamamen normaldir. Cari oran kavramı
da işlemez.

Bankada bakılacaklar: sermaye yeterlilik oranı (SYR), takipteki kredi oranı
(NPL), net faiz marjı, karşılık oranı.

Bu sistem "banka modu" ile bu oranları otomatik kapatır — hesaplanmaz ve
kalite skorundan düşülmez.

İkinci BIST özeli: borcun PARA BİRİMİ. Dövizli borç + TL gelir kombinasyonu,
Türkiye'de şirket batıran ana mekanizmadır. Bu bilgi dipnotlardadır.""",
 tuzak=""""Borcu az, sağlam şirket" — borçsuz şirket bazen sermayeyi VERİMSİZ
kullanıyor demektir. Ucuz borç varken kullanmamak, ROE'yi düşürür.

Doğru soru "borcu var mı" değil, "borcunu ödeyebilir mi ve borçla ne yaptı".""",
 ornek="""EREGL: Net Borç/FAVÖK 1,64 (rahat görünüyor)
        Faiz karşılama 0,80 (ALARM)

Bu ikisi çelişiyor gibi ama değil: FAVÖK'ü borcuna göre makul, ama faaliyet
kârı faiz giderini karşılamıyor. Sebep: FAVÖK ile faaliyet kârı arasındaki fark
(amortisman) çok büyük — sermaye yoğun bir şirket.

Ders: tek orana bakma. İki oran birlikte, tek orandan farklı bir hikâye anlatır.""",
 sorular=["t09", "o03", "o14"], sure=9),

Ders("d304", "Verimlilik ve devir hızları",
 "Sermayenin ne hızla döndüğünü ölçmek — düşük marjlı şirketlerin sırrı.",
 """Devir hızları, "aynı sermayeyle yılda kaç kez iş yapabiliyorsun" sorusunu
cevaplar.

AKTİF DEVİR HIZI = Hasılat / Toplam varlık
1 liralık varlıkla yılda kaç lira satış yapıyorsun. Perakendede yüksek
(2-3), sermaye yoğun sanayide düşük (0,3-0,6).

STOK DEVİR HIZI = SMM / Ortalama stok
Kaç kez stok tazeledin. Gün cinsinden: 365 / devir hızı.
Gıda perakendesinde 15-30 gün, otomotivde 60-90 gün, mücevherde 200+ gün.

ALACAK DEVİR SÜRESİ = (Ortalama alacak / Hasılat) × 365
Sattıktan kaç gün sonra tahsil ediyorsun. Uzuyorsa ya müşteri kalitesi düştü
ya satışı zorlamak için vade uzatıldı.

BORÇ ÖDEME SÜRESİ = (Ortalama ticari borç / SMM) × 365
Tedarikçiye kaç günde ödüyorsun. Uzun olması pazarlık gücü demektir.

Neden önemli: düşük marjlı bir şirket, yüksek devir hızıyla yüksek marjlı bir
şirketten daha çok para kazanabilir.

  ROIC ≈ Faaliyet marjı × Sermaye devir hızı

%2 marj × 8 devir = %16
%20 marj × 0,7 devir = %14

Birinci şirket daha kârlıdır — marjına bakan biri tersini sanır.""",
 bist="""Türkiye'de enflasyon, devir hızını doğrudan bir REKABET AVANTAJINA
çevirir.

Stoku 20 günde dönen bir perakendeci, malı eski (ucuz) maliyetle alıp yeni
(zamlı) fiyattan satar. Stoku 120 günde dönen bir üretici, aynı süreçte maliyet
artışını üstlenir.

Bu, BIM ve benzeri modellerin enflasyonist dönemde neden dayanıklı olduğunun
mekanik açıklamasıdır.""",
 tuzak=""""Devir hızı yükseldi, iyi" — nedenini sor. Stok devir hızı, stok
ERİDİĞİ için de yükselebilir: şirket üretimi durdurmuş, eldekini satıyordur.
Hasılat düşerken devir hızının yükselmesi kötü haberdir.""",
 sure=7),

Ders("d305", "Oranları doğru kıyaslamak",
 "Aynı oranın farklı sektörlerde neden farklı anlam taşıdığını içselleştirmek.",
 """Bir oran tek başına anlamsızdır. Üç referansa göre okunur:

1) KENDİ GEÇMİŞİNE göre — şirketin son 3-5 yıllık ortalamasına kıyasla nerede?
   Bu, en güvenilir kıyastır çünkü iş modeli aynıdır.

2) SEKTÖR EMSALLERİNE göre — aynı işi yapan şirketlerin MEDYANINA kıyasla?
   Ortalama değil MEDYAN kullanılır: tek bir zarar eden şirketin negatif F/K'sı
   ortalamayı bozar, medyanı bozmaz.

3) MAKRO ORTAMA göre — %40 faiz varken F/K 10, %5 faiz varken F/K 10 ile aynı
   anlama gelmez.

SEKTÖRE GÖRE HANGİ ORAN:
· Banka, sigorta → PD/DD, F/K, ROE, sermaye yeterliliği. FD/FAVÖK ANLAMSIZ.
· GYO, gayrimenkul → PD/DD, net aktif değer iskontosu. F/K genelde anlamsız
  (değerleme kârı net kârı bozar).
· Sanayi, havacılık, telekom → FD/FAVÖK (amortisman ağır), net borç/FAVÖK
· Perakende, gıda → F/K, devir hızları, mağaza başına ciro
· Emtia (çelik, kimya, madencilik) → FD/FAVÖK ve NORMALLEŞTİRİLMİŞ kâr.
  Döngüsel olduğu için tek yılın F/K'sı yanıltır.
· Teknoloji → F/S (kâr henüz yoksa), büyüme oranı, brüt marj

Kural: iki şirketi kıyaslamadan önce "bunlar aynı işi mi yapıyor?" diye sor.
Cevap hayırsa, çarpan kıyası yapma.""",
 bist="""Bu sistem sektör medyanını ŞİRKETLERDEN hesaplar: aynı sektördeki
BIST 100 üyelerinin çarpanları toplanır, medyan alınır, uç değerler (0'ın
altı ve 200'ün üstü) elenir.

Ve her sektör için bir "değerleme rehberi" tutar: hangi çarpanın kullanılacağı,
hangisinin anlamsız olduğu ve o sektörde asıl bakılması gerekenler.""",
 tuzak=""""Sektör ortalamasının altında, ucuz" — sektör TOPLUCA pahalı ya da
topluca ucuz olabilir. 2000 yılında bir teknoloji şirketi "sektör ortalamasının
altında" olabilirdi ve yine de tarihsel olarak çok pahalıydı.

Sektör kıyası göreli bir bilgi verir, mutlak bir bilgi değil. Mutlak değer için
ters DCF ve faiz karşılaştırması gerekir.""",
 sorular=["u13", "t16"], sure=7),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 4 — DEĞERLEME
# ═══════════════════════════════════════════════════════════════════

M4 = Modul("m4", "Değerleme",
           "'İyi şirket' ile 'iyi fiyat' ayrı sorulardır. Bu modül ikincisini "
           "cevaplar: bu şirket ne eder ve piyasa ne istiyor?", 2, [

Ders("d401", "Değerlemenin mantığı",
 "Bir şirketin değerinin gelecekteki nakitten geldiğini ve neden tahmin olduğunu anlamak.",
 """Bir varlığın değeri, gelecekte üreteceği nakdin BUGÜNKÜ karşılığıdır.

Neden "bugünkü karşılığı": bugünkü 100 lira, 1 yıl sonraki 100 liradan
değerlidir. Sebepler:
· Faiz — bugünkü parayı bankaya koyup faiz alabilirsin
· Enflasyon — gelecekteki para daha az şey alır
· Risk — gelecekteki para GELMEYEBİLİR

Bu üçü birleşerek İSKONTO ORANINI oluşturur. Türkiye'de bu oran %40-50
civarındadır ve bu, her şeyi değiştirir.

İki değerleme ailesi vardır:

MUTLAK DEĞERLEME — şirketin kendi nakit akışından değer hesaplar
· DCF (indirgenmiş nakit akışı)
· Temettü iskonto modeli
· Net aktif değer

GÖRECELİ DEĞERLEME — benzer şirketlerle kıyaslar
· F/K, FD/FAVÖK, PD/DD, F/S
· Emsal işlem çarpanları

Pratikte ikisi birlikte kullanılır. Mutlak değerleme "ne eder" der ama
varsayımlara aşırı duyarlıdır. Göreceli değerleme "piyasa benzerlerine ne
ödüyor" der ama tüm sektör pahalıysa bunu göremez.

Ve şu unutulmamalı: DEĞERLEME BİR TAHMİNDİR. Kesinlik hissi veren üç haneli
sonuçlar, varsayımların hassasiyetini gizler.""",
 bist="""Yüksek faiz, Türkiye'de değerlemeyi matematiksel olarak zorlaştırır.

%40 iskonto oranında, 5 yıl sonraki 100 lira bugün sadece 18 lira eder. 10 yıl
sonraki 100 lira 3 lira eder. Yani uzak gelecek neredeyse SIFIR değer taşır.

Sonuç: Türkiye'de "10 yıl sonra çok büyüyecek" hikâyeleri, matematiksel olarak
çok az değer üretir. Yakın vadeli nakit akışı çok daha belirleyicidir.

Bu, BIST çarpanlarının gelişmiş ülkelere göre yapısal olarak düşük olmasının
temel sebebidir. "BIST ucuz" cümlesi genelde bu gerçeği atlar.""",
 tuzak=""""DCF yaptım, hisse 240 lira etmeli" — DCF'in çıktısı bir NOKTA değil,
bir ARALIK olmalıdır. Büyüme varsayımını %20'den %25'e çıkardığında sonuç
%40 değişiyorsa, o modelin verdiği kesinlik sahtedir.

Doğru kullanım: birkaç senaryo (kötü/baz/iyi) ve duyarlılık analizi.""",
 sure=7),

Ders("d402", "Çarpanlar: F/K, PD/DD, FD/FAVÖK, F/S",
 "Dört ana çarpanın ne ölçtüğünü ve hangisinin ne zaman kırıldığını bilmek.",
 """F/K = Piyasa değeri / Net kâr
"Bugünkü kâr sürerse yatırımını kaç yılda geri alırsın."
Tersi KAZANÇ VERİMİDİR: F/K 10 → %10 verim. Bunu mevduat faiziyle kıyasla.
Kırıldığı yer: zarar eden ya da kârı sıfıra yakın şirkette anlamsızdır.
Döngüsel sektörde TERS okunur (tepede düşük, dipte yüksek).

PD/DD = Piyasa değeri / Özsermaye
"Defter değerinin kaç katı."
En çok banka ve GYO'da kullanılır — varlıkları finansal olduğu için defter
değeri gerçeğe yakındır.
Kırıldığı yer: varlığı bilançoda görünmeyen şirketlerde (yazılım, marka
ağırlıklı) anlamsızdır.
Mutlaka ROE ile birlikte okunur: düşük PD/DD + düşük ROE = sermaye verimsiz.

FD/FAVÖK = (Piyasa değeri + Net borç) / FAVÖK
"Borç dahil şirket değeri, nakit kârın kaç katı."
F/K'nın göremediği şeyi görür: borç yapısı. İki şirket aynı kârı ediyorsa ama
biri borçsuzsa, F/K'ları benzer çıkar ve seni yanıltır.
Kırıldığı yer: BANKADA anlamsızdır.

F/S = Piyasa değeri / Hasılat
Kârı olmayan ya da dalgalanan şirketlerde son çare.
Kırıldığı yer: marjı görmez. %2 marjlı ve %30 marjlı şirketin F/S'si aynı
olamaz — olmamalıdır.

SERBEST NAKİT VERİMİ = FCF / Piyasa değeri
En dürüst çarpan. Mevduat faiziyle DOĞRUDAN kıyaslanabilir.""",
 bist="""KUR TUZAĞI — BIST'e özgü ve otomatik veri kaynaklarının çöktüğü nokta.

Bazı BIST şirketleri (THYAO gibi ihracatçılar) finansallarını USD açıklar ama
hisseleri TL işlem görür. Bir çarpan hesaplarken piyasa değerini (TL) kâra
(USD) bölersen sonuç ÇÖPTÜR.

Ölçülmüş örnek: yfinance THYAO'nun F/S'sini 15,66 gösteriyor. Kur düzeltmesiyle
gerçeği 0,34. 43 kat hata — ve bu, en çok işlem gören hisselerden birinde.

Bu sistem `financialCurrency` alanını kontrol eder. Kuralı şudur:
· Tablodan tabloya oranlar (marj, ROE) → para birimi nötr, dönüşüm gerekmez
· Fiyat karışan çarpanlar (F/K, PD/DD) → ZORUNLU dönüşüm, yoksa hesaplanmaz""",
 tuzak=""""Düşük F/K = ucuz" avcılığı, sistematik olarak iki şeyi toplar:
döngüsel tepedeki şirketler ve yapısal düşüşteki şirketler.

Piyasa çoğu zaman aptal değildir. Düşük çarpan gördüğünde varsayılan tutumun
"neden bu kadar ucuz?" olmalı, "ne fırsat!" değil. Sebebi bulamıyorsan, o sebep
senin göremediğin bir risktir.""",
 ornek="""EREGL bugün: F/K 1.055 · PD/DD 0,90 · FD/FAVÖK 12,79 · FCF verimi %19,28

F/K anlamsız (net kâr sıfıra yakın, sıfıra bölme artefaktı).
PD/DD 0,90 → defterin altında, "ucuz" görünüyor.
FD/FAVÖK 12,79 → aslında pahalı sayılır (emtia şirketinde 5-7 normaldir).
FCF verimi %19 → nakit üretiyor.

Dört çarpan dört farklı şey söylüyor. Tek birine bakan yanılır. Doğru okuma:
şirket döngü dibinde, defter değerinin altında, nakit üretmeye devam ediyor
ama FAVÖK bazında ucuz değil. Bu bir "izle" hikâyesidir, "al" değil.""",
 sorular=["t06", "t07", "t08", "o06", "o07", "u07", "u08"], sure=10),

Ders("d403", "DCF ve ters DCF",
 "Nakit akışı iskonto etmeyi ve Türkiye'de neden ters DCF'in daha dürüst olduğunu görmek.",
 """DCF (İndirgenmiş Nakit Akışı) şunu yapar:
1) Gelecek 5-10 yılın serbest nakit akışını TAHMİN et
2) Her yılın nakdini iskonto oranıyla bugüne indir
3) 5-10 yıl sonrası için bir "devam eden değer" hesapla
4) Hepsini topla, net borcu düş → özsermaye değeri
5) Hisse adedine böl → hisse başına değer

Formül basittir. Zor olan VARSAYIMLARDIR:
· Büyüme oranı ne olacak?
· Marj ne olacak?
· İskonto oranı kaç?
· Sonsuz büyüme kaç?

Türkiye'de problem: %40 iskonto oranında varsayımların küçük bir değişimi,
sonucu ikiye katlar ya da yarıya indirir. Model sana kesinlik hissi verir ama
o kesinlik sahtedir.

TERS DCF bu problemi çözer. Mantığı tersine çevirir:

  "Bu fiyat, hangi büyümeyi ima ediyor?"

Tahmin ÜRETMEZ; piyasanın zaten yaptığı tahmini AÇIĞA ÇIKARIR. Senin işin
sadece şunu değerlendirmek: bu büyüme makul mü?

Bu çok daha dürüst bir egzersizdir. "Şirket 240 lira eder" demek yerine,
"bugünkü fiyat yılda %70 büyüme bekliyor, bu makul mü?" diye sorarsın.""",
 bist="""Bu sistem ters DCF'i şirketin RAPORLAMA PARA BİRİMİNDE hesaplar ve
iskonto oranını ona göre seçer:
· TRY raporlayan → %40 iskonto, %20 sonsuz büyüme
· USD raporlayan → %11 iskonto, %3 sonsuz büyüme

Sebep: TL nakit akışını %40 ile, USD nakit akışını %11 ile iskonto edersin.
İkisini karıştırmak sonucu tamamen bozar. Piyasa değeri de aynı para birimine
çevrilir ki karşılaştırma tutarlı olsun.""",
 tuzak="""DCF'in en tehlikeli tarafı, İSTEDİĞİN SONUCU ÜRETEBİLMESİDİR.
Bir hisseyi beğeniyorsan, büyüme varsayımını biraz yükseltirsin ve model sana
"ucuz" der. Bu, teyit önyargısının en teknik kılığıdır.

Ters DCF bunu engeller çünkü varsayım girmezsin — çıktıyı değerlendirirsin.""",
 ornek="""Sistemin bugün ölçtüğü üç şirket:

BIMAS: fiyat, serbest nakit akışının 5 yıl yılda %69,8 büyümesini ima ediyor.
       Enflasyon %31,8. Yani REEL %38 büyüme bekleniyor. Çok iddialı.
EREGL: %15,4 büyüme ima ediliyor, enflasyonun ALTINDA. Piyasa reel daralma
       fiyatlıyor.
THYAO: −%24,1 (USD) ima ediliyor. Piyasa ciddi bir çöküş bekliyor.

Üç farklı hikâye. Senin işin: hangisinin beklentisi yanlış?""",
 sorular=["u03", "t16"], sure=9),

Ders("d404", "Değer tuzağı ve döngüsellik",
 "Ucuz görünen şirketin neden ucuz olduğunu bulmayı öğrenmek.",
 """DEĞER TUZAĞI: çarpanları düşük olduğu için ucuz sanılan, ama aslında bir
SEBEPTEN ucuz olan şirket.

Ucuzluğun sebepleri, en masumdan en kötüye:
1) PİYASA GÖZDEN KAÇIRMIŞ — gerçek fırsat. En nadir ihtimal.
2) GEÇİCİ SORUN — düzelirse fırsat. Araştırılabilir.
3) DÖNGÜSEL TEPE — kâr zirvede, F/K düşük görünüyor. Satılacak zaman.
4) YAPISAL DÜŞÜŞ — sektör ölüyor ya da şirket pazar payı kaybediyor.
5) YÖNETİŞİM SORUNU — azınlık hakları korunmuyor, piyasa iskonto uyguluyor.
6) MUHASEBE SORUNU — rakamlara güvenilmiyor.

DÖNGÜSELLİK özel bir dikkat ister. Çelik, kimya, madencilik, otomotiv,
inşaat malzemesi gibi sektörlerde kâr, ekonomik döngüyle birlikte iner çıkar.

Döngüselde çarpan TERS okunur:
· Döngü TEPESİNDE: kâr maksimum → F/K MİNİMUM görünür → aslında PAHALI
· Döngü DİBİNDE: kâr minimum → F/K MAKSİMUM görünür → aslında UCUZ olabilir

Bu yüzden döngüsel şirkette NORMALLEŞTİRİLMİŞ kâr kullanılır: son 5-7 yılın
ortalama kârı ya da ortalama marj × bugünkü ciro.

Ayırt etmenin yolu: kârın düşüşü DÖNGÜSEL mi YAPISAL mı?
· Döngüsel → talep geçici olarak düştü, kapasite duruyor, fiyat düşük
· Yapısal → ikame ürün çıktı, regülasyon değişti, rakip kalıcı üstünlük kurdu""",
 bist="""BIST'te değer tuzağının en net örneği bu sistemin ölçtüğü EREGL'dir:

PD/DD 0,90 — "defterin altında, ucuz!"
Ama: kalite skoru 31,8 · faiz karşılama 0,80x (faizini ödeyemiyor) ·
ROE %0,18 · net marj %0,24 · hasılat reel olarak küçülüyor.

Bu ucuzluk bir fırsat mı, tuzak mı? Cevap, çelik döngüsünün nerede olduğuna
bağlıdır — ve bu, bilançoda değil dünya emtia piyasasında aranır.

İkinci BIST özeli: YÖNETİŞİM İSKONTOSU. Halka açıklık oranı düşük, ana ortakla
ilişkili işlemleri yoğun şirketlerde piyasa kalıcı iskonto uygular. Bu iskonto
"kapanacak" diye beklemek genelde boşunadır.""",
 tuzak=""""Ucuz, alalım, nasılsa döner" — dönmeyebilir. Yapısal düşüşteki bir
şirket her yıl daha da ucuzlar ve sen ortalama düşürerek batarsın.

Kural: ucuzluğun SEBEBİNİ bulamıyorsan alma. Sebebi bilmemek, riski
bilmemektir.""",
 sorular=["u05", "u08", "o06"], sure=8),

Ders("d405", "Piyasa değeri, firma değeri ve net aktif değer",
 "Bir şirketi satın almanın gerçek maliyetini hesaplamayı öğrenmek.",
 """PİYASA DEĞERİ (PD) = Hisse fiyatı × Toplam hisse adedi
Şirketin ÖZSERMAYESİNİN piyasa fiyatı.

FİRMA DEĞERİ (FD) = Piyasa değeri + Net borç
  Net borç = Finansal borç − Nakit ve nakit benzerleri

Neden firma değeri: şirketi satın alırsan, borcunu da devralırsın. Ama
kasasındaki nakit de senin olur. Gerçek maliyet budur.

Örnek: iki şirket, ikisinin de piyasa değeri 10 milyar.
A: 5 milyar nakit, borcu yok → FD = 5 milyar
B: borcu 5 milyar, nakit yok → FD = 15 milyar
Aynı fiyata iki şirket, ama B üç kat pahalı.

Bu yüzden borç yapısı farklı şirketleri kıyaslarken FD/FAVÖK kullanılır,
F/K değil.

NET AKTİF DEĞER (NAD): şirketin tüm varlıklarının güncel piyasa değerinden
tüm borçları düşülünce kalan. GYO ve holdinglerde temel değerleme yöntemidir.

Holdinglerde ayrı bir olgu vardır: HOLDİNG İSKONTOSU. Bir holdingin piyasa
değeri, sahip olduğu iştiraklerin toplam piyasa değerinden genelde DÜŞÜK olur.
Sebepler: merkez giderleri, sermaye dağıtım riski, karmaşıklık, likidite.
BIST'te bu iskonto %30-50 bandında seyredebilir.""",
 bist="""BIST holdinglerinde (KCHOL, SAHOL, ALARK) NAD hesabı temel analizin
merkezindedir: borsada işlem gören iştiraklerin piyasa değeri toplanır, borsada
olmayanlar tahmin edilir, net borç düşülür.

Sonra sorulur: holding, NAD'ının yüzde kaçından işlem görüyor? Tarihsel
iskonto bandına göre nerede?

GYO'larda ise NAD, gayrimenkul değerleme raporlarından gelir ve bu raporlar
şirketin seçtiği değerleme firması tarafından hazırlanır — dikkatle okunmalıdır.""",
 tuzak=""""Holding NAD'ının %50 altında, çok ucuz" — iskonto her zaman vardır
ve KAPANMAYABİLİR. Tarihsel bandın altındaysa fırsat olabilir; ama "iskonto
sıfırlanacak" beklentisiyle alım yapmak, genelde yıllarca beklemek demektir.""",
 sure=7),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 5 — SEKTÖR ANALİZİ
# ═══════════════════════════════════════════════════════════════════

M5 = Modul("m5", "Sektör analizi",
           "Her sektörün kendi finansal fiziği vardır. Bankayı perakendeci gibi "
           "okumak, en hızlı yanılma yoludur.", 2, [

Ders("d501", "Bankacılık",
 "Bankanın neden tamamen farklı okunduğunu ve hangi üç sayının belirleyici olduğunu öğrenmek.",
 """Banka bir üretici değildir. İş modeli şudur: ucuza borçlan (mevduat), pahalıya
borç ver (kredi), aradaki farkı kazan.

Bu yüzden bankada BORÇ HAMMADDEDİR. Mevduat bilançoda yükümlülüktür ama kötü
bir şey değildir — bankanın çalışma malzemesidir. Borç/özsermaye oranı 8-10
olabilir ve bu normaldir.

Bankada bakılacak üç sayı:

1) NET FAİZ MARJI (NIM) = (Faiz geliri − Faiz gideri) / Getirili aktifler
   Ana kârlılık ölçüsü. Faiz ortamına çok duyarlıdır.

2) TAKİPTEKİ KREDİ ORANI (NPL) = Takipteki krediler / Toplam krediler
   Kredi kalitesi. Yükseliyorsa banka kötü kredi vermiş demektir ve karşılık
   ayırmak zorunda kalır — bu doğrudan kârı yer.
   Yanında KARŞILIK ORANI (coverage) bakılır: takipteki kredinin yüzde kaçı
   için karşılık ayrılmış?

3) SERMAYE YETERLİLİK ORANI (SYR) = Özkaynak / Risk ağırlıklı varlıklar
   Yasal alt sınır vardır. Düşükse banka büyüyemez, sermaye artırımı gerekir.

Değerleme: PD/DD ve F/K kullanılır. FD/FAVÖK, cari oran, net borç/FAVÖK
ANLAMSIZDIR.

PD/DD'yi mutlaka ROE ile birlikte oku. Basit sezgi: sürdürülebilir ROE,
sermaye maliyetine eşitse PD/DD 1 olmalıdır. ROE sermaye maliyetinin
üstündeyse 1'in üstü hak edilir.""",
 bist="""Türk bankacılığında ek boyutlar:
· TCMB REGÜLASYONLARI — kredi büyüme sınırları, menkul kıymet tutma
  zorunluluğu, zorunlu karşılıklar. Bunlar kârlılığı doğrudan etkiler ve
  sık değişir.
· TÜFE'YE ENDEKSLİ MENKUL KIYMETLER — bankalar portföylerinde tutar.
  Enflasyon yükseldiğinde bu kalemden büyük gelir yazarlar. Bu gelir GERÇEK
  ama TEK SEFERLİKtir ve enflasyon düştüğünde kaybolur.
· KUR KORUMALI MEVDUAT ve benzeri araçlar bilanço yapısını değiştirir.

Bu sistem banka sektöründe kâr kalitesi oranını da kapatır: bankada faaliyet
nakit akışı mevduat/kredi hareketinden oluşur, kâr kalitesi ölçmez. GARAN'ın
oranı 0,05 çıkıyor ve bu hiçbir sorun göstermiyor.""",
 tuzak=""""Faiz arttı, bankalar kazanır" — fazla basit. Faiz artışı iki karşıt
etki yaratır:
· Kredi faizi mevduat faizinden hızlı ayarlanırsa marj AÇILIR (olumlu)
· Ekonomi yavaşlar, takipteki krediler ARTAR (olumsuz)

Hangi etkinin baskın olacağı, artışın hızına ve ekonominin dayanıklılığına
bağlıdır. Genelde ilk aşamada marj kazanır, ilerleyen dönemde kredi riski
öne çıkar.""",
 sorular=["t14", "o13"], sure=9),

Ders("d502", "Holdingler",
 "Holding iskontosunu ve NAD analizini anlamak.",
 """Holding, başka şirketlerde pay sahibi olan şirkettir. Kendi başına üretim
yapmaz; iştiraklerinin performansını taşır.

Değerleme yöntemi NET AKTİF DEĞER (NAD):
1) Borsada işlem gören iştiraklerin piyasa değerini × holdingin payı
2) Borsada olmayan iştirakleri tahmin et (çarpan ya da defter değeri)
3) Gayrimenkul, nakit, diğer varlıkları ekle
4) Holdingin kendi net borcunu düş
→ NAD

Sonra: holdingin piyasa değeri NAD'ın yüzde kaçı?

HOLDİNG İSKONTOSU: piyasa değeri neredeyse her zaman NAD'ın ALTINDADIR.
Sebepleri:
· Merkez giderleri (holding kendi masrafını üretmez)
· Sermaye dağıtım riski (holding parayı kötü yatırıma koyabilir)
· Vergi (iştirak satışında vergi doğar)
· Karmaşıklık ve şeffaflık eksikliği
· Yatırımcı isterse iştirakleri doğrudan alabilir

İskonto BIST'te tarihsel olarak %30-50 bandında seyreder.

Analiz sorusu: bugünkü iskonto, kendi tarihsel bandının neresinde?
· Bandın üst ucundaysa (iskonto büyük) → görece ucuz
· Alt ucundaysa → görece pahalı""",
 bist="""BIST'te büyük holdingler (KCHOL, SAHOL, ALARK, DOHOL) endeksin önemli
bir kısmını oluşturur.

Dikkat edilecek nokta: holdingin kârının ne kadarı BANKACILIKTAN geliyor?
Türkiye'de büyük holdinglerin çoğu banka sahibidir ve banka kârı holdingin
net kârının yarısından fazlasını oluşturabilir. O zaman holdingi analiz
ediyorsun sanıp aslında bankayı analiz ediyorsundur.

İkinci nokta: iştirak yapısı karmaşıksa (holding içinde holding), NAD hesabı
çift sayımdan korunmalıdır.""",
 tuzak=""""İskonto %50, çok ucuz, kapanacak" — iskonto yapısaldır ve
kapanmayabilir. Yıllarca aynı seviyede kalabilir.

İskontonun kapanması için bir KATALİZÖR gerekir: iştirak satışı, temettü
politikası değişikliği, sadeleşme, geri alım programı. Katalizör yoksa
iskonto sadece bir gözlemdir, bir tez değil.""",
 sure=7),

Ders("d503", "Sanayi, otomotiv ve dayanıklı tüketim",
 "Sermaye yoğun ve döngüsel iş modellerini okumayı öğrenmek.",
 """Bu sektörlerin ortak özellikleri:
· SERMAYE YOĞUN — fabrika, makine, büyük capex
· DÖNGÜSEL — talep ekonomiyle birlikte iner çıkar
· OPERASYONEL KALDIRAÇ yüksek — sabit gider büyük

OPERASYONEL KALDIRAÇ kritik bir kavramdır: sabit giderler yüksek olduğu için,
ciro %10 artınca kâr %30 artar; ciro %10 düşünce kâr %30 düşer. Kâr, ciroyu
abartarak takip eder.

Bakılacaklar:
· KAPASİTE KULLANIM ORANI — fabrika ne kadar doluluk çalışıyor
· BİRİM MALİYET ve girdi fiyatları
· İHRACAT PAYI — iç talep zayıflarsa ihracat kurtarır mı?
· AMORTİSMAN yükü — net kârı bozar, bu yüzden FD/FAVÖK tercih edilir

OTOMOTİVDE ek olarak:
· Kredi faizi ve taksit koşulları (talep buna bağlı)
· ÖTV/vergi düzenlemeleri — bir gecede talebi değiştirir
· Model döngüsü — yeni model çıkışı satışı canlandırır
· Ana üreticiyle lisans/sözleşme yapısı

Değerleme: FD/FAVÖK ve NORMALLEŞTİRİLMİŞ kâr. Tek yılın F/K'sı döngüsel
sektörde yanıltır.""",
 bist="""BIST'te otomotivin (FROTO, TOASO) özel bir dinamiği var: bu şirketler
hem iç pazara satar hem İHRACAT yapar. Kur yükseldiğinde ihracat geliri TL
olarak şişer, ama iç talep alım gücü kaybı yüzünden daralır.

Net etki, ihracat/iç pazar dengesine bağlıdır ve bu oran her şirkette farklıdır.

Sanayide (EREGL, KRDMD) belirleyici olan dünya emtia fiyatıdır — Türkiye'deki
hiçbir gelişme, Çin'in çelik ihracat politikası kadar etkili değildir.""",
 tuzak=""""Kapasite artırıyor, büyüyecek" — kapasite artışı, talep gelmezse
sabit gider artışı demektir ve marjı EZER. Yeni yatırımın devreye girdiği
dönem, döngünün tersine döndüğü döneme denk gelirse şirket zorlanır.

Doğru soru: bu kapasite hangi talep varsayımıyla kuruldu ve o varsayım hâlâ
geçerli mi?""",
 sure=8),

Ders("d504", "Perakende ve gıda",
 "İnce marjlı, yüksek devirli iş modelinin nasıl okunacağını öğrenmek.",
 """Perakendede net marj %2-4 arasındadır ve bu NORMALDİR. Kârlılık marjdan
değil, DEVİR HIZINDAN gelir.

Bakılacaklar:
· MAĞAZA SAYISI ve büyüme hızı
· AYNI MAĞAZA SATIŞ BÜYÜMESİ (like-for-like) — en önemli sayı. Yeni mağaza
  açarak ciro büyütmek kolaydır; mevcut mağazadan daha çok satmak gerçek
  performanstır.
· MÜŞTERİ TRAFİĞİ ve SEPET ORTALAMASI — büyüme fiyattan mı, hacimden mi?
· STOK DEVİR HIZI
· NAKİT DÖNÜŞÜM DÖNGÜSÜ — perakendede genelde NEGATİFTİR ve bu bir üstünlüktür

Negatif nakit döngüsü ne demek: müşteriden peşin alırsın, tedarikçiye 60 gün
sonra ödersin. Yani tedarikçi seni finanse eder. Büyüdükçe nakit ÜRETİRSİN.
Bu, düşük marjla büyüyebilmenin sırrıdır.

Enflasyonist ortamda ek avantaj: stoku hızlı dönen perakendeci, eski maliyetle
aldığı malı zamlı fiyattan satar. Enflasyon onun için bir marj kaynağıdır —
ta ki alım gücü kaybı hacmi düşürene kadar.""",
 bist="""BIST perakendesinde (BIMAS, MGROS, SOKM) kritik ölçü, ciro büyümesinin
ENFLASYONA göre nerede olduğudur.

Sistem bunu doğrudan ölçüyor: BIMAS'ın yıllık hasılat büyümesi %6,0, enflasyon
%31,8. Yani şirket REEL OLARAK KÜÇÜLÜYOR — nominal rakama bakan biri bunu
göremez.

Bu, "iyi şirket kötü dönem" mi yoksa "yapısal pazar payı kaybı" mı, cevabı
aynı mağaza satış büyümesinde ve rakiplerin rakamlarında aranır.""",
 tuzak=""""Ciro %40 arttı, harika" — enflasyon %31,8 ise reel büyüme %6'dır.
Ve bu %6'nın ne kadarı yeni mağazadan, ne kadarı mevcut mağazadan geliyor?

Yeni mağaza açarak büyümek sermaye gerektirir ve bir noktada doygunluğa ulaşır.
Aynı mağaza büyümesi ise sürdürülebilir bir güçtür.""",
 sorular=["u09", "d304"], sure=8),

Ders("d505", "Enerji, elektrik ve altyapı",
 "Regüleli ve borçlu iş modellerini, tahvil benzeri davranışlarını anlamak.",
 """Bu sektörlerin ortak özellikleri:
· AĞIR BORÇLU — santral, şebeke, altyapı yatırımı büyük sermaye ister
· UZUN VADELİ SÖZLEŞMELİ — gelir görece öngörülebilir
· REGÜLEYE TABİ — fiyatlar serbest değil, kurul belirler
· YÜKSEK TEMETTÜ ÖDER — büyüme sınırlı, nakit dağıtılır

Bu özellikler bir sonuç doğurur: bu hisseler TAHVİL GİBİ DAVRANIR. Faiz
yükseldiğinde değer kaybederler, faiz düştüğünde değer kazanırlar. Sebep
basittir: temettü verimi, tahvil faiziyle rekabet halindedir.

Bakılacaklar:
· Net borç / FAVÖK (genelde yüksektir, sektörde 3-4 normaldir)
· Sözleşme yapısı ve süresi
· Regülasyon riski — tarife kararları
· Kur riski — enerji yatırımları genelde dövizli finanse edilir
· Kapasite ve üretim hacmi

Değerleme: FD/FAVÖK ve temettü verimi. F/K, amortisman yükü yüzünden yanıltır.

ELEKTRİK ÜRETİMİNDE ek boyut: üretim kaynağı (hidro, doğalgaz, rüzgâr, güneş)
maliyet yapısını tamamen değiştirir. Doğalgaz santrali gaz fiyatına, hidro
yağışa bağımlıdır.""",
 bist="""Türkiye'de bu sektörün en büyük riski KUR + REGÜLASYON kombinasyonudur:
· Yatırım dövizli finanse edilir (borç dövizli)
· Gelir TL'dir ve tarifesi kurul tarafından belirlenir
· Kur yükselirse borç şişer, tarife aynı hızda artmazsa şirket ezilir

Bu sistemin sektör verisinde Elektrik & Altyapı, 60 günde XU100'ün 31 puan
gerisinde — sektörün topluca baskı altında olduğunu gösteriyor. Böyle bir
tabloda tek bir şirketin "ucuz" görünmesi, genelde sektörel bir sebeptendir.""",
 tuzak=""""Temettü verimi %8, cazip" — mevduat faizi %40 iken %8 temettü verimi
cazip DEĞİLDİR. Ayrıca faiz yükselmeye devam ederse hissenin fiyatı düşer ve
temettü kazancını silersin.

Temettü hisseleri, faizin DÜŞMEYE BAŞLADIĞI dönemde cazip hale gelir.""",
 sure=8),

Ders("d506", "Havacılık, turizm ve ulaştırma",
 "Yüksek operasyonel kaldıraçlı, dövizli ve şoklara açık modelleri okumak.",
 """Havacılık, finansal olarak en zor sektörlerden biridir:
· Sabit gider çok yüksek (uçak, personel, slot)
· Operasyonel kaldıraç aşırı — doluluk %5 değişince kâr uçar ya da çöker
· Yakıt maliyeti kontrol dışı ve büyük
· Şoklara açık (salgın, savaş, doğal afet)
· Sermaye yoğun, borçlu

Bakılacaklar:
· DOLULUK ORANI (load factor) — en kritik tek sayı
· BİRİM GELİR (RASK) ve BİRİM MALİYET (CASK) — ikisinin makası kârı belirler
· YOLCU SAYISI ve arz (AKK) büyümesi
· YAKIT MALİYETİ payı ve korunma (hedge) politikası
· Filo yaşı ve kiralama yapısı

Değerleme: FD/FAVÖK ve FD/FAVKÖK (kira öncesi). Uçaklar kiralık olabildiği
için kira giderinin nasıl muhasebeleştiğine dikkat edilir.

TURİZMDE benzer dinamik: yüksek sabit gider, mevsimsellik, dövizli gelir,
şoklara açıklık.""",
 bist="""THYAO, BIST'in en özel şirketlerinden biridir ve iki sebeple:

1) FİNANSALLARINI USD AÇIKLAR. Hissesi TL işlem görür. Bu ikisini karıştıran
   her oran çöp üretir — yfinance'in F/S'si 15,66, gerçeği 0,34.
   Bu sistem `financialCurrency` kontrolüyle düzeltir.

2) Büyümesi TL enflasyonuyla değil, USD enflasyonuyla (~%3) kıyaslanmalıdır.
   Yanlış referans kullanınca kalite skoru 43 çıkıyordu; doğrusu 76,5.

Ayrıca THYAO doğal bir KUR KORUMASINA sahiptir: geliri de gideri de büyük
ölçüde dövizlidir. Kur hareketi net etkisi görece küçüktür — ama dövizli
borcu da vardır, net döviz pozisyonuna bakmak gerekir.

Petrol fiyatı THYAO ve PGSUS için en belirleyici dış değişkendir.""",
 tuzak=""""Yolcu sayısı arttı, kâr artacak" — yolcu sayısı arz artışıyla
gelmiş olabilir. Doluluk oranı düşerken yolcu sayısı artabilir ve bu kârlılığı
BOZAR. Hacim değil, DOLULUK ve BİRİM GELİR belirleyicidir.""",
 sorular=["u10"], sure=8),

Ders("d507", "İnşaat, GYO ve gayrimenkul",
 "Değerleme kârının net kârı nasıl bozduğunu ve NAD iskontosunu anlamak.",
 """GYO'larda (Gayrimenkul Yatırım Ortaklığı) temel bir muhasebe olgusu vardır:
yatırım amaçlı gayrimenkuller GERÇEĞE UYGUN DEĞERLE ölçülür ve değer artışı
GELİR TABLOSUNA KÂR olarak yazılır.

Sonuç: GYO'nun net kârının büyük kısmı NAKİT OLMAYAN değerleme kârıdır.
Bu yüzden GYO'da F/K neredeyse anlamsızdır — kâr, gayrimenkul fiyatlarının
nereye gittiğini yansıtır, şirketin performansını değil.

GYO'da bakılacaklar:
· NET AKTİF DEĞER (NAD) ve fiyatın NAD'a oranı
· KİRA GELİRİ ve doluluk oranı — gerçek nakit üreten kalem budur
· FFO (Funds From Operations) = Net kâr − değerleme kârı + amortisman
  GYO'nun gerçek operasyonel performansı
· Net borç / varlık oranı
· Portföy dağılımı (AVM, ofis, konut, lojistik)

İNŞAATTA farklı bir dinamik: gelir tanıma yöntemi kritiktir (tamamlanma
yüzdesi mi, teslimde mi). Sözleşmelerin sabit fiyatlı olması, enflasyonda
maliyet artışının müteahhitte kalması demektir.

İkisi de FAİZE aşırı duyarlıdır: konut kredisi faizi talebi doğrudan belirler.""",
 bist="""Türkiye'de gayrimenkul, enflasyona karşı geleneksel korunma aracı
olarak görülür ve bu, GYO değerlemelerini destekler.

Ama dikkat: GYO'nun değerleme raporları, şirketin seçtiği değerleme firması
tarafından hazırlanır. Bağımsızlık derecesi ve kullanılan varsayımlar okunmalıdır.

Bu sistemin sektör verisinde GYO & İnşaat, 60 günde XU100'ün 6,8 puan gerisinde
— faizin yüksek olduğu bir ortamda beklenen tablo.""",
 tuzak=""""GYO net kârı patladı, harika çeyrek" — muhtemelen gayrimenkul
değerleme kârıdır. Nakit girmemiştir, temettü ödenemez, sürdürülebilir değildir.

Doğru bakılacak yer: kira geliri ve FFO.""",
 sorular=["o04"], sure=8),

Ders("d508", "Teknoloji, savunma ve büyüme şirketleri",
 "Kârı henüz olmayan ya da sözleşmeye dayalı iş modellerini değerlendirmek.",
 """TEKNOLOJİDE klasik oranlar sık kırılır:
· Kâr henüz yoksa F/K yok → F/S kullanılır
· Varlıkların çoğu bilançoda görünmez (yazılım, marka, ekip) → PD/DD anlamsız
· Ar-Ge gideri mi, yatırım mı? Muhasebe politikası kârı değiştirir

Bakılacaklar:
· BÜYÜME ORANI ve sürdürülebilirliği
· BRÜT MARJ — yazılımda %70+ beklenir; düşükse iş modeli sorgulanır
· TEKRARLAYAN GELİR payı (abonelik) — tek seferlik satıştan çok değerlidir
· MÜŞTERİ KAZANIM MALİYETİ vs MÜŞTERİ YAŞAM BOYU DEĞERİ
· Nakit yakma hızı ve kalan pist (runway)

SAVUNMA farklı bir hayvandır:
· Gelir SÖZLEŞMEYE dayalıdır — bakılacak sayı SİPARİŞ DEFTERİ (backlog)
· Backlog / yıllık ciro = kaç yıllık iş garantide
· Devlet müşteri: tahsilat güvenli ama fiyat pazarlığı sınırlı
· İhracat sözleşmeleri dövizli — kur avantajı
· Uzun proje süreleri, gelir tanıma tamamlanma yüzdesine göre

Değerleme: savunmada F/K ve FD/FAVÖK çalışır ama backlog'a göre ileriye dönük
okunmalıdır.""",
 bist="""BIST teknoloji ve savunma hisseleri (ASELS, ASTOR, teknoloji grubu)
son dönemde çok sert hareket etti. Bu sistemin sektör verisi bunu gösteriyor:
Teknoloji 120 günde +%194,9, ama son 20 günde −%28,0.

Bu tablo iki şey öğretir:
1) Hikâyeye dayalı sektörlerde çarpanlar hızla şişer ve hızla söner
2) Bir sektörün 120 günlük performansı, bugün girmenin iyi fikir olduğu
   anlamına gelmez — tam tersi olabilir

BIST'te teknoloji hisselerinin halka açıklık oranı düşük olabilir; bu, hem
oynaklığı hem manipülasyon riskini artırır.""",
 tuzak=""""Yüksek büyüme, yüksek çarpanı hak eder" — kısmen doğru ama iki koşulla:
büyüme SÜRDÜRÜLEBİLİR olmalı ve KÂRLI olmalı (ROIC > sermaye maliyeti).

Zarar ederek büyüyen şirket, Türkiye'nin %40 faiz ortamında değer YAKAR.
Gelişmiş ülkedeki "önce büyü, sonra kârlılığa geç" modeli burada çok daha
pahalıdır.""",
 sorular=["u06", "u07"], sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 6 — MAKROEKONOMİ
# ═══════════════════════════════════════════════════════════════════

M6 = Modul("m6", "Makroekonomi",
           "Türkiye'de bir hissenin fiyatını, şirketin kendisi kadar makro "
           "ortam belirler. Bu modül o ortamı okumayı öğretir.", 2, [

Ders("d601", "Enflasyon: nominal ile reelin farkı",
 "Neden nominal getirinin bir yanılsama olduğunu ve reel düşünmeyi öğrenmek.",
 """Enflasyon, paranın satın alma gücünün azalmasıdır. Yatırımda yarattığı
etki tek cümleyle özetlenebilir: SAYILAR BÜYÜR AMA ZENGİNLEŞMEZSİN.

Reel getiri hesabı:
  Reel ≈ Nominal − Enflasyon   (kabaca)
  Tam formül: (1 + nominal) / (1 + enflasyon) − 1

Şirket üzerindeki etkileri:
· CİRO ve KÂR nominal olarak şişer — büyüme yanılsaması yaratır
· MALİYET de şişer; fiyata geçirebilen korunur, geçiremeyenin marjı ezilir
· STOK KÂRI oluşur — eski maliyetle alınan mal yeni fiyattan satılır
· BORÇ REEL OLARAK ERİR — sabit faizli borçlu şirket enflasyondan kazanır
· NAKİT ERİR — kasada duran para değer kaybeder

Piyasa üzerindeki etkisi:
· Enflasyon faizi yukarı iter
· Faiz iskonto oranını yükseltir
· İskonto oranı çarpanları düşürür
Sonuç: enflasyon yükseldikçe borsanın çarpanları YAPISAL OLARAK düşer.

Bu yüzden yüksek enflasyonlu ülkelerde F/K'lar düşüktür. Bu bir "ucuzluk"
değil, bir DENGE durumudur.""",
 bist="""Bu sistemin ölçtüğü somut rakam, dersin tamamını özetler:

BIST 100 son 1 yıl nominal getiri: +%28,1
Enflasyon (TÜFE): %31,8
REEL getiri: −%3,5

Bir yıl boyunca borsada olan biri, alım gücü olarak FAKİRLEŞTİ — ama hesabında
sayının büyüdüğünü gördü ve muhtemelen kazandığını sandı.

Sistem her getiriyi reel olarak da gösterir. `makro` komutu bu satırı her
seferinde yazar, tam bu yüzden.

İkinci nokta: ENFLASYON MUHASEBESİ (TMS-29). 2023'ten beri şirketler geçmiş
dönem rakamlarını bugünkü satın alma gücüne göre düzeltiyor. Bu, yıllar arası
kıyası anlamlı hale getirdi — ama düzeltilmiş ve düzeltilmemiş rakamları
karıştırırsan saçmalarsın.""",
 tuzak=""""Enflasyonda hisse alınır, korunursun" — YARIM doğru. Hisse enflasyonu
GEÇEBİLİRSE korur. Geçemezse nominal artış görürsün ve fakirleşirsin.

Korunmanın koşulu şirket bazındadır: fiyatlama gücü olan, stoku hızlı dönen,
sabit faizli borçlu şirketler korunur. Regüle fiyatlı, uzun vadeli sabit
sözleşmeli, nakit ağırlıklı şirketler ezilir.""",
 sorular=["t13", "u09"], sure=8),

Ders("d602", "Faiz, TCMB ve para politikası",
 "Faizin borsayı üç ayrı kanaldan nasıl etkilediğini anlamak.",
 """POLİTİKA FAİZİ, TCMB'nin bankalara uyguladığı bir haftalık repo faizidir.
Piyasadaki tüm faizler bunun etrafında şekillenir.

Faizin borsaya üç kanaldan etkisi:

1) İSKONTO KANALI (genelde en güçlüsü)
   Risksiz getiri yükselince, riskli varlığa ödenen çarpan düşer. Şirketin kârı
   hiç değişmese bile hisse düşer. Bu, matematiksel bir zorunluluktur.

2) MALİYET KANALI
   Borçlu şirketin faiz gideri artar, net kârı düşer. Net Borç/FAVÖK'ü yüksek
   şirketler en çok etkilenir.

3) TALEP KANALI
   Kredi pahalanır, tüketici ertelenebilir harcamayı erteler. Otomotiv, beyaz
   eşya, konut önce etkilenir.

Ayrıca REKABET etkisi: mevduat faizi %40 iken, borsadan %25 beklenen getiri
elde etmek için risk almanın anlamı sorgulanır. Para borsadan mevduata kayar.

REEL FAİZ = Nominal faiz − Enflasyon
Pozitif reel faiz, tasarrufu ödüllendirir ve TL'yi destekler.
Negatif reel faiz, tasarrufu cezalandırır ve dövize/reel varlığa kaçış yaratır.""",
 bist="""Türkiye'de faiz kararları, gelişmiş ülkelere göre çok daha SERT ve
ÖNGÖRÜLEMEZ olabilir. Politika faizi kısa sürede yüzlerce baz puan değişebilir.

Bu, iki sonuç doğurur:
1) Uzun vadeli DCF varsayımları çok kırılgandır
2) Faiz kararı günleri (TCMB PPK toplantıları) borsada yüksek oynaklık yaratır

Takip edilecek takvim: TCMB PPK toplantıları (yılda 8), enflasyon açıklamaları
(her ayın 3'ü civarı), Fed toplantıları.

Bu sistem politika faizini otomatik izlemiyor (TCMB EVDS API anahtarı
gerektiriyor); enflasyonu borsapy üzerinden anahtarsız alıyor. Faizi elle
takip etmen gerekiyor.""",
 tuzak=""""Faiz indi, borsa yükselir" — indirimin SEBEBİ önemlidir:
· Enflasyon gerçekten düştüğü için indi → olumlu
· Siyasi baskıyla, enflasyon yüksekken indi → TL değer kaybeder, ikinci dalga
  olarak ithalatçı ve dövizli borçlu ezilir

Faiz kararını tek başına değil, kur ve enflasyon beklentisiyle birlikte oku.""",
 sorular=["t14", "o13"], sure=8),

Ders("d603", "Kur: kim kazanır, kim kaybeder",
 "Kur hareketinin bilançoya dört ayrı kanaldan nasıl girdiğini görmek.",
 """TL değer kaybettiğinde bir şirket dört kanaldan etkilenir:

1) GELİR — ihracat geliri dövizliyse TL karşılığı artar
2) MALİYET — ithal girdi TL cinsinden pahalanır
3) BİLANÇO — dövizli borç TL cinsinden şişer ve gelir tablosuna KUR FARKI
   ZARARI olarak düşer. Nakit çıkışı olmadan net kâr çöker.
4) TALEP — alım gücü düşer, iç talep daralır

Net etkiyi bulmak için tek bir kaleme bakılır: NET DÖVİZ POZİSYONU
  = Dövizli varlıklar − Dövizli yükümlülükler
Bu bilgi bilançonun ön yüzünde DEĞİL, DİPNOTLARDA yazar.

DOĞAL KORUMA (natural hedge): geliri de gideri de aynı para biriminde olan
şirket, kur hareketinden az etkilenir. THYAO buna örnektir.

Kabaca:
KAZANANLAR — ihracatçı sanayi, havacılık, dövizli gelirli turizm, madencilik
KAYBEDENLER — ithal girdili üretici, dövizli borçlu TL gelirli şirketler
              (enerji, telekom klasik örnek), iç talebe dayalı perakende""",
 bist="""Türkiye'de kur, borsanın en belirleyici tek değişkenidir. Sebep: BIST
şirketlerinin önemli kısmı ya ihracatçıdır ya dövizli borçludur.

Ve bir üst katman daha var: BIST'in kendisi dolar bazında ölçülür. Yabancı
yatırımcı için önemli olan endeksin TL getirisi değil, USD getirisidir.

Bu sistemin ölçtüğü rakam: XU100 son 3,29 yılda TL bazında +%221, ama USD
bazında sadece +%31. Yabancı yatırımcının gördüğü ikinci rakamdır.
(USD/TRY aynı dönemde 19,63'ten 48,08'e gitti — getirinin çoğu kur.)

Kur takibi için sistem USD/TRY ve EUR/TRY'yi izler; `makro` komutunda 1 gün,
1 ay, 3 ay ve 1 yıllık değişimleri gösterir ve enflasyona göre "TL reel
değerleniyor mu, kaybediyor mu" yorumunu yapar.""",
 tuzak=""""İhracatçı = kur kazananı" ezberi. Üç şeyi kontrol et:
1) İthal girdi oranı ne? Girdisi de ithalse net etki küçük.
2) Dövizli borcu var mı? Varsa kur farkı zararı geliri götürebilir.
3) İhracat fiyatı dövizli mi sabitlenmiş, yoksa dünya fiyatına mı bağlı?

Bilançoyu ve dipnotları görmeden karar verilmez.""",
 sorular=["t15", "u10"], sure=8),

Ders("d604", "Cari açık, CDS ve dış finansman",
 "Ülke riskinin borsaya nasıl fiyatlandığını anlamak.",
 """CARİ AÇIK: bir ülkenin dış dünyayla mal, hizmet ve gelir alışverişindeki
açığı. Türkiye yapısal olarak cari açık verir — enerji ithalatı ana sebeptir.

Neden önemli: cari açık finanse edilmek zorundadır. Finansman kaynakları:
· Doğrudan yatırım (en kaliteli, kalıcı)
· Portföy yatırımı (sıcak para, hızlı çıkabilir)
· Borçlanma
· Rezerv kullanımı

Finansman kalitesi düşükse, dış şok anında TL baskı altına girer.

CDS (Credit Default Swap): ülkenin borcunu ödeyememe riskine karşı sigorta
primi. Baz puan cinsinden ölçülür.
· Düşük CDS → düşük ülke riski → yabancı sermaye girişi kolay
· Yüksek CDS → yüksek risk primi → hem borçlanma pahalı hem borsa çarpanları
  baskılanır

CDS, borsanın çarpanını doğrudan etkiler: risk primi yükseldiğinde, aynı kâra
piyasa daha az ödemeye razı olur.

REZERVLER: TCMB'nin brüt ve net rezervleri. Net rezerv (swap hariç) TL'nin
savunulabilirliğinin göstergesidir.""",
 bist="""Bu sistemin makro paneli CDS'i doğrudan izlemiyor (veri kaynağı
gerektiriyor), ama vekil göstergeler var:
· VIX — küresel risk iştahı
· Dolar endeksi (DXY) — küresel dolar talebi
· Gelişen piyasalar endeksi (EEM) — BIST'in dahil olduğu varlık sınıfı
· ABD 10 yıllık faizi — gelişen piyasalardan çıkış baskısının ana sürücüsü

Sistemin "rejim" hesabı bu göstergelerden bir puan üretir: RİSK AÇIK, ılımlı,
temkinli, SAVUNMA. Momentum stratejileri risk açıkken çalışır; savunma
rejiminde nakitte beklemek kazançtır.

CDS'i ayrıca elle takip etmek isterseniz günlük olarak yayınlanır.""",
 tuzak=""""Cari açık kapandı, iyi haber" — cari açık BÜYÜMENİN yavaşlaması
yüzünden de kapanabilir. Yani iyi haber gibi görünen sayı, ekonominin
daraldığının işareti olabilir.

Sayının kendisine değil, SEBEBİNE bak.""",
 sure=7),

Ders("d605", "Küresel bağlantılar: Fed, emtia, risk iştahı",
 "BIST'in küresel sermaye akımlarına nasıl bağlı olduğunu görmek.",
 """BIST, GELİŞEN PİYASA (emerging market) varlık sınıfının parçasıdır.
Yabancı yatırımcı Türkiye'yi tek başına değil, bu sepetin bir üyesi olarak
değerlendirir.

Sonuç: Türkiye'de hiçbir şey olmasa bile, küresel risk iştahı düştüğünde BIST
düşer. "Bizim şirketlerimizin bununla ne ilgisi var?" sorusunun cevabı: fon
akımı.

Takip edilecek küresel değişkenler:

FED FAİZİ ve ABD 10 YILLIK TAHVİL FAİZİ
ABD'de risksiz getiri yükseldiğinde, gelişen piyasada risk almanın anlamı
azalır. Sermaye çıkar. Bu, gelişen piyasalar için en güçlü tek dış sürücüdür.

DOLAR ENDEKSİ (DXY)
Dolar güçlendiğinde gelişen piyasa para birimleri baskılanır.

VIX
Küresel korku endeksi. 20'nin altı sakin, 30'un üstü panik.

EMTİA FİYATLARI
· Petrol → Türkiye net ithalatçı, yükselişi cari açığı ve enflasyonu artırır
· Altın → risk iştahının tersine hareket eder
· Bakır → küresel sanayi talebinin göstergesi

MSCI GELİŞEN PİYASALAR ENDEKSİ
BIST'in göreli performansını ölçmek için referans.""",
 bist="""Bu sistem 12 makro göstergeyi izler ve bunlardan bir rejim puanı üretir:
VIX seviyesi, USD/TRY'nin aylık enflasyona göre hareketi, BIST'in gelişen
piyasalara göre 3 aylık göreli gücü, ABD 10 yıllık faizinin 3 aylık değişimi.

Bugünkü ölçüm: VIX 15,9 (risk iştahı açık), USD/TRY 1 ayda %1,8 (enflasyona
paralel), rejim "ılımlı" — normal işlem, pozisyon boyutunu abartma.

Rejim bilgisinin pratik değeri: hangi stratejinin çalışacağını belirler.
Momentum ve kırılım stratejileri risk iştahı açıkken işler. Savunma rejiminde
nakit oranını yükseltmek, kazanmak kadar değerlidir.""",
 tuzak=""""Türkiye'ye özgü bir hikâye buldum, küresel piyasa beni etkilemez" —
etkiler. Yabancı yatırımcı gelişen piyasa sepetinden çıkarken senin şirketinin
hikâyesine bakmaz, pozisyonunu kapatır.

Bu, özellikle BIST 30 gibi yabancı payının yüksek olduğu hisselerde belirgindir.""",
 sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 7 — TEKNİK ANALİZ
# ═══════════════════════════════════════════════════════════════════

M7 = Modul("m7", "Teknik analiz",
           "Ne alacağına temel analiz karar verir; ne zaman alacağına teknik "
           "analiz yardım eder. Ve göstergelerin kırıldığı yerler.", 2, [

Ders("d701", "Trendin gerçek tanımı",
 "Trendi hareketli ortalamayla değil, tepe-dip dizilimiyle tanımlamayı öğrenmek.",
 """Trend nedir? Çoğu kaynak "fiyat ortalamanın üstündeyse yükseliş trendi" der.
Bu bir KISAYOLDUR, tanım değildir.

Gerçek tanım YAPISALDIR:
· YÜKSELİŞ TRENDİ = her tepe bir öncekinden yüksek VE her dip bir öncekinden
  yüksek
· DÜŞÜŞ TRENDİ = her tepe bir öncekinden alçak VE her dip bir öncekinden alçak

İki ara durum vardır ve ikisi de bilgi taşır:
· SIKIŞMA — dipler yükseliyor ama tepe kırılamıyor. Bir taraf kazanmak üzere;
  kırılım yakın olabilir.
· BOZULMA — tepe yükseldi ama dip kırıldı. Trend zayıflıyor, dikkat.

Neden ortalama yerine bu: hareketli ortalama GECİKMELİ ve TÜRETİLMİŞ bir
göstergedir. Yapı ise fiyatın kendisidir. Trend, ortalama kesişmeden çok önce
bozulur ve yapıya bakan bunu görür.

Tepe ve dip nasıl belirlenir: bir barın solunda ve sağında belirli sayıda
(örneğin 5) daha alçak bar varsa o bir TEPEDİR. Kritik nokta: sağ taraf henüz
oluşmadığı için son barlar KESİNLEŞMEZ. Gerçek zamanlı analizde bu gecikme
kaçınılmazdır — geçmiş grafiğe bakıp "işte tepe" demek kolaydır.""",
 bist="""Bu sistemin `yapi` komutu tam bunu ölçer: son üç tepeyi ve son üç dibi
listeler, dizilime bakıp YÜKSELEN / DÜŞEN / sıkışan / bozulan der.

Ve fractal hesabında geleceğe bakmayı önlemek için sonucu kaydırır — son
`pencere` bar için tepe/dip kesinleşmez. Bu detay atlanırsa backtest gerçekte
mümkün olmayan bir bilgiyle çalışır ve sahte başarı üretir.""",
 tuzak=""""Fiyat 200 günlük ortalamanın üstünde, trend yukarı" — ortalama
yataysa ve fiyat etrafında dolaşıyorsa, trend YOKTUR. Ortalamanın kendisinin
EĞİMİNE de bakılmalıdır.

Ayrıca yapı ile ortalama çelişebilir: ASELS'te sistem bugün "kısa vadeli yapı
DÜŞEN" ama "üç zaman diliminde de yukarı" diyor. Bu çelişki değil, bilgidir:
güçlü trend içinde geri çekilme.""",
 sorular=["o10"], sure=7),

Ders("d702", "Destek, direnç ve hacim",
 "Seviyelerin neden çalıştığını ve neden tam da bu yüzden kırıldığını anlamak.",
 """DESTEK: fiyatın düşerken alıcı bulduğu seviye.
DİRENÇ: fiyatın yükselirken satıcı bulduğu seviye.

Neden çalışırlar? Mistik bir sebep yok — HAFIZA ve EMİR YOĞUNLAŞMASI:
· Orada daha önce alanlar var; fiyat oraya dönünce "başabaşa geldim" diye satar
· Orada almak isteyip kaçıranlar var; ikinci şansta alır
· Herkes aynı grafiğe baktığı için emirler orada yoğunlaşır

Kritik sonuç: çok bakılan seviye, tam da bu yüzden bir MIKNATIS ve bir
KIRILGANLIK noktasıdır. Herkesin stop'u aynı yerdeyse, oraya değdiğinde
zincirleme satış tetiklenir.

HACİM, seviyelerin güvenilirliğini belirler:
· Yüksek hacimle oluşan seviye → çok kişi orada işlem yapmış, güçlü
· Düşük hacimle oluşan seviye → zayıf

Ve kırılımda hacim TEYİT görevi görür:
· Hacimle kırılım → gerçek olma olasılığı yüksek
· Hacimsiz kırılım → sahte olma olasılığı yüksek

ROL DEĞİŞİMİ: kırılan direnç destek olur, kırılan destek direnç olur.""",
 bist="""Bu sistem kırılım stratejisinde `Hacim_orani > 1,4` şartı koyar:
kırılım gününün hacmi, son 20 günün ortalamasının en az 1,4 katı olmalı.

Bu şart olmadan backtest sonuçları belirgin şekilde kötüleşiyor — yani hacim
teyidi ölçülebilir bir katkı sağlıyor, bir inanç meselesi değil.

Ayrıca sistem hisse bazında SAHTE KIRILIM ORANI hesaplar: geçmişteki
kırılımların yüzde kaçı tutmuş? ASELS'te 91 kırılımın 59'u tutmuş (%65) —
yani bu hissede kırılımlar görece güvenilir. Her hissede aynı değildir.""",
 tuzak=""""Destek kırıldı, satmalıyım" refleksi — kırılımların önemli kısmı
SAHTEdir. Fiyat seviyenin altına sarkar, stopları toplar, sonra geri döner.
Buna "stop avı" denir ve likit olmayan hisselerde bilinçli olarak yapılabilir.

Korunma: kapanış teyidi bekle (gün içi delinme değil, kapanışta altında olmalı)
ve hacme bak.""",
 sure=7),

Ders("d703", "Hareketli ortalamalar",
 "En basit göstergenin ne işe yaradığını ve yatay piyasada neden battığını görmek.",
 """Hareketli ortalama (MA), fiyatın belirli bir dönemdeki ortalamasıdır. İki
tür:
· BASİT (SMA) — tüm günlere eşit ağırlık
· ÜSSEL (EMA) — son günlere daha çok ağırlık, daha hızlı tepki verir

Ne işe yarar: GÜRÜLTÜYÜ FİLTRELER. Günlük dalgalanmayı temizleyip yönü
gösterir.

Yaygın kullanımlar:
· 20 günlük → kısa vadeli trend, geri çekilme seviyesi
· 50 günlük → orta vadeli trend
· 200 günlük → uzun vadeli trend. "Boğa/ayı" ayrımının klasik sınırı.

KESİŞİM sinyalleri:
· Altın kesişim (golden cross) — 50 günlük 200 günlüğü yukarı keser
· Ölüm kesişimi (death cross) — tersi

Ama en önemli gerçek şudur: HAREKETLİ ORTALAMA GECİKMELİDİR. Tanımı gereği
geçmiş fiyattan hesaplanır. Sinyal geldiğinde hareketin bir kısmı bitmiştir.

Ve ikinci gerçek: YATAY PİYASADA SÜREKLİ YANLIŞ SİNYAL ÜRETİR. Fiyat ortalama
etrafında salınırken kesişimler arka arkaya gelir, her biri zarar ettirir.
Buna WHIPSAW denir.

Çözüm: bir TREND FİLTRESİ ekle. ADX gibi bir gösterge, trendin var olup
olmadığını söyler. Trend yoksa kesişimleri dikkate alma.""",
 bist="""Bu sistem 200 günlük ortalamayı bir FİLTRE olarak kullanır, sinyal
olarak değil: strateji sadece SMA200'ün üstündeki hisselerde alım arar.

Sebep basit ve ölçülmüş: SMA200 filtresi olmadan "aşırı satım tepkisi"
stratejisi düşen bıçağı yakalamaya dönüşüyor ve zarar ediyor.

ADX filtresi de kullanılıyor (ADX > 20). Ama burada dürüst bir uyarı var:
ADX eşiği tam 20'de sıçrıyor — ADX>20 ile +%117,7, ADX>15 ile +%61, ADX>25 ile
+%68. Bu keskin tepe AŞIRI UYDURMA işaretidir ve bu eşiğe güvenilmemeli.""",
 tuzak=""""Altın kesişim oldu, alalım" — bu sinyal geldiğinde fiyat genelde
dipten önemli ölçüde yükselmiştir. Kesişim, trendin BAŞLANGICINI değil,
DEVAM ETTİĞİNİ teyit eder.

Ayrıca ortalamalar kendi aralarında korele oldukları için, üç farklı ortalamaya
bakmak üç ayrı teyit DEĞİLDİR — aynı bilgiyi üç kez görmüş olursun.""",
 sorular=["o10"], sure=7),

Ders("d704", "Momentum göstergeleri: RSI, MACD, Stokastik",
 "Momentum göstergelerinin ne ölçtüğünü ve trendde neden yanılttıklarını görmek.",
 """RSI (Göreli Güç Endeksi), 0-100 arasında bir değer üretir. Son n günün
yükseliş hareketlerinin toplam harekete oranını ölçer.
· 70 üstü → geleneksel olarak "aşırı alım"
· 30 altı → "aşırı satım"

MACD, iki üssel ortalamanın farkıdır (12 ve 26 günlük). Bir de sinyal çizgisi
(9 günlük) vardır. Kesişimler alım/satım sinyali sayılır.

STOKASTİK, kapanışın son n günün aralığındaki konumunu ölçer.

Üçünün de ortak sorunu: TRENDDE YANILTIRLAR.

RSI güçlü bir yükseliş trendinde HAFTALARCA 70-80 arasında kalabilir.
"Aşırı alım, düşer" diye satılan hisse iki katına çıkabilir. Buna
"band walking" denir.

Doğru kullanım: momentum göstergesini TREND FİLTRESİYLE birlikte oku.
· Fiyat SMA200 üstünde + RSI 30 altı → trend içi geri çekilme, ALIM fırsatı
· Fiyat SMA200 altında + RSI 30 altı → düşen bıçak, uzak dur
· Fiyat SMA200 üstünde + RSI 80 → trend güçlü, satış sinyali DEĞİL

Kritik ayrım: RSI'nin yüksek olması, ELDEKİ pozisyonu satma sebebi değildir.
Yeni pozisyona girmek için kötü bir zaman olduğunu söyler. İkisi farklı
şeylerdir.""",
 bist="""Bu sistem RSI'yi skorun ZAMANLAMA bileşeninde kullanır — satış sinyali
olarak değil.

RSI 80 üstü olan hisse düşük zamanlama puanı alır. Sonuç: "trend ve şirket iyi
konumlanmış ama fiyat şu an giriş için pahalı nokta" mesajı.

Ölçülmüş kanıt: RSI(2) tabanlı aşırı satım tepki stratejisi bu veri setinde
%53 kazanma oranıyla bile ZARAR ediyor (−%22,0). Kırılım stratejisi neredeyse
aynı kazanma oranıyla (%48) +%117,7 yapıyor. Momentum göstergesine dayalı ters işlem, BIST'te
çalışmıyor.""",
 tuzak=""""RSI 70 üstü sat, 30 altı al" ezberi. Bu kural trendli piyasada
sistematik olarak para kaybettirir: kazananı erken satar, düşeni erken alır.

Göstergeler fiyatın matematiksel dönüşümüdür — YENİ BİLGİ ÜRETMEZLER, mevcut
bilgiyi düzenlerler.""",
 sorular=["o11"], sure=8),

Ders("d705", "Oynaklık: ATR ve Bollinger",
 "Oynaklığı ölçmeyi ve pozisyon boyutuna çevirmeyi öğrenmek.",
 """ATR (Ortalama Gerçek Aralık), fiyatın günlük olarak ne kadar oynadığını
ölçer. Gerçek aralık, şunların en büyüğüdür:
· Bugünün yükseği − bugünün düşüğü
· |Bugünün yükseği − dünkü kapanış|  (boşluğu yakalar)
· |Bugünün düşüğü − dünkü kapanış|

ATR'nin en değerli kullanımı YÖN DEĞİL, BOYUTLANDIRMADIR:
· Stop mesafesi = k × ATR (bu sistemde 2,0-2,5)
· Pozisyon adedi = risk bütçesi / stop mesafesi

Neden ATR ile: sabit yüzde stop (örneğin %5) yanlıştır çünkü her hissenin
oynaklığı farklıdır. Günde %1 oynayan hissede %5 stop çok geniş, günde %6
oynayanda çok dardır. ATR bunu otomatik ayarlar.

BOLLINGER BANTLARI: 20 günlük ortalama ± 2 standart sapma. Fiyatın
istatistiksel olarak nerede olduğunu gösterir.
· Bantlar daralıyorsa (squeeze) → oynaklık düşük, büyük hareket yaklaşıyor
  olabilir
· Bantlar genişliyorsa → oynaklık yüksek

Kritik uyarı: "banda değdi, döner" YANLIŞTIR. Güçlü trendde fiyat üst bant
boyunca YÜRÜR (band walking). Bollinger bir dönüş sinyali değil, bir
BAĞLAM göstergesidir.""",
 bist="""Bu sistem ATR'yi üç yerde kullanır:
1) Stop seviyesi — giriş − 2,0/2,5 × ATR (sinyali veren stratejiye göre)
2) Hedef — giriş + 4,0/5,0 × ATR
3) FİLTRE — ATR%'si 7'nin üstündeki hisseler elenir

Üçüncüsü önemli: günde %7+ oynayan hisse, kumar bölgesidir ve genelde brüt
takas/VBTS tedbiri riski taşır. Bu filtre, sistemin en çok hisse elediği
kuraldır.

Alt sınır da var (%0,8): hiç oynamayan hisseden getiri çıkmaz.""",
 tuzak=""""Oynaklık yüksek = risk yüksek" — kısmen doğru ama eksik. Oynaklık
ölçülebilir riski gösterir. Asıl tehlike, DÜŞÜK oynaklıkta gizlenen risktir:
sakin görünen bir hisse tek haberle %20 düşebilir.

BIST'te tavan/taban ±%20. ATR bunu öngöremez.""",
 sorular=["t18"], sure=8),

Ders("d706", "Kırılım, sahte kırılım ve Fibonacci",
 "Kırılımların çoğunun neden sahte olduğunu ve nasıl filtreleneceğini öğrenmek.",
 """KIRILIM (breakout): fiyatın belirli bir direnç seviyesini (örneğin son 20
günün zirvesi) aşması.

Mantığı: o seviyenin üstünde arz yok demektir; yeni alıcılar yeni fiyat
seviyesi arar.

SAHTE KIRILIM: fiyat seviyeyi aşar, ama tutunamaz ve geri döner. Literatürde
kırılımların yarıdan fazlasının sahte olduğu söylenir ve bu, hisse bazında
ÖLÇÜLEBİLİR bir şeydir.

Filtreleme yolları:
· HACİM TEYİDİ — kırılım günü hacmi ortalamanın belirgin üstünde olmalı
· KAPANIŞ TEYİDİ — gün içi delinme değil, kapanışta üstünde olmalı
· ZAMAN TEYİDİ — 2-3 gün üstünde kalmalı
· TREND FİLTRESİ — genel trend yukarıysa kırılımın tutma şansı artar

FIBONACCI GERİ ÇEKİLME SEVİYELERİ: bir hareketin %23,6, %38,2, %50, %61,8 ve
%78,6'sı.

Neden çalışır? Doğa yasası değil — KENDİ KENDİNİ GERÇEKLEŞTİREN BEKLENTİDİR.
Çok sayıda kişi aynı seviyelere bakar ve oraya emir koyar. Ve tam bu yüzden,
herkesin stop'u aynı yerde toplandığında o seviye kırılmaya açık hale gelir.

Fibonacci tek başına sinyal değildir. Seviyeye gelen fiyatın orada NE YAPTIĞINA
bak: hacimle tepki mi veriyor, yoksa geçip gidiyor mu?""",
 bist="""Bu sistem her hisse için SAHTE KIRILIM ORANINI geçmişten hesaplar:
20 günlük zirveyi aşan barları bulur, sonraki 3 gün seviyenin altına dönüp
dönmediğine bakar.

ASELS: 91 kırılımın 59'u tutmuş (%65) → kırılımlar görece güvenilir
THYAO: 65 kırılımın 42'si tutmuş (%65)

Bu bir hisse seçim kriteridir: kırılım stratejisi, kırılımı tutan hisselerde
uygulanmalıdır. Her hissede aynı davranış yoktur.""",
 tuzak=""""Fibonacci %61,8'e geldi, dönecek" — Fibonacci bir OLASILIK bölgesi
işaretler, bir kehanet değil. Fiyat oraya geldiğinde tepki verirse anlamlıdır;
vermezse seviye geçersizdir.

Ve seçici hafıza tuzağı: geçmiş grafikte Fibonacci'nin tuttuğu yerler göze
çarpar, tutmadığı yerler görünmez.""",
 sorular=["o10"], sure=8),

Ders("d707", "Çoklu zaman dilimi analizi",
 "Büyük resmin yönü belirlediğini, küçük resmin zamanlamayı verdiğini öğrenmek.",
 """Aynı hisse, farklı zaman dilimlerinde farklı hikâyeler anlatır. Günlük
grafikte düşüyor olabilir, haftalıkta yükseliyor olabilir. İkisi de doğrudur.

TEMEL KURAL: büyük zaman dilimi YÖNÜ belirler, küçük zaman dilimi ZAMANLAMAYI
verir.

Pratik kullanım:
1) AYLIK grafiğe bak → ana trend ne? Bu, yönü belirler.
2) HAFTALIK grafiğe bak → orta vadeli yapı ne?
3) GÜNLÜK grafiğe bak → giriş noktası nerede?

Üçü de aynı yöndeyse en elverişli durumdur. Çeliştiklerinde:
· Aylık yukarı + günlük aşağı → trend içi geri çekilme. Alım fırsatı olabilir.
· Aylık aşağı + günlük yukarı → tepki yükselişi. Kısa tut, hedefi küçült.
· Hepsi aşağı → uzun taraf için girme.

Neden bu sıra: küçük zaman diliminde gördüğün "güçlü yükseliş", büyük zaman
diliminde bir düşüş trendinin içindeki geçici tepki olabilir. Akıntıya karşı
yüzmek, aynı işi çok daha zor hale getirir.

Yaygın hata: sadece günlük grafiğe bakıp karar vermek. Günlük grafik gürültü
oranı en yüksek olan zaman dilimidir.""",
 bist="""Bu sistemin `yapi` komutu üç zaman dilimini birlikte gösterir ve bir
UYUM hükmü verir: TAM UYUM (yukarı/aşağı), kısmi uyum, ÇELİŞKİ.

Ölçülmüş örnekler:
· ASELS: günlük yukarı, haftalık yukarı, aylık yukarı → TAM UYUM. En elverişli.
· THYAO: günlük aşağı, haftalık aşağı, aylık yukarı → kısmi uyum,
  "pozisyonu küçült" uyarısı.

Bu bilgi pozisyon BOYUTUNU etkilemeli: tam uyumda normal boyut, çelişkide
küçültülmüş boyut.""",
 tuzak=""""Günlük grafikte harika görünüyor" — hangi zaman diliminde işlem
yaptığını netleştir. 2 hafta tutacaksan günlük ve haftalık grafik senin
zaman dilimindir; 15 dakikalık grafiğe bakmanın anlamı yoktur.

Zaman dilimi karışıklığı, en sık görülen tutarsızlık kaynağıdır: günlük
grafiğe bakıp alım yapıp, saatlik grafiğe bakıp panikle satmak.""",
 sure=7),

Ders("d708", "Göstergelerin kırıldığı yerler",
 "Her göstergenin ne zaman yanılttığını topluca görmek — teknik analizin en değerli kısmı.",
 """Çoğu kaynak göstergenin NE olduğunu anlatır, NE ZAMAN işe yaramadığını
anlatmaz. Asıl fark orada.

RSI — güçlü trendde haftalarca 70 üstünde kalır. Yatay piyasada işe yarar,
trendde yanıltır.

HAREKETLİ ORTALAMA KESİŞİMİ — yatay piyasada sürekli yanlış sinyal (whipsaw).
Trend filtresi olmadan kullanılmaz.

MACD — geç kalır. Sinyal geldiğinde hareketin önemli kısmı bitmiştir.

BOLLINGER — "banda değdi, döner" yanlıştır. Güçlü trendde fiyat bant boyunca
yürür.

DESTEK/DİRENÇ — çok bakılan seviye, tam da bu yüzden kırılır. Herkesin stop'u
aynı yerdeyse orası bir mıknatıstır.

KIRILIM — önemli kısmı sahtedir. Hacim teyidi şarttır.

FORMASYONLAR — geçmiş grafikte herkes görür. Gerçek zamanda formasyonun
tamamlanıp tamamlanmayacağı belli değildir. Seçici hafıza en büyük tuzaktır.

FIBONACCI — kendi kendini gerçekleştiren beklentidir, doğa yasası değil.

VE HEPSİ BİRDEN — beş gösterge aynı şeyi söylüyorsa, bu beş ayrı teyit
DEĞİLDİR. Hepsi aynı fiyat serisinden türer; tek bir bilgiyi beş kez duyarsın.
Buna "sahte çeşitlilik" denir ve güven duygusunu haksız yere artırır.

Genel kural: göstergeler fiyatın matematiksel dönüşümüdür. Yeni bilgi
ÜRETMEZLER. Hepsi tanımı gereği GECİKMELİDİR.""",
 bist="""Bu sistem üç stratejiyi 3,28 yıllık BIST verisinde ölçtü ve sonuç,
göstergelere körü körüne güvenmemek gerektiğini gösteriyor:

· "tepki" (RSI2 aşırı satım): %53 kazanma oranı, ama −%22,0 getiri
· "kirilim" (Donchian + hacim): %48 kazanma oranı, +%117,7 getiri

Kazanma oranları neredeyse eşit; getiri arasında 140 puan fark var. Sebep
kazanç/kayıp büyüklüğü: kırılımın ortalama kazancı %15,5 / kaybı %7,9;
tepkinin kazancı %4,0 / kaybı %5,5.

Ve sistem iki dürüstlük notu tutuyor: (1) kırılımın ADX eşiği tam 20'de
sıçrıyor — aşırı uydurma işareti, ölçülen +%117,7 gerçekte olacağından iyimser.
(2) Aynı dönemde XU100 al-tut +%221 getirdi; üç strateji de endeksin altında.""",
 tuzak="""En tehlikeli tuzak: göstergeleri ARTIRARAK güven kazanmaya çalışmak.
"7 göstergem var, hepsi al diyor" cümlesi, tek bir sinyalin yedi kez
tekrarlanmasından ibaret olabilir.

Doğru yaklaşım: az sayıda, BİRBİRİNDEN FARKLI bilgi kaynağı. Örneğin biri
trend (yapı), biri momentum, biri hacim, biri temel — bunlar gerçekten farklı
şeyler ölçer.""",
 sorular=["o10", "o11", "o12"], sure=9),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 8 — RİSK YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════

M8 = Modul("m8", "Risk yönetimi",
           "İyi yatırımcı ile kötü yatırımcı arasındaki en büyük fark. Strateji "
           "getiriyi belirler, risk yönetimi hayatta kalıp kalmayacağını.", 2, [

Ders("d801", "Kayıp asimetrisi",
 "Neden kaybı küçük tutmanın kazancı büyütmekten daha değerli olduğunu görmek.",
 """Yüzdeler simetrik DEĞİLDİR. %50 kaybettikten sonra %50 kazanmak seni başa
döndürmez.

100 → %50 kayıp → 50 → %50 kazanç → 75

Geri kazanma formülü: gereken kazanç = kayıp / (100 − kayıp)

  %10 kayıp → %11 gerekir
  %20 kayıp → %25
  %33 kayıp → %50
  %50 kayıp → %100
  %75 kayıp → %300
  %90 kayıp → %900

Bu asimetri, risk yönetiminin TAMAMININ sebebidir. Kaybı küçük tutmak,
kazancı büyütmekten matematiksel olarak daha değerlidir.

İkinci sonuç: OYNAKLIK ZARARLIDIR. Aynı ortalama getiriye sahip iki portföyden
oynaklığı düşük olan, daha çok para biriktirir. Sebep aynı asimetri.

  +%50 sonra −%50 → 0,75 kalır
  +%10 sonra −%10 → 0,99 kalır

Üçüncü sonuç: KURTARILAMAZ NOKTA vardır. %90 kaybettikten sonra pratikte geri
dönüş yoktur. Bu yüzden risk yönetiminin ilk amacı kazanmak değil, OYUNDA
KALMAKTIR.""",
 bist="""Bu sistem işlem başına %1,5 risk kullanır. Sebep doğrudan bu
asimetridir:

· %1,5 risk ile üst üste 10 kayıp → sermaye %14 düşer, geri kazanmak için %16
  gerekir. Dayanılabilir.
· %20 risk ile üst üste 10 kayıp → sermaye %89 düşer, geri kazanmak için %790
  gerekir. Pratikte imkânsız.

Ve Monte Carlo simülasyonu gösteriyor ki 200 işlemde en uzun kayıp serisi
19 İŞLEM olabiliyor. "Üst üste 10 kayıp gelmez" varsayımı yanlıştır.""",
 tuzak=""""Bir kere büyük vurayım, sonra dikkatli olurum" — bu düşünce, geri
dönüşü olmayan bir kayba giden en kısa yoldur. Büyük pozisyon bir kez yanlış
gittiğinde, sonrasında "dikkatli olacak" bir sermaye kalmaz.""",
 sorular=["u12"], sure=7),

Ders("d802", "Pozisyon boyutlandırma",
 "'Kaç lot alayım' sorusunun doğru cevabının nasıl hesaplandığını öğrenmek.",
 """Yanlış soru: "kaç lot alayım?"
Doğru soru: "bu işlem yanlış giderse kaç TL kaybetmeyi göze alıyorum?"

Formül:
  Risk bütçesi = Sermaye × İşlem başına risk %
  Stop mesafesi = Giriş fiyatı − Stop fiyatı
  Adet = Risk bütçesi / Stop mesafesi

Örnek: 1.000 TL sermaye, %1,5 risk = 15 TL bütçe.
EREGL 38,28 TL, stop 36,38 TL → mesafe 1,90 TL.
Adet = 15 / 1,90 = 7,9 → 7 adet. Maliyet 268 TL.

Bu yöntemin güzelliği: oynak hissede otomatik olarak az, sakin hissede çok
adet alırsın. Her işlemin RİSKİ eşitlenir.

İKİNCİ TAVAN gereklidir: tek hissede sermayenin en fazla %X'i. Sebep, stop'un
garanti olmamasıdır. Boşluklu açılışta hesapladığından fazla kaybedebilirsin,
o yüzden ağırlık sınırı bir güvenlik ağıdır.

RİSK YÜZDESİ NE OLMALI:
· %0,5-1 → çok temkinli, öğrenme aşaması için uygun
· %1-2 → standart
· %2-5 → agresif, deneyim gerektirir
· %5+ → hayatta kalma süreni ciddi şekilde kısaltır""",
 bist="""1.000 TL'de acı bir gerçek var: BIST'te KESİRLİ HİSSE YOK.

TKFEN 218,10 TL. %1,5 risk bütçesi 15 TL. Ama 1 adedin stop riski 25,30 TL —
bütçenin üstünde. Sistem "alınamıyor, bu hisse için ~1.687 TL sermaye gerekir"
diyor.

Yani küçük sermayede asıl kısıt strateji değil, TAM ADET ZORUNLULUĞUDUR.
Pahalı hisseler otomatik olarak dışarıda kalır ve seçim havuzun daralır.

Bu bir kusur değil, gerçektir. Zorlamak için risk yüzdesini yükseltmek,
hayatta kalma süreni kısaltır.""",
 tuzak=""""Bu işleme çok güveniyorum, büyük gireyim" — güven duygusu bir bilgi
DEĞİLDİR. Geçmişte en emin olduğun işlemlerin sonuçlarına bak; muhtemelen
ortalamadan farklı değildir.

Pozisyon boyutu, güvenden değil, MATEMATİKTEN gelmelidir.""",
 sorular=["t18", "u12"], sure=8),

Ders("d803", "Beklenen değer ve Kelly",
 "Bir stratejinin uzun vadede kazanıp kazanmayacağını hesaplamayı öğrenmek.",
 """BEKLENEN DEĞER, bir stratejinin işlem başına matematiksel beklentisidir:

  BD = (Kazanma oranı × Ortalama kazanç) − (Kaybetme oranı × Ortalama kayıp)

Pozitifse strateji uzun vadede kazandırır. Negatifse, ne kadar oynasan da
kaybedersin — kısa vadeli şans bunu değiştirmez.

KRİTİK SEZGİ: kazanma oranı tek başına hiçbir şey söylemez.

Bu sistemin ölçtüğü üç örnek:
· %53 kazanma, ort. kazanç %4,0, ort. kayıp %5,5 → BD NEGATİF, zararda
· %48 kazanma, ort. kazanç %15,5, ort. kayıp %7,9 → BD POZİTİF, +%117,7
· %90 kazanma, ort. kazanç %1,0, ort. kayıp %15,0 → BD NEGATİF

Üçüncüsü özellikle öğreticidir: 10 işlemin 9'unu kazanıp yine de batabilirsin.

BAŞABAŞ KAZANMA ORANI = ort. kayıp / (ort. kazanç + ort. kayıp)
Ödül/risk 1:2,21 olan bir sistemde başabaş için sadece %31 kazanma yeter.

KELLY KRİTERİ, teorik optimum pozisyon büyüklüğünü verir:
  Kelly = (kazanma oranı × (ödül/risk + 1) − 1) / (ödül/risk)

UYARI: tam Kelly matematiksel olarak optimaldir ama DAYANILMAZ derecede
oynaktır — %50 düşüşler normaldir. Profesyoneller çeyrek Kelly kullanır.""",
 bist="""Bu sistemin kırılım stratejisi için hesap:
Tam Kelly sermayenin %21,4'ünü söylüyor. Çeyrek Kelly ile %5,3.

Sistem varsayılan olarak %1,5 kullanıyor — çeyrek Kelly'nin bile altında.
Sebep: Kelly, kazanma oranının ve ödül/riskin GELECEKTE DE AYNI KALACAĞINI
varsayar. Gerçekte kenar zamanla aşınır ve piyasa rejimi değişir.

Backtest rakamları geçmişe uydurulmuş olabileceği için, Kelly'yi olduğu gibi
kullanmak hesaplanandan çok daha riskli olur.""",
 tuzak="""Monte Carlo simülasyonunun YUKARI tarafına güvenmek. Sistem %10
riskle "medyan 1050x" gösteriyor — bu bir hedef değil, uyarıdır. O sayıyı
üreten risk seviyesi seni aynı hızla sıfıra da götürebilir (%9,3 batma
olasılığı).

Bu tür simülasyonlardan alınacak tek sağlam bilgi AŞAĞI taraftır.""",
 sorular=["o12"], sure=9),

Ders("d804", "Çeşitlendirme ve korelasyon",
 "Kaç hisse tutmanın yeterli olduğunu ve gizli yoğunlaşmayı tanımayı öğrenmek.",
 """Çeşitlendirme, ŞİRKETE ÖZGÜ riski azaltır. Bir şirketin başına gelen kötü
olay (dava, yangın, muhasebe skandalı) portföyün tamamını silmesin diye.

Ama SİSTEMATİK riski (tüm piyasayı etkileyen) azaltmaz. Piyasa çökerse her şey
çöker.

Matematiği (tipik BIST hissesi, yıllık oynaklık ~%45, ortalama korelasyon 0,5):
   1 hisse  → portföy oynaklığı %45,0
   2 hisse  → %39,0
   4 hisse  → %35,6
   8 hisse  → %33,8
  20 hisse  → %32,6

Dikkat: 1'den 4'e çıkmak büyük fayda sağlıyor. 8'den 20'ye çıkmak neredeyse
hiçbir şey. Sebep KORELASYON — aynı piyasadaki hisseler birlikte hareket eder.

GİZLİ YOĞUNLAŞMA en sık yapılan hatadır. 5 farklı hisse tutuyor olabilirsin
ama hepsi:
· Aynı sektördeyse (5 banka)
· Aynı makro faktöre bağlıysa (hepsi faize duyarlı, hepsi kur kazananı)
· Aynı holding grubundaysa
· Aynı müşteri tabanına satıyorsa (hepsi iç talep)

...bu çeşitlendirme değil, tek bahsin beş parçaya bölünmesidir.

ETKİN HİSSE SAYISI, gerçek çeşitlendirmeyi ölçer: 5 hissen olabilir ama etkin
sayı 1,8 çıkabilir.""",
 bist="""Bu sistem `risk/portfoy` hesabında ortalama korelasyonu ve etkin hisse
sayısını ölçer. Ortalama korelasyon 0,7'nin üstündeyse açık uyarı verir:
"bu portföy çeşitlendirilmiş GÖRÜNÜYOR ama tek bir bahis gibi hareket ediyor."

BIST'e özgü bir zorluk daha var: 1.000 TL ile gerçek çeşitlendirme neredeyse
imkânsızdır. Kesirli hisse olmadığı için 2-3 pozisyona sıkışırsın ve sonucu
büyük ölçüde şans belirler.

Bu, sermaye artırmanın neden strateji iyileştirmekten daha etkili olduğunun
matematiksel sebebidir.""",
 tuzak=""""20 hisse aldım, riskim yok" — piyasa riski çeşitlendirilemez.
20 BIST hissesi tutan biri, BIST düştüğünde düşer.

Sistematik riski yönetmenin tek yolu NAKİT ORANIDIR. Nakit bir pozisyondur ve
kötü rejimde en değerli pozisyondur.""",
 sorular=["t19", "u14"], sure=8),

Ders("d805", "Stop-loss: ne yapar, ne yapmaz",
 "Stop'un neden garanti olmadığını ve doğru nasıl kullanıldığını öğrenmek.",
 """STOP-LOSS, kaybı önceden belirlenen bir seviyede sınırlama emridir.

Asıl işlevi psikolojiktir: kararı SAKİN OLDUĞUN ANDA verirsin, panik anında
değil. Kayıp büyüdükçe rasyonel karar verme yeteneği düşer; stop bunu
devre dışı bırakır.

NEREYE KONULUR:
· ATR bazlı — giriş − k×ATR. Hissenin kendi oynaklığına uyarlanır.
· Yapı bazlı — son önemli dibin altına
· Yüzde bazlı — en kaba yöntem, hisseden hisseye oynaklık farkını görmez

İZ SÜREN STOP (trailing): fiyat yükseldikçe stop'u yukarı çekmek. Kârı korur.
Ama çok sıkı çekilirse normal dalgalanmada seni dışarı atar.

STOP GARANTİ DEĞİLDİR — bu, en pahalı yanılgıdır:
· Boşluklu açılışta stop seviyesinin ALTINDAN gerçekleşir
· Likit olmayan hissede kayma büyük olur
· Tavan/taban kuralı BIST'te ±%20; bir gecede bu kadar boşluk gerçektir

Bu sistemin backtestinde en kötü işlemler tam olarak bunlar: stop 2×ATR (~%5)
olmasına rağmen %12-20 kayıp. "Stop koydum, riskim %2" cümlesi eksiktir.""",
 bist="""Midas'ta İZ SÜREN STOP YOKTUR. Elle yönetmen gerekir.

Bu sistem `portfoy` komutunda her gün hesaplar ve söyler: "stop'u 36,38 → 38,10
yukarı çek". Mobil uygulamada bunun yanında bir "Uygula" düğmesi var — ama
Midas'ta emri güncellemeyi unutma; sistem sadece kayıt tutar.

Ayrıca sistem "azami tutma süresi" kuralı da uygular: strateji tipine göre
6-25 iş günü. Süre dolduğunda sinyal gelmese bile çıkılır. Sebep: sermayenin
işlemeyen bir pozisyonda kilitli kalması, fırsat maliyetidir.""",
 tuzak=""""Stop'a değdi ama hisse geri döndü, stop kullanmayacağım" — bu, bir
kez yaşanan olaydan genel kural çıkarmaktır. Stop bazen seni erken çıkarır;
karşılığında BÜYÜK kayıplardan korur.

Sistem stop'suz test edildiğinde ortalama getiri artabilir ama azami düşüş
katlanır — ve o düşüşe psikolojik olarak dayanamayıp sistemi terk edersin.""",
 sorular=["o08"], sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 9 — PORTFÖY YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════

M9 = Modul("m9", "Portföy yönetimi",
           "Tek tek hisseleri seçmek işin yarısı. Diğer yarısı: ne kadarını, "
           "ne zaman, hangi ağırlıkla tutacağın.", 2, [

Ders("d901", "Varlık dağılımı ve nakit",
 "Nakdin bir pozisyon olduğunu ve rejime göre ayarlandığını anlamak.",
 """Getirinin büyük kısmı, hangi hisseyi seçtiğinden değil, VARLIK DAĞILIMINDAN
gelir: paranın ne kadarı hissede, ne kadarı nakitte, ne kadarı başka varlıkta.

NAKİT BİR POZİSYONDUR. "Nakitte bekliyorum" pasiflik değil, aktif bir karardır.
İki şey sağlar:
1) Düşüşte kayıp yaşamazsın (asimetri dersini hatırla)
2) Fırsat çıktığında hareket edebilirsin

Rejime göre nakit oranı:
· RİSK AÇIK → %15 civarı
· ılımlı → %30
· temkinli → %45
· SAVUNMA → %70

Portföy zirveden %15+ aşağıdaysa bu oranlar yükseltilir. Sebep: düşüş
dönemlerinde iki hata yaygındır — hepsini satıp dibi kaçırmak, ya da "geri
alacağım" diye riski artırmak. İkisi de sistemi terk etmektir.

Türkiye'de ek bir alternatif var: mevduat faizi %40 civarında. Bu, nakit
tutmanın FIRSAT MALİYETİNİ düşürür — nakit beklerken bile getiri elde
edersin. Gelişmiş ülkelerde nakit sıfır getirir, burada getirir.

Bu, BIST'te nakit oranını yüksek tutmayı gelişmiş ülkelere göre daha cazip
hale getirir.""",
 bist="""Bu sistemin `dagitim` komutu üç profil sunar (temkinli/dengeli/agresif)
ve gerçek bir kısıtı gösterir:

1.000 TL, dengeli profil, 4 aday → sadece 431 TL yerleşebiliyor, %57 nakitte
kalıyor. Sebep tam adet zorunluluğu: TKFEN 218 TL, bütçe payı 175 TL, alınamıyor.

Sistem bunu bir hata olarak değil, gerçek olarak raporluyor: "küçük sermayede
bu kaçınılmazdır — zorlamak için pahalı hisseyi atlamak, ucuz ama kötü hisseye
yönelmekten iyidir."

Ayrıca sistem rejime göre nakit önerisi verir ve şu matematiği hatırlatır:
sermayeni %50 kaybedersen başa dönmek için %100 kazanman gerekir.""",
 tuzak=""""Param boş duruyor, bir şey alayım" — bu, en pahalı dürtülerden
biridir. Sinyal yoksa işlem yapılmaz.

Bu sistem bazı günler "bugün hiçbir hisse giriş sinyali vermiyor" diyor ve
bunu bir sorun olarak sunmuyor. Nakitte beklemek de bir pozisyondur.""",
 sure=7),

Ders("d902", "Ağırlıklandırma ve yeniden dengeleme",
 "Eşit ağırlık ile momentum ağırlığı arasındaki farkı ve hangisinin ne zaman doğru olduğunu bilmek.",
 """AĞIRLIKLANDIRMA yöntemleri:

EŞİT AĞIRLIK — her pozisyona aynı tutar. Basit, şeffaf, kimseyi kayırmaz.
Küçük portföyde genelde en iyisidir.

RİSK BAZLI (risk parity) — her pozisyon aynı RİSKİ taşısın. Oynak hisseye az,
sakin hisseye çok tutar konur. Bu sistemin ATR bazlı boyutlandırması bunu yapar.

GÜVEN BAZLI — en beğendiğine en çok. Teorik olarak cazip, pratikte tehlikeli:
güven duygusu bir bilgi değildir ve en çok güvendiğin işlem en büyük kaybın
olabilir.

YENİDEN DENGELEME: ağırlıklar hedeften saptığında düzeltmek. Kazananı kısmen
satıp kaybedeni almak demektir — sezgiye aykırıdır ama riski hedefte tutar.

KRİTİK AYRIM — ve bu çok karıştırılır:
· AL-TUT portföyünde yeniden dengeleme DOĞRUDUR. Riski sabit tutar.
· MOMENTUM sisteminde yeniden dengeleme YANLIŞTIR. Momentum stratejisinin
  mantığı kazananı TUTMAK, kaybedeni STOP'la kesmektir. Kazananı satıp
  kaybedeni almak, stratejinin tam tersini yapmaktır.

Hangi sistemi kullandığını bil ve kurallarını karıştırma.""",
 bist="""Bu sistem momentum/kırılım tabanlıdır. Bu yüzden `dagitim` komutu
dengeleme kontrolü yapar ama açık bir not düşer:

"Momentum sistemi kullanıyorsan yeniden dengeleme YAPMA — kazananı satmak
stratejinin mantığına aykırıdır. Dengeleme, uzun vadeli al-tut portföyleri
içindir."

Küçük sermayede pratik bir kısıt daha var: dengeleme işlem gerektirir, işlem
kayma maliyeti doğurur. 1.000 TL'lik portföyde sık dengeleme, faydasından çok
maliyet üretir.""",
 tuzak=""""Kazanan pozisyonu büyüteyim, iyi gidiyor" (piramitleme) — bu bazı
sistemlerde meşru bir tekniktir ama kuralı önceden yazılmış olmalıdır. Anlık
hevesle pozisyon büyütmek, en büyük pozisyonun en tepede oluşmasına yol açar.""",
 sure=7),

Ders("d903", "Performans ölçümü: doğru sayıya bakmak",
 "Getirinin tek başına yetersiz olduğunu, risk düzeltilmiş ölçüleri öğrenmek.",
 """"%40 kazandım" cümlesi tek başına bir şey ifade etmez. Sorulacaklar:

1) NE KADAR RİSK ALARAK? — %40 getiri için %60 düşüş yaşadıysan, bu iyi bir
   sonuç değildir.
2) NE KADAR SÜREDE? — 5 yılda %40, yılda %7 demektir.
3) ALTERNATİFE GÖRE NEREDE? — mevduat %40 verirken borsadan %40 almak, risk
   karşılığı SIFIR getiri demektir.
4) ENFLASYONA GÖRE NEREDE? — %31,8 enflasyonda %40 nominal getiri, reel %6'dır.

ÖLÇÜLER:

SHARPE ORANI = (Getiri − Risksiz getiri) / Oynaklık
Aldığın risk başına ne kazandığını ölçer. Risksiz getiri Türkiye'de %40
civarıdır ve bunu hesaba katmayan Sharpe yanıltır.

SORTINO = aynı ama sadece AŞAĞI yönlü oynaklığı sayar. Yukarı oynaklık risk
değildir, o yüzden daha adil bir ölçüdür.

AZAMİ DÜŞÜŞ (max drawdown) = zirveden dibe en büyük kayıp. Psikolojik olarak
en önemli sayı: buna dayanamayıp sistemi terk edersen, ortalama getirinin
hiçbir anlamı kalmaz.

CALMAR = Yıllık getiri / Azami düşüş. "Yaşadığın acı başına kazanç."

KAZANMA ORANI ve KÂR FAKTÖRÜ = toplam kazanç / toplam kayıp.""",
 bist="""Bu sistemin ölçtüğü rakamlar, dersin tamamını örnekliyor:

(2026-08-26 ölçümü · 3,29 yıl · Sharpe %40 risksiz getiriye göre)

kirilim : +%117,7 getiri · Sharpe −0,71 · azami düşüş −%11,3
trend   : +%82,1 getiri · Sharpe −0,91 · azami düşüş −%16,1
XU100   : +%221,1 getiri · Sharpe −0,03 · azami düşüş −%22,9

BÜTÜN SHARPE'LAR NEGATİF. Sebebi basit ve acı: kirilim yıllık %26,7
kazandırdı, aynı dönemde mevduat %40 veriyordu. Risksiz alternatifin altında
kalan bir stratejinin risk-ayarlı skoru negatiftir.

Endeks düşüşü en çok yaşattı (−%22,9), ama risk-ayarlı olarak stratejilerin
HEPSİNDEN iyiydi. "Daha az düşüşle daha az kazanmak" tek başına başarı
değildir; ölçüt mevduattır.

Ve dürüst not: aynı dönemde USD bazında XU100 +%31, kirilim −%11. Nominal TL
getirisi, gerçeğin sadece bir kısmını anlatıyor.

Bu rakamlar 2026-08-26'da düzeltildi: backtest o güne kadar Sharpe'ı risksiz
getiriyi ÇIKARMADAN hesaplıyordu ve kirilim için 1,93 gösteriyordu. Sistem,
bu dersin bir alt satırında uyardığı hatayı kendisi yapıyormuş.

Sistem Sharpe'ı risksiz getiriye göre hesaplar — %40 varsayılan. Bunu sıfır
almak, Türkiye'de her stratejiyi olduğundan iyi gösterir.""",
 tuzak=""""Getirim yüksek, iyi yatırımcıyım" — kısa dönemde getiri, beceriden
çok ŞANSTAN gelir. Beceriyi ayırt etmek için çok sayıda işlem ve uzun süre
gerekir.

Bu yüzden SÜREÇ ölçülür, sonuç değil: kurallara uydun mu, tez yazdın mı,
pozisyon boyutu doğru muydu?""",
 sorular=["u15"], sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 10 — YATIRIM PSİKOLOJİSİ
# ═══════════════════════════════════════════════════════════════════

M10 = Modul("m10", "Yatırım psikolojisi",
            "En pahalı hatalar bilgi eksikliğinden değil, duygudan doğar. "
            "Bu modül kendi kendine sabotajın kataloğudur.", 1, [

Ders("d1001", "Kayıptan kaçınma ve dispozisyon etkisi",
 "Neden kazananı erken satıp kaybedeni yıllarca tuttuğunu anlamak.",
 """İnsan beyni kaybı, aynı büyüklükteki kazançtan yaklaşık İKİ KAT güçlü
hisseder. 100 lira kaybetmenin acısı, 100 lira kazanmanın sevincinden büyüktür.

Bu asimetri iki davranış üretir:

DİSPOZİSYON ETKİSİ — kazananı erken satmak, kaybedeni tutmak.
Sebep: kâr realize etmek iyi hissettirir (kazanç kesinleşir), zarar realize
etmek acı verir (kayıp kesinleşir, "hata yaptım" itirafı olur).

Sonucu felakettir: küçük kârlar, büyük zararlar. Beklenen değer negatife döner.
Kazanma oranın yükselir ama paran azalır.

BATIK MALİYET YANILGISI — "bu kadar bekledim, şimdi satamam."
Geçmişte kaybettiğin para, bugünkü karara girmez. Doğru soru şudur:
"Bu hisseyi bugün, bu fiyattan, sıfırdan alır mıydım?" Cevap hayırsa satmalısın.

Korunma yolları:
· Stop'u ÖNCEDEN belirle ve mekanik uygula
· Yanılma koşulunu ALIM ÖNCESİ yaz
· Kararı, verildiği andaki bilgiye göre değerlendir""",
 bist="""Bu sistem üç yerde bu etkiye karşı koyar:

1) Stop ve hedef alım anında hesaplanır ve kaydedilir
2) `portfoy` komutu her gün "SAT" ya da "TUT" der — kararı sana bırakmaz,
   kuralı hatırlatır
3) Tez modülü, yanılma koşulunu alımdan ÖNCE yazdırır

Ve ölçülmüş kanıt: "tepki" stratejisi %54 kazanma oranıyla zarar ediyor,
"kirilim" %46 ile kazanıyor. Yüksek kazanma oranı, tam da bu davranışın
ürünüdür — küçük kârları erken almak.""",
 tuzak=""""Zarardayım ama satmam, ortalama düşürürüm" — zararına ortalama
düşürmek, yanılmış olma ihtimaline karşı bahsi BÜYÜTMEKTİR.

Profesyoneller kazanan pozisyonu büyütür, kaybedeni değil. Tersini yapmak,
en büyük pozisyonun en kötü fikirde oluşmasına yol açar.

Sistem bunu tespit edip uyarı verir: girişin altında %5+ ekleme yapıyorsan
"DUR" seviyesinde uyarı çıkar.""",
 sorular=["o08", "t20"], sure=8),

Ders("d1002", "FOMO, sürü davranışı ve kovalama",
 "Yükselen hisseyi kovalama dürtüsünün mekanizmasını tanımak.",
 """FOMO (Fear Of Missing Out): kaçırma korkusu.

Mekanizması: bir hisse hızla yükselir. Sen almamışsındır. Her gün yükselişi
izlersin. "Bu kadar yükseldiyse bir bildikleri var" düşüncesi oluşur. Sonunda
dayanamayıp en tepede alırsın.

Bu, en pahalı davranışsal hatadır çünkü SİSTEMATİK olarak zirvede alım
yaptırır.

SÜRÜ DAVRANIŞI: herkesin aldığını almak psikolojik olarak güvenlidir. Yanılırsan
bile yalnız yanılmamış olursun. Ama piyasada çoğunluğun yaptığı şey, tanımı
gereği fiyata çoktan yansımıştır.

ÇAPA ETKİSİ (anchoring): ilk gördüğün fiyata takılmak.
"40 liraydı, şimdi 55, pahalı" — 40 lira bir çapadır, bir değer ölçüsü değil.
Şirket o arada büyümüş olabilir.

Tanıma işaretleri:
· "Kaçırıyorum" hissi
· Hisseyi 3 gün önce almak istemiyordun, şimdi istiyorsun
· Gerekçen "çok yükseliyor"
· Normalden büyük pozisyon almak istiyorsun

Korunma: alım öncesi tek soru — "bu hisseyi 3 gün önce de almak istiyor
muydum, yoksa yükseldiği için mi istiyorum?" """,
 bist="""Sistem bu dürtüyü ölçülebilir hale getirip engelliyor:

· RSI 75 üstünde alım → "DUR" uyarısı + tam bu soru
· Son 5 günde %20+ yükselmiş hissede alım → "parabolik hareketin sonuna yakın
  giriliyor olabilir" uyarısı
· Gün içi +%9 üstü kapanan hisse → tarama listesinden otomatik ELENİR

Ve skorun ZAMANLAMA bileşeni aşırı alımı cezalandırır: TUPRS bugün trend 30/30,
momentum 25/25 alıyor ama zamanlama 0,8/25 — "mükemmel şirket, berbat zaman".""",
 tuzak=""""Bu sefer farklı" — piyasa tarihindeki en pahalı dört kelime. Her
balonda söylenmiştir.

İkinci tuzak: kaçırdığın hareketi telafi etmeye çalışmak. Kaçırdığın fırsat bir
KAYIP DEĞİLDİR. Her gün yeni fırsat çıkar; kaçırdığını kovalamak gerçek kayba
yol açar.""",
 sorular=["o11"], sure=8),

Ders("d1003", "Teyit önyargısı ve aşırı güven",
 "Kendi fikrinin esiri olmayı engelleyen yöntemleri öğrenmek.",
 """TEYİT ÖNYARGISI: bir görüş oluşturduktan sonra sadece onu destekleyen bilgiyi
aramak, çürüten bilgiyi görmezden gelmek.

Bir hisseyi aldıktan sonra bu etki güçlenir — çünkü artık o hissenin iyi olması
senin ÇIKARINADIR. Kötü haberi ciddiye almazsın.

AŞIRI GÜVEN: kendi bilgi ve yeteneğini olduğundan fazla sanmak.
Belirtileri: pozisyonu büyütmek, çeşitlendirmeyi azaltmak, araştırmayı
kısaltmak, kaldıraç kullanmak.

Ve en sinsi olan:

SONUÇ YANILGISI — kararı sonucuna göre değerlendirmek.
Kötü bir kararla para kazanmak, o kararı doğru sanmana yol açar. Bir dahakine
daha büyük yaparsın. Borsa kötü kararları hemen cezalandırmaz; bu yüzden
öğrenmesi zordur.

Dört kombinasyon:
· İyi karar + iyi sonuç → tekrarla
· İyi karar + kötü sonuç → YİNE tekrarla (olasılık böyle çalışır)
· KÖTÜ karar + iyi sonuç → EN TEHLİKELİSİ
· Kötü karar + kötü sonuç → dersini al

KORUNMA — kırmızı takım egzersizi:
Bir hisseyi beğendiğinde, önce NEDEN ALMAMAN gerektiğini yaz. Bütün kötü
tarafları ara. Sonra tersini yap. İki listeyi yan yana koy.

Bir tez, ancak en güçlü karşı argümanı bildikten sonra sağlamdır.""",
 bist="""Bu sistemde iki mekanizma var:

1) TEZ KAYDI — alım anındaki objektif durum (kalite skoru, çarpanlar, kırmızı
   bayraklar, makro rejim) dondurulur. Altı ay sonra "aslında biliyordum"
   diyemezsin; o günkü gerçek rakamlar orada.

2) `tez --ai` — dil modeli ŞEYTANIN AVUKATI rolünde tezini eleştirir. Tek
   kurala uyar: model sayı üretmez, sistemin ölçtüğü sayılar üzerine akıl
   yürütür. İnsan kendi fikrini çürütmekte kötüdür; bu iş için dışarıdan bir
   ses gerekir.""",
 tuzak=""""Araştırdım, eminim" — araştırmanın YÖNÜ önemlidir. Tezini destekleyen
20 kaynak okumak, teyit önyargısını güçlendirir. Tezini çürüten 1 kaynak
okumak daha değerlidir.

Kendine sor: "Bu hisseyi bugün SATANLAR ne biliyor da ben bilmiyorum?" """,
 sorular=["o09", "u15"], sure=8),

Ders("d1004", "İntikam işlemi ve aşırı işlem",
 "Kaybı telafi dürtüsünün ve sıkıntıdan işlem yapmanın maliyetini görmek.",
 """İNTİKAM İŞLEMİ: kaybettikten sonra "hemen geri alayım" dürtüsüyle işlem
yapmak.

Mekanizması: kayıp acı verir, beyin acıyı hemen sonlandırmak ister. Sabır
kaybolur. Pozisyon büyütülür, kurallar esnetilir, araştırma kısaltılır.

Sonuç neredeyse her zaman daha büyük kayıptır.

AŞIRI İŞLEM (overtrading): gereğinden çok işlem yapmak.
Sebepleri: sıkıntı, "bir şey yapıyor olma" ihtiyacı, kaybı telafi çabası,
kaçırma korkusu.

Maliyeti: Midas'ta BIST komisyonu sıfır olsa bile kayma ve kötü karar maliyeti
gerçektir. Günde 5 işlem yapan biri %0,15 kayma ile ayda ~%15 kaybeder.

TİLT (kontrolü kaybetme): peş peşe kayıplardan sonra tamamen kural dışına
çıkmak. Poker literatüründen gelen bu terim, borsada da geçerlidir.

Korunma kuralları:
· Günlük kayıp limiti — belirli bir kaybın üstünde o gün kapat
· Peş peşe kayıptan sonra zorunlu ara
· İşlem sayısı üst sınırı
· Karar günlüğü — her işlemin gerekçesini yaz. Yazamıyorsan yapma.""",
 bist="""Sistem bunu otomatik tarıyor:
· Son 5 günde 2+ zararlı kapanış varsa → "DUR" seviyesinde intikam uyarısı
· Pozisyon son 10 işlemin ortalamasının 1,8 katından büyükse → boyut uyarısı
· Bugün 3+ işlem kapatılmışsa → "aşırı işlem" uyarısı, "bugünü kapat" önerisi

Ve `ayarlar.yaml` içinde `gunluk_kayip_limiti_yuzde: 4` var — gün içi bu kadar
kaybettiysen durman gerektiğini söyler.""",
 tuzak=""""Bugün kaybettim, bugün geri alacağım" — piyasanın senin günlük
takviminden haberi yoktur. Kaybı hangi gün telafi edeceğine sen karar veremezsin.

Ve şu: işlem yapmamak bir eylemdir. En iyi işlem çoğu zaman yapılmayan
işlemdir.""",
 sorular=["o08"], sure=7),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 11 — BİLGİ KAYNAKLARI VE KAP
# ═══════════════════════════════════════════════════════════════════

M11 = Modul("m11", "Bilgi kaynakları ve KAP",
            "İyi yatırımcı her gördüğü habere inanmaz. Kaynağı ayırt etmeyi ve "
            "KAP okumayı öğrenmek, BIST'te ciddi bir avantajdır.", 2, [

Ders("d1101", "KAP nedir ve nasıl okunur",
 "Birincil kaynağa gitmeyi ve hangi bildirimlerin önemli olduğunu öğrenmek.",
 """KAP (Kamuyu Aydınlatma Platformu), BIST şirketlerinin yasal olarak açıklama
yapmak zorunda olduğu resmi platformdur: kap.org.tr

Neden birincil kaynak: haber siteleri KAP bildirimini AKTARIR ve aktarırken
eksiltir, abartır ya da yanlış yorumlar. KAP'ta ham metin vardır.

ÖNEMLİ BİLDİRİM TÜRLERİ:

FİNANSAL RAPOR — çeyreklik ve yıllık tablolar + dipnotlar. En değerli belge.
ÖZEL DURUM AÇIKLAMASI — yatırımcı kararını etkileyebilecek her gelişme:
  · Yeni sözleşme/ihale kazanımı (tutar ve süre kritik)
  · Yatırım kararı, kapasite artışı
  · Ortaklık yapısı değişikliği
  · Yönetim değişikliği
  · Borçlanma, tahvil ihracı
  · Dava, ceza, soruşturma
  · Geri alım programı
KÂR PAYI DAĞITIM KARARI
SERMAYE ARTIRIMI (bedelli/bedelsiz)
FAALİYET RAPORU — yıllık, yönetimin kendi anlatımı

NASIL OKUNUR — bir sözleşme duyurusu örneği:
1) TUTAR ne? Şirketin yıllık cirosunun yüzde kaçı?
2) SÜRE ne? 5 yıla yayılıyorsa yıllık etkisi beşte biridir.
3) MARJ belli mi? Ciro artışı kâr artışı demek değildir.
4) KESİN mi, ön anlaşma mı?
5) Bu iş ZATEN beklenen bir şey miydi?""",
 bist="""KAP'ın resmi bir API'si yok ve sayfa yapısı sık değişiyor. Bu yüzden
bu sisteme entegre EDİLMEDİ — kazıma güvenilir olmazdı ve sessizce yanlış
veri üretme riski taşırdı.

Yani KAP'a ELLE bakman gerekiyor. Günlük rutine ekle: portföyündeki
hisselerin KAP bildirimlerini kontrol et. Bilanço dönemlerinde (Mayıs, Ağustos,
Kasım, Mart başları) özellikle.

Sistem sana yalnızca hangi kaynağın ne kadar güvenilir olduğunu söyleyebiliyor
(`psikoloji.kaynak_degerlendir`).""",
 tuzak=""""Haber sitesinde okudum" — haber sitesi bir ARACIDIR. Manşet
"şirket dev ihale aldı" derken, KAP metninde "ön yeterlilik aşamasını geçti"
yazıyor olabilir. İkisi aynı şey değildir.

Her zaman birincil kaynağa git.""",
 sure=8),

Ders("d1102", "Kaynak güvenilirliği ve manipülasyon",
 "Bilgi ile söylentiyi ayırmayı ve manipülasyon işaretlerini tanımayı öğrenmek.",
 """Bilgi kaynakları güvenilirlik sırasına göre:

5/5 KAP BİLDİRİMİ — yasal zorunlulukla açıklanır, yanlışsa yaptırımı var
5/5 DENETLENMİŞ FİNANSAL RAPOR — bağımsız denetimden geçmiş
4/5 ŞİRKET SUNUMU — doğru ama SEÇİLMİŞ bilgi; iyi haber öne çıkarılır
3/5 ANALİST RAPORU — modele dayanır ama varsayımlar tartışmalı; kurumun
    çıkar ilişkisine bak
3/5 HABER AJANSI — hızlı ama bazen eksik/yanlış aktarır
2/5 KÖŞE YAZISI — görüş, veri değil; yazarın pozisyonu olabilir
1/5 SOSYAL MEDYA (X, Telegram) — en düşük güvenilirlik
0/5 SÖYLENTİ — doğrulanana kadar bilgi değildir

SOSYAL MEDYA hakkında net bir gerçek: "bu hisse uçacak" diyen kişi genelde
ZATEN ALMIŞTIR ve senin alımınla çıkacaktır. Bu, teknik olarak bir çıkar
çatışmasıdır ve nadiren açıklanır.

MANİPÜLASYON İŞARETLERİ:
· Aciliyet dili — "son şans", "kaçırma", "yarın geç olacak"
· Hedef fiyat vaadi — "3 aya 100 lira"
· Kaynak belirsizliği — "duyduğuma göre", "içeriden bilgi"
· Aşırı kesinlik — gerçek analist olasılık konuşur, kesinlik değil
· Düşük halka açıklık + ani hacim artışı + sosyal medya kampanyası

VE EN ÖNEMLİ AYRIM:
· GERÇEKLEŞMİŞ VERİ — olmuş bitmiş, doğrulanabilir
· BEKLENTİ — henüz olmamış, fiyata çoktan yansımış olabilir
· YORUM — birinin görüşü

"İyi haber geldi ama hisse düştü" olayının tamamı bu ayrımda yatar: haber
beklentiyi aşmadıysa, gerçekleştiğinde alıcı kalmaz.""",
 bist="""BIST'te manipülasyon riski, halka açıklık oranı düşük ve işlem hacmi
az olan hisselerde belirgin şekilde yüksektir. Sığ bir emir defterinde küçük
bir alım fiyatı yüzde onlarca oynatabilir.

Bu sistemin 20 milyon TL günlük hacim filtresi, kısmen bu riske karşıdır.
Ayrıca VBTS tedbirli hisseleri kontrol etmek senin sorumluluğunda — sistem
bunu otomatik göremiyor.

SPK manipülasyonu suç sayar ve soruşturur, ama tespit genelde olaydan çok
sonra gelir. Korunma sende.""",
 tuzak=""""Bu bilgi henüz kimse bilmiyor" — eğer sosyal medyada gördüysen,
binlerce kişi biliyor demektir. Gerçek içeriden bilgi zaten yasadışıdır ve
sana ulaşmaz.

Bilginin değeri, ne kadar AZ kişinin bildiğiyle orantılıdır. Herkesin bildiği
bilgi fiyattadır.""",
 sure=8),

Ders("d1103", "Bilanço dönemi ve beklenti yönetimi",
 "Finansal sonuç açıklamalarında fiyatın neden 'mantıksız' hareket ettiğini anlamak.",
 """Bilanço açıklamaları BIST'in en oynak dönemleridir. Hisse, açıklanan rakama
değil, RAKAMIN BEKLENTİDEN SAPMASINA tepki verir.

Neden: piyasa fiyatı, beklenen sonucu zaten içerir. Şirket beklenen kârı
açıklarsa yeni bilgi yoktur, fiyat hareket etmez.

Dört olası durum:
· Beklentiden İYİ → fiyat yükselir
· Beklentiden KÖTÜ → düşer
· Beklentiye UYGUN → hareket etmez, ama İLERİYE DÖNÜK açıklamalar önemli olur
· İyi rakam + kötü beklenti → DÜŞER (en çok şaşırtan durum)

Bilanço okuma sırası (manşetten değil, buradan başla):
1) HASILAT — reel olarak büyümüş mü? (enflasyona göre)
2) BRÜT MARJ — trend ne yönde?
3) FAALİYET KÂRI — ana iş nasıl?
4) FİNANSMAN GİDERİ — kur farkı ne yazmış?
5) NAKİT AKIŞI — kâr nakde dönüyor mu?
6) BİLANÇO — borç ve işletme sermayesi nasıl değişmiş?
7) DİPNOTLAR — net döviz pozisyonu, vade yapısı, ilişkili taraf

BIST bilanço takvimi:
· 1. çeyrek → Mayıs başı
· 6 aylık → Ağustos başı
· 9 aylık → Kasım başı
· Yıllık → Mart başı (tam denetimli, en güvenilir)""",
 bist="""Türkiye'ye özgü iki durum:

1) KUR FARKI, çeyrek sonuçlarını tamamen bozabilir. Ana işi iyi olan şirket kur
   zararı yüzünden net zarar açıklayabilir; ana işi kötü olan şirket kur geliri
   yüzünden rekor kâr açıklayabilir. Faaliyet kârına bak.

2) ENFLASYON MUHASEBESİ (TMS-29), 2023'ten beri uygulanıyor. Geçmiş dönem
   rakamları bugünkü satın alma gücüne göre düzeltiliyor. Düzeltilmiş ve
   düzeltilmemiş rakamları karıştırmak, büyüme hesabını tamamen bozar.""",
 tuzak=""""Rekor kâr açıkladı ama hisse düştü, piyasa mantıksız" — piyasa
mantıksız değil, senin baktığın sayıya bakmıyor. Muhtemel sebepler: beklenti
daha yüksekti, kârın kalitesi kötüydü, ya da ileriye dönük beklenti düşürüldü.

Fiyat geçmişe değil, GELECEĞE bakar.""",
 sorular=["t03", "u02"], sure=8),
])


# ═══════════════════════════════════════════════════════════════════
# MODÜL 12 — KENDİ SİSTEMİN
# ═══════════════════════════════════════════════════════════════════

M12 = Modul("m12", "Kendi sistemin",
            "Ustanın son dersi: hisse seçmek değil, tekrarlanabilir bir karar "
            "süreci kurmak. Buradan sonrası senin.", 3, [

Ders("d1201", "Yatırım tezi: alımdan önce yazılan şey",
 "On soruyu cevaplayamıyorsan neden satın aldığını bilmediğini kabul etmek.",
 """Bir hisse almadan önce cevaplanması gereken on soru:

1) Ne satın alıyorum? Şirketin iş modeli ne?
2) Neden satın alıyorum? Yatırım tezim ne?
3) Şirket nasıl para kazanıyor?
4) Finansalları nasıl?
5) Şirketin değeri ne?
6) Piyasa fiyatı bu değere göre nasıl?
7) Büyüme beklentisi ne?
8) En büyük risk ne?
9) HANGİ DURUMDA YANILDIĞIMI KABUL EDERİM?
10) Ne kadar kaybetmeyi göze alıyorum?

Bu on sorudan en kritiği DOKUZUNCUDUR ve en çok atlanan da odur.

Neden kritik: yanılma koşulu ÖNCEDEN yazılmazsa, sonradan hiç yazılmaz. Fiyat
düştüğünde beynin gerekçe üretir, her düşüş "geçici" görünür ve "biraz daha
bekleyeyim" cümlesi başlar.

İki tür yanılma koşulu:
· FİYAT bazlı — "stop seviyesinin altında kapanış". Mekanik, tartışmasız.
· TEZ bazlı — "çeyreklik FAVÖK marjı %8'in altına düşerse". Daha değerlidir,
  çünkü fiyat düşüşü tek başına yanıldığını göstermez; tezin bozulması gösterir.

Tezi YAZMAK şart. Aklından geçirmek yetmez — yazılmamış tez, sonradan
hatırladığın tezdir ve o, gerçekte düşündüğün şey değildir.""",
 bist="""Bu sistemin tez modülü sekiz soru sorar ve alım anındaki objektif
durumu birlikte DONDURUR: teknik skor, RSI, kalite skoru, kırmızı bayraklar,
çarpanlar, makro rejim.

Altı ay sonra "aslında o zaman da pahalıydı" demek yerine, o günkü gerçek
rakamlara bakarsın.

Ve `tezler` komutu bir karne tutar: tam tez yazdığın işlemlerle yazmadıklarının
ortalama getirisi. Aradaki fark, disiplinin sana ne kazandırdığının ölçüsüdür.

Mobil uygulamada `al` düğmesi, tezin yoksa "DUR" uyarısı verir ve kaydı kilitler.""",
 tuzak=""""Tezi biliyorum, yazmaya gerek yok" — insan hafızası, geçmiş
düşüncelerini bugünkü sonuca göre yeniden yazar (geriye dönük yanlılık).
Kazandığında "biliyordum" dersin, kaybettiğinde "aslında şüphelenmiştim".

Yazılı tez bu yeniden yazmayı imkânsız kılar. Değeri buradadır.""",
 sorular=["t20", "u15"], sure=8),

Ders("d1202", "Strateji geliştirme ve backtest",
 "Bir kuralın gerçekten çalışıp çalışmadığını dürüstçe ölçmeyi öğrenmek.",
 """Bir strateji şu dört şeyi TAM olarak tanımlamalıdır:
1) GİRİŞ — hangi koşulda alınır
2) ÇIKIŞ — hangi koşulda satılır (kâr ve zarar için ayrı ayrı)
3) BOYUT — ne kadar alınır
4) EVREN — hangi hisselerde uygulanır

Bunlardan biri bile belirsizse, o bir strateji değil bir sezgidir.

BACKTEST, kuralı geçmiş veride test etmektir. Dürüst bir backtest şunları
modellemek ZORUNDADIR:

· GELECEĞE BAKMAMA — sinyal t günü kapanışında üretilir, işlem t+1 açılışında
  yapılır. Aynı günün kapanışından alım varsayan test, gerçekte mümkün olmayan
  bir bilgiyi kullanır.
· KAYMA (slippage) — alışta yukarı, satışta aşağı
· KOMİSYON
· LİKİDİTE — nakit yoksa sinyal kaçırılır
· PİYASA KURALLARI — tavanda açılan hisse alınamaz
· BOŞLUKLU STOP — stop seviyesinin altında açılırsa oradan çıkılır
· HAYATTA KALMA YANLILIĞI — bugün var olan hisselerle test etmek, batmış
  şirketleri dışarıda bırakır ve sonucu iyimser gösterir

AŞIRI UYDURMA (overfitting) en büyük tehlikedir: parametreleri geçmiş veriye
o kadar uydurursun ki, gelecekte çalışmaz. Belirtisi: küçük bir parametre
değişikliğinin sonucu çok değiştirmesi.

Sağlamlık testleri:
· Parametre ızgarası — komşu değerlerde de çalışıyor mu?
· Kayan pencere — farklı dönemlerde de çalışıyor mu?
· Kayma duyarlılığı — maliyet arttıkça ne kadar bozuluyor?""",
 bist="""Bu sistemin backtest motoru yukarıdaki maddelerin hepsini modelliyor
ve sonuçları dürüstçe raporluyor:

kirilim: +%117,7 · Sharpe −0,71 (risksiz %40'a göre) · azami düşüş −%11,3
Sağlamlık: 24 parametre kombinasyonunun 24'ünde kârlı (medyan +%97);
kayma 0→50bp'de +%142→+%115.

AMA açık iki uyarı da tutuyor.

BİR: ADX eşiği tam 20'de sıçrıyor (ADX>20 → +%117,7, ADX>15 → +%61,
ADX>25 → +%68). Bu keskin tepe AŞIRI UYDURMA işaretidir.

İKİ — ve bu daha öğretici: ADX>15 ile ADX>20 neredeyse AYNI SAYIDA işlem
açıyor (190'a karşı 189), ama getiri iki katı fark ediyor. Aynı işlem sayısı,
iki katı getiri. Demek ki fark kuralın kalitesinden değil, 1.000 TL sermaye ve
4 pozisyon sınırı altında SIRAYA giren sinyallerden geliyor. Bir sinyalin
birkaç gün erken gelmesi, sonraki ayların tamamen farklı hisselerle
doldurulmasına yol açıyor. Buna "yol bağımlılığı" denir ve küçük sermayede
etkisi büyüktür.

Bir backtest raporunun kendi zayıflığını söylemesi, güvenilirliğinin
göstergesidir.""",
 tuzak=""""Backtest %300 getiri verdi" — ilk sorulacak: kaç parametre denedin?
100 kombinasyon denersen, biri şans eseri harika çıkar. Buna "veri madenciliği
yanlılığı" denir.

İkinci soru: bu dönem tek bir piyasa rejimi mi? 3 yıllık boğa piyasasında
test edilmiş bir strateji, ayı piyasasında hiç denenmemiştir.""",
 sorular=["o12"], sure=9),

Ders("d1203", "Karar günlüğü ve kendi karnen",
 "Süreci sonuçtan ayırmayı ve gerçekten öğrenmeyi mümkün kılan alışkanlık.",
 """Borsada öğrenmek zordur çünkü GERİ BİLDİRİM GÜRÜLTÜLÜDÜR:
· İyi karar kötü sonuç verebilir
· Kötü karar iyi sonuç verebilir
· Sonuç haftalar sonra gelir
· Bu arada neden öyle karar verdiğini unutmuşsundur

Karar günlüğü bu üç sorunu da çözer. Her işlemde yazılacaklar:

ALIM ANINDA:
· Tarih, fiyat, adet
· Tez (neden alıyorum)
· Yanılma koşulu
· Beklenen tutma süresi
· O günkü objektif rakamlar
· DUYGU DURUMU — sakin miyim, heyecanlı mı, telafi peşinde mi?

ÇIKIŞ ANINDA:
· Çıkış fiyatı ve sebebi
· Tez doğru muydu?
· Kural dışına çıktım mı?
· NE ÖĞRENDİM?

Sonuncusu en önemlisidir. Kapanış notu olmayan işlem, tekrarlanacak hatadır.

Ayda bir kez günlüğü baştan oku ve sor:
· En sık yaptığım hata ne?
· Kurallarıma ne sıklıkta uymadım?
· Uymadığım zamanlar daha mı iyi sonuç verdi, daha mı kötü?
· Hangi tür işlemler kazandırıyor?

SÜREÇ ÖLÇÜLÜR, SONUÇ DEĞİL. Kısa vadede sonuç şanstır; süreç senin
kontrolündedir.""",
 bist="""Bu sistemde günlük iki parçadan oluşuyor:
· `tez` — alım anındaki düşünce + objektif rakamlar (dondurulur)
· pozisyon kapatılırken "ne öğrendin?" sorusu — kapanış notu

`tezler` komutu karneyi çıkarır: işlem sayısı, kazanma oranı, ortalama getiri,
ve kritik olarak TAM TEZ yazdıklarınla EKSİK tezlerin ortalama getirisi.

Bu iki satır arasındaki fark, disiplinin sana ne kazandırdığının ölçüsüdür ve
kimsenin sana söyleyemeyeceği bir sayıdır — sadece kendi verinden çıkar.""",
 tuzak=""""Kazandım, doğru karardı" — SONUÇ YANILGISI. Rulette kırmızıya koyup
kazanan da kazanmıştır.

Kararı, VERİLDİĞİ ANDAKİ bilgiye göre değerlendir. Bu yüzden tez yazılır ve
saklanır: sonucun, karar anındaki düşünceni bulandırmasını engeller.""",
 sorular=["u15", "t20"], sure=8),

Ders("d1204", "Ustanın son dersi",
 "Bütün müfredatın altı cümlede özeti ve bundan sonra ne yapacağın.",
 """Buraya kadar öğrendiklerin altı ilkede toplanır:

1) HİSSEYİ DEĞİL, ŞİRKETİ DÜŞÜN.
   Fiyat kısa vadede oy makinesi, uzun vadede tartı makinesidir.

2) FİYATI DEĞİL, DEĞERİ DÜŞÜN.
   3 liralık hisse 400 liralıktan ucuz değildir. Ucuzluk, fiyatın değere
   oranıdır.

3) TAHMİNİ DEĞİL, OLASILIKLARI DÜŞÜN.
   "Bu hisse yükselecek" bir tahmindir. "Bu senaryoda %60 ihtimalle şu olur"
   bir analizdir.

4) KAZANCI DEĞİL, RİSK/GETİRİ ORANINI DÜŞÜN.
   %46 kazanma oranlı strateji, %54'lükten daha çok kazandırabilir.

5) TEK BİR GÖSTERGEYİ DEĞİL, BÜTÜN RESMİ DÜŞÜN.
   Beş gösterge aynı fiyat serisinden türüyorsa, beş teyit değil bir teyittir.

6) VE EN ÖNEMLİSİ:
   Borsada amacın her zaman haklı çıkmak değil; YANLIŞ OLDUĞUNDA AZ KAYBETMEK,
   HAKLI OLDUĞUNDA YETERİNCE KAZANABİLMEKTİR.

BUNDAN SONRA NE YAPACAKSIN:

· Bu müfredatı bir kez bitirmek yetmez. Aralıklı tekrar sistemi soruları
  düzenli karşına getirecek — bırak getirsin.
· Üç ay kâğıt üzerinde işlet. Her gün tara, seç, tez yaz, sonucu kaydet —
  para koymadan. Sistem sana uyuyor mu, kayıplara dayanabiliyor musun, burada
  anlarsın.
· Sonra küçük başla. 1.000 TL'nin işi para kazanmak değil, ÖĞRENMEK.
· Karneni ayda bir oku.
· Ve şunu unutma: bu sermayede en güçlü değişken strateji değil, DÜZENLİ
  EKLEMEDİR. Ayda 500 TL ekleyip yılda %30 kazanmak, 3 yılda ~25.000 TL eder;
  eklemesiz aynı oran 1.000 TL'yi 2.197 TL yapar.""",
 bist="""Son bir dürüstlük notu, bu sistemin kendi ölçümlerinden:

(2026-08-26 ölçümü — rakamlar `cekirdek/olcumler.py`'de, oradan güncellenir.)

BIST 100'ün son bir yıllık REEL getirisi −%4,2.
Ve sistemin CANLI sicili (4,1 ay, 767 sinyal): 20 günlük vadede %35,5
kazanma, ortalama −%0,98. Backtest ne söylerse söylesin, canlı ölçüm bu.

Bu rakamlar seni caydırmak için değil, BEKLENTİNİ DOĞRU KURMAK için burada.
Gerçekçi beklentiyle başlayan biri, kötü dönemde sistemi terk etmez.

Ayda %3-5 hedefle. Yılda %40-60 eder ve bu bile piyasanın en iyi %5'inde
olmak demektir.""",
 tuzak="""Bu müfredatı bitirdikten sonra en büyük risk AŞIRI GÜVENDİR.
Bilgi arttıkça, bilgiye duyulan güven bilginin kendisinden hızlı artar.

Öğrendiklerin seni ortalamanın üstüne çıkarır — ama piyasada karşındaki de
öğreniyor. Alçakgönüllülük bir erdem değil, bir hayatta kalma stratejisidir.""",
 sorular=["t20", "u15", "u12"], sure=9),
])


# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# M13 — GRAFİK OKUMA
#
# Neden ayrı modül: teknik analiz modülü (m7) göstergeleri anlatıyor ama
# grafiğin KENDİSİNİ okumayı hiçbir yer anlatmıyordu. Mumun ne olduğunu
# bilmeden RSI öğrenmek, alfabeyi bilmeden şiir okumaya benziyor.
#
# Bu modülün her dersinin bir ŞEMASI var (egitmen_sema.py) — kavramı
# gerçek verinin gürültüsü içinde değil, temiz bir çizimde gösteriyor.
# ═══════════════════════════════════════════════════════════════════

M13 = Modul("m13", "Grafik okuma",
            "Göstergelerden önce grafiğin kendisi: mum ne anlatır, destek "
            "nedir, trend nasıl çizilir. Her ders bir şemayla.", 1, [

Ders("d1301", "Grafik türleri ve neden mum",
 "Çizgi, bar ve mum grafiklerinin farkını ve mumun neden standart olduğunu görmek.",
 """Bir fiyat grafiği, zaman içindeki fiyatı gösterir. Üç yaygın tür var:

ÇİZGİ GRAFİK — yalnızca KAPANIŞ fiyatlarını birleştirir. En sade, en az
bilgi. Uzun vadeli yönü görmek için iyidir; gün içinde ne yaşandığını
söylemez.

BAR GRAFİK — her dönem için dört fiyatı da gösterir: açılış, en yüksek,
en düşük, kapanış. Bilgi tam ama okuması yorucu.

MUM GRAFİK — aynı dört fiyatı gösterir, ama açılış ile kapanış arasını
DOLU bir gövde olarak çizer. Yön renkle anlaşılır. Aynı bilgi, çok daha
hızlı okunur.

Mum grafiğin standart olmasının sebebi bilgi miktarı değil, OKUMA HIZI:
gözün bir bakışta yön, güç ve kararsızlığı ayırt edebilmesi.

Bir dördüncü tür daha var: HACİM. Fiyatın altında çubuk olarak çizilir ve
"bu hareket kaç kişiyi ilgilendirdi" sorusunu cevaplar. Fiyatı hacimsiz
okumak, sesi kısılmış film izlemek gibidir.""",
 bist="""Bu sistem GÜNLÜK mumla çalışır. Yani her mum bir işlem gününü
temsil eder: 10:00 açılışı, gün içi en yüksek/en düşük, 18:00 kapanışı.

BIST'te gün içi veri 15 dakika gecikmeli geldiği için sistem gün içi
mumla çalışmaz — çalışsaydı gecikmiş veriyle karar veriyor olurdun.""",
 tuzak="""Çizgi grafiğe bakıp "hisse istikrarlı yükseliyor" demek. Çizgi
grafik gün içi dalgalanmayı gizler; aynı dönemin mum grafiğinde uzun
fitiller görürsün — yani yol hiç de düz değildi. Stop seviyeni çizgi
grafiğe bakarak kurarsan, göremediğin dalgalanma seni vurur."""),

Ders("d1302", "Bir mum neyi anlatır",
 "Gövde ve fitilin ne olduğunu, uzun fitilin neden 'reddedilmiş fiyat' demek olduğunu öğrenmek.",
 """Her mum bir zaman diliminin DÖRT fiyatını taşır:

AÇILIŞ — dönem başındaki fiyat
EN YÜKSEK — dönem içinde görülen en yüksek fiyat
EN DÜŞÜK — dönem içinde görülen en düşük fiyat
KAPANIŞ — dönem sonundaki fiyat

GÖVDE, açılış ile kapanış arasıdır. Kapanış açılıştan yüksekse mum
yükselen (bu uygulamada yeşil), düşükse düşen (kırmızı) çizilir.

FİTİL (gölge ya da iğne), gövdenin dışına taşan ince çizgilerdir. Üst
fitil o dönemin en yükseğine, alt fitil en düşüğüne uzanır.

Okuma kuralları:

UZUN GÖVDE — taraflardan biri baskındı, hareket kararlıydı.
KISA GÖVDE — kararsızlık; açılışla kapanış birbirine yakın.
UZUN ALT FİTİL — fiyat aşağı çekildi ama geri alındı. Alıcılar orada.
UZUN ÜST FİTİL — fiyat yukarı gitti ama tutunamadı. Satıcılar orada.

Uzun fitil, REDDEDİLMİŞ FİYAT demektir: piyasa oraya gitti, beğenmedi,
geri döndü. Bu yüzden fitil uçları sık sık destek/direnç olur.""",
 bist="""Sistem her hisse için açılış, en yüksek, en düşük, kapanış ve
hacmi saklar (`gunluk_fiyat` tablosu). ATR hesabı doğrudan fitillerden
gelir: fitiller uzunsa ATR büyür, stop mesafesi genişler.

Yani mumun şekli, senin pozisyon boyutunu doğrudan etkiliyor.""",
 tuzak="""Yalnızca kapanışa bakıp "bugün +%2, iyi gün" demek. Aynı gün
%6 yükselip sonra %4 geri vermiş olabilir — o uzun üst fitil, alıcıların
tükendiğini söylüyor. Kapanış tek başına o bilgiyi taşımaz."""),

Ders("d1303", "Destek ve direnç",
 "Fiyatın neden belirli seviyelerde durduğunu ve bunun bir nokta değil bölge olduğunu görmek.",
 """DİRENÇ, fiyatın yükselirken zorlandığı, sık sık durup geri döndüğü
seviyedir. DESTEK, düşerken tutunduğu seviyedir.

Neden oluşurlar? Hafıza. Bir fiyattan alım yapıp zarar edenler, fiyat
oraya geri geldiğinde "başabaşta çıkayım" diye satar — bu satış baskısı
direnç yaratır. Aynı şekilde bir seviyeden alıp kazananlar, fiyat oraya
dönünce yine almak ister — bu da destek yaratır.

ÜÇ KURAL:

1) Destek ve direnç NOKTA DEĞİL BÖLGEDİR. "142,30 direnci" demek yanlış;
   "142-145 bandı" demek doğrudur.

2) Kırılan direnç DESTEĞE dönüşür, kırılan destek DİRENCE. Rol değişimi
   teknik analizin en tekrar eden gözlemidir.

3) Bir seviyeye ne kadar çok dokunulduysa o kadar önemlidir — ama
   kırıldığında da o kadar sert hareket üretir.

Yükselen trendin tanımı buradan çıkar: her tepe bir öncekinden yüksek
(yükselen zirveler), her dip bir öncekinden yüksek (yükselen dipler).""",
 bist="""Bu sistem destek/direnç ÇİZMİYOR — bilinçli bir tercih. Seviye
çizmek özneldir; aynı grafikte iki kişi farklı yerler işaretler.

Onun yerine sistem ölçülebilir olanı kullanıyor: SMA200 (uzun vadeli
ortalama), Donchian kanalları (son N günün en yüksek/en düşüğü) ve ATR
(oynaklık). Bunlar da destek/direnç işlevi görür ama kimsenin yorumuna
bağlı değildir.""",
 tuzak="""Grafiğe sonradan bakıp "işte tam buradan dönmüş" demek. Geçmişe
bakınca her dönüş noktası bariz görünür; asıl soru o seviyeyi dönüşten
ÖNCE işaretleyip işaretlemediğindir. Bunu test etmenin tek yolu, seviyeyi
yazıp tarih atmaktır."""),

Ders("d1304", "Trend çizgisi nasıl çizilir",
 "Trend çizgisinin hangi noktaları birleştirdiğini ve kırılımın neden hemen sinyal olmadığını öğrenmek.",
 """Yükselen trendde çizgi DİPLERİ birleştirir. Düşen trendde TEPELERİ.
Bu ters çevrilmez: yükselen trendde tepeleri birleştirmek kanalın üst
sınırını verir, trend çizgisini değil.

ÇİZME KURALLARI:

En az İKİ nokta gerekir — ama iki noktadan her zaman bir çizgi geçer,
yani iki nokta hiçbir şey kanıtlamaz. ÜÇÜNCÜ dokunuş çizgiyi anlamlı
kılar.

Çizgi ne kadar dikse o kadar kırılgandır. 45 dereceye yakın trendler
uzun ömürlü olur; dik trendler hızla kırılır.

Fitilleri mi gövdeleri mi birleştirmeli? İkisi de kullanılır. Gövdeleri
birleştirmek daha muhafazakârdır: fitiller anlık taşkınlıkları içerir.

KIRILIM: Fiyatın çizgiyi delmesi trendin bittiği anlamına GELMEZ. Tek
mumluk delme, en sık yanıltan olaydır. Teyit için genelde kapanışın
çizginin ötesinde olması ve hacmin artması beklenir.""",
 bist="""Sistem trend çizgisi çizmiyor; trendi ölçülebilir tanımlarla
belirliyor: fiyat SMA200'ün üstünde mi, EMA20 EMA50'nin üstünde mi, ADX
18'in üstünde mi.

`trend` stratejisinin girişi tam olarak bu: yükselen trendde EMA20'ye
geri çekilip toparlanan hisse. Yani "trend çizgisine dokunup dönme"nin
ölçülebilir hâli.""",
 tuzak="""Çizgiyi verilere UYDURMAK. Grafikte çizgiyi biraz eğip
kaydırınca herkes kendi tezini doğrulayan bir trend bulur. Kural şu:
çizgiyi çizdikten sonra fiyatın ona uyması gerekir, çizginin fiyata
değil."""),

Ders("d1305", "Boşluk (gap)",
 "Boşluğun ne olduğunu, neden oluştuğunu ve 'boşluk kapanır' ezberinin sınırını görmek.",
 """BOŞLUK, bir mumun en düşüğünün bir öncekinin en yükseğinin üstünde
kalmasıdır (yukarı boşluk) ya da tersi (aşağı boşluk). Aradaki fiyat
aralığında HİÇ İŞLEM GEÇMEMİŞTİR.

Neden oluşur: piyasa kapalıyken gelen haber. Bilanço, KAP açıklaması,
temettü, sermaye artırımı, makro şok. Açılışta fiyat bir öncekinin
bittiği yerden değil, haberin gerektirdiği yerden başlar.

TÜRLERİ:

KOPUŞ BOŞLUĞU — uzun bir yatay seyirden sonra, yeni bir trendin başında.
KAÇIŞ BOŞLUĞU — trendin ortasında, hızlanma işareti.
TÜKENME BOŞLUĞU — trendin sonunda, son atak.

"Boşluklar kapanır" yaygın bir söz ve çoğu zaman doğrudur — fiyat geri
gelip o aralığı doldurur. Ama kopuş boşlukları sık sık kapanmaz.""",
 bist="""BIST'te boşluk yaygındır: seans 18:00'de kapanır, haberler gece
KAP'a düşer, ertesi sabah 10:00'da fiyat boşlukla açılır.

Bu, backtest için önemli bir ayrıntı: bu sistemin backtesti stop'un
boşluklu açılışta STOP FİYATINDAN DEĞİL AÇILIŞTAN çalıştığını varsayar.
Yani "stopum 100'dü" desen bile hisse 92'den açtıysa 92'den çıkarsın.
Gerçekçi olmayan backtestler bunu görmezden gelir ve sonucu iyi
gösterir.""",
 tuzak="""Boşluğun kapanacağına bahis girmek. "Nasılsa doldurur" diyerek
düşen bir hisseyi almak, en pahalı ezberlerden biridir. Kopuş boşlukları
aylarca kapanmaz; o süre boyunca paran orada kilitli kalır."""),

Ders("d1306", "Üç temel mum formasyonu",
 "Çekiç, doji ve yutan mumun ne anlattığını ve neden tek başına sinyal olmadığını öğrenmek.",
 """ÇEKİÇ — kısa gövde üstte, uzun alt fitil. Fiyat aşağı çekildi ama
alıcılar geri aldı. Alt fitil gövdenin en az iki katı olmalı. Düşüş
trendinin DİBİNDE oluşursa dönüş adayıdır.

DOJİ — açılış ile kapanış neredeyse aynı; gövde yok gibi. Taraflar
berabere kaldı, kararsızlık var. Uzun bir trendin sonunda görülürse
"güç tükeniyor" işaretidir.

YUTAN BOĞA — iki mum. Küçük bir düşen mum, ardından onu tamamen kapsayan
büyük bir yükselen mum. Satıcılar bir gün önce kazandıklarını tek günde
geri verdi.

HEPSİNİN ORTAK KURALI: yer önemlidir. Aynı çekiç, düşüşün dibinde dönüş
adayı, yükselişin ortasında hiçbir şeydir. Formasyon TEK BAŞINA sinyal
değildir; nerede oluştuğu ve sonraki mumun ne yaptığı belirler.

Ve dürüst bir sınır: mum formasyonlarının istatistiksel gücü, popüler
anlatımda iddia edildiğinden çok daha zayıftır.""",
 bist="""Bu sistem mum formasyonu ARAMIYOR. Sebep ölçüm: formasyonların
tanımı özneldir ("uzun fitil" ne kadar uzun?) ve backteste sokulduğunda
tutarlı bir kenar üretmiyorlar.

Sistemin `tepki` stratejisi benzer bir fikri ölçülebilir biçimde
kullanıyor: RSI2 ile aşırı satım + trend içinde olma şartı. Aynı sezgi,
tartışmasız tanım.""",
 tuzak="""Formasyon avcılığı. Yeterince bakarsan her grafikte bir çekiç
bulursun — insan beyni gürültüde desen görmek üzere kuruludur. Formasyon
gördüğünde sorulacak soru şudur: bu formasyonu geçmişte kaç kez gördüm
ve kaçında işe yaradı? Cevabı yoksa sinyal değil, hikâyedir."""),

Ders("d1307", "Zaman dilimi ve gürültü",
 "Aynı hareketin farklı zaman dilimlerinde neden farklı göründüğünü ve hangisinin seçileceğini görmek.",
 """Aynı fiyat hareketi, hangi pencereden baktığına göre bambaşka
görünür. Günlük grafikte dalgalı ve kararsız görünen bir hisse, haftalık
grafikte düzgün yükseliyor olabilir.

KISA ZAMAN DİLİMİ (dakikalık, saatlik): çok sinyal, çok gürültü. Her
sinyalde işlem yaparsan komisyon ve spread seni yer.

UZUN ZAMAN DİLİMİ (haftalık, aylık): az sinyal, az gürültü, ama geç
kalırsın.

Seçim, ne kadar sık karar verebileceğine bağlıdır — göstergeye değil.
Gün içi grafiğe bakıp haftalık pozisyon tutmak, ya da tersi, en yaygın
tutarsızlıktır.

ÇOKLU ZAMAN DİLİMİ yaklaşımı: yönü uzun dilimde belirle, girişi kısa
dilimde ara. Ama bu, iki farklı dilimde iki farklı karar vermek DEĞİLDİR
— uzun dilim yönü belirler, kısa dilim yalnızca zamanlama yapar.""",
 bist="""Bu sistem yalnızca GÜNLÜK mumla çalışır ve bu bir sınır değil,
tercih.

İki sebep: (1) BIST verisi 15 dakika gecikmeli — gün içi karar vermek
gecikmiş veriyle karar vermektir. (2) Sistem günde bir kez, kapanıştan
sonra çalışıyor; kararlar bir gecelik düşünme payıyla veriliyor.

Sinyal vadeleri de buna göre: 1, 5 ve 20 günlük.""",
 tuzak="""Zaman dilimi değiştirerek tez aramak. Pozisyon zarardayken
günlükten haftalığa geçip "aslında trend hâlâ yukarı" demek, analiz
değil kendini kandırmadır. Zaman dilimi POZİSYONDAN ÖNCE seçilir ve
pozisyon süresince değişmez."""),
])

MODULLER = [M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, M13]
TUM_DERSLER = [d for m in MODULLER for d in m.dersler]
DERS_HARITA = {d.kod: d for d in TUM_DERSLER}
MODUL_HARITA = {m.kod: m for m in MODULLER}


def ders_getir(kod: str) -> Ders | None:
    return DERS_HARITA.get(kod.lower().strip())


def modul_getir(kod: str) -> Modul | None:
    return MODUL_HARITA.get(kod.lower().strip())


def ders_modulu(ders_kod: str) -> Modul | None:
    for m in MODULLER:
        if any(d.kod == ders_kod for d in m.dersler):
            return m
    return None
