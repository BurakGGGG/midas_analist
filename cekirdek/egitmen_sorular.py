"""Soru bankası: usta → çırak müfredatı.

Tasarım kuralı: her cevap NEDEN-SONUÇ anlatır, tanım vermez. Bir öğrenci
"F/K fiyat bölü kazançtır" diyebilir ve hiçbir şey anlamamış olabilir.
Bu yüzden her sorunun `tuzak` alanı var: yaygın yanlış cevap ve neden yanlış.

Seviyeler: 1 temel · 2 orta · 3 usta
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Soru:
    kod: str
    seviye: int
    kategori: str
    soru: str
    cevap: str
    tuzak: str = ""          # yaygın yanlış cevap ve NEDEN yanlış
    ipucu: str = ""
    anahtar: list[str] = field(default_factory=list)   # cevapta geçmesi beklenen kavramlar


# ═══════════════════════════════════════════ SEVİYE 1 — "adın gibi bil"

TEMEL = [
Soru("t01", 1, "temel", "Hisse senedi nedir?",
 """Bir şirketin mülkiyetinin bölünmüş parçasıdır. 1 adet THYAO almak, THYAO'nun
yaklaşık 1,37 milyarda birine ortak olmak demektir — kâğıt değil, ŞİRKET satın
alırsın.

Bu ortaklık sana iki hak verir: şirket kâr dağıtırsa payını alırsın (temettü),
ve şirketin değeri artarsa payının değeri artar. Ama yükümlülük vermez —
şirket batarsa borcundan sorumlu değilsin, sadece koyduğun para gider.""",
 tuzak="""'Fiyatı yükselsin diye alınan bir şey' demek en yaygın hata. Bu
düşünce seni fiyata baktırır, şirkete değil. Fiyat kısa vadede oy makinesi,
uzun vadede tartı makinesidir.""",
 anahtar=["ortaklık", "şirket", "pay"]),

Soru("t02", 1, "temel", "Bir hissenin fiyatı neden yükselir veya düşer?",
 """Fiyatı kimse 'belirlemez'. Emir defterinde alıcı ve satıcı eşleştiğinde
oluşur. Fiyat yükseliyorsa alıcılar satıcılardan daha sabırsız demektir —
bekleyip ucuza almak yerine satıcının fiyatını kabul ediyorlar.

Arkasındaki sebep ikiye ayrılır:
· BEKLENTİ değişimi — şirketin gelecekte kazanacağı para hakkındaki görüş değişti
· ÇARPAN değişimi — aynı kâra piyasanın ödemeye razı olduğu katsayı değişti
  (faiz, risk iştahı, likidite bunu belirler)

Türkiye'de üçüncü bir çarpan daha var: TL'nin değeri. Fiyat TL cinsindendir.""",
 tuzak="""'Çok alan olursa yükselir' demek doğru ama boş. Asıl soru şu:
İNSANLAR NEDEN ALIYOR? Cevap veremiyorsan sadece sonucu tarif etmişsin.""",
 anahtar=["arz", "talep", "beklenti", "çarpan"]),

Soru("t03", 1, "temel", "Bir şirket para kazanıyorsa hissesi kesin yükselir mi?",
 """Hayır. Çünkü fiyat, kâr eden bir şirket olmasını ZATEN içeriyor olabilir.

Piyasa beklentiyi fiyatlar. Şirket 100 lira kâr açıklarsa ve piyasa 120
bekliyorduysa, kâr etmiş olmasına rağmen hisse düşer. 'İyi haber geldi ama
hisse düştü' olayının tamamı budur.

İkinci sebep: kâr artıyor ama ÇARPAN düşüyor olabilir. Faiz yükseldiğinde
piyasa aynı kâra daha az ödemeye razı olur. Kâr %20 artar, çarpan %30 düşer,
hisse net olarak düşer.""",
 tuzak="""'Kâr = yükseliş' bağı kurmak, borsada en pahalı sezgisel hatadır.
Fiyat kârın kendisini değil, KÂR HAKKINDAKİ BEKLENTİNİN DEĞİŞİMİNİ takip eder.""",
 anahtar=["beklenti", "fiyatlanmış", "çarpan"]),

Soru("t04", 1, "temel", "Şirketin değeri ile hisse fiyatı arasındaki fark nedir?",
 """DEĞER, şirketin gelecekte üreteceği nakdin bugünkü karşılığıdır — hesaplanır,
tahmin edilir, tartışılır.
FİYAT, bugün birinin ödemeye razı olduğu rakamdır — ekranda yazar.

İkisi çoğu zaman eşit değildir. Yatırımın tamamı bu farkta yaşar: fiyat
değerin altındaysa alırsın, üstündeyse almazsın.

Ama dikkat: değeri sen hesaplıyorsun ve yanılabilirsin. 'Ucuz' dediğin şey
senin hesabına göre ucuzdur; piyasa senin görmediğin bir şey görüyor olabilir.""",
 tuzak="""Fiyatın düşük olmasını 'ucuz' sanmak. 3 TL'lik hisse 400 TL'likten
ucuz değildir. Ucuzluk fiyatın DEĞERE oranıdır, fiyatın kendisi değil.""",
 anahtar=["değer", "fiyat", "iskonto"]),

Soru("t05", 1, "temel", "Piyasa değeri nedir?",
 """Hisse fiyatı × toplam hisse adedi. Şirketin tamamını bugünkü fiyattan satın
almanın maliyeti.

Neden önemli: kıyaslamanın tek doğru birimi budur. THYAO 300 TL, EREGL 38 TL —
bu bir şey söylemez. Ama THYAO 412 milyar TL, EREGL 258 milyar TL dersen,
şirketlerin büyüklüğünü gerçekten kıyaslamış olursun.

Bir adım ötesi FİRMA DEĞERİ: piyasa değeri + net borç. Şirketi satın alırken
borcunu da devraldığın için gerçek maliyet budur.""",
 tuzak="""Hisse adedini görmezden gelmek. Bedelsiz sermaye artırımında adet
ikiye katlanır, fiyat yarıya iner, piyasa değeri AYNI kalır. Zenginleşmedin.""",
 anahtar=["piyasa değeri", "hisse adedi", "firma değeri"]),

Soru("t06", 1, "carpan", "F/K nedir ve ne anlatır?",
 """Piyasa değeri ÷ yıllık net kâr. 'Şirket bugünkü kârını sürdürürse yatırımını
kaç yılda geri alırsın' sorusunun cevabı.

F/K 10 demek, %10 kazanç verimi demek (1/10). Bu yüzden F/K'yı her zaman
MEVDUAT FAİZİYLE kıyasla. Türkiye'de faiz %40 iken F/K 10 olan hisse, %10
getiri vaat ediyor demektir — risksiz alternatifin çok altında.

BIST çarpanlarının gelişmiş ülkelere göre yapısal olarak düşük olmasının
sebebi budur. 'BIST ucuz' cümlesi genelde bu gerçeği atlar.""",
 tuzak="""F/K'yı tek başına kullanmak. Kârın kalitesini, sürdürülebilirliğini
ve borçluluğu göstermez. Zarar eden şirkette hiç çalışmaz (negatif ya da
anlamsız çıkar).""",
 anahtar=["net kâr", "kazanç verimi", "faiz"]),

Soru("t07", 1, "carpan", "PD/DD nedir?",
 """Piyasa değeri ÷ özsermaye (defter değeri). Şirketin muhasebe defterindeki
net varlığının kaç katına satıldığı.

1'in altı 'defter değerinin altında' demektir — teorik olarak şirketi alıp
varlıklarını satsan kâr edersin. Pratikte nadiren o kadar basittir.

En çok BANKALARDA ve GYO'da kullanılır, çünkü onların varlıkları büyük ölçüde
finansal ve defter değeri gerçeğe yakındır. Bir yazılım şirketinde PD/DD
anlamsızdır — asıl varlığı bilançoda görünmez.""",
 tuzak="""Düşük PD/DD'yi otomatik 'ucuz' saymak. Özsermayesi eriyen bir şirkette
PD/DD düşer ve bu iyi haber değildir. PD/DD'yi mutlaka ROE ile birlikte oku:
düşük PD/DD + düşük ROE = şirket sermayeyi verimsiz kullanıyor.""",
 anahtar=["özsermaye", "defter değeri", "ROE"]),

Soru("t08", 1, "carpan", "FD/FAVÖK nedir?",
 """Firma değeri (piyasa değeri + net borç) ÷ FAVÖK (faiz, amortisman ve vergi
öncesi kâr).

Neden var: F/K borç yapısını görmezden gelir. İki şirket aynı kârı ediyorsa
ama biri borçsuz diğeri boğazına kadar borçluysa, F/K'ları benzer çıkar ve
seni yanıltır. FD/FAVÖK borcu hesaba katar, bu yüzden farklı sermaye
yapılarını kıyaslamayı SAĞLAR.

Sermaye yoğun sektörlerde (sanayi, havacılık, telekom) F/K'dan güvenilirdir,
çünkü amortisman net kârı bozar ama nakit çıkışı değildir.""",
 tuzak="""Bankada kullanmak. Bankada borç hammaddedir, 'firma değeri' kavramı
işlemez. Ayrıca FAVÖK nakit akışı DEĞİLDİR — yatırım harcamasını içermez.""",
 anahtar=["firma değeri", "net borç", "FAVÖK"]),

Soru("t09", 1, "temel", "Şirketin borcu neden önemlidir?",
 """Borç kârı büyütür ama riski de büyütür — iki yönlü kaldıraçtır.

