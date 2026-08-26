# Midas Analist

BIST için karar destek sistemi. **Otomatik alım-satım botu değildir** — Midas'ın
geliştirici API'si yoktur, hiçbir yazılım senin adına emir veremez. Emri sen
girersin; sistem neyi, neden, ne kadar alacağını söyler ve seni kendi kurallarına
bağlar.

## İki arayüz

| | |
|---|---|
| **Terminal** | `analist.py` — 29 komut, tam güç |
| **Mobil** | Flutter uygulaması + FastAPI sunucusu ([mobil/README.md](mobil/README.md)) — tek koyu tema, piksel görünüm |

Mobil için sunucuyu başlat: `./sunucu.sh` — telefonun kullanacağı adresi yazar.
Buluta taşımak için: `./dagit.sh --ilk` — bkz. [Buluta taşıma](#buluta-taşıma).

## Kurulum

```bash
cd ~/midas_borsa_botu
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

İsteğe bağlı AI katmanı için:

```bash
.venv/bin/pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
export MIDAS_AI_TAVAN_TL=100      # aylık tavan; 0 = sınırsız
```

Anahtar yoksa sistem tam çalışır, sadece AI yorumları devre dışı kalır.
Tavan dolduğunda da aynı şey olur — çağrılar durur, sistem çalışmaya devam eder.

## 29 komut

**Günlük döngü**

| komut | ne yapar |
|---|---|
| `tara` | Tüm BIST'i tarar, skorlar, sinyal verenleri sıralar |
| `portfoy` | Açık pozisyonlarda sat/tut kararı, iz süren stop önerisi |
| `al HISSE ADET FIYAT` | Alımı kaydeder — **önce davranışsal tarama yapar** |
| `sat HISSE` | Pozisyon kaydını kapatır |

**Analiz**

| komut | ne yapar |
|---|---|
| `analiz HISSE` | Teknik: skor, seviyeler, pozisyon planı |
| `yapi HISSE` | Tepe/dip yapısı, Fibonacci, çoklu zaman dilimi, kırılım güvenilirliği |
| `sirket HISSE` | Temel analiz + değerleme + ters DCF + sektör rehberi |
| `makro` | 12 makro gösterge, enflasyon, piyasa rejimi |
| `sektor` | 10 sektörün göreli gücü, lider/geciken |
| `backtest` | Stratejileri geçmiş veride dürüstçe test eder |

**Günlük iş (kendi kendine öğrenme)**

| komut | ne yapar |
|---|---|
| `gunluk` | Günün işini elle çalıştırır (18:10'da otomatik) |
| `ozet [--gun N]` | Gün özeti: piyasa, en çok hareket edenler, sinyaller, haberler |
| `gecmis HISSE` | Bir hissenin günlük seyri + o günlere denk gelen haberler |
| `karne` | **Sistemin kendi sinyallerinin gerçek sicili** — backtest değil |
| `ambar` | Veri ambarı durumu, son çalışmalar |
| `doldur --gun N` | Geçmişi yeniden üretip sicili doldurur (ileri bakışsız) |
| `ai-butce` | AI harcaması, aylık tavan, iş bazında döküm |

**Eğitmen**

| komut | ne yapar |
|---|---|
| `mufredat [modul]` | 12 modül, 65 ders haritası (~8,5 saat okuma) |
| `ogret` | Günlük oturum: bugünün dersi + pekiştirme soruları |
| `ders KOD` | Belirli bir dersi oku (örn. `ders d402`) |
| `ilerleme` | Seviyen, modül ilerlemen, en çok zorlandıkların |
| `sirket-oku HISSE` | "Bu şirketi 10 dakikada anlat" — 16 adımlı egzersiz |

**Disiplin**

| komut | ne yapar |
|---|---|
| `tez HISSE` | 8 soruluk yatırım tezi yazdırır, alım anını dondurur |
| `tezler` | Açık tezler + kapanmışların karnesi |
| `kontrol HISSE ADET FIYAT` | Alım öncesi davranışsal tuzak taraması |
| `risk` | Beklenen değer, Monte Carlo, çeşitlendirme matematiği |
| `dagitim` | Portföy dağıtımı, nakit oranı, yeniden dengeleme kontrolü |
| `gerceklik` | Getiri hedefinin matematiği |
| `ogren [konu]` | 10 konuda eğitim — özellikle göstergelerin yanıldığı yerler |

Ortak bayraklar: `--duz` (renksiz), `--sermaye 5000`, `--ai` (sirket/tez'de).

## Günlük ritim

BIST 10:00–18:00. Veri ~15 dk gecikmeli — gün sonu kararı için, scalping için değil.

| saat | ne |
|---|---|
| 09:30 | `portfoy` — çıkış var mı? |
| 09:45 | Varsa satış emrini Midas'ta gir |
| 18:10 | **Otomatik** — günlük iş çalışır (aşağıya bak) |
| 18:15 | `ozet` — bugün ne oldu, ne değişti |
| — | Aday varsa `sirket` + `tez` yaz |
| Ertesi 10:00 | Açılışta al (backtest bu varsayımla ölçer) |

Haftalık: `makro`, `sektor`. Aylık: `tezler` (karnen), `karne`, `backtest`.

## Günlük iş — sistemin kendini geliştirdiği yer

Her iş günü **18:10'da** (kapanıştan 10 dk sonra) otomatik çalışır. Kurulum:

```bash
./kur_zamanlayici.sh     # systemd user timer kurar, cron'a düşer
systemctl --user list-timers midas-gunluk   # doğrula
./gunluk.sh              # elle çalıştır
```

Altı adım, sırayla:

| # | adım | ne yapar |
|---|---|---|
| 1 | **Fiyat** | 100 hissenin kapanışını ambara yazar — dün 100 TL, bugün 103 TL bilgisi buradan gelir |
| 2 | **Haber** | 6 RSS kaynağını tarar, haberleri hisselerle eşler (+ AI katmanı) |
| 3 | **Tarama** | Günün sinyallerini üretir ve **kaydeder** (o günkü fiyat, stop, hedefle birlikte) |
| 4 | **Ölçüm** | Vadesi dolmuş eski sinyallerin gerçekte ne yaptığını hesaplar |
| 5 | **Özet** | Piyasa geneli, en çok hareket edenler, sinyaller, haberler |
| 6 | **Sicil** | Karneyi günceller |

**Öğrenme burada:** sistem internetten okuyup "daha iyi analist" olmuyor — bu
mümkün değil. Yaptığı şey ölçülebilir: *kendi verdiği sinyalin sonucunu takip
ediyor.* Sinyali kaydediyor, vadesi dolunca gerçek fiyat serisinde ne olduğunu
hesaplıyor, karneye yazıyor. Kenar aşınıyorsa sana söylüyor.

**Ambar:** `veri/ambar.db` (SQLite, WAL). 7 tablo — fiyat, haber, haber
eşleşmesi, sinyal, sinyal sonucu, gün özeti, çalışma günlüğü.

**Geçmişi doldurmak:** `doldur --gun 90` geçmiş 90 günü yeniden üretir. Her gün
için **yalnızca o güne kadarki veriyi** kullanır (`dilim = g.iloc[:konum+1]`) —
ileri bakış yok, yoksa sicil anlamsız olurdu.

**Haber eşlemesinin sınırı dürüstçe:** kelime eşlemesi 95 haberde yalnızca 3-4
eşleşme buluyor. Bu bir hata değil, kasıtlı katılık — "TÜRK" kelimesi THYAO'ya,
"HACI" SAHOL'a eşleşmesin diye ~70 hisse için elle yazılmış takma ad listesi ve
jenerik kelime kara listesi var. Yanlış eşleşme, eşleşmemekten daha zararlıdır.

Gerçek boşluk şurada: *"gıda devinde yönetim değişikliği"* başlığı ULKER'i
ilgilendirir ve hiçbir takma ad listesi bunu yakalayamaz. Sınıflandırma dil
işidir. Anahtar tanımlıysa Claude bu adımı da yapar (aşağıya bak).

## Eğitmen

**12 modül, 65 ders, ~8,5 saat okuma, ~17.500 kelime.** Sınav değil, müfredat:
önce okursun, sonra pekiştirirsin.

| # | Modül | Ders |
|---|---|---|
| m1 | Piyasanın mekaniği | 9 |
| m2 | Finansal tabloları okumak | 6 |
| m3 | Oran analizi | 5 |
| m4 | Değerleme | 5 |
| m5 | Sektör analizi (banka, holding, sanayi, perakende, enerji, havacılık, GYO, teknoloji) | 8 |
| m6 | Makroekonomi | 5 |
| m7 | Teknik analiz | 8 |
| m8 | Risk yönetimi | 5 |
| m9 | Portföy yönetimi | 3 |
| m10 | Yatırım psikolojisi | 4 |
| m11 | Bilgi kaynakları ve KAP | 3 |
| m12 | Kendi sistemin | 4 |

Her ders beş bölümden oluşur: **anlatım** (mekanizma, tanım değil) · **örnek**
(gerçek BIST rakamlarıyla) · **BIST/Midas özeli** (genel finans kitaplarında
olmayan kısım) · **tuzak** (bu konuda en sık yapılan hata ve nedeni) ·
**pekiştirme soruları**.

**50 pekiştirme sorusu**, üç seviye. Sorular sadece **okuduğun derslerden**
gelir — ders okumadan o dersin sorusu sorulmaz.

**Aralıklı tekrar (SM-2):** bildiğin soru seyrekleşir (1 → 6 → 16 → 45 gün),
bilmediğin sıfırdan başlar. Seviye ders okumaya dayanır (2/3 ağırlık), sorular
ikincildir (1/3).

**Canlı sorular** — statik bir sınavı gerçek yatırımdan ayıran şey. Bugünkü
verinden üretilir:

> *"EREGL'in F/K oranı 1.055 çıkıyor, PD/DD ise 0,90. Bu şirket pahalı mı?"*
> *"TRALT bugün 73 skorla üst sıralarda ama zamanlama puanı 25 üzerinden 7. Alır mısın?"*
> *"Portföyündeki TRENJ %11 zararda. Ne yaparsın, kararı neye dayandırırsın?"*

**Şirket okuma egzersizi** (`sirket-oku`): 16 adım. Her adımda önce kendi
cevabını kurarsın, sonra sistemin ölçtüğü rakama bakarsın. Sonunda tek soru:
bu şirketi neden alırsın, neden almazsın?

## Ölçülmüş sonuçlar

BIST 100, 2023-05-15 → 2026-08-24 (3,28 yıl, 819 bar), 1.000 TL, 15bp kayma,
sıfır komisyon. Fiyat onarımı açıkken (aşağıda 8. tuzak) yeniden ölçüldü:

| | getiri | yıllık | Sharpe | azami düşüş | işlem | kazanma |
|---|---|---|---|---|---|---|
| **kirilim** | +118,6% | +26,9% | 1.93 | −11,3% | 189 | %48 |
| **trend** | +84,5% | +20,5% | 1.27 | −16,1% | 236 | %48 |
| **tepki** | −21,7% | −7,2% | −0.74 | −28,2% | 328 | %53 |
| XU100 al-tut | +222,3% | — | — | — | — | — |

**Üçü de endeksin altında.** Al-tut BIST 100'ü aynı dönemde +%222 getirmiş;
en iyi strateji +%119. Bu stratejilerin gerekçesi endeksi yenmek değil, daha
düşük düşüşle (−%11 vs −%23) ve 1.000 TL'nin alabileceği hisselerle çalışmak.
Endeksin kendisini alamıyorsun — BIST 100'ü kopyalamak 100 hisse demek.

**Sağlamlık:** kirilim 24 parametre kombinasyonunun 24'ünde kârlı (medyan +%97);
kayma 0→50bp'de +%142→+%115. (Bu iki ölçüm onarım öncesi veriyle yapıldı;
büyüklükler birkaç puan kayabilir, yön değişmez.)

**Ama:** ADX eşiği tam 20'de sıçrıyor:

| eşik | getiri | işlem |
|---|---|---|
| ADX>15 | +%61,0 | 190 |
| **ADX>20** | **+%118,6** | **189** |
| ADX>25 | +%68,3 | 163 |
| ADX>30 | +%58,4 | 138 |

Keskin tepe aşırı uydurma işaretidir. Ama asıl öğretici olan şu: **ADX>15 ile
ADX>20 neredeyse aynı sayıda işlem açıyor (190'a karşı 189), getiri ise iki
katı.** Fark kuralın kalitesinden gelmiyor — 1.000 TL sermaye ve 4 pozisyon
sınırı altında sinyaller sıraya giriyor, bir sinyalin birkaç gün erken gelmesi
sonraki ayların tamamen farklı hisselerle dolmasına yol açıyor. Yol
bağımlılığı: küçük sermayede backtest sonucu, kuraldan çok şansa bağlı.
Ölçülen +%118,6 gerçekte olacağından iyimser.

**Ve TL yanıltıcı:** aynı dönem USD bazında XU100 +%31,6, kirilim **−%10,8**,
trend −%24,7, tepki −%68,0. (USD/TRY 19,63 → 48,07.) BIST 100'ün son 1 yıl
reel getirisi **−%3,7** (nominal +%28,1, enflasyon %31,8).

## Canlı sicil — backtest'in söylemediği

Backtest geçmişe uydurulabilir. Canlı sicil uydurulamaz. `karne` komutu bunu
gösterir. 2026-04-21 → 2026-08-24 (4,1 ay, 767 sinyal), stop ve hedef uygulanmış:

| vade | sinyal | kazanma | ort. getiri |
|---|---|---|---|
| 1 gün | 752 | %47,3 | +0,02% |
| 5 gün | 730 | %45,3 | −0,07% |
| **20 gün** | **626** | **%35,5** | **−0,98%** |

Stratejiye göre (20 gün): tepki %47,5 (+0,45%) · trend %30,9 (−1,27%) ·
kirilim %25,0 (−3,29%).

**Canlı, backtest'in altında:** kirilim −23,0 puan, trend −17,1 puan, tepki
−5,5 puan. Bu tek başına "strateji bozuldu" demek değil — kıyas yapısal olarak
canlının aleyhine:

- Backtest aynı anda **en fazla 4 pozisyon** taşır ve en güçlü momentumu seçer.
  Canlı sicil **tüm** sinyalleri sayar, zayıflar dahil.
- Backtest 3,28 yıl / çok rejim; canlı sicil 4,1 ay / muhtemelen tek rejim.
- Backtest nakit kısıtı uygular, sermaye bitince sinyal kaçırır; canlı sicilde
  böyle bir kısıt yok.
- 100 sinyalin altındaki hiçbir alt kırılım (kirilim: 80) güvenilir değildir.

Karne bu dört uyarıyı her çalıştırmada ekrana basar — rakamı çıplak bırakmaz.

**Rahatsız edici bulgu:** 1.000 TL ile **alınamayacak kadar pahalı** hisseler
(139 sinyal) ortalama **+1,26%**, alınabilenler (487 sinyal) **−1,62%** getirdi.
Sermayenin küçüklüğü sadece "az kazanmak" değil, **daha kötü hisse havuzu**
anlamına geliyor olabilir.

## Veri katmanında çözülen tuzaklar

Bunlar kozmetik değil; her biri sessizce yanlış sonuç üretiyordu:

1. **Kur uyuşmazlığı.** THYAO finansallarını USD açıklar, hissesi TL işlem görür.
   yfinance F/S'sini 15,66 gösteriyor — gerçeği **0,34**. Sistem `financialCurrency`
   kontrol eder; oranlar tablodan tabloya (para birimi nötr), fiyat karışan
   çarpanlar zorunlu dönüşümden geçer.
2. **Yanlış enflasyon referansı.** USD raporlayan şirketin büyümesini TL
   enflasyonuyla kıyaslamak sağlıklı şirketi "reel küçülüyor" diye damgalar.
   Her şirket kendi para biriminin enflasyonuyla ölçülür.
3. **Bankada anlamsız oranlar.** Cari oran, borç/özsermaye, FD/FAVÖK ve kâr
   kalitesi bankada geçersiz — banka için borç hammaddedir. Sistem bunları kapatır.
4. **Sıfıra bölme artefaktı.** EREGL net marjı %0,24 iken nakit/net kâr 127x
   çıkıp "mükemmel" görünüyordu. Net kâr anlamlı değilse oran geçersiz sayılır.
5. **Sektör endeksi geçmişi yok.** yfinance XUTEK, XGIDA gibi 14 sektör endeksinin
   sadece 1 günlük geçmişini taşıyor. Sektör serileri bileşenlerden piyasa değeri
   ağırlıklı kuruluyor.
6. **Önbellek kapsama hatası.** 400 günlük istekle dolan dosya 1200 günlük istekte
   sessizce kullanılıyor, backtest kısa geçmişle çalışıyordu.
7. **Veri boşluğunda hayalet çöküş.** O gün işlem görmeyen hisse değerlemeden
   düşüyor, özkaynak eğrisinde olmayan −%76 düşüş görünüyordu.
8. **Kaçırılmış bedelsiz/bölünme.** Yahoo bazı BIST hisselerinde bölünmeyi
   ileriye uygulayıp geçmişi düzeltmiyor. EUREN'de ham veri 2024-12-02'de
   **−%63,6'lık tek günlük çöküş** gösteriyordu — böyle bir gün yaşanmadı.
   Sahte çöküş ATR'yi şişirir ve tepki stratejisine olmayan bir alım sinyali
   ürettirir. `yf.download(repair=True)` bunu onarır ama **scikit-learn ister**;
   kurulu değilse yfinance hatayı yutar ve boş çerçeve döndürür. 60 hissenin
   4'ünde onarım fark yaratıyor. `requirements.txt`'e eklendi; eksikse sistem
   bir kez uyarır ve onarımsız devam eder.

## Risk kuralları

`ayarlar.yaml` içinde: işlem başına risk %1,5 · tek hissede en fazla %35 ·
aynı anda 4 pozisyon · stop = giriş − 2,5×ATR · hedef = giriş + 5×ATR.

**Sermaye sabit değil.** Mobil uygulamada bir defter var: hesabına eklediğin
parayı kazandığın paradan ayrı tutar. "Portföyüm 1.400 TL" tek başına
performans değildir — 1.000 yatırıp 400 kazanmış da olabilirsin, 1.400 yatırıp
sıfır kâr etmiş de. Ayrıntı: [mobil/README.md](mobil/README.md#sermaye-defteri).
Terminal tarafında `--sermaye` bayrağıyla verilir.

Sinyal veren stratejinin kendi ATR çarpanları kullanılır — ekranda gördüğün stop,
backtestte ölçülen stopla aynıdır.

**Stop garantili değildir.** En kötü backtest işlemleri "boşluklu stop": hisse
stop seviyesinin altında açılır, %12–20 kaybettirir. BIST'te günlük tavan/taban ±%20.

## Buluta taşıma

PC'nin sürekli açık kalmasına gerek yok: API ve 18:10 günlük işi bulutta
çalışır. Hedef, kalıcı diski olan tek bir açık makine — Oracle Cloud'un
Always Free ARM sunucusu ücretsiz katmanda yeterli.

**Neden Cloud Run değil.** `veri/ambar.db` her gün büyür: fiyat geçmişi,
üretilen sinyaller ve bu sinyallerin sonuçları orada birikir. Öğrenme
katmanının canlı sicili bu birikimden çıkar. Cloud Run'da kalıcı disk yok
ve örnek uykuya daldığında dosya sistemi sıfırlanır — API ayakta kalır ama
sistem kendi geçmişini her seferinde unutur. Eski betik `bulut/` altında
duruyor; kullanma.

### 1. Sunucuyu aç (bir kereliğine, tarayıcıdan)

Oracle Cloud'da ücretsiz hesap aç, sonra bir örnek oluştur:

| Alan | Değer |
|---|---|
| Image | Ubuntu 24.04 |
| Shape | VM.Standard.A1.Flex — 2 OCPU, 12 GB |
| SSH key | kendi açık anahtarın (`~/.ssh/id_*.pub`) |
| Public IP | **Reserved** — Ephemeral de örnek yaşadığı sürece sabit kalır ama örneği silip yeniden kurarsan kaybolur; adres değişince HTTPS adı ve telefondaki ayar da değişir |

Sonra ağı aç: VCN > Security List > Ingress Rules'a `0.0.0.0/0` için
**80** ve **443** portlarını ekle. Bu adım atlanırsa sunucu kurulur,
çalışır ve dışarıdan hiç yanıt vermez — en sık takılınan yer burası.

### 2. Dağıt (PC'den)

```bash
echo "MIDAS_SUNUCU=ubuntu@SUNUCU_IP" >> .env
./dagit.sh --ilk
```

Betik `.env`'i ve `veri/` geçmişini gönderir, sunucuda Python ortamını
kurar, systemd servislerini yazar, Caddy ile HTTPS sertifikası alır ve
API anahtarını basar. Sonraki dağıtımlar sadece `./dagit.sh`.

Adres alan adı gerektirmez: `sslip.io` genel IP'yi ada çevirir
(`140-238-12-34.sslip.io`), Let's Encrypt de o ada gerçek sertifika verir.

### 3. Telefonu bağla

Ayarlar > Sunucu'ya `https://...sslip.io`, API anahtarı alanına dağıtımın
bastığı anahtarı gir.

### Bilinmesi gerekenler

- **Saat dilimi.** Kurulum sunucuyu `Europe/Istanbul` yapar. Kod her yerde
  çıplak `date.today()` kullanır; sunucu UTC kalsaydı 18:10 işi 21:10'da
  çalışır ve gün kaydı yanlış tarihe düşerdi.
- **API anahtarı zorunlu.** Anahtarsız dağıtımı betik reddeder — açık bir
  API'nin bütün uçları herkese açıktır.
- **8000 portu dışarı kapalı.** uvicorn yalnızca `127.0.0.1`'e bağlanır,
  dışarıya Caddy TLS ile çıkar.
- **Oracle boşta kalan ücretsiz örnekleri geri alabilir.** Uzun süre çok
  düşük CPU/ağ kullanımı olan Always Free makineleri geri alma hakkını
  saklı tutuyor; uyarı e-postası gelir. `veri/`'yi ara sıra yedekle:
  `rsync -az ubuntu@IP:midas/veri/ ./veri_yedek/`
- **PC'de zamanlayıcı kurduysan kapat**, yoksa aynı iş iki yerde çalışır:
  `systemctl --user disable --now midas-gunluk.timer`. Kurulu değilse
  `kur_zamanlayici.sh`'ı artık PC'de çalıştırma — zamanlama bulutta.


## Dosya düzeni

```
analist.py              CLI, 29 komut
ilerleme.json           eğitim ilerlemen (ogret komutu yazar)
sunucu.sh               API'yi yerel ağda başlatır
gunluk.sh               günlük işi çalıştırır (zamanlayıcı bunu çağırır)
kur_zamanlayici.sh      systemd user timer / cron kurar (Pzt-Cum 18:10)
dagit.sh                buluttaki sunucuya dağıtır (--ilk ile kurulum)
bulut/sunucu_kur.sh     sunucuda çalışır: systemd, HTTPS, saat dilimi
bulut/cloudrun_dagit.sh eski Cloud Run betiği (kalıcı disk yok, kullanılmıyor)
Dockerfile              konteyner tanımı
veri/ambar.db           SQLite ambar: fiyat, haber, sinyal, sonuç, gün özeti
veri/kap_sirketler.json KAP unvan -> hisse kodu eşlemesi (30 günde bir tazelenir)
api/
  main.py               FastAPI, 31 uç nokta (durumsuz)
  donusum.py            JSON güvenli dönüşüm (NaN -> null)
  onbellek.py           açılışta ısıtma + periyodik tazeleme
mobil/                  Flutter uygulaması
ayarlar.yaml            risk ve filtre ayarları
portfoy.json            açık pozisyonlar
tezler.json             yatırım tezleri (al/sat/tez komutları yazar)
cekirdek/
  evren.py              BIST 100 / BIST 30 listeleri
  veri.py               fiyat verisi + disk önbelleği
  temel_veri.py         finansal tablolar, kur-güvenli
  gostergeler.py        RSI, MACD, ATR, ADX, Bollinger, Donchian...
  strateji.py           3 strateji + 0-100 skorlama + filtreler
  temel.py              oran analizi, kalite skoru, kırmızı bayraklar
  degerleme.py          çarpanlar, ters DCF, sektör medyanı
  makro.py              12 makro gösterge, TÜFE, piyasa rejimi
  sektor.py             sentetik sektör endeksleri, sektör rehberi
  istatistik.py         beklenen değer, Kelly, Monte Carlo, korelasyon
  risk.py               pozisyon boyutu, BIST fiyat adımları
  backtest.py           gerçekçi backtest motoru
  tarayici.py           günlük tarama
  portfoy.py            pozisyon takibi
  tez.py                yatırım tezi, alım anı dondurma, karne
  psikoloji.py          davranışsal tuzak taraması, kaynak değerlendirme
  formasyon.py          trend yapısı, Fibonacci, çoklu zaman, sahte kırılım oranı
  portfoy_yonetimi.py   varlık dağılımı, ağırlıklandırma, yeniden dengeleme
  ogren.py              10 konuluk eğitim (referans)
  egitmen_sorular.py    50 soruluk müfredat: cevap + yaygın hata + anahtar kavram
  egitmen.py            aralıklı tekrar (SM-2), seviye, canlı soru üretimi
  egitmen_dersler.py    12 modül, 65 ders (~17.500 kelime)
  ambar.py              SQLite veri ambarı (7 tablo, WAL)
  haber.py              6 RSS kaynağı, makro haber ayıklama
  kap.py                KAP bildirimleri: günün açıklamaları, önem derecesi
  dogrulama.py          ikinci kaynak (İş Yatırım, TCMB) + çapraz kontrol
  telegram.py           bildirim taşıma katmanı (bağımlılıksız)
  bildirim.py           bildirim metinleri (günlük özet, stop uyarısı)
  izleme.py             stop/hedef izleme defteri
  bot_calistir.py       botun periyodik turu (timer bunu çağırır)
  defter.py             karar günlüğü: kullanıcının kendi sicili
  olcumler.py           derslerde aktarılan ölçüm rakamlarının tek kaynağı
  haber_esleme.py       haber -> hisse eşlemesi (takma ad + jenerik kara liste)
  ogrenme.py            sinyal kaydı, sonuç ölçümü, karne, kıyas uyarıları
  gunluk.py             günlük iş: 6 adım, gün özeti, geriye doldurma
  gunluk_calistir.py    zamanlayıcının çağırdığı giriş noktası
  ai.py                 LLM katmanı: iş-başına model, bütçe tavanı, harcama kaydı
  haber_ai.py           haberleri Claude ile hisseye bağlama (evren doğrulamalı)
  rapor.py              terminal çıktısı
```

## AI katmanı

**Fine-tuning yok — ve gerekmiyor.** Claude API'de model eğitme yüzeyi yoktur.
Zaten istemezsin: finansal seriler düşük sinyal-gürültü oranına sahiptir; küçük
sermaye ve kamuya açık veriyle eğitilen model gürültüye uyar, kazandığı şey
şanstan ayırt edilemez. **Sistemin gerçek öğrenmesi AI'sız çalışıyor** — her
akşam kendi sinyalinin sonucunu ölçüyor (`karne`). Claude öğrenen taraf değil,
akıl yürütme katmanı.

**Tek kural:** *model asla sayı üretmez.* Rakamlar yfinance + kendi hesabımızdan
gelir; model yorumlar, itiraz eder, sınıflandırır. Bu kural bozulursa uydurma
rakam sessizce sisteme girer.

### Her iş kendi modelini kullanır

Hepsine en pahalı modeli koşmak israftır.

| iş | model | ne yapar |
|---|---|---|
| `haber_sinifla` | Haiku 4.5 | Başlıkları hisselere bağlar — hacimli, basit |
| `gunluk_yorum` | Haiku 4.5 | Tarama sonuçlarını bağlama oturtur |
| `tez_elestir` | **Opus 5** | Kendi tezine karşı argüman — seyrek, zor, yüksek değerli |
| `finansal_ozet` · `sirket_anlat` · `haber_degerlendir` | Sonnet 5 | Anlatım |

### Haber sınıflandırma — VARSAYILAN KAPALI

**Ölçüldü ve işe yaramadı.** 2026-08-25: 95 gerçek haberde AI katmanı
yalnızca **1 eşleşme** ekledi ve o eşleşme **yanlıştı** —
*"Marmarabirlik, 6,8 milyar lira net ciroya ulaştı"* → ULKER. Marmarabirlik
bir zeytin kooperatifi; model "gıda" bağı kurmuş.

**Sebep sınıflandırıcı değil, kaynak.** O günün 147 başlığı: İran, Boeing,
Macron, BİM indirim broşürü, AİHM kararı, vefat haberi. Beslemelerde BIST
şirket haberi neredeyse yok — model 147'nin 146'sını doğru şekilde atladı.
Olmayan sinyali daha zekice sınıflandırmak sinyal üretmez.

Açmak için `.env` içinde `MIDAS_AI_HABER=1`. Kaynak sorunu çözülmeden
açmanın anlamı yok: ayda ~9 TL harcar, ölçülebilir değer üretmez.

Kod duruyor çünkü **kaynak düzelirse hazır** — ve üç güvenlik kuralı
sınandı, çalışıyor:

1. **Model yalnızca bizim evrenimizden kod seçebilir.** Döndürdüğü her kod
   doğrulanır; uydurulmuş kod atılır. (Test: `test_gecersiz_bag_atilir`)
2. **Model fiyat/hedef/tahmin üretmez** — yalnızca sınıflandırır.
3. **Kelime eşlemesi tabandır**, model üstüne ekler. Çakışmada elle yazılmış
   takma ad listesi kazanır. Model çökse ya da bütçe dolsa da eski davranış
   aynen sürer.

### Bütçe tavanı

**Aritmetik acımasız:** 1.000 TL sermayede ayda ~54 TL API gideri, gerçekçi
aylık getiri hedefinin (%3-5) **üstündedir**. Bu parayı işlem kârından
çıkarırsan matematiksel olarak kaybedersin — **eğitim bütçesi say, ayrı tut.**

`MIDAS_AI_TAVAN_TL` (varsayılan 100) aylık sert sınırdır. Her çağrı gerçek
`usage` token sayılarından fiyatlanıp ambara yazılır; tavan dolunca çağrılar
durur ve sistem anahtarsızmış gibi çalışmaya devam eder. Döküm: `ai-butce`.

Tek çağrı maliyeti (USD/TRY 48):

| iş | Haiku | Sonnet 5 | Opus 5 |
|---|---|---|---|
| Haber sınıflandırma (147 başlık) | 0,39 TL | 1,18 TL | 1,97 TL |
| Tez eleştirisi | 0,38 TL | 1,15 TL | 1,92 TL |

### Testler

```bash
.venv/bin/python -m pytest testler/ -q     # 22 test, API anahtarı GEREKTİRMEZ
```

Testlerin tamamı sahte yanıtlarla çalışır. Sebebi tek: bu katmanın riski
modelin ne kadar iyi düşündüğü değil, **kötü çıktıyı nasıl karşıladığımız.**

## İkinci kaynak ve çapraz kontrol

Fiyat, temel veri ve makro — üçü de yfinance'ten geliyordu. Tek kaynak
sessizce bozulursa sistem yanlış veriyle çalışır ve **bunu fark etmez.**
`cekirdek/dogrulama.py` ikinci bir kaynağa sorup farkı bildirir.

| Kaynak | Ne verir | Durum |
|---|---|---|
| İş Yatırım | BIST kapanış, hacim, **USD bazlı fiyat**, piyasa değeri | Resmi API değil, aracı kurumun ucu |
| TCMB | Günlük resmi döviz kuru, geçmiş dahil | **Resmi ve belgelenmiş**, anahtar istemez |

**Eşik neden %1:** 8 hisse × 38 ortak günde iki kaynağın kapanışları ortalama
%0,00, azami %0,23 farkla örtüştü (2026-08-25 ölçümü). %1, normal gürültünün
dört katı ama gerçek bir bozulmanın çok altı.

**İlk çalıştırmada yakaladığı gerçek hata:** CVKMD'de %61,3 sapma. yfinance
2026-08-03'teki ~%159'luk bedelsizi bilmiyor, geçmişi düzeltmiyor ve seride
sahte bir uçurum bırakıyor — 37,82'den 14,42'ye tek günlük "çöküş". İş
Yatırım'ın serisi kesintisiz. `scikit-learn` kurulu ve `repair=True` açıkken
bile oldu; yani onarım her sermaye işlemini yakalamıyor.

Günlük iş yalnızca **filtreyi geçen** hisseleri kontrol eder (en fazla 30):
bozuk fiyatın tehlikeli olduğu tek yer o hisseye sinyal üretilmesidir.

Katman karar üretmez, uyarır. Kaynağa ulaşılamazsa sessizce atlanır —
**ağ arızası veri arızası değildir**, her gün "veri şüpheli" diyen bir sistem
okunmaz olur. `testler/test_dogrulama.py` bu iki ucu da kilitler.


## Referans nasıl hesaplanır

Canlı sicili kıyaslamak için bir taban gerekir. Bu tabanın iki klasik hatası
2026-08-25'te ölçülüp giderildi.

**1. Elma-armut.** Eski referans bir PORTFÖY backtestinden geliyordu: aynı
anda en fazla 4 pozisyon, nakit kısıtı, seçilmiş altküme. Canlı sicil ise
TÜM sinyalleri sayar. Bu, canlıyı yapısal olarak kötü gösteriyordu. Yeni
referans sinyal seviyesinde — canlı sicille aynı şeyi ölçüyor.

**2. Hayatta kalanın yanılgısı.** Eski referans bugünün BIST 100 listesini
geçmişe uyguluyordu; listeye sonradan girenler oraya iyi performansla girdi.
Çözüm: endeks üyeliği yerine **o günkü 20 günlük TL hacmine göre ilk 100**
hisse. Bu sıralama geleceği bilmez.

570 BIST şirketi üzerinde ölçülen fark:

| Strateji | Bugünün BIST 100'ü | O günkü ilk 100 | Yanlılık |
|---|---|---|---|
| trend | %51,0 | %48,4 | 2,6 puan |
| tepki | %55,6 | %56,1 | ~0 |
| kirilim | %52,3 | %48,9 | 3,4 puan |

> Basit "BIST 100 içi vs dışı" kıyası 12-14 puanlık fark gösteriyor — ama o
> fark hayatta kalanın yanılgısı değil, büyük/küçük hisse farkı. Zamanında
> hacim sırası ikisini ayırıyor.

Düzeltmenin sonucu: `trend`'in karantina sınırına uzaklığı 3,2 puandan
1,1 puana indi. Hüküm değişmedi ama artık kıl payı.


## Strateji karantinası

Canlı sicili beklenenin altında kalan strateji **önerilmez** — ama sinyal
üretmeye ve ambara yazmaya devam eder. Fark önemli: kapatılan strateji
hakkında yeni kanıt birikmez, karantina kalıcı hapse dönüşür ve strateji
düzelse bile bunu kimse göremez.

Karar **veriye** bağlı, strateji adına değil. `ogrenme.strateji_siniflari()`
canlı kazanma oranını, o kadar aylık bir pencerede tarihsel olarak beklenen
dağılımla karşılaştırır:

| Sınıf | Koşul | Önerilir mi |
|---|---|---|
| `normal` | beklenenin alt çeyreğinin üstünde | evet |
| `izlemede` | alt %5 ile alt çeyrek arasında | evet, işaretli |
| `karantina` | beklenenin alt %5'inin altında | **hayır** |
| `hüküm_yok` | 2 aydan az veya 30 sinyalden az | evet |

`hüküm_yok` bilinçli olarak önerilir: veri yokluğu suç değildir, yeni bir
strateji baştan cezalandırılmamalı.

**25 Ağustos 2026 durumu:** `trend` ve `kirilim` karantinada, `tepki`
izlemede. Yani o gün üretilen iki sinyalin ikisi de (EUPWR, ALARK — trend)
gösteriliyor ama önerilmiyor; ekranda "önerilen 0" yazıyor.

Karantina üç yerde görünür: tarama ekranı (rozet uyarı renginde ⚠), gün
özeti (`⚠ sicili zayıf`) ve `/tarama` yanıtındaki `strateji_durumlari`.
`testler/test_karantina.py` davranışı kilitler — özellikle "düzelen strateji
kendiliğinden çıkar" ve "tek ayla hüküm verilmez" kurallarını.


## Kaç bağımsız bahis

Ekranda "3 sinyal" görmek üç ayrı fırsat gibi okunur. Bu sistemin bütün
sinyalleri **uzun yönlü ve aynı anda açık** — çoğu zaman tek bir bahsin üç
parçası. Ölçüsü:

    N_etkin = n / (1 + (n-1) · ρ̄)

4 sinyal, aralarındaki korelasyon 0,8 ise → **1,2 bağımsız bahis**. Risk
dörde bölünmez; dördü birden aynı yöne gider.

Kart üç şey söyler: kaç bağımsız bahis, en yakın çift (hangi ikisi aslında
aynı bahis), ve sektör yoğunlaşması. Sektör ayrı bir risktir — geçmiş
getiriler ayrışmış olsa bile sektöre özel bir haber hepsini birden vurur,
o yüzden korelasyon düşükken bile uyarı çıkabilir.

## Günün dersi

65 derslik müfredat ayrı bir sekmede duruyordu ve açılmıyordu: ölçüldü,
**65 dersten 1'i okunmuştu.** Sebep içerik değil akış — kimse "eğitim" için
ayrı zaman ayırmıyor.

Çözüm: dersi o günün gerçek olayına bağlamak. `egitmen.baglamsal_ders()`
duruma göre seçer:

| Bugün olan | Gelen ders |
|---|---|
| Bir strateji karantinada | `d1202` Strateji geliştirme ve backtest |
| Sinyaller yoğunlaşmış | `d804` Çeşitlendirme ve korelasyon |
| Reel getiri negatif | `d601` Enflasyon: nominal ile reelin farkı |
| KAP'ta yoğun bildirim | `d1101` KAP nedir ve nasıl okunur |
| Hiç önerilen sinyal yok | `d1004` İntikam işlemi ve aşırı işlem |
| Portföy boş | `d1201` Yatırım tezi |
| Özel durum yok | müfredattan sıradaki okunmamış ders |

Ders kartı **neden bugün bu ders** olduğunu da yazar; bu olmadan kart
rastgele bir öneri gibi görünür ve tıklanmaz. Uç (`/egitmen/gunun-dersi`)
tarama çalıştırmaz, her şeyi ambardan okur.


## Grafik okuma modülü (m13)

Teknik analiz modülü (m7) göstergeleri anlatıyordu ama **grafiğin kendisini
okumayı** hiçbir yer anlatmıyordu. Mumun ne olduğunu bilmeden RSI öğrenmek,
alfabeyi bilmeden şiir okumaya benzer.

7 ders, her birinin bir **şeması** var (`cekirdek/egitmen_sema.py`):

| Ders | Şema |
|---|---|
| d1301 Grafik türleri ve neden mum | zaman dilimi |
| d1302 Bir mum neyi anlatır | mum anatomisi (gövde, fitil, açılış/kapanış) |
| d1303 Destek ve direnç | zikzak + etiketli seviyeler |
| d1304 Trend çizgisi nasıl çizilir | dipleri birleştiren çizgi, dip 1-2-3 |
| d1305 Boşluk (gap) | iki mum arası boşluk |
| d1306 Üç temel mum formasyonu | çekiç, doji, yutan boğa |
| d1307 Zaman dilimi ve gürültü | günlük vs haftalık aynı hareket |

**Şema ≠ canlı grafik.** `egitmen_gorsel.py` gerçek veriyi çizer ("bu
hissenin gerçek RSI'si"); `egitmen_sema.py` kavramı çizer. "Destek nedir"
sorusunun cevabı gerçek bir grafiğin gürültüsünde kaybolur — temiz bir
zikzakta iki etiketle anlaşılır. İkisi birbirini tamamlar.

Şema sözleşmesi sunucuda tarif, istemcide çizim: `{cizgiler, mumlar,
seviyeler, etiketler, oklar}` + koordinat uzayı. Sunucu piksel bilmez,
istemci kavram bilmez. `mobil/lib/parca/sema.dart` bir `CustomPainter`.

> Yeni ders eklendiğinde `/egitmen/mufredat` içindeki `surum` ve
> `mobil/lib/servis/egitmen.dart` içindeki `mufredatSurum` **birlikte**
> artırılmalı. Artmazsa telefon eski müfredatı kullanmaya devam eder ve
> kimse fark etmez.

## Derslerde görsel

Ders kitabındaki uydurma grafik, öğrenilen şeyin gerçek piyasada nasıl
göründüğünü göstermez. Bu yüzden ders görselleri **canlı veriden** üretilir:
`d704` (momentum) gerçek bir BIST hissesinin gerçek RSI'sini çizer ve
"RSI 70'i aştıktan sonraki 20 günde ortalama getiri %X" der.

| Ders | Görsel | Ne gösterir |
|---|---|---|
| d601, d603 | `nominal_reel` | XU100 TL vs dolar bazında, ikisi de 100'e endeksli |
| d701, d703 | `fiyat_sma` | Gerçek fiyat + EMA20 + SMA200 |
| d704 | `rsi` | Gerçek RSI, "70 üstü sat" ezberinin ölçülmüş yanlışı |
| d705 | `oynaklik` | ATR yüzdesi seyri |
| d801 | `kayip_asimetrisi` | Kaybı telafi için gereken kazanç eğrisi |
| d804 | `korelasyon` | Bugünkü sinyallerin ikili korelasyonu |
| d1202, d1203 | `sicil_aylik` | Sistemin kendi aylık kazanma oranı |

Üç tasarım kararı:

- **Grafik anlatımdan SONRA gelir.** Bağlamı kurmadan grafiğe bakan, grafikte
  ne göreceğini bilmiyor.
- **Her grafiğin bir "sonuç" cümlesi var.** Grafik tek başına yorumlanmaz;
  "ne görmelisin" yazmazsa çoğu okuyucu bakıp geçer.
- **Veri gelmezse hiçbir şey çizilmez.** Boş bir grafik çerçevesi, grafik
  olmamasından kötüdür. Görsel ayrı uçtan gelir, ders metni onu beklemez.

## Hakimiyet ekranı

`seviye_durumu` zaten bileşik bir yüzde hesaplıyordu (derslerin 2/3,
soruların 1/3 ağırlığıyla) ama ekranda görünmüyordu. Artık **"%N hakimsin"**
halkayla en üstte.

Altında **konu haritası**: 12 modülün her biri için okunan/toplam. Tek bir
yüzde "nerede zayıfım" sorusunu cevaplamaz — asıl işe yarayan harita budur.


## Karar defteri

`sinyal` tablosu **sistemin ne önerdiğini** tutar. `karar` tablosu
**kullanıcının ne yaptığını**. İkisi ayrı, çünkü ölçülmek istenen şey
aradaki farktır:

> Sistem bir gün 7 sinyal üretir, sen 2'sini alırsın. Asıl beceri o
> seçimdedir — ve şimdiye kadar hiçbir yerde kayıtlı değildi. Sicil
> "sistem ne yaptı" sorusunu cevaplıyordu; "ben ne yaptım" sorusunun
> cevabı yoktu.

### Üç tasarım kuralı

**Değiştirilemez günlük.** Satır güncellenmez, yalnızca eklenir. Satış da
ayrı bir karardır ve alımı silmez. Sonradan "ben zaten biliyordum" demeyi
imkânsız kılan tek şey budur — psikoloji modülünün tamamı bu yanılgı
üzerine kurulu (d1003).

**Karar anı dondurulur.** Alım kaydedilirken sistemin o gün ne dediği
(sinyal var mıydı, hangi strateji, önerilir miydi, skor kaç) aynı satıra
yazılır. Sonradan sorgulanmaz — çünkü sonradan bakınca sistem hep haklı
görünür.

**Sinyal tazeliği 5 gün.** Bu pencere olmadan, hissenin aylar önce bir kez
sinyal vermiş olması bugünkü alımı "sinyalli" yapar ve takip oranı ölçümü
anlamını yitirir; her hisse bir gün sinyal vermiştir.

### Ölçülenler

| | |
|---|---|
| Kazanma oranı, ortalama getiri | kapanan işlemlerde |
| **Sistemi takip oranı** | alımların kaçı sinyalliydi |
| Karantinalı alım | sicili zayıf stratejiden kaç alım |
| **Sinyalli vs kendi fikrin** | ayrı ölçülür — seçim becerisi buradan görünür |
| Stop disiplini | stopun altında kapanan işlem var mı |

Örneklem uyarısı sistemin sicilindekiyle aynı: 20 işlemin altında hüküm
çıkmaz.

### Kağıt / gerçek

Varsayılan **kağıt üzerinde** (`kagit=1`). Gerçek para açıkça belirtilmeli
(`/aldim THYAO 302 gercek`) — kaza ile gerçek kayıt oluşmasın. Gerçek
parayla başlamadan önce kağıt üzerinde takip, riski sıfır ölçümü gerçek
olan tek ara adımdır.

### Pozisyonlar türetilir

Ayrı bir "pozisyon" tablosu **yok**. Açık pozisyonlar kararlardan FIFO ile
hesaplanır. İki kaynak tutulursa biri diğerinden sapar ve hangisinin doğru
olduğu bilinmez.

### Tek kaynak: sunucu

Pozisyonlar eskiden telefonda yaşıyordu ("sunucu çökerse geçmişini
göremezsin" gerekçesiyle). Defter eklenince aynı pozisyon iki yerde
tutulmaya başladı ve sapma riski doğdu. Çözüm: **defter tek kaynak.**

- Telefon açılışta `/defter`'den tazeler, yerel kopyayı yalnızca
  **çevrimdışı okumak** için saklar
- Alım ve kapatma önce sunucuya yazar; sunucu kabul etmezse yerelde de
  yazılmaz — telefonda olup defterde olmayan pozisyon oluşmasın
- Ağ hatasında kullanıcıya açıkça söylenir; sessiz başarısızlık, kaydettiğini
  sanıp hiçbir yerde olmamasına yol açardı

Eski gerekçe de geçerliliğini yitirdi: sunucu artık 7/24 bulutta.

Botla girilen bir pozisyon (`/aldim`) uygulamanın Portföy ekranında,
uygulamadan girilen bir pozisyon botun `/pozisyon` çıktısında görünür.


## Telegram bildirimleri

Günlük iş her akşam 18:10'da çalışıp günü özetliyordu — sonra kullanıcı
uygulamayı açana kadar bekliyordu. Sunucu 7/24 çalışıyor ama tek yönlüydü:
dışarı hiçbir şey söylemiyordu.

Daha somut olarak: gerçek pozisyon açtığında **stopunu kimse izlemiyordu.**
Sistem günde bir kez, kapanıştan sonra bakıyor. Stop saat 11:00'de geçilirse
akşama kadar haberin olmaz — o da uygulamayı açarsan.

**Neden Telegram:** uygulama derlemeye, mağazaya, Firebase anahtarına gerek
yok; bedava; her telefonda çalışır; iki yönlü. Bağımlılık da eklenmedi —
tek bir HTTPS POST için `urllib` yetiyor.

### Kurulum

1. Telegram'da **@BotFather** → `/newbot` → token'ı al
2. **@userinfobot** → `/start` → sohbet kimliğini al
3. `.env` içine yaz:
   ```
   MIDAS_TELEGRAM_TOKEN=123456789:AAG...
   MIDAS_TELEGRAM_SOHBET=123456789
   ```
4. `./dagit.sh`

Yapılandırma yoksa katman **sessizce kapalı** kalır — sistem tam çalışır.

### Ne gönderir

| Ne zaman | Ne |
|---|---|
| 18:10 işinden sonra | Günün özeti: endeks, genişlik, reel getiri, sinyaller, karantina, KAP |
| Seans içinde (dakikada bir) | İzlenen pozisyon stop/hedef seviyesini geçince |

### Komutlar

```
/durum              günün özeti
/tarama             bugünün sinyalleri, stop ve hedefle
/hisse THYAO        tek hisse analizi (canlı, ~1-5 sn)
/karne              sistemin canlı sicili
/ders               günün dersi (o günün durumuna bağlı)
/izle THYAO 250 300 pozisyonu izlemeye al
/liste              izlenen pozisyonlar
/birak THYAO        izlemeyi bırak
```

Hisse kodu tek başına da yazılabilir (`THYAO`) — `/hisse` yazmaya gerek yok.

Komut listesi Telegram menüsüne kaydedilir (`setMyCommands`); menü olmadan
kullanıcı komutları ezberlemek zorunda kalır, bir botun kullanılmama
sebeplerinin başında bu gelir. Menü ve yardım metni **tek kaynaktan**
üretilir (`bildirim.KOMUTLAR`) — ayrışırlarsa kullanıcı olmayan bir komutu
dener.

**Gecikme:** timer dakikada bir çalışır ve her tur 45 saniye uzun yoklama
yapar; komut neredeyse anında cevaplanır. Yoklamasız çalışsaydı ortalama
gecikme yarım dakika olurdu — bir sohbet botunda bu kırık hissettirir.
Tur 0,01 saniyede açıldığı için dakikalık çalışmanın maliyeti yok.

### Tasarım kararları

- **İçerik ve taşıma ayrı** (`bildirim.py` / `telegram.py`): mesaj metnini
  sınamak için Telegram'a bağlanmak gerekmesin.
- **Sürekli çalışan süreç yok.** systemd timer 5 dakikada bir çağırır,
  betik çıkar. Daemon, tek kullanıcılı bir sistemde izlenmesi ve yeniden
  başlatılması gereken fazladan bir hareketli parça olurdu.
- **Aynı uyarı günde bir kez.** Her turda mesaj atmak kullanıcıyı botu
  susturmaya götürür; susturulmuş bot, olmayan bottan kötüdür.
- **Yapılandırılmamış olmak hata değil.** Bot çıkış kodu 0 döner — 1
  dönseydi timer her 5 dakikada bir başarısız birim kaydı düşürür ve
  gerçek bir arıza görünmez olurdu.
- **Bildirim, işin kendisi değil.** Telegram çökerse günlük iş başarılı
  sayılır; bildirim adımı kendi hata kabuğunda ve en sonda.

### Pozisyonlar neden ayrı defterde

API durumsuzdur, pozisyonlar telefonda yaşar. Sunucu onları bilmez ve
bilmemeli. Ama alarm için neyi izleyeceğini bilmesi gerekiyor — çözüm
telefonun portföyünü sunucuya taşımak değil, botun kendi küçük izleme
listesini tutması (`veri/izleme.json`, `/izle` komutuyla dolar).


## Ölçüm rakamları ve tutarlılık koruması

Müfredat birçok yerde "sistemin ölçtüğü rakam" diye sayı aktarır. Bunlar
`cekirdek/olcumler.py`'de **tek kaynakta** tutulur ve
`testler/test_olcum_tutarlilik.py` her rakamın ilgili ders metninde
geçtiğini doğrular. Ölçüm yenilenip sabitler güncellenirse, ders metni de
güncellenene kadar test düşer.

Neden gerekti: 2026-08-26'da dersler `kirilim Sharpe 1,93` diye
aktarıyordu. Doğrusu **−0,71**.

**Sebep — ve sistemin kendi dersini ihlal etmesi:** `backtest.metrik_hesapla`
Sharpe'ı risksiz getiriyi ÇIKARMADAN hesaplıyordu. `istatistik.performans`
baştan beri doğru yapıyordu (`risksiz_yillik=40`), yani kod tabanında iki
farklı Sharpe vardı ve dersler yanlış olanı aktarıyordu — üstelik aynı
dersin bir alt satırı *"Sistem Sharpe'ı risksiz getiriye göre hesaplar"*
diye iddia ediyordu.

Türkiye'de bu fark her şeyi değiştirir: kirilim 3,29 yılda yıllık %26,7
kazandırdı, aynı dönemde mevduat %40 veriyordu. Risksiz alternatifin
altında kalan bir stratejinin risk-ayarlı skoru **negatiftir**.

| | eski (yanlış) | doğru |
|---|---|---|
| kirilim | Sharpe 1,93 | **−0,71** |
| trend | Sharpe 1,27 | **−0,91** |
| XU100 | Sharpe 1,53 | **−0,03** |

Sonuç dersin hükmünü de tersine çevirdi: endeks, risk-ayarlı olarak
stratejilerin hepsinden iyiymiş.

> Veri katmanına dokunulduğunda ya da evren değiştiğinde backtest yeniden
> çalıştırılıp `olcumler.py` ve `OLCUM_TARIHI` güncellenmeli. Test, ders
> metinlerinin geride kalmasını engeller.


## Bilinen sınırlar

- Veri ~15 dk gecikmeli; gün içi hassas girişler için uygun değil
- **yfinance bazı BIST sermaye işlemlerini kaçırıyor** — bedelsiz/bölünme
  kaydı yoksa geçmiş düzeltilmez ve seride sahte uçurum kalır. `repair=True`
  bunu her zaman yakalamıyor. Çapraz kontrol katmanı bu sınıfı görünür
  kılar ama otomatik DÜZELTMEZ: uyarı gelen hissenin verisine elle bak
- BIST 100 listesi Ağustos 2026 sabiti; endeks 3 ayda bir revize edilir
- Backtest 3,28 yıl = tek bir piyasa rejimi, 2018 gibi bir kriz içermiyor
- **KAP bildirimleri yalnızca bugünü kapsar.** Kullanılan uç geçmiş sorgusu
  desteklemiyor; günlük iş 18:10'da çalışıp o günü ambara yazar. İş bir gün
  çalışmazsa o günün bildirimleri geri getirilemez
- **KAP ucu resmi olarak belgelenmiş değil.** Next.js uygulamasının kullandığı
  JSON ucu (2026-08-25'te doğrulandı). Haber vermeden değişebilir; değişirse
  `kap.topla()` boş döner ve sistem KAP'sız çalışmaya devam eder —
  `testler/test_kap.py` bu davranışı kilitler
- **RSS haber kaynakları BIST şirket haberi taşımıyor.** Mevcut 5 besleme
  genel ekonomi yayınlıyor; 95 haberde 3-4 eşleşme normaldir. Şirkete özel
  bilgi artık KAP'tan geliyor, bu beslemeler makro bağlam için duruyor
- **BloombergHT beslemesi 2026-08-06'dan beri donmuş** — 6 kaynak yazıyor
  ama pratikte 5 çalışıyor. Yayıncı düzeltirse kendiliğinden geri gelir
- **Canlı sicil 4,1 ay** — ve asıl mesele süre değil: sinyaller BAĞIMSIZ
  DEĞİL. Hepsi uzun yönlü ve aynı anda açık, aynı ayın sinyalleri aynı kaderi
  paylaşıyor. Aylık kazanma oranı %16,9 ile %81,2 arasında savruluyor. Gerçek
  örneklem büyüklüğü sinyal sayısı değil **ay sayısı** — 769 değil, 4.
  `kayma_analizi` artık buna göre blok önyükleme kullanıyor
- **Referans evreni bugün borsada olan şirketlerden kurulur** — kotasyondan
  tamamen çıkmış şirketler eksik, küçük bir yanlılık kalıyor. "Endeksten
  düştü" etkisi giderildi (aşağıya bak), "şirket battı" etkisi giderilemedi
- Günlük iş artık bulut sunucusunda çalışıyor (bkz. Buluta taşıma); systemd
  timer `Persistent=true` ile sunucu kapalıysa açılışta telafi eder
- TCMB politika faizi ve Türkiye CDS'i makro panelde yok (EVDS API anahtarı gerekir);
  enflasyon borsapy üzerinden anahtarsız geliyor
- Sistem sadece **uzun** taraf; açığa satış yok
- Sektör medyanları ilk çalıştırmada yavaş (100 şirketin finansalı çekilir, 24 saat önbellek)

## Uyarı

Bu bir yatırım tavsiyesi değildir. Geçmiş getiri gelecek getiriyi göstermez.
Backtest sonuçları gerçek işlem sonuçlarını garanti etmez. Kaybetmeyi göze
alamayacağın parayla işlem yapma.
