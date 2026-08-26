# Midas Analist — mobil

Python çekirdeğinin Flutter istemcisi. Sunucu **durumsuzdur**: pozisyonlar ve
tezler telefonda saklanır, sunucuya yalnızca hesaplanmak için gönderilir.
Sunucu kapalıyken bile geçmişini görürsün.

## Çalıştırma

**1. Sunucuyu başlat** (proje kökünde):

```bash
./sunucu.sh
```

Ekrana üç adres yazar. Telefondan bağlanacaksan `http://192.168.x.x:8000`
satırındakini not al.

**2. Uygulamayı çalıştır:**

```bash
cd mobil
flutter run                    # bağlı cihaz/emülatörde
flutter run -d chrome          # tarayıcıda
flutter build apk --release --split-per-abi   # APK üret
```

APK'lar: `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` (19,2 MB —
modern telefonlar için bu).

**3. Ayarlar > Sunucu** alanına adresi gir, "Bağlantıyı dene" ile doğrula.

| Nereden çalıştırıyorsun | Adres |
|---|---|
| Android emülatör | `http://10.0.2.2:8000` (varsayılan) |
| Gerçek telefon, aynı Wi-Fi | `http://<PC-IP>:8000` |
| Tarayıcı / masaüstü | `http://127.0.0.1:8000` |
| Cloud Run | `https://...run.app` + API anahtarı |

## Ekranlar

| Sekme | Ne yapar |
|---|---|
| **Bugün** | Portföy özeti, aksiyon gereken pozisyonlar, piyasa rejimi, sinyal sayısı |
| **Tarama** | Skor sıralı adaylar; sermayeye göre kaç adet, stop, hedef |
| **Portföy** | Sat/tut kararı, iz süren stop önerisi ("Uygula" ile tek dokunuş), portföy riski |
| **Tezler** | Açık tezler, bozulma kontrolü, kapanmışların karnesi |
| **Daha** | **Sermaye**, **eğitmen**, **gün özeti**, **sicil**, makro, sektörler, risk matematiği, öğren, ayarlar |

### Sermaye defteri

Sermaye sabit değil — hesabına para ekledikçe uygulamadan güncellersin.
`Daha > Sermaye` ya da Bugün ekranındaki **SERMAYE +/−** düğmesi.

Defterin tek amacı **yatırdığın parayı kazandığından ayırmak.** "Portföyüm
1.400 TL" tek başına performans değildir: 1.000 yatırıp 400 kazanmış da
olabilirsin, 1.400 yatırıp sıfır kâr etmiş de. Ekran üç rakamı ayrı gösterir:

| | ne demek |
|---|---|
| **Toplam sermaye** | Nakit + açık pozisyonların maliyeti |
| **Yatırdığın para** | Senin cebinden çıkan net tutar — kâr/zarar hariç |
| **Gerçekleşen kâr** | Yalnızca KAPANMIŞ pozisyonlardan |

Kâr/zarar kayıtları pozisyon kapattığında **otomatik** yazılır. Elle
eklemen gereken tek şey para giriş/çıkışı.

Midas'taki gerçek toplamla uyuşmazsa sağ üstteki **hizala** düğmesi farkı
kapatır — ama önce farkın nereden geldiğini sorar (para mı yatırdın, işlem
mi yaptın). Bu soru şart: aynı fark, sebebine göre "yatırdığın para"yı ya da
"kazandığın para"yı değiştirir; karıştırılırsa getiri yüzdesi anlamsızlaşır.

### Gün özeti ve sicil

**Gün özeti** (`Daha > Gün özeti`) sunucunun her akşam 18:10'da ürettiği raporu
gösterir: piyasa geneli (kaç hisse arttı/azaldı), en çok yükselenler ve
düşenler, o günün sinyalleri, eşleşen haberler. Sağ üstteki tarih seçiciyle
geçmiş günlere bakabilirsin — "dün 100 TL, bugün 103 TL" bilgisi burada.

**Sicil** (`Daha > Sicil`) sistemin kendi sinyallerinin gerçekte ne yaptığını
gösterir. Backtest değil: kaydedilmiş canlı sinyaller, vadesi dolunca gerçek
fiyat serisinde ölçülmüş. Vadelere göre kazanma oranı, stratejiye göre kırılım,
canlı-backtest kıyası ve o kıyasın **neden yapısal olarak canlının aleyhine
olduğunu** anlatan uyarılar birlikte gelir.

Bu iki ekran sunucu gerektirir — veri ambarı sunucudadır.

### Eğitmen

**12 modül, 65 ders.** Günlük oturum önce bugünün dersini gösterir, sonra
pekiştirme sorularını. Sorular sadece okuduğun derslerden gelir.

Ders ekranı beş bölüm: anlatım · örnek · BIST/Midas özeli · tuzak · pekiştirme.
Sağ üstteki yer imi ile "buna dönmem lazım" işaretleyebilirsin.