İşler iyiyken borçla büyüyen şirket, özsermaye getirisini yükseltir. İşler
kötüleştiğinde ise faiz ödemesi durmaz: satış düşse de borç faizi aynı kalır.
Şirketleri batıran şey genelde zarar değil, NAKİT SIKIŞIKLIĞIDIR.

Türkiye'de iki ek boyut var:
· Faiz yüksek — borcun maliyeti çok ağır
· Borç dövizliyse, TL değer kaybettiğinde borç TL cinsinden şişer ama gelir
  TL ise şişmez. Bu makas şirket öldürür.

Bakılacak oran: Net Borç / FAVÖK. 4'ün üstü tehlike bölgesi.""",
 tuzak="""'Borcu var, demek ki kötü' demek. Borçsuz şirket bazen sermayeyi
verimsiz kullanıyor demektir. Sorun borcun VARLIĞI değil, ÖDENEBİLİRLİĞİDİR.""",
 anahtar=["kaldıraç", "faiz karşılama", "net borç/FAVÖK", "kur riski"]),

Soru("t10", 1, "bilanco",
 "Ciro, brüt kâr, faaliyet kârı ve net kâr arasındaki fark nedir?",
 """Gelir tablosunda yukarıdan aşağı inen bir merdiven:

CİRO (hasılat) — satılan malın toplam tutarı. Hiçbir maliyet düşülmemiş.
  eksi: satılan malın maliyeti
BRÜT KÂR — ürünün kendi maliyetinin üstünde ne kadar satılabildiği.
  Yüksek brüt marj = fiyatlama gücü.
  eksi: pazarlama, genel yönetim, Ar-Ge
FAALİYET KÂRI — ANA İŞİN performansı. En dürüst satır burasıdır.
  eksi/artı: faiz, kur farkı, tek seferlik kalemler
  eksi: vergi
NET KÂR — cebe kalan.

Kritik: net kâr en çok manipüle edilebilen ve en çok dalgalanan satırdır.
Kur farkı bir çeyrekte net kârı ikiye katlar, ertesi çeyrek yarıya indirir —
şirketin işi hiç değişmeden.""",
 tuzak="""Sadece net kâra bakmak. Faaliyet kârı düşerken net kâr artıyorsa,
o artış ana işten gelmiyor demektir — arayıp bulman gerekir.""",
 anahtar=["hasılat", "brüt", "faaliyet", "net", "marj"]),

Soru("t11", 1, "bilanco", "Serbest nakit akışı nedir?",
 """Faaliyetlerden gelen nakit − yatırım harcaması (capex). Şirketin işini
sürdürdükten sonra ELİNDE GERÇEKTEN KALAN para.

Neden en önemli sayı: temettü buradan ödenir, borç buradan kapatılır, geri
alım buradan yapılır. Kâr bir muhasebe kararıdır; nakit gerçektir.

Kâr ile nakit arasındaki fark nereden gelir: kâr, satış yapıldığında yazılır —
para tahsil edilmese bile. Şirket mal satar, faturayı keser, kâr yazar, ama
parayı 6 ay sonra alır (ya da hiç alamaz).""",
 tuzak="""FAVÖK'ü nakit akışı sanmak. FAVÖK yatırım harcamasını, işletme
sermayesi değişimini ve vergiyi içermez. Sermaye yoğun bir şirkette FAVÖK
yüksek, serbest nakit akışı negatif olabilir.""",
 anahtar=["capex", "faaliyet nakit akışı", "kâr kalitesi"]),

Soru("t12", 1, "temel", "Temettü nedir?",
 """Şirketin kârından ortaklara dağıttığı nakit.

Kritik nokta: dağıtım günü hisse fiyatı temettü kadar DÜŞER. Şirketin
kasasından çıkan para, şirketin değerinden de çıkar. Yani temettü bedava para
değildir — cebinden cebine aktarımdır.

Peki neden değerli? Çünkü şirket o nakdi senden daha kötü değerlendirecekse,
sana vermesi daha iyidir. Kötü yatırım yapan bir yönetim, dağıtmayarak değer
yok eder.

Türkiye'de ek boyut: temettüde stopaj var, alım-satım kazancında (bireysel
yatırımcı için) %0. Vergi açısından nötr değil.""",
 tuzak="""Yüksek temettü verimini otomatik iyi saymak. Verim = temettü/fiyat.
Fiyat çöktüğü için verim yükselmiş olabilir. Ayrıca %40 mevduat faizi varken
%3 temettü verimi bir çekicilik değildir.""",
 anahtar=["nakit dağıtım", "fiyat düşüşü", "stopaj"]),

Soru("t13", 1, "makro", "Enflasyon borsayı nasıl etkiler?",
 """İki karşıt yönde çalışır:

OLUMLU — şirketlerin nominal cirosu ve kârı enflasyonla birlikte şişer. Hisse
reel varlık olduğu için, nakit tutmaya göre koruma sağlar.

OLUMSUZ — enflasyon faizi yukarı iter, faiz de borsanın çarpanını aşağı iter.
Ayrıca maliyet artışını fiyata geçiremeyen şirketin marjı ezilir.

Asıl mesele şu: nominal getiri seni kandırır. Bu sistemin ölçtüğü rakam —
BIST 100'ün son bir yıllık nominal getirisi %28,1, enflasyon %31,8. Yani REEL
getiri NEGATİF. Kazandığını sanırken alım gücü kaybediyorsun.""",
 tuzak="""'Enflasyonda borsa kazandırır' demek yarım doğrudur. Enflasyonu
GEÇEBİLİRSE kazandırır. Geçemezse nominal artış görürsün ama fakirleşirsin.""",
 anahtar=["reel getiri", "nominal", "çarpan", "fiyatlama gücü"]),

Soru("t14", 1, "makro", "Faiz yükselirse şirketler ve borsa neden etkilenir?",
 """Üç ayrı kanaldan:

1) MALİYET — borçlu şirketin faiz gideri artar, kârı düşer. Net Borç/FAVÖK'ü
   yüksek olanlar en çok acı çeker.
2) ÇARPAN — risksiz getiri yükseldiğinde, riskli varlığa ödenen çarpan düşer.
   Şirketin kârı hiç değişmese bile hisse düşer. Bu kanal genelde en güçlüsü.
3) TALEP — kredi pahalanır, tüketici ertelenebilir harcamayı erteler.
   Otomotiv, beyaz eşya, konut önce etkilenir.

Kimler kazanır: bankalar (marjı açılır, ama kredi riski de artar), net nakit
pozisyonunda oturan şirketler (mevduat geliri artar).""",
 tuzak="""'Faiz arttı, banka kazanır' demek fazla basit. Marj açılır ama
takipteki krediler de artar. Hangi etkinin baskın olduğu duruma bağlıdır.""",
 anahtar=["iskonto oranı", "çarpan", "borç maliyeti", "talep"]),

Soru("t15", 1, "makro",
 "Dolar/TL yükselirse hangi şirketler faydalanır, hangileri zarar görür?",
 """Ayrım geliri ve maliyeti hangi para biriminde diye sorarak yapılır.

KAZANANLAR — geliri dövizli, maliyeti TL:
· İhracatçı sanayi (EREGL, otomotiv, tekstil)
· Havacılık (bilet geliri büyük ölçüde döviz)
· Dövizli geliri olan turizm

KAYBEDENLER — maliyeti dövizli, geliri TL:
· İthal girdi kullanan üreticiler
· Dövizli borcu olup TL geliri olan herkes (enerji, telekom klasik örnek)
· İç talebe dayalı perakende (alım gücü erir)

Ama tek başına yeterli değil: şirketin dövizli BORCU da var mı? Geliri dövizli
ama borcu daha çok dövizliyse net etki negatif olabilir.""",
 tuzak="""'İhracatçı kazanır' ezberi. Girdisi de ithalse net etki küçüktür.
Bilançoda net döviz pozisyonuna bakmadan karar verilmez.""",
 anahtar=["doğal koruma", "net döviz pozisyonu", "ihracatçı", "dövizli borç"]),

Soru("t16", 1, "carpan", "Bir şirketin UCUZ olduğunu nasıl anlarsın?",
 """Tek bir çarpana bakarak anlayamazsın. Üç katmanlı bakılır:

1) KENDİ GEÇMİŞİNE göre — bugünkü F/K'sı son 5 yıl ortalamasının altında mı?
2) SEKTÖR EMSALLERİNE göre — aynı işi yapan şirketlerin medyanının altında mı?
   (Sektörler arası kıyas anlamsızdır; bankanın PD/DD'si 1,2, perakendenin
   2,9 olabilir ve ikisi de normaldir.)
3) KENDİ DEĞERİNE göre — ters DCF ile: bugünkü fiyat hangi büyümeyi ima
   ediyor? O büyüme makul mü?

Ve en önemlisi: ucuzluğun SEBEBİNİ bul. Ucuz şirket genelde bir nedenden
ucuzdur. Sebep geçiciyse fırsat, kalıcıysa tuzaktır.""",
 tuzak="""DEĞER TUZAĞI. Bu sistemin ölçtüğü örnek: EREGL PD/DD 0,90 ile
'defterin altında' görünüyor — ama kalite skoru 31,8 ve faiz karşılama oranı
0,8x, yani faizini bile ödeyemiyor. Ucuz, çünkü sorunlu.""",
 anahtar=["sektör medyanı", "ters DCF", "değer tuzağı", "sebep"]),

