"""Yerleşik eğitim: terimler, mekanizmalar ve göstergelerin YANILDIĞI yerler.

Çoğu borsa kaynağı göstergenin ne olduğunu anlatır, ne zaman işe yaramadığını
anlatmaz. Asıl fark orada. Her konuda 'tuzak' bölümü var.
"""
from __future__ import annotations

KONULAR: dict[str, dict] = {

"borsa": {
 "baslik": "Borsa nasıl çalışır, fiyat nasıl oluşur",
 "ozet": """Hisse senedi bir şirketin küçük bir mülkiyet payıdır. 1 adet THYAO
almak, THYAO'nun 1,37 milyarda birine ortak olmak demektir.

Fiyatı kimse 'belirlemez' — alıcı ve satıcı emirleri eşleştiğinde oluşur.
Emir defterinde (derinlik) alıcılar aşağıda, satıcılar yukarıda sıralanır.
Bir alıcı satıcının fiyatını kabul ederse işlem gerçekleşir ve o an 'son fiyat'
olur. Fiyat yükseliyorsa alıcılar sabırsız, düşüyorsa satıcılar sabırsız demektir.

BIST 10:00-18:00 arası açık. Açılış ve kapanışta 'tek fiyat' seansı vardır:
emirler toplanır, en çok işlemi gerçekleştirecek tek fiyat hesaplanır.""",
 "bist_ozel": """• Günlük tavan/taban: ana pazarda ±%20 (bazı pazarlarda ±%10)
• Kapanış seansında sınır ±%3
• Fiyat adımı: 20 TL altı 0,01 · 20-50 TL 0,02 · 50-100 TL 0,05 · 100+ 0,10
• BIST'te kesirli hisse YOKTUR — en az 1 adet alınır""",
 "tuzak": """'Fiyat düştü, ucuzladı' yanılgısı. Fiyat bir şeyin ucuzluğunu
göstermez; şirketin değerine ORANI gösterir. 400 TL'lik hisse 40 TL'likten
pahalı değildir — kaç adet olduğuna ve şirketin kaç para kazandığına bağlıdır.""",
},

"emir": {
 "baslik": "Emir türleri ve hangisi ne zaman",
 "ozet": """PİYASA EMRİ: 'ne olursa olsun şimdi al'. Hızlıdır ama fiyatı sen
belirlemezsin. Likit olmayan hissede beklediğinden çok kötü fiyat alabilirsin.

LİMİT EMRİ: 'en fazla şu fiyattan al'. Fiyatı kontrol edersin ama emrin
gerçekleşmeyebilir. Küçük sermayede genelde doğru seçim budur.

STOP (ZARAR DURDUR): fiyat belirlenen seviyeye gelirse emir aktifleşir.
Zararı sınırlamak için kullanılır.

STOP-LİMİT: stop tetiklenince limit emri girer. Kötü fiyattan satılmayı
engeller ama hızlı düşüşte hiç satamama riski taşır.""",
 "bist_ozel": """Midas'ta 4 emir türü var; iz süren (trailing) stop yok.
Bu yüzden stop'u yukarı çekme işini elle yapman gerekir —
`analist.py portfoy` bunu her gün hatırlatır.""",
 "tuzak": """STOP GARANTİ DEĞİLDİR. Hisse stop seviyenin ALTINDA açılırsa
(gap), emrin o düşük fiyattan gerçekleşir. Backtestimizde en kötü işlemler
tam olarak bunlar: %12-20 kayıp. Stop koydun diye 'riskim %2' deme.""",
},

"spread": {
 "baslik": "Spread, hacim, likidite — görünmeyen maliyet",
 "ozet": """SPREAD: en iyi alış ile en iyi satış arasındaki fark. 100,00 alış /
100,10 satış varsa spread 0,10 TL (%0,1). Alıp hemen satsan bu kadar kaybedersin.

LİKİDİTE: istediğin miktarı fiyatı bozmadan alıp satabilme. Günlük 20 milyon TL
işlem gören hissede 1000 TL'lik emrin hiçbir etki yaratmaz; 500 bin TL işlem
gören hissede aynı emir fiyatı oynatabilir.

Midas BIST komisyonu SIFIR — ama spread ve kayma sıfır değil. Gerçek maliyetin
budur ve işlem sıklığıyla doğru orantılı artar.""",
 "bist_ozel": """Sistem `asgari_tl_hacim: 20000000` filtresiyle günlük 20 milyon
TL altındaki hisseleri eler. Sebep: likidite tuzağı. Alması kolay, satması zor
hisselere düşmek küçük sermayenin en sinsi riskidir.""",
 "tuzak": """Sıfır komisyon 'bedava işlem' demek değildir. Günde 5 işlem yapan
biri %0,15 kayma ile ayda ~%15 kaybeder. Backtestte kayma 0'dan 50bp'ye
çıkınca trend stratejisinin getirisi %119'dan %28'e düştü.""",
},

"aciga_satis": {
 "baslik": "Açığa satış",
 "ozet": """Sahip olmadığın hisseyi ödünç alıp satmak, sonra (umarak) daha ucuza
geri alıp iade etmektir. Düşüşten kazanmanın yoludur.

Risk asimetriktir: alımda en fazla yatırdığını kaybedersin (%100). Açığa satışta
hisse yükselirse kaybın SINIRSIZDIR — %300 yükselirse %300 kaybedersin.""",
 "bist_ozel": """BIST'te açığa satış izne ve teminata tabidir; VBTS tedbiri olan
hisselerde tamamen yasaklanabilir. Midas'ta bireysel açığa satış pratikte yok.
Bu sistem SADECE uzun taraf çalışır — düşüşte kazanmaz, nakde geçer.""",
 "tuzak": """'Bu hisse çok şişti, kesin düşer' düşüncesi. Piyasa senin
ödeme gücünün tükendiğinden daha uzun süre mantıksız kalabilir.""",
},

"temettu": {
 "baslik": "Temettü, bedelli ve bedelsiz sermaye artırımı",
 "ozet": """TEMETTÜ: şirketin kârından ortaklara dağıttığı nakit. Dağıtım günü
hisse fiyatı temettü kadar DÜŞER — bedava para değil, cebinden cebine aktarım.
Değeri, şirketin o nakdi senden daha kötü değerlendirecek olmasındadır.

BEDELSİZ: şirket iç kaynaklarını sermayeye ekler, elindeki adet artar ama
toplam değerin DEĞİŞMEZ. 100 TL'lik 1 hisse, %100 bedelsizde 50 TL'lik 2 hisse
olur. Zenginleşmedin.

BEDELLİ: şirket yeni hisse satarak para toplar. Katılmazsan payın SULANIR.
Şirketin neden paraya ihtiyacı olduğu kritik sorudur — yatırım için mi,
borç kapatmak için mi?""",
 "bist_ozel": """Bireysel yatırımcı için BIST hisse alım-satım kazancında
stopaj %0'dır. Temettüde stopaj vardır. Sistem `auto_adjust=True` kullanır:
geçmiş fiyatlar temettü ve bedelsize göre düzeltilmiştir, yoksa backtest
sahte düşüşler görürdü.""",
 "tuzak": """Yüksek temettü verimi cazip görünür ama çoğu zaman fiyat düştüğü
için yüksektir (verim = temettü/fiyat). Ayrıca %40 mevduat faizi varken
%3 temettü verimi bir çekicilik değildir.""",
},

"gostergeler": {
 "baslik": "Teknik göstergeler NE ZAMAN YANILIR",
 "ozet": """Göstergeler fiyatın matematiksel dönüşümüdür — yeni bilgi üretmezler,
mevcut bilgiyi düzenlerler. Hepsi GECİKMELİDİR, çünkü geçmiş fiyattan hesaplanır.""",
 "bist_ozel": """Bu sistem 3,28 yıllık BIST verisinde ölçtü:
• RSI(2) aşırı satım tepki stratejisi: %53 kazanma oranıyla bile ZARARDA (-%21,7)
• Kırılım stratejisi: %48 kazanma oranıyla KÂRDA (+%118,6)
Kazanma oranı iyi strateji göstergesi değildir — kazanç/kayıp büyüklüğü belirler.""",
 "tuzak": """HER GÖSTERGENİN KIRILDIĞI YER:

• RSI — güçlü trendde haftalarca 70 üstünde kalır. 'Aşırı alım, düşer' diye
  satılan hisse iki katına çıkabilir. RSI yatay piyasada işe yarar, trendde yanıltır.

• Hareketli ortalama kesişimi — yatay piyasada sürekli yanlış sinyal üretir
  (whipsaw). Bu yüzden ADX gibi bir trend filtresi şart.

• MACD — geç kalır. Sinyal geldiğinde hareketin önemli kısmı bitmiştir.

• Bollinger — 'banda değdi, döner' yanlıştır. Güçlü trendde fiyat bant boyunca
  yürür (band walking).

• Destek/direnç — çok bakılan seviye, tam da bu yüzden kırılır. Herkesin stop'u
  aynı yerdeyse orası bir mıknatıstır.

• Kırılım — %50'den fazlası SAHTE kırılımdır. Hacim teyidi olmadan alma;
  sistemimiz `Hacim_orani > 1.4` şartı koyar.

• Formasyonlar — geçmiş grafikte herkes görür. Gerçek zamanda formasyonun
  tamamlanıp tamamlanmayacağı belli değildir. Seçici hafıza en büyük tuzaktır.

• Hepsi birden — 5 gösterge aynı şeyi söylüyorsa, bu 5 ayrı teyit değildir.
  Hepsi aynı fiyat serisinden türer; tek bir bilgiyi 5 kez duyarsın.""",
},

"temel_analiz": {
 "baslik": "Finansal tabloları okumak",
 "ozet": """GELİR TABLOSU — bir dönemde ne kadar kazandı:
  Hasılat → Brüt kâr → Faaliyet kârı → FAVÖK → Net kâr
  Aşağı indikçe daha çok kalem düşülür. Faaliyet kârı ana işin performansıdır;
  net kâr kur farkı ve tek seferlik kalemlerle şişip sönebilir.

BİLANÇO — belirli bir ANDA neye sahip, ne borçlu:
  Varlıklar = Borçlar + Özsermaye (her zaman eşittir)

NAKİT AKIŞ — en zor manipüle edilen tablo. Kâr muhasebe kararıdır, nakit
gerçektir. `Nakit/Net kâr` oranı sürekli 1'in altındaysa kâr şüphelidir.""",
 "bist_ozel": """KUR TUZAĞI: bazı BIST şirketleri (THYAO gibi) finansallarını
USD açıklar ama hisse TL işlem görür. yfinance bunları karıştırır ve THYAO'nun
F/S oranını 15,66 gösterir — gerçeği 0,34. Sistem `financialCurrency` alanını
kontrol edip düzeltir.

ENFLASYON TUZAĞI: %31,8 enflasyonda hasılatı %20 artan şirket BÜYÜMÜYOR,
küçülüyor. Sistem büyümeyi enflasyona göre değerlendirir — ve USD raporlayan
şirketi USD enflasyonuyla kıyaslar.""",
 "tuzak": """Bankada cari oran, borç/özsermaye ve FD/FAVÖK ANLAMSIZDIR —
bankada borç hammaddedir. Bankada faaliyet nakit akışı da kâr kalitesi ölçmez;
mevduat/kredi hareketinden oluşur. Sistem banka için bu oranları kapatır.""",
},

"degerleme": {
 "baslik": "Ucuz mu pahalı mı",
 "ozet": """F/K = Piyasa değeri / Net kâr. Kaç yılda kendini amorti eder.
FD/FAVÖK = (Piyasa değeri + net borç) / FAVÖK. Borç yapısı farklı şirketleri
  kıyaslamayı sağlar; F/K'nın yapamadığı budur.
PD/DD = Piyasa değeri / Özsermaye. Bankalarda ve GYO'da esastır.
PEG = F/K / büyüme. Hızlı büyüyen yüksek F/K hak eder.
Serbest nakit verimi = FCF / Piyasa değeri. Mevduat faiziyle DOĞRUDAN kıyaslanır.""",
 "bist_ozel": """Türkiye'de %40 faiz varken F/K 10 olan bir hisse, %10 getiri
demektir — mevduatın çok altında. Bu yüzden BIST çarpanları gelişmiş ülkelere
göre yapısal olarak düşüktür. 'BIST ucuz' demek genelde bu gerçeği atlar.

TERS DCF daha dürüsttür: 'bu fiyat hangi büyümeyi ima ediyor?' diye sorar,
tahmin üretmez. Sen sadece 'bu büyüme makul mü' dersin.""",
 "tuzak": """DEĞER TUZAĞI: ucuz şirket genellikle bir SEBEPTEN ucuzdur.
Örnek — EREGL PD/DD 0,90 ile 'defterin altında' görünür, ama kalite skoru
31,8 ve faiz karşılama oranı 0,8x (faizini ödeyemiyor). Ucuzluk tek başına
alım gerekçesi değildir; kaliteyle birlikte okunur.

DÖNGÜSEL TUZAK: çelik, kimya gibi döngüsel sektörlerde kâr TEPEDEYKEN F/K
en DÜŞÜK görünür — ve tam o an satılacak zamandır.""",
},

"risk": {
 "baslik": "Risk yönetimi — asıl fark burada",
 "ozet": """POZİSYON BÜYÜKLÜĞÜ: 'kaç lot alayım' değil, 'stop'a düşerse kaç TL
kaybederim' sorusuyla belirlenir.
  Adet = (Sermaye × Risk%) / (Giriş − Stop)

Sistem varsayılanı işlem başına %1,5. 1000 TL'de 15 TL. Üst üste 10 kayıp
%14 eder — sistemi terk etmeden dayanılabilir bir seviye.

ÇEŞİTLENDİRME: 5 farklı BANKA hissesi almak çeşitlendirme DEĞİLDİR; tek bahsi
beş parçaya bölmektir. Korelasyon 0,7 üstündeyse portföy tek hisse gibi hareket eder.""",
 "bist_ozel": """1000 TL'de asıl kısıt strateji değil sermayedir. BIST'te
kesirli hisse yok: 400 TL'lik hisseden 1 adet zaten sermayenin %40'ı.
2-3 pozisyona sıkışırsın ve sonucu şans belirler.""",
 "tuzak": """'Üst üste 10 kayıp gelmez' yanılgısı. Monte Carlo simülasyonu:
%46 kazanma oranıyla 200 işlemde en uzun kayıp serisi 19 İŞLEM. Gelir.
Sistemini o seriye dayanacak şekilde kur, ortalamaya göre değil.""",
},

"psikoloji": {
 "baslik": "Kendi kendine sabotaj",
 "ozet": """En pahalı hatalar bilgi eksikliğinden değil, duygudan doğar:

• FOMO — yükselen hisseyi kaçırma korkusuyla tepeden almak
• İNTİKAM — kaybı hemen geri alma dürtüsüyle riski büyütmek
• ZARARINA ORTALAMA — yanılmış olma ihtimaline karşı bahsi büyütmek
• KAYIPTAN KAÇINMA — kazananı erken satıp kaybedeni yıllarca tutmak
• TEYİT ÖNYARGISI — sadece tezini destekleyen haberi okumak
• SONUÇ YANILGISI — kâr eden her işlemi 'doğru karar' sanmak""",
 "bist_ozel": """Sistem `analist.py al` komutunda bu tuzakları otomatik tarar:
RSI 75 üstü alım, son 5 günde 2+ zarar, sermayenin %40'ından fazlası tek
hissede, zararına ortalama, tez yokluğu — hepsi uyarı üretir.""",
 "tuzak": """En tehlikelisi SONUÇ YANILGISI: kötü bir kararla para kazanmak,
o kararı doğru sanmana yol açar ve bir dahakine daha büyük yaparsın.
Kararı sonucuna göre değil, VERİLDİĞİ ANDAKİ bilgiye göre değerlendir.
Bu yüzden tez yazılır ve saklanır.""",
},
}

SIRA = ["borsa", "emir", "spread", "aciga_satis", "temettu",
        "gostergeler", "temel_analiz", "degerleme", "risk", "psikoloji"]


def konu_listesi() -> list[tuple[str, str]]:
    return [(k, KONULAR[k]["baslik"]) for k in SIRA if k in KONULAR]


def konu_getir(ad: str) -> dict | None:
    ad = ad.lower().strip()
    if ad in KONULAR:
        return {"anahtar": ad, **KONULAR[ad]}
    for k, v in KONULAR.items():
        if ad in k or ad in v["baslik"].lower():
            return {"anahtar": k, **v}
    return None