Müfredat ve soru bankası bir kez indirilip cihazda saklanır; **aralıklı tekrar
hesabı telefonda yapılır** — dersleri internetsiz okuyabilirsin. Sadece canlı
sorular (bugünkü piyasa verisinden üretilenler) bağlantı ister.

Hisse detayında sağ üstteki 🎓 ikonu "şirketi oku" egzersizini açar.

Hisse detayı üç sekme: **Teknik** (grafik, skor kırılımı, seviyeler, pozisyon
planı) · **Yapı** (tepe/dip, çoklu zaman dilimi, Fibonacci, kırılım
güvenilirliği) · **Şirket** (17 oran, kırmızı bayraklar, çarpanlar, ters DCF).

## Alım akışı

`Alım kaydet` → davranışsal tarama çalışır → **kritik uyarı varsa kayıt kilitli**.
Devam etmek için onay kutusunu işaretlemen gerekir. Bu sürtünme bilerek var:
kritik uyarıya rağmen alım yapmak bir karar olmalı, refleks değil.

Kayıttan sonra tez yazma ekranı açılır. Tez, o günün objektif durumunu
(kalite skoru, çarpanlar, kırmızı bayraklar, makro rejim) birlikte dondurur.

## Bilinen sınırlar

- Uygulama Midas'ta **emir vermez**. Midas'ın geliştirici API'si yok.
- Sunucu çalışmıyorsa analiz ekranları boş kalır; kayıtlı pozisyon ve tezler görünür.
- İlk açılışta sunucu ~100 hisse indirir; birkaç dakika sürebilir.
- Şirket sekmesi ilk çekimde yavaştır (finansal tablolar + sektör emsalleri).
- Gün özeti ve sicil ekranları çevrimdışı çalışmaz; ambar sunucuda tutulur.
- Gün özeti yalnızca günlük iş çalıştıysa dolu gelir. Sunucuda
  `./kur_zamanlayici.sh` kurulmalı ya da `./gunluk.sh` elle çalıştırılmalı.
- Sermaye defteri yalnızca **bu cihazda** yaşar. Uygulamayı silersen gider;
  sunucuya gönderilmez.
- Uygulama Midas hesabına bağlanmaz — bakiyeni okumaz. Defteri sen tutarsın.

## Dosya düzeni

```
lib/
  main.dart              giriş
  tema.dart              renk/tipografi + Türkçe sayı biçimleme
  servis/
    modeller.dart        Pozisyon, Tez, Ayarlar
    api.dart             HTTP istemcisi, hata çevirisi
    depo.dart            yerel depo + uygulama durumu
  parca/
    kart.dart            ortak bileşenler
    grafik.dart          fiyat/RSI grafikleri, karşılaştırma çubuğu
  ekran/                 22 ekran (sermaye, gün özeti, sicil dahil)
assets/font/             Piksel (DejaVu Sans Mono türevi) + lisans
test/gorunum_test.dart   ekran görüntüsü koşumu (aşağıya bak)
```

## Görünüm

**Tek koyu tema, piksel/terminal estetiği.** Üç kural `lib/tema.dart` içinde
yazılı ve **testle kilitli** (`test/widget_test.dart` → "Piksel tema kuralları"):

1. **Yuvarlaklık yok.** Her köşe 90°; yarıçap yalnızca `kose` sabitinden geçer.
2. **Gölge yok.** Derinlik gölgeyle değil, 1px kenarlıkla anlatılır.
3. **Tek font:** sabit genişlikli. Sayı sütunları kendiliğinden hizalanır —
   borsa ekranında okuma hızı buna bağlı.

Açık tema kasten yok: iki tema demek her rengi iki kez doğrulamak demekti ve
yarısı hiç kullanılmıyordu. Cihaz açık moddaysa bile uygulama koyu kalır.

Skor göstergesi halka değil **on blok** — piksel ızgarasında daire yamuk
görünür ve dolgu oranı gözle okunmaz; blok sayılabilir. Fiyat grafiği
basamaklı (`isStepLineChart`): kavisli çizgi barlar arasında olmayan ara
değer uydurur.

Yazı tipi `assets/font/` içinde gömülü (DejaVu Sans Mono, Bitstream Vera
türevi — gömme serbest). Türkçe karakterlerin ve `₺` işaretinin tamamını
taşıdığı doğrulandı.

**Ekran görüntüsü almak** (emülatör gerekmez):

```bash
flutter test --update-goldens --run-skipped --tags gorunum
```

`test/gorunum/` altına PNG basar. Bu koşum normal `flutter test` sırasında
atlanır: amacı gözle bakmak, piksel kıyaslamak değil — font sürümü değişince
gerçek bir hatayı değil ortam farkını bildirirdi.