Soru("t17", 1, "bilanco", "Bir şirketin KALİTELİ olduğunu nasıl anlarsın?",
 """Kalite, ucuzluktan ayrı bir sorudur ve dört başlıkta ölçülür:

1) KÂRLILIK — faaliyet marjı istikrarlı mı, brüt marj yüksek mi (fiyatlama gücü)
2) SERMAYE GETİRİSİ — ROIC enflasyonun üstünde mi? Değilse şirket her yıl reel
   olarak sermaye yakıyordur.
3) BİLANÇO — Net Borç/FAVÖK düşük, faiz karşılama yüksek, cari oran sağlıklı
4) KÂR KALİTESİ — en kritik tek gösterge: faaliyet nakit akışı / net kâr.
   Sürekli 1'in altındaysa kâr kâğıt üstünde kalıyor demektir.

Türkiye'ye özgü eşik kayması: %31,8 enflasyonda %20 ROE, özsermayenin REEL
olarak eridiği anlamına gelir. Gelişmiş ülkede mükemmel olan sayı burada
yetersizdir.""",
 tuzak="""Büyümeyi kaliteyle karıştırmak. Zarar ederek büyüyen şirket kaliteli
değildir. Ayrıca nominal büyümeyi reel büyüme sanmak: %25 büyüme, %31,8
enflasyonda KÜÇÜLMEDİR.""",
 anahtar=["ROIC", "marj istikrarı", "kâr kalitesi", "reel"]),

Soru("t18", 1, "risk", "Risk nedir ve nasıl ölçülür?",
 """İki ayrı tanım var ve karıştırılırsa pahalıya patlar:

AKADEMİK TANIM — getirinin oynaklığı (standart sapma). Ölçülebilir, hesaplanır,
Sharpe oranında kullanılır.

GERÇEK TANIM — kalıcı sermaye kaybı olasılığı. Şirket batarsa oynaklık artık
bir şey ifade etmez.

Pratikte bakılan ölçüler:
· Oynaklık (yıllık %) — tipik BIST hissesinde %40-60
· Azami düşüş (max drawdown) — zirveden dibe kayıp
· Batma riski — bu risk seviyesiyle sermayeyi yarılama olasılığı

Bu sistemin Monte Carlo ölçümü: %1,5 risk ile 200 işlemde batma olasılığı ~%0;
%20 risk ile %39,5. Aynı strateji, sadece pozisyon boyutu farklı.""",
 tuzak="""Riski 'kaybetme ihtimali' diye tarif edip orada bırakmak. Ölçülmeyen
risk yönetilemez. Ve en sinsi risk düşük oynaklıkta gizlenir: sakin görünen
hisse tek haberle %20 düşebilir — BIST'te tavan/taban ±%20.""",
 anahtar=["oynaklık", "kalıcı kayıp", "azami düşüş", "pozisyon boyutu"]),

Soru("t19", 1, "risk", "Neden bütün parayı tek hisseye koymamalısın?",
 """Çünkü tek bir şirkete özgü olay (dava, yönetim skandalı, üretim kazası,
muhasebe hilesi) sermayenin tamamını silebilir ve bu olayı önceden bilmenin
yolu yoktur.

Matematiği: tek hissede yıllık oynaklık ~%45. 4 hisseye dağıtınca ~%35,6'ya
iner — çünkü şirkete özgü riskler kısmen birbirini götürür.

Ama çeşitlendirmenin SINIRI var: 8 hisseden 20'ye çıkmak oynaklığı %33,8'den
%32,6'ya indiriyor, neredeyse hiçbir şey. Sebep korelasyon — aynı piyasadaki
hisseler birlikte hareket eder. Piyasa riskini çeşitlendiremezsin.

1000 TL'de acı gerçek: BIST'te kesirli hisse yok. 400 TL'lik hisseden 1 adet
zaten sermayenin %40'ı. Bu sermayede gerçek çeşitlendirme zordur.""",
 tuzak="""5 farklı BANKA hissesi almayı çeşitlendirme sanmak. Bu, tek bahsi
beşe bölmektir. Ortalama korelasyon 0,7'nin üstündeyse portföy tek hisse gibi
hareket eder.""",
 anahtar=["korelasyon", "şirkete özgü risk", "sistematik risk", "etkin çeşitlendirme"]),

Soru("t20", 1, "psikoloji", "Bir yatırım kararında yanıldığını nasıl anlarsın?",
 """Ancak ÖNCEDEN yazdıysan anlarsın. Yanılma koşulu alımdan sonra tanımlanamaz —
o noktada her düşüş 'geçici' görünür ve beynin gerekçe üretir.

Yanılma koşulu iki türlü olur:
· FİYAT bazlı — 'stop seviyesinin altında kapanış' (mekanik, tartışmasız)
· TEZ bazlı — 'çeyreklik FAVÖK marjı %8'in altına düşerse' (şirket bazlı)

İkincisi daha değerlidir, çünkü fiyat düşüşü tek başına yanıldığını göstermez;
tezin bozulması gösterir.

Kritik ayrım: KARAR ile SONUÇ farklıdır. Kötü bir kararla para kazanabilirsin.
Kararı, verildiği andaki bilgiye göre değerlendir — sonucuna göre değil.""",
 tuzak="""'Zarardayım demek ki yanıldım' ya da 'kârdayım demek ki haklıydım'
demek. Buna SONUÇ YANILGISI denir ve en tehlikeli hatadır: kötü kararla
kazanmak, o kararı tekrarlamana ve bu sefer daha büyük yapmana yol açar.""",
 anahtar=["yanılma koşulu", "önceden yazmak", "tez bozulması", "sonuç yanılgısı"]),
]


# ═══════════════════════════════════════════ SEVİYE 2 — senaryo ve tuzak

ORTA = [
Soru("o01", 2, "bilanco",
 "Şirketin cirosu %50 arttı ama net kârı %10 arttı. Neden olabilir?",
 """Ciro ile kâr arasındaki merdivende bir yerde sızıntı var. Sırayla ara:

· MALİYET ARTIŞI — girdi fiyatları cirodan hızlı arttı, brüt marj ezildi.
  Enflasyonist ortamda en yaygın sebep.
· FİYATLAMA GÜCÜ YOK — şirket hacmi artırmak için indirim yaptı. Ciro büyür,
  marj küçülür. 'Kârsız büyüme'.
· FAALİYET GİDERİ — büyümek için pazarlama ve personel harcaması yapıldı.
  Yatırımsa iyi, kontrolsüzse kötü.
· FİNANSMAN — büyüme borçla finanse edildi, faiz gideri kârı yedi.
· KUR FARKI — dövizli borçta kur zararı yazıldı.
· GEÇEN YIL BAZ ETKİSİ — geçen yıl tek seferlik bir gelir vardı, bu yıl yok.

Doğru refleks: brüt marj mı düştü, faaliyet marjı mı, yoksa net marj mı?
Hangisi düştüyse sebep orada.""",
 tuzak="""Tek bir sebebe atlamak. Gelir tablosunu yukarıdan aşağı okuyup
marjların HANGİ BASAMAKTA bozulduğunu bulmadan cevap verilmez.""",
 anahtar=["marj", "brüt", "faaliyet", "kur farkı", "baz etkisi"]),

Soru("o02", 2, "bilanco",
 "Şirketin net kârı artıyor ama nakit akışı düşüyor. Ne düşünürsün?",
 """Bu, bilançoda görülebilecek en önemli uyarı sinyallerinden biridir. Muhtemel
sebepler, en masumdan en kötüye:

· İŞLETME SERMAYESİ BÜYÜMESİ — şirket hızlı büyüyor, stok ve alacak şişiyor.
  Büyüme finanse ediliyor. Geçici olabilir.
· ALACAK TAHSİLATI BOZULUYOR — satış yapılıyor, fatura kesiliyor, kâr
  yazılıyor ama para gelmiyor. Müşteri kalitesi düşmüş olabilir.
· STOK BİRİKİYOR — üretilen mal satılmıyor. İlerideki dönemde değer düşüklüğü
  yazılabilir.
· KÂR MUHASEBESEL — tek seferlik değerleme kârı, iştirak kârı, kur farkı geliri.
  Nakit üretmeyen kâr.
· AGRESİF MUHASEBE — gelirin erken yazılması, giderin ertelenmesi.

Bakılacak oran: Faaliyet Nakit Akışı / Net Kâr. Sürekli 1'in altındaysa kâr
şüphelidir. Tek çeyrek anlam ifade etmez, TREND'e bak.""",
 tuzak="""'Kâr artıyor, iyi' deyip geçmek. Muhasebe kârı bir karardır; nakit
gerçektir. Şirketler zarar ettiği için değil, NAKİTSİZ kaldığı için batar.""",
 anahtar=["işletme sermayesi", "alacak", "stok", "kâr kalitesi", "trend"]),

Soru("o03", 2, "bilanco",
 "Şirketin borcu iki yılda iki katına çıktı. Bu iyi mi kötü mü?",
 """Tek başına ne iyi ne kötü. Üç soru sorulur:

1) BORÇ NEREYE GİTTİ?
   · Yeni fabrika, kapasite, satın alma → yatırım. Getirisi sermaye maliyetinin
     üstündeyse DEĞER YARATIR.
   · İşletme sermayesi açığı, eski borcun çevrilmesi, zarar finansmanı →
     tehlike sinyali.
2) ÖDEYEBİLİYOR MU?
   Net Borç/FAVÖK ve faiz karşılama oranına bak. FAVÖK de iki katına çıktıysa
   borç oranı sabit kalmıştır — sorun yok. FAVÖK yerinde sayıyorsa alarm.
3) HANGİ PARA BİRİMİNDE, HANGİ VADEDE?
   Dövizli borç + TL gelir = kur riski. Kısa vadeli borç yüksekse çevirme
   riski var; faizler yükselmişken yenilemek pahalıya patlar.

Türkiye'de ek boyut: %40-60 faiz ortamında borçla büyümek çok pahalıdır.
Yatırımın getirisi bunun üstünde olmalı ki mantıklı olsun.""",
 tuzak="""Mutlak borç rakamına bakmak. Önemli olan borcun BÜYÜKLÜĞÜ değil,
FAVÖK'e ve özsermayeye ORANI ile ödenebilirliğidir.""",
 anahtar=["borcun kullanımı", "net borç/FAVÖK", "faiz karşılama", "vade", "para birimi"]),

Soru("o04", 2, "bilanco",
 "Şirket çok yüksek kâr açıklıyor ama kasasında para yok. Ne olmuş olabilir?",
 """Kâr ile nakit arasındaki köprüyü kur:

· Kâr NAKİT OLMAYAN kalemlerden geliyor olabilir — yatırım amaçlı gayrimenkul
  değerleme kârı, iştirak değer artışı, ertelenmiş vergi geliri, kur farkı geliri.
  Bunlar gelir tablosunda kâr yazar ama kasaya para girmez.
· Nakit İŞLETME SERMAYESİNE bağlanmış — alacak ve stok şişmiş.
· Nakit YATIRIMA gitmiş — capex yüksek. Bu kötü olmayabilir, ama serbest nakit
  akışı negatiftir.
· Nakit BORÇ ÖDEMESİNE gitmiş.
· Nakit TEMETTÜ olarak dağıtılmış.

Nereye gittiğini nakit akış tablosu söyler: üç bölümü (faaliyet / yatırım /
finansman) okursan para yolunu görürsün.

GYO'larda bu durum yapısaldır: değerleme kârı net kârı şişirir, o yüzden
GYO'da F/K genellikle anlamsızdır.""",
 tuzak="""Kârı otomatik nakit sanmak. 'Şirket 1 milyar kâr etti' cümlesi
'1 milyar para kazandı' demek DEĞİLDİR.""",
 anahtar=["nakit olmayan kalem", "değerleme kârı", "nakit akış tablosu", "capex"]),

Soru("o05", 2, "bilanco",
 "Satışlar artıyor ama kâr marjı düşüyor. Ne olmuş olabilir?",
 """Şirket büyümeyi marjdan satın alıyor. Sebepler:

· FİYAT İNDİRİMİ ile hacim kovalanıyor — rekabet artmış olabilir
· ÜRÜN KARMASI değişti — düşük marjlı ürünlerin payı arttı
· MALİYET ARTIŞI fiyata geçirilemiyor — fiyatlama gücü zayıf
· YENİ PAZARA giriş maliyeti — geçici olabilir, yatırım sayılır
· KAPASİTE artışı henüz doluluk kazanmadı — sabit giderler bölünemiyor

Kritik soru: bu GEÇİCİ bir yatırım dönemi mi, yoksa KALICI rekabet erozyonu mu?

Ayrım nasıl yapılır: brüt marj düşüyorsa fiyatlama/maliyet sorunu (kalıcı olma
ihtimali yüksek). Brüt marj sabit ama faaliyet marjı düşüyorsa gider artışı
(yatırım olabilir, geçici olabilir).""",
 tuzak="""Ciro büyümesini otomatik iyi haber saymak. Kârsız büyüme, sermayeyi
düşük getiriyle bağlamaktır. En kötüsü: pazar payı için zarar eden şirket.""",
 anahtar=["fiyatlama gücü", "ürün karması", "brüt vs faaliyet marjı", "geçici mi kalıcı mı"]),

Soru("o06", 2, "carpan", "F/K = 5 olan şirket kesin ucuz mudur?",
 """Hayır. F/K 5, altı farklı sebepten olabilir ve bunların çoğu iyi haber değil:

1) DÖNGÜSEL TEPE — çelik, kimya gibi sektörlerde kâr zirvedeyken F/K en DÜŞÜK
   görünür. Tam da satılacak zamandır. (Peter Lynch'in klasik uyarısı.)
2) TEK SEFERLİK KÂR — arsa satışı, iştirak satışı kârı şişirmiş. Gelecek yıl
   yok.
3) YAPISAL DÜŞÜŞ — piyasa şirketin kârının kalıcı olarak düşeceğini fiyatlıyor.
4) BORÇ — F/K borcu görmez. FD/FAVÖK'e bak, orada pahalı çıkabilir.
5) YÖNETİŞİM RİSKİ — azınlık hakları korunmuyorsa piyasa iskonto uygular.
6) GERÇEKTEN UCUZ — piyasa gözden kaçırmış. En nadir ihtimal.

Türkiye'de ek: %40 faiz varken F/K 5 (=%20 kazanç verimi) MEVDUATIN ALTINDA
getiri demektir. Yani F/K 5 burada "ucuz" değil, normal olabilir.""",
 tuzak="""Düşük F/K avcılığı. Ekranda F/K'ya göre sıralayıp en düşüğü almak,
sistematik olarak döngüsel tepeleri ve yapısal düşüşteki şirketleri toplamaktır.""",
 anahtar=["döngüsel", "tek seferlik", "kâr sürdürülebilirliği", "faiz karşılaştırması"]),

Soru("o07", 2, "carpan",
 "F/K'sı 30 olan şirket mi daha pahalıdır, F/K'sı 5 olan mı?",
 """Bu soru bilerek kurulmuş bir tuzaktır. Cevap: BİLİNMEZ.

F/K bir fiyattır, değer değil. Neyin karşılığında ödendiğine bakmadan pahalı
ya da ucuz denemez.

F/K 30 olan şirket yılda %40 büyüyorsa, üç yıl sonra F/K'sı 11'e iner.
F/K 5 olan şirket her yıl %15 küçülüyorsa, üç yıl sonra F/K'sı 8'e ÇIKAR —
fiyat hiç değişmese bile.

Bakılacak şey:
· Büyüme (PEG oranı bunu kabaca düzeltir)
· Kârın sürdürülebilirliği ve kalitesi
· Sermaye getirisi (yüksek ROIC yüksek çarpanı hak eder)
· Sektör — bankanın F/K'sı ile yazılımın F/K'sı kıyaslanmaz
· Borç yapısı

Ve her zaman: bu iki şirket AYNI SEKTÖRDE mi? Değilse kıyas anlamsız.""",
 tuzak="""İki sayıyı yan yana koyup büyüğüne 'pahalı' demek. Bu, borsadaki
en yaygın ve en pahalı yüzeysel muhakemedir.""",
 anahtar=["büyüme", "PEG", "ROIC", "sektör", "sürdürülebilirlik"]),

Soru("o08", 2, "psikoloji",
 "100.000 TL yatırdın, hisse %20 düştü. Ne yaparsın?",
 """Doğru cevap bir EYLEM değil, bir SÜREÇTİR:

1) Önce şunu sor: yanılma koşulum gerçekleşti mi? Alım öncesi yazdığım şey ne
   idi? (Yazmadıysan asıl sorun burada — bu düşüşte objektif hiçbir dayanağın yok.)
2) Neden düştüğünü araştır. Üç ihtimal:
   · TÜM PİYASA düştü → tezinle ilgisi yok
   · SEKTÖR düştü → tezin sektöre dayanıyorsa yeniden değerlendir
   · SADECE BU HİSSE düştü → şirkete özgü bir şey var, bul
3) Tez bozuldu mu? Kalite skoru düştü mü, yeni kırmızı bayrak çıktı mı,
   trend kırıldı mı? Bu sistem bunları ölçer.
4) Baştan yazdığın risk planına göre hareket et. Stop'a değdiyse sat —
   'biraz daha bekleyeyim' cümlesi tam burada başlar ve orada biter.

Kritik: 'Düşen hisse mutlaka yükselir' diye bir kural YOKTUR. %50 düşen hisse
eski fiyatına dönmek için %100 yükselmek zorundadır.""",
 tuzak="""'Satmam, nasıl olsa çıkar' — bu bir strateji değil, kayıptan kaçınma
refleksidir. Aynı derecede yanlış olan diğer uç: panikle satıp tezini hiç
kontrol etmemek.""",
 anahtar=["yanılma koşulu", "sebep araştırma", "risk planı", "asimetri"]),

Soru("o09", 2, "psikoloji",
 "Bir hisseyi çok beğendin. Şimdi neden ALMAMAN gerektiğini anlat.",
 """Bu bir soru değil, bir DİSİPLİN egzersizidir. Amacı kendi fikrinin esiri
olmanı engellemektir.

Yapılacak: tezini çürütecek en güçlü argümanları ARA. Kendi görüşünü
destekleyen haberleri okumak kolaydır (teyit önyargısı); çürüteni aramak
öğrenilmesi gereken bir alışkanlıktır.

Sorulacaklar:
· Bu şirketin en büyük rakibi ne yapıyor?
· Bu tez neden HERKESÇE biliniyorsa fiyata yansımamış olsun?
· Kârı düşürecek en olası üç senaryo ne?
· Sektörde yapısal bir değişim var mı? (regülasyon, teknoloji, ikame ürün)
· Yönetim geçmişte azınlık hissedarını korudu mu?
· Bu hisseyi bugün SATANLAR ne biliyor da ben bilmiyorum?

Sonra tersini yap: neden alınmalı? İki listeyi yan yana koy.

Bir tez, ancak en güçlü karşı argümanı bildikten sonra sağlamdır.""",
 tuzak="""Karşı argümanları 'zaten biliyorum' diye geçiştirmek. Yazmadığın
karşı argümanı bilmiyorsun demektir. Bu sistemde `tez --ai` tam bu iş için
şeytanın avukatlığı yapar.""",
 anahtar=["teyit önyargısı", "karşı argüman", "karşı taraf", "yapısal risk"]),

Soru("o10", 2, "teknik", "Bir grafiğe bakıyorsun. Buradan alır mısın?",
 """Doğru cevap: "Sadece grafiğe bakarak karar vermem."

Grafik ne söyler: fiyatın geçmişte ne yaptığını, trendin yönünü, hacmin nerede
yoğunlaştığını, oynaklığın seviyesini. Bunlar ZAMANLAMA için değerlidir.

Grafik ne söylemez: şirketin ne kadar kazandığını, borcunu, sektörünün
durumunu, fiyatın değerine göre nerede olduğunu.

Doğru kullanım sırası:
1) NE alacağıma temel analiz + değerleme karar verir
2) NE ZAMAN alacağıma teknik analiz yardım eder
3) NE KADAR alacağıma risk yönetimi karar verir

Grafikte görülmesi gerekenler: trend yapısı (tepe/dip dizilimi), destek-direnç,
hacim teyidi, oynaklık (ATR), kırılım gerçek mi sahte mi.

Ve şu ölçüm akılda kalsın: bu sistem kırılımların yaklaşık %35'inin SAHTE
olduğunu ölçtü. Hacim teyidi olmadan kırılım alınmaz.""",
 tuzak="""Grafiği kehanet aracı sanmak. Göstergeler fiyatın matematiksel
dönüşümüdür — yeni bilgi ÜRETMEZLER, mevcut bilgiyi düzenlerler. Hepsi
gecikmelidir.""",
 anahtar=["zamanlama", "tek başına yeterli değil", "hacim teyidi", "sahte kırılım"]),

Soru("o11", 2, "teknik", "RSI 80'e çıktı. Hisse aşırı alım, satmalı mıyım?",
 """Hayır — RSI tek başına satış sinyali değildir ve tam bu noktada en çok
yanıltır.

Neden: RSI yatay piyasada işe yarar (aşırı uçlardan dönüş olur), ama GÜÇLÜ
TRENDDE haftalarca 70-80 arasında kalabilir. 'Aşırı alım' diye satılan hisse
iki katına çıkabilir.

Doğru okuma: RSI'yi trend filtresiyle birlikte kullan.
· Fiyat SMA200 üstünde + RSI yüksek → trend güçlü, RSI satış sinyali değil
· Fiyat SMA200 altında + RSI yüksek → tepki yükselişi, dikkat

Bu sistemde RSI'nin yeri: skorun ZAMANLAMA bileşeninde. RSI 80 üstü olan hisse
düşük zamanlama puanı alır — "iyi şirket olabilir ama giriş için pahalı nokta"
demektir. Satış sinyali değil, GİRİŞ uyarısıdır.

Fark önemli: elindeki pozisyonu RSI yüzünden satmak ile yeni pozisyona RSI
yüzünden girmemek aynı şey değildir.""",
 tuzak="""'RSI 70 üstü sat, 30 altı al' ezberi. Bu kural trendli piyasada
sistematik olarak para kaybettirir — kazananı erken satar, düşen bıçağı yakalar.""",
 anahtar=["trend filtresi", "SMA200", "zamanlama vs çıkış", "band walking"]),

Soru("o12", 2, "risk",
 "Bir stratejinin kazanma oranı %54 ama zararda. Nasıl olur?",
 """Kazanma oranı tek başına hiçbir şey söylemez. Belirleyici olan
KAZANÇ/KAYIP BÜYÜKLÜĞÜDÜR.

Beklenen değer = (kazanma oranı × ortalama kazanç) − (kaybetme oranı × ortalama kayıp)

Bu sistemin gerçek ölçümü:
· "tepki" stratejisi: %53 kazanma, ortalama kazanç %4,0, ortalama kayıp %5,5
  → beklenti NEGATİF, 3,28 yılda −%21,7
· "kirilim" stratejisi: %48 kazanma, ortalama kazanç %15,5, ortalama kayıp %7,9
  → beklenti POZİTİF, aynı dönemde +%118,6

Yani daha AZ kazanan strateji daha çok para kazandı.

Sebep davranışsal: yüksek kazanma oranı, küçük kârları erken almaktan gelir.
Kaybedeni tutup kazananı erken satmak (dispozisyon etkisi) kazanma oranını
yükseltir ve seni batırır.

Ödül/risk 1:2,21 olan bir sistemde başabaş için sadece %31 kazanma yeter.""",
 tuzak="""'Yüksek kazanma oranı = iyi strateji' sanmak. %90 kazanıp %1 kâr
alan, %10 kaybedip %15 zarar eden strateji matematiksel olarak zarardadır.""",
 anahtar=["beklenen değer", "ödül/risk", "dispozisyon etkisi", "başabaş oranı"]),

Soru("o13", 2, "makro",
 "Faiz indirimi hangi sektörleri neden etkiler?",
 """Faiz indirimi üç kanaldan çalışır, sektörlere farklı vurur:

KAZANANLAR:
· GYO / İNŞAAT — konut kredisi ucuzlar, talep canlanır; ayrıca borç yükü hafifler
· DAYANIKLI TÜKETİM (otomotiv, beyaz eşya) — taksitli alım ucuzlar
· BORÇLU SANAYİ — faiz gideri düşer, net kâr artar
· TEMETTÜ HİSSELERİ (elektrik, telekom) — tahvil gibi değerlenirler, faiz
  düşünce cazipleşirler

KAYBEDENLER / KARIŞIK:
· BANKALAR — net faiz marjı daralabilir. Ama kredi hacmi artar ve takipteki
  krediler azalır; net etki belirsizdir.
· SİGORTA — portföy getirisi düşer

Ve genel etki: iskonto oranı düşünce borsanın ÇARPANI yükselir. Bu, şirket
kârları hiç değişmese bile endeksi yukarı taşır.

Türkiye özeli: faiz indirimi enflasyon beklentisini bozarsa TL değer kaybeder,
o zaman ihracatçı kazanır ama ithalatçı ve dövizli borçlu ezilir. Yani faiz
indiriminin etkisi, KUR üzerinden ikinci bir dalga daha yapar.""",
 tuzak="""'Faiz düştü, her şey yükselir' demek. Faiz indiriminin SEBEBİ önemlidir:
enflasyon gerçekten düştüğü için mi indi, yoksa siyasi baskıyla mı? İkincisi
kuru bozar ve net etki negatif olabilir.""",
 anahtar=["iskonto oranı", "kredi talebi", "net faiz marjı", "kur ikinci dalga"]),

Soru("o14", 2, "temel",
 "Bir şirketin borcu ne zaman tehlikelidir?",
 """Borç şu koşullarda tehlikeli olur — hepsi birlikte değerlendirilir:

1) ÖDEME GÜCÜ ZAYIF — Net Borç/FAVÖK > 4 ve faiz karşılama < 2
2) VADE UYUMSUZLUĞU — kısa vadeli borçla uzun vadeli yatırım finanse edilmiş.
   Yenileme zamanı geldiğinde piyasa kapalıysa şirket kilitlenir.
3) PARA BİRİMİ UYUMSUZLUĞU — dövizli borç, TL gelir. TL %20 değer kaybederse
   borç TL cinsinden %20 şişer, gelir şişmez.
4) FAİZ TİPİ — değişken faizli borç, faiz artışında anında vurur.
5) DÖNGÜSEL SEKTÖR + YÜKSEK BORÇ — en tehlikeli kombinasyon. Döngü döndüğünde
   FAVÖK yarıya iner ama faiz aynı kalır.
6) TEMİNAT/KOVENANT — belirli oranlar bozulursa banka borcu erkene çekebilir.

Ve şu: şirketler zarar ettiği için değil, NAKİTSİZ kaldığı için batar.
Kârlı bir şirket bile vadesi gelen borcu ödeyemezse iflas eder.""",
 tuzak="""Sadece borç/özsermaye oranına bakmak. Bu oran statiktir; ödeme gücünü
FAVÖK ve nakit akışı belirler. Ayrıca bankada bu oran tamamen anlamsızdır.""",
 anahtar=["net borç/FAVÖK", "faiz karşılama", "vade", "kur uyumsuzluğu", "likidite"]),

Soru("o15", 2, "bilanco", "Kâr mı daha önemli, nakit akışı mı?",
 """Uzun vadede ikisi buluşur; kısa vadede NAKİT daha güvenilirdir.

Kâr bir muhasebe kararıdır: ne zaman gelir yazılacağı, amortismanın hangi
yöntemle ayrılacağı, karşılıkların ne kadar olacağı — hepsi yönetimin takdirinde.
Yasal sınırlar içinde bile kârı şişirmenin ya da söndürmenin çok yolu vardır.

Nakit ise banka hesabında ya vardır ya yoktur. Manipüle etmek çok daha zordur.

Ama nakit akışı da tek başına yeterli değil:
· Faaliyet nakit akışı, işletme sermayesi oyunlarıyla bir çeyrek şişirilebilir
  (ödemeleri geciktirmek gibi)
· Yatırım yapmayan şirketin nakdi iyi görünür ama geleceğini yiyordur

Doğru yaklaşım: ikisini BİRLİKTE oku. Kritik oran, faaliyet nakit akışı /
net kâr. Bir kaç yıl üst üste 1'in altındaysa, kâr kâğıt üstündedir.

İstisna: bankada faaliyet nakit akışı mevduat/kredi hareketinden oluşur ve
kâr kalitesi ölçmez. Bu sistem banka için o oranı kapatır.""",
 tuzak="""'Nakit kraldır' deyip kârı görmezden gelmek de hata. Ağır yatırım
dönemindeki sağlıklı bir şirket negatif serbest nakit akışı gösterir.""",
 anahtar=["muhasebe takdiri", "kâr kalitesi", "birlikte okuma", "banka istisnası"]),
]


# ═══════════════════════════════════════════ SEVİYE 3 — ustalık

USTA = [
Soru("u01", 3, "usta", "Bir şirketin kârı neden artar?",
 """Kâr artışının kaynağını bilmeden kalitesini bilemezsin. Beş kaynak var ve
değerleri çok farklıdır:

1) HACİM — daha çok sattı. Sürdürülebilirliği pazarın büyümesine bağlı. İYİ.
2) FİYAT — birim fiyatı artırdı. Fiyatlama gücü göstergesi. ÇOK İYİ.
   (Enflasyonda fiyat artışının ne kadarı gerçek zam, ne kadarı sadece
   enflasyona ayak uydurma — ayırt et.)
3) MARJ — maliyeti düşürdü ya da ürün karması iyileşti. İYİ, ama bir sınırı var.
4) TEK SEFERLİK — arsa satışı, iştirak satışı, dava kazancı, kur farkı geliri.
   DEĞERSİZ, gelecek yıl yok. Ama F/K'yı düşük gösterir ve seni tuzağa çeker.
5) MUHASEBE — amortisman yöntemi değişikliği, karşılık iptali, aktifleştirme.
   ŞÜPHELİ.

Bir de altıncı var: BAZ ETKİSİ. Geçen yıl kötüyse bu yıl %200 artış görürsün
ve bu bir başarı değildir.

Doğru refleks: kâr artışını gelir tablosunun hangi satırından geldiğini bularak
sınıflandır. Faaliyet kârı artmadan net kâr artıyorsa, artış ana işten gelmiyor.""",
 tuzak="""Kâr artışını tek bir olgu sanmak. '%80 kâr artışı' manşeti, tek
seferlik bir arsa satışı olabilir ve hisse açıklama sonrası düşebilir.""",
 anahtar=["hacim", "fiyat", "marj", "tek seferlik", "baz etkisi"]),

Soru("u02", 3, "usta", "Kâr artarken hisse neden düşebilir?",
 """Dört ayrı mekanizma, hepsi gerçek:

1) BEKLENTİ AŞILAMADI — piyasa %40 artış bekliyordu, %25 geldi. Kâr arttı ama
   fiyat düştü. Fiyat kârı değil, beklentinin DEĞİŞİMİNİ takip eder.
2) ÇARPAN DARALDI — faiz yükseldi, risk iştahı düştü. Kâr %20 arttı, F/K
   çarpanı %30 düştü → hisse net %14 düştü.
3) KÂRIN KALİTESİ KÖTÜ — artış tek seferlik kalemden geldi, piyasa bunu
   ayıkladı ve "esas iş kötüleşiyor" dedi.
4) GELECEĞE DAİR SİNYAL — şirket iyi bir çeyrek açıkladı ama yönetim beklentiyi
   düşürdü, ya da sipariş defteri zayıfladı. Piyasa geçmişe değil geleceğe bakar.

Beşinci: "haberi al, gerçekleşince sat". İyi haber zaten fiyatlanmışsa,
gerçekleştiğinde alıcı kalmaz.""",
 tuzak="""Bunu 'piyasa mantıksız' diye açıklamak. Piyasa senin bilmediğin bir
şey biliyor olabilir — ya da senin baktığın sayıya değil, başka bir sayıya
bakıyordur.""",
 anahtar=["beklenti", "çarpan daralması", "kâr kalitesi", "ileriye dönük"]),

Soru("u03", 3, "usta", "Şirket çok iyi ama neden kötü bir yatırım olabilir?",
 """Çünkü kalite ile fiyat AYRI sorulardır. Mükemmel şirketi çok pahalıya almak,
vasat şirketi ucuza almaktan daha kötü sonuç verebilir.

Mekanizma: piyasa şirketin iyi olduğunu zaten biliyor ve fiyatlamış. O fiyat,
gelecekteki mükemmel performansın önemli kısmını içeriyor. Şirket
mükemmel performans gösterse bile sen para kazanamazsın — çünkü onun için
zaten ödedin.

Ters DCF tam bunu ölçer: bu sistemin ölçtüğü örnek — BIMAS'ın bugünkü fiyatı,
serbest nakit akışının 5 yıl boyunca yılda %69,8 büyümesini ima ediyor
(enflasyon %31,8). Şirket iyi olabilir; o büyüme makul mü, asıl soru bu.

İkinci sebep: BÜYÜK SAYILAR YASASI. 10 milyar cirolu şirketin %50 büyümesi
ile 100 milyar cirolunun %50 büyümesi aynı zorlukta değildir.

Üçüncüsü: iyi şirketin kötü YÖNETİMİ. Nakdi kötü satın almalara harcayan
yönetim, sağlam bir işi yıllar içinde eritir.""",
 tuzak="""'İyi şirket = iyi yatırım' denklemi. Bu, borsadaki en pahalı
denklemlerden biridir. Ödediğin fiyat, alacağın getiriyi belirler.""",
 anahtar=["fiyat vs kalite", "beklenti fiyatlanmış", "ters DCF", "büyük sayılar"]),

Soru("u04", 3, "usta", "Şirket kötü ama hisse neden yükselebilir?",
 """Çünkü fiyat, mevcut duruma değil, DURUMUN DEĞİŞİM YÖNÜNE tepki verir.

· KÖTÜDEN AZ KÖTÜYE — piyasa iflas fiyatlıyordu, şirket hayatta kaldı.
  "Beklenenden az kötü" bir yükseliş sebebidir. Buna dönüşüm (turnaround) denir.
· ÇARPAN GENİŞLEMESİ — faiz indi, risk iştahı arttı. Şirket hiç değişmedi.
· VARLIK DEĞERİ — şirket zarar ediyor ama sahip olduğu arsa/marka/iştirak
  piyasa değerinden fazla.
· SATIN ALMA BEKLENTİSİ — birileri şirketi almak istiyor.
· SPEKÜLASYON ve MANİPÜLASYON — düşük halka açıklık oranı olan hisselerde,
  fiyat temelden tamamen kopabilir. BIST'te bunun örneği çoktur.
· KISA POZİSYON SIKIŞMASI

Kritik ders: hisse yükseldi diye şirketin iyi olduğu sonucu ÇIKMAZ. Fiyat
hareketi bir kanıt değildir.""",
 tuzak="""Yükselen hisseyi 'demek ki iyiymiş' diye yorumlayıp sonradan almak.
Bu, manipülasyonun tam olarak beklediği davranıştır.""",
 anahtar=["değişim yönü", "turnaround", "çarpan genişlemesi", "manipülasyon"]),

Soru("u05", 3, "usta", "Ucuz şirket ile ucuz hisse arasındaki fark nedir?",
 """UCUZ ŞİRKET — çarpanları düşük: F/K, PD/DD, FD/FAVÖK sektör medyanının
altında. Bu bir GÖZLEMDİR, ölçülür.

UCUZ HİSSE — fiyatı, şirketin gerçek değerinin altında. Bu bir YARGIDIR,
hesaplanır ve yanılabilirsin.

Fark neden kritik: bir şirket çarpan olarak ucuz olup değer olarak PAHALI
olabilir. Kârı kalıcı olarak düşecek bir şirketin bugünkü F/K'sı 4 olabilir;
kâr yarıya inince F/K 8 olur ve hisse hiç ucuz değildi.

Tersi de doğru: çarpanları yüksek bir şirket, büyümesi devam edecekse değer
olarak ucuz olabilir.

Köprü şu soru: bugünkü kâr NORMALLEŞMİŞ kâr mı? Döngüsel tepede mi, dipte mi?
Değerleme her zaman normalleştirilmiş kâr üzerinden yapılır.""",
 tuzak="""Çarpan taramasını değerleme sanmak. Ekranda F/K'ya göre sıralamak
'ucuz şirketleri' bulur — 'ucuz hisseleri' değil. Aradaki fark, değer
tuzağının kendisidir.""",
 anahtar=["çarpan vs değer", "normalleştirilmiş kâr", "değer tuzağı", "döngü"]),

Soru("u06", 3, "usta", "Büyüyen şirket neden bazen kötü yatırım olabilir?",
 """Büyüme kendiliğinden değer yaratmaz. Değer yaratması için tek bir koşul var:
yatırılan sermayenin getirisi (ROIC), sermayenin maliyetinin ÜSTÜNDE olmalı.

ROIC < sermaye maliyeti ise, şirket büyüdükçe DEĞER YOK EDER. Her yeni lira
yatırım, geri getirdiğinden az kazandırır. Büyüme bu durumda zararı büyütür.

Türkiye'de bu eşik çok yüksek: %40-50 faiz varken sermaye maliyeti de o
civardadır. %25 ROIC ile büyüyen bir şirket, gelişmiş ülkede yıldızdır,
burada değer yakıyor olabilir.

İkinci sebep: büyüme NAKİT YAKAR. Hızlı büyüyen şirketin stoku ve alacağı
şişer, capex artar. Serbest nakit akışı negatife döner ve şirket sürekli
finansmana muhtaç hale gelir. Finansman kapanırsa büyüme şirketi öldürür.

Üçüncüsü: büyüme fiyata çoktan yansımış olabilir (bkz. u03).""",
 tuzak="""Ciro büyümesini otomatik olumlu saymak. Doğru soru 'ne kadar
büyüdü' değil, 'bu büyümeyi hangi sermayeyle ve hangi getiriyle satın aldı'.""",
 anahtar=["ROIC vs sermaye maliyeti", "kârlı büyüme", "nakit yakma", "reel eşik"]),

Soru("u07", 3, "usta", "Yüksek F/K her zaman kötü müdür?",
 """Hayır. Yüksek F/K üç meşru sebepten olabilir:

1) YÜKSEK BÜYÜME — bugünkü kâr küçük ama hızla büyüyor. F/K 40 olan şirket
   yılda %50 büyürse 3 yılda F/K'sı 12'ye iner.
2) YÜKSEK KALİTE ve DÜŞÜK SERMAYE İHTİYACI — ROIC'i çok yüksek, büyümek için
   az sermaye gereken şirketler yüksek çarpanı HAK EDER.
3) DÖNGÜSEL DİP — kâr geçici olarak çökmüş, F/K şişmiş görünüyor. Aslında
   satın alınacak zamandır. (Döngüselde F/K TERS okunur: yüksek F/K = ucuz,
   düşük F/K = pahalı.)

Yüksek F/K ne zaman gerçekten kötü: büyüme yavaşlıyorsa, kalite düşükse,
ya da çarpan sadece hikâyeye dayanıyorsa. Çarpan daralması en hızlı zarar
mekanizmasıdır — kâr aynı kalsa bile hisse yarılanabilir.

Türkiye'ye özgü: %40 faiz varken F/K 40 (=%2,5 kazanç verimi) çok zor
savunulur. Buradaki eşikler gelişmiş ülkeden farklıdır.""",
 tuzak="""Yüksek F/K'yı otomatik 'balon' saymak da, otomatik 'büyüme primi'
saymak da hata. Hangi sebeple yüksek olduğunu BULMADAN karar verilmez.""",
 anahtar=["büyüme", "ROIC", "döngüsel ters okuma", "çarpan daralması"]),

Soru("u08", 3, "usta", "Düşük F/K her zaman iyi midir?",
 """Hayır — ve bu soru o06'nın aynası olarak bilerek soruluyor.

Düşük F/K'nın en sık sebepleri:
· DÖNGÜSEL TEPE — kâr zirvede, F/K en düşük görünüyor, satılacak an
· KÂRIN KALICI DÜŞÜŞÜ — piyasa şirketin kârının azalacağını fiyatlıyor
· TEK SEFERLİK KÂR — geçen yılın olağanüstü kalemi
· YÖNETİŞİM İSKONTOSU — azınlık hakları korunmuyor, piyasa güvenmiyor
· LİKİDİTE İSKONTOSU — hisse az işlem görüyor, kurumsal yatırımcı giremiyor
· BORÇ — F/K borcu görmez; FD/FAVÖK'te pahalı çıkabilir

Piyasa çoğu zaman aptal değildir. Düşük F/K gördüğünde varsayılan tutumun
"neden bu kadar ucuz?" olmalı, "ne fırsat!" değil.

Cevabı bulamıyorsan, piyasa senin görmediğin bir şey görüyor demektir.""",
 tuzak="""Düşük F/K'ya göre tarama yapıp en düşükleri almak. Bu, sistematik
olarak döngüsel tepe ve yapısal düşüş toplamaktır. Buna değer tuzağı denir
ve bu sistemde EREGL örneğiyle ölçülmüştür.""",
 anahtar=["döngüsel tepe", "kalıcı düşüş", "yönetişim", "değer tuzağı"]),

Soru("u09", 3, "usta", "Enflasyon hangi şirketleri avantajlı hale getirir?",
 """Ayrım tek bir yetenekte: maliyet artışını fiyata NE KADAR HIZLI geçirebiliyor?

AVANTAJLI:
· FİYATLAMA GÜCÜ olanlar — marka, tekel benzeri konum, ikamesi zor ürün
· HIZLI DEVİR HIZI olanlar — perakende, gıda. Stoku hızlı döner, eski maliyetle
  alıp yeni fiyattan satar.
· REEL VARLIK sahipleri — gayrimenkul, madencilik, altyapı. Varlığın nominal
  değeri enflasyonla artar.
· SABİT FAİZLİ BORÇLU olanlar — borç reel olarak erir (enflasyon borçluyu
  zenginleştirir)
· DÖVİZ GELİRLİ olanlar — TL enflasyonu geliri etkilemez

DEZAVANTAJLI:
· UZUN VADELİ SABİT FİYATLI SÖZLEŞMESİ olanlar (taahhüt, inşaat)
· REGÜLE FİYATLI sektörler — zam için izin bekleyenler
· UZUN ÜRETİM DÖNGÜSÜ olanlar — maliyet bugün, satış bir yıl sonra
· NAKİT AĞIRLIKLI bilançolar — nakit erir

Ama uzun vadede herkes kaybeder: yüksek enflasyon planlamayı imkânsızlaştırır,
faizi yükseltir, çarpanları düşürür.""",
 tuzak="""'Enflasyonda hisse alınır' genellemesi. Doğru soru şirket bazında:
bu şirket zammı ne kadar sürede geçirebiliyor? Geçiremeyenin marjı ezilir.""",
 anahtar=["fiyatlama gücü", "stok devir hızı", "reel varlık", "sabit faizli borç"]),

Soru("u10", 3, "usta",
 "Kur artışı bir şirketin gelirini ve maliyetini nasıl değiştirir?",
 """Dört ayrı kanaldan ve hepsini birlikte hesaplamak gerekir:

1) GELİR — ihracat geliri dövizliyse TL karşılığı artar. Ama miktar sabit
   kalırsa bu sadece nominal bir artıştır.
2) MALİYET — ithal girdi TL cinsinden pahalanır. Girdi oranı yüksekse gelir
   artışını yer.
3) BİLANÇO (en çok atlanan) — dövizli borç TL cinsinden şişer ve bu, gelir
   tablosuna KUR FARKI ZARARI olarak tek kalemde düşer. Nakit çıkışı olmadan
   net kâr çöker.
4) TALEP — TL değer kaybı alım gücünü düşürür, iç talep daralır.

Net etkiyi bulmak için bakılacak şey: NET DÖVİZ POZİSYONU (dövizli varlık −
dövizli yükümlülük) ve doğal koruma (natural hedge) derecesi.

Bu sistemin yakaladığı somut örnek: THYAO finansallarını USD açıklar ama
hissesi TL işlem görür. Bu ikisini karıştıran her oran çöp üretir — yfinance
THYAO'nun F/S'sini 15,66 gösteriyor, gerçeği 0,34.""",
 tuzak="""'İhracatçı = kur kazananı' ezberi. Girdisi de ithalse ve dövizli
borcu varsa net etki negatif olabilir. Bilançoyu görmeden karar verilmez.""",
 anahtar=["net döviz pozisyonu", "doğal koruma", "kur farkı zararı", "iç talep"]),

Soru("u11", 3, "usta", "Temettü almak gerçekten bedava para mıdır?",
 """Hayır. Temettü dağıtıldığı gün hisse fiyatı temettü kadar düşer. Şirketin
kasasından çıkan para, şirketin değerinden de çıkar. Toplam servetin
değişmez — sadece bir kısmı hisseden nakde döner.

Peki neden önemli:
· DİSİPLİN — nakdi dağıtan yönetim, onu kötü satın almalara harcayamaz
· SİNYAL — düzenli temettü, kârın gerçek ve nakit olduğunun kanıtıdır
· SERMAYE DAĞITIMI — şirket o nakdi senden daha kötü değerlendirecekse, sana
  vermesi doğrudur

Ve ne zaman KÖTÜ:
· Yüksek ROIC'i olan bir şirket temettü dağıtıyorsa, büyüme fırsatı yok demektir
· Borçlanarak temettü dağıtmak değer yok eder
· Türkiye'de temettüde stopaj var, alım-satım kazancında (bireysel için) %0 —
  vergi açısından temettü dezavantajlı

Ayrıca: %40 mevduat faizi varken %3 temettü verimi bir çekicilik değildir.""",
 tuzak="""'Temettü aldım, kâr ettim' düşüncesi. Aynı gün hissen düştü. Kâr
edip etmediğin, TOPLAM getirine (fiyat değişimi + temettü) bakılarak bulunur.""",
 anahtar=["fiyat düzeltmesi", "sermaye dağıtımı", "stopaj", "toplam getiri"]),

Soru("u12", 3, "risk",
 "Bir hisse %50 düştüğünde, %50 yükselerek neden eski fiyatına dönmez?",
 """Çünkü yüzdeler farklı tabana uygulanır. 100 → 50 düşüş %50'dir. 50 → 100
yükseliş %100'dür.

Genel formül: %x kayıptan kurtulmak için gereken kazanç = x / (100 − x)
· %10 kayıp → %11 gerekir
· %20 kayıp → %25
· %33 kayıp → %50
· %50 kayıp → %100
· %75 kayıp → %300
· %90 kayıp → %900

Bu asimetri, risk yönetiminin TAMAMININ sebebidir. Kaybı küçük tutmak,
kazancı büyütmekten matematiksel olarak daha değerlidir.

Pratik sonucu: bu sistem işlem başına %1,5 risk kullanır. Üst üste 10 kayıp
sermayeyi ~%14 düşürür — geri kazanmak için %16 gerekir, dayanılabilir.
%20 risk kullansaydın 10 kayıp seni %89 aşağı indirirdi; geri dönmek için
%790 gerekirdi. Pratikte imkânsız.

Aynı asimetri bileşik getiride de var: -%50 ve +%50 sırayla gerçekleşirse
elinde 0,75 kalır.""",
 tuzak="""Yüzdeleri toplanabilir sanmak. -%50 sonra +%50 sıfır etmez, -%25 eder.
Bu, oynaklığın neden zararlı olduğunun matematiksel açıklamasıdır.""",
 anahtar=["asimetri", "geri kazanma matematiği", "pozisyon boyutu", "bileşik"]),

Soru("u13", 3, "usta",
 "Aynı sektörde iki şirket. Biri F/K 8, diğeri F/K 16. Hangisini alırsın?",
 """Bu bilgiyle KARAR VERİLEMEZ. Sormak gereken sorular:

· ROIC'leri ne? Yüksek getirili şirket yüksek çarpanı hak eder.
· Büyüme oranları ne? F/K 16 olan iki kat hızlı büyüyorsa çarpan farkı mantıklı.
· Borçları ne? F/K borcu görmez; FD/FAVÖK'te sıralama tersine dönebilir.
· Kârları normalleşmiş mi? Biri tek seferlik kârla F/K'sını düşürmüş olabilir.
· Marj trendleri ne yönde? Genişleyen marj, daralan marjdan değerlidir.
· Yönetişim ve halka açıklık farkı var mı?
· Kâr kaliteleri (nakit/net kâr) nasıl?

Ucuz olan genelde bir SEBEPTEN ucuzdur. Sebebi bulamıyorsan, o sebep senin
göremediğin bir risktir.

Ve doğru cevap bazen "ikisini de almam" olur.""",
 tuzak="""Aynı sektör olduğu için doğrudan kıyaslanabilir sanmak. Aynı sektörde
bile iş modelleri farklı olabilir — bir perakendeci kendi mağazasına sahipse,
diğeri kiralıyorsa bilançoları kıyaslanamaz.""",
 anahtar=["ROIC", "büyüme", "borç", "normalleştirme", "sebep"]),

Soru("u14", 3, "risk",
 "Portföyünde 5 hisse var ve hepsi aynı gün %8 düştü. Bu ne anlama gelir?",
 """Portföyün çeşitlendirilmiş DEĞİL. Beş ayrı bahis gibi görünüyor ama tek bir
bahis.

Ölçüsü: ortalama korelasyon. 0,7'nin üstündeyse portföy tek hisse gibi hareket
eder. Bu sistem bunu `risk/portfoy` uç noktasında hesaplar ve "etkin hisse
sayısı" verir — 5 hissen olabilir ama etkin sayı 1,8 çıkabilir.

Yaygın gizli yoğunlaşmalar:
· Aynı sektör (5 banka almak çeşitlendirme değildir)
· Aynı makro faktör (hepsi faize duyarlı, ya da hepsi kur kazananı)
· Aynı müşteri tabanı (hepsi iç talebe bağlı)
· Aynı holding grubu

Ama şunu da bil: piyasa geneli düştüğünde HER portföy düşer. Sistematik riski
çeşitlendiremezsin — onu ancak NAKİT oranıyla ve pozisyon boyutuyla yönetirsin.

Bu yüzden nakit bir pozisyondur.""",
 tuzak="""Hisse SAYISINI çeşitlendirme sanmak. Önemli olan kaç tane değil,
birbirinden ne kadar bağımsız olduklarıdır.""",
 anahtar=["korelasyon", "etkin hisse sayısı", "gizli yoğunlaşma", "sistematik risk"]),

Soru("u15", 3, "psikoloji",
 "Bir işlemden %40 kâr ettin. Kararın doğru muydu?",
 """Sonuçtan karara geriye doğru gitmek yanlıştır. Buna SONUÇ YANILGISI denir
ve en tehlikeli düşünce hatasıdır.

Doğru değerlendirme, kararı VERİLDİĞİ ANDAKİ bilgiye göre yapar:
· Tezim yazılı mıydı ve sağlam mıydı?
· Pozisyon boyutu risk kurallarıma uygun muydu?
· Stop ve hedef önceden belli miydi?
· Süreç mi işledi, yoksa şans mı yardım etti?

Dört olası kombinasyon:
· İyi karar + iyi sonuç → tekrarla
· İyi karar + kötü sonuç → yine tekrarla (olasılık böyle çalışır)
· KÖTÜ KARAR + İYİ SONUÇ → EN TEHLİKELİSİ. Kötü alışkanlığı pekiştirir ve
  bir sonrakinde daha büyük yaparsın.
· Kötü karar + kötü sonuç → dersini al

Borsa, kötü kararları hemen cezalandırmaz — bu yüzden öğrenmesi zordur.
Bu sistemde tez yazılıp SAKLANMASININ sebebi budur: karar anındaki
düşünceni sonucun bulandırmasını engeller.""",
 tuzak="""'Kazandım demek ki doğruydu.' Kumarhanede rulette kırmızıya koyup
kazanan biri de kazanmıştır. Süreç ile sonucu ayır.""",
 anahtar=["sonuç yanılgısı", "süreç vs sonuç", "olasılık", "tez kaydı"]),
]

TUM_SORULAR = TEMEL + ORTA + USTA


# ═══════════════════════════════════════════ Şirket okuma kontrol listesi

SIRKET_OKUMA = [
    ("is_modeli", "Ne iş yapıyor?",
     "Ürünü/hizmeti ne, kime satıyor. Tek cümlede anlatamıyorsan anlamamışsındır."),
    ("nasil_kazanir", "Nasıl para kazanıyor?",
     "Gelir kalemleri neler, hangisi baskın, tekrarlayan mı tek seferlik mi."),
    ("gelir_buyume", "Gelirleri büyüyor mu?",
     "Nominal değil REEL bak: enflasyonun üstünde mi? 3 yıllık trende bak."),
    ("kar_buyume", "Kârı büyüyor mu?",
     "Hasılattan hızlı büyüyorsa marj genişliyor demektir — iyi işaret."),
    ("borc", "Borcu ne durumda?",
     "Net Borç/FAVÖK, faiz karşılama, vade ve para birimi uyumu."),
    ("nakit", "Nakit üretiyor mu?",
     "Serbest nakit akışı pozitif mi, faaliyet nakit akışı/net kâr 1'in üstünde mi."),
    ("karlilik", "Kârlılık oranları nasıl?",
     "Brüt/faaliyet/net marj ve trendleri. ROE ve ROIC enflasyonun üstünde mi?"),
    ("sektor", "Sektörü büyüyor mu?",
     "Pazar büyüyor mu, yoksa şirket pay mı çalıyor? İkisi çok farklı."),
    ("rakipler", "Rakipleri kim?",
     "Pazar payı nasıl değişiyor, rekabet fiyat üzerinden mi kalite üzerinden mi."),
    ("avantaj", "Şirketin avantajı ne?",
     "Marka, ölçek, maliyet, ağ etkisi, düzenleme, konum. Yoksa marjı erir."),
    ("yonetim", "Yönetim nasıl?",
     "Sermaye dağıtımı geçmişi, azınlık haklarına saygı, verdiği sözü tutmuş mu."),
    ("pahali_mi", "Hisse pahalı mı?",
     "Kendi geçmişine, sektör medyanına ve ters DCF'e göre."),
    ("ucuz_mu", "Ucuzsa NEDEN ucuz?",
     "Sebebi bul. Geçiciyse fırsat, kalıcıysa tuzak."),
    ("buyume_potansiyeli", "Önümüzdeki yıllarda büyüme potansiyeli var mı?",
     "Kapasite, pazar, yeni ürün. Ve bu büyüme kârlı mı (ROIC > sermaye maliyeti)?"),
    ("en_buyuk_risk", "En büyük riski ne?",
     "Tek bir cümlede yazamıyorsan yeterince düşünmemişsindir."),
    ("karar", "Bu şirketi neden ALIRSIN veya neden ALMAZSIN?",
     "Önemli olan doğru hisseyi seçmen değil, doğru düşünce sürecini göstermen."),
]


# ═══════════════════════════════════════════ Alım öncesi 10 soru

ALIM_ONCESI = [
    ("ne", "Ne satın alıyorum? Şirketin iş modeli ne?"),
    ("neden", "Neden satın alıyorum? Yatırım tezim ne?"),
    ("nasil_kazanir", "Şirket nasıl para kazanıyor?"),
    ("finansal", "Finansalları nasıl?"),
    ("deger", "Şirketin değeri ne?"),
    ("fiyat_deger", "Piyasa fiyatı bu değere göre nasıl?"),
    ("buyume", "Büyüme beklentisi ne?"),
    ("risk", "En büyük risk ne?"),
    ("yanilma", "Hangi durumda yanıldığımı kabul ederim?"),
    ("kayip", "Bu yatırımda ne kadar kaybetmeyi göze alıyorum?"),
]

# Ustanın son dersi
ILKELER = [
    "Borsada amacın her zaman haklı çıkmak değil; yanlış olduğunda az kaybetmek, "
    "haklı olduğunda yeterince kazanabilmektir.",
    "Hisseyi değil, şirketi düşün.",
    "Fiyatı değil, değeri düşün.",
    "Tahmini değil, olasılıkları düşün.",
    "Kazancı değil, risk/getiri oranını düşün.",
    "Tek bir göstergeyi değil, bütün resmi düşün.",
]
