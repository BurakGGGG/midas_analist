// Görsel doğrulama koşumu.
//
// Emülatör olmadan gerçek widget'ları gerçek temayla çizip PNG'ye basar.
// `flutter test --update-goldens --run-skipped --tags gorunum` ile üretilir;
// çıktı test/gorunum/ altına düşer.
//
// Amaç kıyaslama değil GÖZLE BAKMAK: piksel tema tutarlı mı, köşe kalmış mı,
// font uygulanmış mı. Bu yüzden CI'da kırılmasın diye normal koşuda atlanır.
@Tags(['gorunum'])
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'dart:convert';

import 'package:midas_analist/ekran/alistirma.dart';
import 'package:midas_analist/ekran/ayarlar.dart';
import 'package:midas_analist/ekran/defter.dart';
import 'package:midas_analist/ekran/alim.dart';
import 'package:midas_analist/ekran/bugun.dart';
import 'package:midas_analist/ekran/ders.dart';
import 'package:midas_analist/ekran/ilerleme.dart';
import 'package:midas_analist/ekran/ogret.dart';
import 'package:midas_analist/ekran/tez_yaz.dart';
import 'package:midas_analist/ekran/hisse.dart';
import 'package:midas_analist/ekran/makro.dart';
import 'package:midas_analist/ekran/mufredat.dart';
import 'package:midas_analist/ekran/ogren.dart';
import 'package:midas_analist/ekran/sektor.dart';
import 'package:midas_analist/ekran/sirket_oku.dart';
import 'package:midas_analist/ekran/gun_ozeti.dart';
import 'package:midas_analist/ekran/karne.dart';
import 'package:midas_analist/ekran/risk_ekran.dart';
import 'package:midas_analist/ekran/tezler.dart';
import 'package:midas_analist/ekran/hesap.dart';
import 'package:midas_analist/ekran/portfoy.dart';
import 'package:midas_analist/ekran/tarama.dart';
import 'package:midas_analist/servis/api.dart';
import 'package:midas_analist/ekran/kilit.dart';
import 'package:midas_analist/ekran/sermaye.dart';
import 'package:midas_analist/ekran/sozluk.dart';
import 'package:midas_analist/servis/alistirma.dart' show kum;
import 'package:midas_analist/servis/egitmen.dart' show egitmen;
import 'package:midas_analist/servis/kilit.dart' show kilit;
import 'package:midas_analist/parca/kart.dart';
import 'package:midas_analist/servis/depo.dart';
import 'package:midas_analist/servis/modeller.dart';
import 'package:midas_analist/tema.dart';
import 'package:shared_preferences/shared_preferences.dart';

Widget _sarmala(Widget govde) => MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: temaKoyu,
      home: govde,
    );

/// Golden koşumu varsayılan olarak sahte font kullanır ve her harfi dolu
/// kutu çizer. Gerçek fontu yüklemezsek "yazı tipi uygulandı mı" sorusunu
/// bu ekran görüntüleri cevaplayamaz.
Future<void> _fontuYukle() async {
  final y = FontLoader('Piksel');
  for (final ad in ['PixelMono-Regular.ttf', 'PixelMono-Bold.ttf']) {
    final b = File('assets/font/$ad').readAsBytesSync();
    y.addFont(Future.value(ByteData.view(b.buffer)));
  }
  await y.load();

  // İkon fontu da yüklenmezse her ikon boş kare çıkar ve görsel kontrol
  // yanıltıcı olur.
  final ikonYol = File(
      '${Platform.environment['HOME']}/flutter/bin/cache/artifacts'
      '/material_fonts/MaterialIcons-Regular.otf');
  if (ikonYol.existsSync()) {
    final i = FontLoader('MaterialIcons');
    i.addFont(
        Future.value(ByteData.view(ikonYol.readAsBytesSync().buffer)));
    await i.load();
  }
}

/// Ağ yerine diskteki gerçek sunucu yanıtlarını döndürür.
///
/// Veri UYDURMA DEĞİL: gerçek /tarama, /portfoy/kontrol ve /risk/portfoy
/// yanıtları kırpılarak kaydedildi. Uydurma veri gerçek render sorunlarını
/// göstermez — uzun sembol adları, karantina rozetleri, negatif kâr ve
/// sektör uyarısı ancak gerçek veriyle ekrana gelir.
class _SahteApi extends Api {
  _SahteApi() : super('http://sahte');

  Map<String, dynamic> _oku(String ad) => Map<String, dynamic>.from(
      jsonDecode(File('test/gorunum/$ad').readAsStringSync()) as Map);

  @override
  Future<Map<String, dynamic>> tarama({
    required double sermaye, bool sadeceSinyal = false,
    String evren = 'bist100', double riskYuzde = 1.5,
    double azamiPozisyon = 35, int adet = 40,
  }) async =>
      _oku('tarama_veri.json');

  Map<String, dynamic> _ikili(String ad) => Map<String, dynamic>.from(
      (_oku('karne_risk_veri.json')[ad]) as Map);

  Map<String, dynamic> _t(String ad) =>
      Map<String, dynamic>.from(_oku('tum_veri.json')[ad] as Map);

  @override
  Future<Map<String, dynamic>> makro({bool grafik = false}) async => _t('makro');

  @override
  Future<Map<String, dynamic>> gununDersi(
          {int portfoyAdet = 0, List<String> okunan = const []}) async =>
      _t('gunders');

  @override
  Future<Map<String, dynamic>> egitmenCanli(
          {required double sermaye, int azami = 2,
          List<Pozisyon> pozisyonlar = const []}) async =>
      _t('canli');

  @override
  Future<Map<String, dynamic>> tezAnlik(String sembol,
          {double sermaye = 1000}) async =>
      _t('tezanlik');

  @override
  Future<Map<String, dynamic>> alimKontrol({
    required String sembol, required int adet, required double fiyat,
    required double sermaye, required bool tezVarMi,
    required List<Pozisyon> acik,
    List<Map<String, dynamic>> gecmis = const [],
  }) async =>
      _t('alim');

  @override
  Future<Map<String, dynamic>> sektor() async => _t('sektor');

  @override
  Future<List<dynamic>> ogrenListe() async =>
      (_t('ogren')['konular'] ?? []) as List<dynamic>;

  @override
  Future<Map<String, dynamic>> ogrenKonu(String konu) async => _t('ogrenkonu');

  @override
  Future<Map<String, dynamic>> egitmenMufredat() async => _t('mufredat');

  @override
  Future<Map<String, dynamic>> egitmenSorular() async => _t('sorular');

  @override
  Future<Map<String, dynamic>> dersGorseli(String kod) async => _t('gorsel');

  @override
  Future<Map<String, dynamic>> hisse(String sembol,
          {required double sermaye, bool grafik = true}) async =>
      _t('hisse');

  @override
  Future<Map<String, dynamic>> yapi(String sembol) async => _t('yapi');

  @override
  Future<Map<String, dynamic>> sirket(String sembol,
          {bool sektorKiyas = true}) async =>
      _t('sirket');

  @override
  Future<Map<String, dynamic>> egitmenSirketOku(String sembol) async =>
      _t('sirketoku');

  Map<String, dynamic> _defterOzet(String ad) => Map<String, dynamic>.from(
      (_oku('defter_ozet_veri.json')[ad]) as Map);

  @override
  Future<Map<String, dynamic>> defter() async => _defterOzet('defter');

  @override
  Future<Map<String, dynamic>> gunlukOzet({String? tarih}) async =>
      _defterOzet('ozet');

  @override
  Future<Map<String, dynamic>> gunlukHaberler({int azami = 25}) async =>
      const {'haberler': []};

  @override
  Future<List<dynamic>> tezSorulari() async => const [
        {'anahtar': 'neden_sirket', 'soru': 'Neden BU şirket?'},
        {'anahtar': 'neden_fiyat', 'soru': 'Neden BU fiyat?'},
        {'anahtar': 'hakli_kosul', 'soru': 'Hangi durumda haklı çıkacaksın?'},
        {'anahtar': 'yanilma_kosulu', 'soru': 'Hangi durumda yanıldığını kabul edeceksin?'},
        {'anahtar': 'hedef', 'soru': 'Hedefin ne?'},
        {'anahtar': 'sure', 'soru': 'Yatırım süren ne kadar?'},
        {'anahtar': 'alternatif', 'soru': 'Mevduata konsa ne olurdu?'},
        {'anahtar': 'en_buyuk_risk', 'soru': 'En büyük risk ne?'},
      ];

  @override
  Future<Map<String, dynamic>> gunlukKarne() async => _ikili('karne');

  @override
  Future<Map<String, dynamic>> risk({required double sermaye}) async =>
      _ikili('risk');

  @override
  Future<Map<String, dynamic>> alistirmaGorevler() async => {
        'surum': 1,
        'baslangic_bakiye': 10000.0,
        'gorevler': [
          {
            'kod': 'g03', 'tur': 'sayi',
            'baslik': 'Stop: nereden çıkacağını önceden söylemek',
            'amac': 'Stopu duyguya değil oynaklığa göre koymak.',
            'anlatim': 'STOP, "buraya gelirse yanıldığımı kabul ediyorum" '
                'dediğin fiyat. Alımdan ÖNCE konur, çünkü sonra konamaz: '
                'fiyat düşerken her seviye "biraz daha bekleyeyim" gibi '
                'görünür.\n\nNereye konur? Hissenin NORMAL GÜNLÜK '
                'DALGALANMASININ DIŞINA. Bunu ölçen sayı ATR.',
            'soru': 'GESAN 92,20 ₺\'den aldın. ATR 3,70 ₺. Stopu 2 ATR '
                'altına koyarsan kaç lira olur?',
            'dogru': 84.80, 'tolerans': 0.10, 'birim': '₺',
            'ipucu': 'giriş − (2 × ATR)',
            'aciklama': '92,20 − 7,40 = 84,80 ₺.',
            'ders': 'd805', 'secenekler': [],
          },
        ],
      };

  @override
  Future<Map<String, dynamic>> portfoyKontrol(
          List<Pozisyon> pozlar, double sermaye) async =>
      Map<String, dynamic>.from(_oku('portfoy_veri.json')['portfoy'] as Map);

  @override
  Future<Map<String, dynamic>> riskPortfoy(List<Pozisyon> pozlar) async =>
      Map<String, dynamic>.from(_oku('portfoy_veri.json')['risk'] as Map);
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await _fontuYukle();
  });

  testWidgets('bilesen galerisi', (t) async {
    await t.binding.setSurfaceSize(const Size(420, 940));
    await t.pumpWidget(_sarmala(
      Scaffold(
        appBar: AppBar(
          title: const Text('MIDAS ANALIST'),
          actions: [
            IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: () {}),
          ],
        ),
        body: ListView(
          children: [
            const Baslik('Portföy', alt: 'Açık pozisyonlar ve nakit'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Kutu(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('1.437,50 ₺',
                        style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.w700,
                            color: Renk.metin)),
                    const SizedBox(height: 12),
                    const Divider(),
                    const Satir('Nakit', '312,50 ₺'),
                    const Satir('Piyasada', '1.125,00 ₺'),
                    Satir('Kâr', '+137,50 ₺',
                        renk: Renk.arti, kalin: true),
                    Satir('Zarardaki', '-42,10 ₺', renk: Renk.eksi),
                  ],
                ),
              ),
            ),
            const Baslik('Skor göstergesi'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Kutu(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: const [
                    SkorHalka(78, alt: 'THYAO'),
                    SkorHalka(56, alt: 'GARAN'),
                    SkorHalka(31, alt: 'EUREN'),
                  ],
                ),
              ),
            ),
            const Baslik('Rozetler ve düğmeler'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Kutu(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: const [
                        Rozet('kirilim'),
                        Rozet('trend', dolu: true),
                        Rozet('alınabilir', renk: Renk.arti),
                        Rozet('stop yakın', renk: Renk.eksi),
                        Rozet('tez yok', renk: Renk.uyari),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        FilledButton(
                            onPressed: () {}, child: const Text('ALIM KAYDET')),
                        const SizedBox(width: 8),
                        OutlinedButton(
                            onPressed: () {}, child: const Text('VAZGEÇ')),
                      ],
                    ),
                    const SizedBox(height: 14),
                    const TextField(
                      decoration: InputDecoration(
                          labelText: 'Adet', hintText: 'kaç lot'),
                    ),
                  ],
                ),
              ),
            ),
            const Baslik('Uyarı kutuları'),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                children: [
                  Not('Stop garantili değildir: hisse stop seviyesinin altında '
                      'açılabilir.',
                      baslik: 'kritik',
                      ikon: Icons.warning_amber_sharp,
                      renk: Renk.eksi),
                  SizedBox(height: 8),
                  Not('Veri ~15 dakika gecikmeli. Gün sonu kararı için uygun.'),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Yukleniyor(mesaj: 'Veri çekiliyor...'),
            const SizedBox(height: 24),
          ],
        ),
      ),
    ));
    await t.pump(const Duration(milliseconds: 120));
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('gorunum/bilesenler.png'),
    );
  });

  testWidgets('bos ve hata durumlari', (t) async {
    await t.binding.setSurfaceSize(const Size(420, 560));
    await t.pumpWidget(_sarmala(
      Scaffold(
        appBar: AppBar(title: const Text('TARAMA')),
        body: Column(
          children: [
            const Expanded(
              child: Bos(Icons.radar_sharp, 'Bugün sinyal yok',
                  alt: 'Filtreleri gevşetmek yerine beklemek genelde doğrudur.'),
            ),
            const Divider(),
            Expanded(
              child: HataGorunum(
                Exception('x'),
                tekrar: () {},
              ),
            ),
          ],
        ),
      ),
    ));
    await t.pump();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('gorunum/durumlar.png'),
    );
  });

  testWidgets('sermaye defteri', (t) async {
    // Otomatik tohum kaydı (Ayarlar.sermaye=1000) devreye girmesin diye
    // deftere hazır bir kayıt koyup öyle yüklüyoruz.
    SharedPreferences.setMockInitialValues({
      'para_hareketleri_v1':
          '[{"tarih":"2026-06-01","tutar":0,"tur":"duzeltme","not":""}]',
    });
    await depo.yukle();
    await depo.paraEkle(const ParaHareketi(
        tarih: '2026-06-01', tutar: 1000, tur: HareketTur.yatirma,
        not: 'ilk yatırım'));
    await depo.paraEkle(const ParaHareketi(
        tarih: '2026-07-14', tutar: 137.5, tur: HareketTur.kar,
        not: 'THYAO 3 adet · 300,00 → 345,83'));
    await depo.paraEkle(const ParaHareketi(
        tarih: '2026-07-28', tutar: -62.3, tur: HareketTur.zarar,
        not: 'EUREN 40 adet · 4,10 → 2,54'));
    await depo.paraEkle(const ParaHareketi(
        tarih: '2026-08-20', tutar: 500, tur: HareketTur.yatirma,
        not: 'maaştan ayırdım'));

    await t.binding.setSurfaceSize(const Size(420, 1180));
    await t.pumpWidget(_sarmala(const SermayeEkran()));
    await t.pump(const Duration(milliseconds: 100));
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('gorunum/sermaye.png'),
    );
  });

  // ── sonradan eklenen ekranlar ────────────────────────────────────────────
  // Üçü de tek başına çizilebiliyor: sözlük önbellekten okuyor, hesap ve
  // kilit ağ istemiyor. Ağ mocklamadan gerçek görüntü almanın yolu bu.

  testWidgets('sozluk', (t) async {
    SharedPreferences.setMockInitialValues({
      'sozluk_v1': '''
{"surum":1,"toplam_terim":3,"bolumler":[
 {"kod":"stratejiler","ad":"Stratejiler",
  "aciklama":"Sistemin tanıdığı üç giriş kalıbı. Üçü de t günü kapanışında sinyal üretir.",
  "terimler":[
   {"terim":"kirilim","kisa":"20 günlük zirvenin hacimle kırılması (breakout).",
    "aciklama":"Kapanış son 20 günün en yükseğinin üstüne çıktığında, ama yalnızca hacim son 20 günün ortalamasının 1,4 katından fazlaysa girer.",
    "nerede":"Tarama ekranında sinyal sütununda.","ders":"d1308","kolonlar":[]},
   {"terim":"tepki","kisa":"Yükseliş trendi içindeki aşırı satım tepkisi.",
    "aciklama":"","nerede":"","ders":"d704","kolonlar":[]}]},
 {"kod":"gostergeler","ad":"Göstergeler",
  "aciklama":"Tarama ve hisse ekranlarındaki sütunlar.",
  "terimler":[
   {"terim":"Göreli güç (GG)","kisa":"Hissenin endeksten ne kadar iyi performans gösterdiği.",
    "aciklama":"GG60 = hissenin 60 günlük getirisi eksi XU100'ün 60 günlük getirisi.",
    "nerede":"Taramada GG60 sütunu.","ders":"d903","kolonlar":["GG20","GG60"]}]}]}
''',
    });
    await depo.yukle();
    await t.binding.setSurfaceSize(const Size(420, 1000));
    await t.pumpWidget(_sarmala(const SozlukEkran()));
    await t.pump(const Duration(milliseconds: 200));
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/sozluk.png'));
  });

  testWidgets('hesap girisi', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await t.binding.setSurfaceSize(const Size(420, 820));
    await t.pumpWidget(_sarmala(const HesapEkran()));
    await t.pump(const Duration(milliseconds: 100));
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/hesap.png'));
  });

  testWidgets('pin ekrani', (t) async {
    SharedPreferences.setMockInitialValues({});
    await kilit.yukle();
    await t.binding.setSurfaceSize(const Size(420, 900));
    await t.pumpWidget(_sarmala(KilitEkran(acilinca: () {})));
    await t.pump(const Duration(milliseconds: 100));
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/kilit.png'));
  });

  // ── ana ekranlar ─────────────────────────────────────────────────────────
  // En çok bakılan iki ekran ve ikisi de ağ verisiyle çiziliyor. Depo'daki
  // apiUretici kancası olmadan gözle doğrulanamıyorlardı.

  testWidgets('tarama', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);

    await t.binding.setSurfaceSize(const Size(420, 1500));
    await t.pumpWidget(_sarmala(const TaramaEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/tarama.png'));
  });

  testWidgets('portfoy', (t) async {
    SharedPreferences.setMockInitialValues({
      'pozisyonlar_v1':
          '[{"sembol":"GESAN","adet":3,"giris":84.5,"stop":78.2,'
          '"hedef":101.4,"tarih":"2026-08-14","strateji":"kirilim"},'
          '{"sembol":"THYAO","adet":1,"giris":312.0,"stop":296.4,'
          '"hedef":351.0,"tarih":"2026-08-20","strateji":"trend"}]',
    });
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);

    await t.binding.setSurfaceSize(const Size(420, 1400));
    await t.pumpWidget(_sarmala(const PortfoyEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/portfoy.png'));
  });

  // ── hiç bakılmamış ekranlar ──────────────────────────────────────────────

  testWidgets('tezler', (t) async {
    SharedPreferences.setMockInitialValues({
      'tezler_v1': '''
[{"sembol":"GESAN","tarih":"2026-08-14","fiyat":84.5,"adet":3,
  "cevaplar":{"neden_sirket":"Elektrik taahhüt; enerji yatırımları hızlanıyor",
    "neden_fiyat":"20 günlük zirveyi hacimle kırdı, FD/FAVÖK sektör medyanının altında",
    "hakli_kosul":"3 çeyrek üst üste FAVÖK marjı %12 üstünde kalırsa",
    "yanilma_kosulu":"78,20 altında kapanış ya da yeni ihale iptali",
    "hedef":"110,70 (3,5 ATR)","sure":"20 gün",
    "alternatif":"Mevduat %45; bu işlem 2,5 ödül/risk sunuyor",
    "en_buyuk_risk":"Proje bazlı gelir; tek ihale kaybı çeyreği bozar"},
  "anlik":{"skor":73.3,"rsi":68.6},"kapanis":null},
 {"sembol":"THYAO","tarih":"2026-08-20","fiyat":312.0,"adet":1,
  "cevaplar":{"neden_sirket":"Havacılık, kapasite artışı",
    "neden_fiyat":"EMA20'ye geri çekildi"},
  "anlik":{"skor":61.0},"kapanis":null},
 {"sembol":"EUREN","tarih":"2026-07-02","fiyat":41.0,"adet":8,
  "cevaplar":{"neden_sirket":"Kimya","yanilma_kosulu":"RSI2 70 üstü"},
  "anlik":{"skor":58.0},
  "kapanis":{"fiyat":38.2,"tarih":"2026-07-19","getiri_yuzde":-6.8,
    "sebep":"stop","ders":"Tez zayıftı: neden BU fiyat sorusunu atlamışım"}}]''',
    });
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1200));
    await t.pumpWidget(_sarmala(const TezlerEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/tezler.png'));
  });

  testWidgets('karne', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1900));
    await t.pumpWidget(_sarmala(const KarneEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/karne.png'));
  });

  testWidgets('risk', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1600));
    await t.pumpWidget(_sarmala(const RiskEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/risk.png'));
  });

  testWidgets('ayarlar', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await t.binding.setSurfaceSize(const Size(420, 1400));
    await t.pumpWidget(_sarmala(const AyarlarEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/ayarlar.png'));
  });

  testWidgets('defter', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1500));
    await t.pumpWidget(_sarmala(const DefterEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/defter.png'));
  });

  testWidgets('gun ozeti', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1800));
    await t.pumpWidget(_sarmala(const GunOzetiEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/gun_ozeti.png'));
  });

  testWidgets('makro', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1600));
    await t.pumpWidget(_sarmala(const MakroEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/makro.png'));
  });

  testWidgets('sektor', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1200));
    await t.pumpWidget(_sarmala(const SektorEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/sektor.png'));
  });

  testWidgets('ogren', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 900));
    await t.pumpWidget(_sarmala(const OgrenEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/ogren.png'));
  });

  testWidgets('mufredat', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1400));
    await t.pumpWidget(_sarmala(const MufredatEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/mufredat.png'));
  });

  testWidgets('ders', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await egitmen.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 2200));
    await t.pumpWidget(_sarmala(const DersEkran('d101')));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/ders.png'));
  });

  testWidgets('hisse', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 2000));
    await t.pumpWidget(_sarmala(const HisseEkran('THYAO')));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/hisse.png'));
  });

  testWidgets('sirket_oku', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1400));
    await t.pumpWidget(_sarmala(const SirketOkuEkran('THYAO')));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/sirket_oku.png'));
  });

  testWidgets('bugun', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1900));
    await t.pumpWidget(_sarmala(const BugunEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/bugun.png'));
  });

  testWidgets('ogret', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await egitmen.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1600));
    await t.pumpWidget(_sarmala(const OgretEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/ogret.png'));
  });

  testWidgets('ilerleme', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await egitmen.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1900));
    await t.pumpWidget(_sarmala(const IlerlemeEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/ilerleme.png'));
  });

  testWidgets('alim', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1600));
    await t.pumpWidget(_sarmala(const AlimEkran('GESAN', baslangicFiyat: 92.2)));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/alim.png'));
  });

  testWidgets('tez_yaz', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);
    await t.binding.setSurfaceSize(const Size(420, 1400));
    await t.pumpWidget(_sarmala(const TezYazEkran('GESAN', fiyat: 92.2)));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/tez_yaz.png'));
  });

  testWidgets('alistirma mod secimi', (t) async {
    SharedPreferences.setMockInitialValues({});
    await depo.yukle();
    await kum.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);

    await t.binding.setSurfaceSize(const Size(420, 900));
    await t.pumpWidget(_sarmala(const AlistirmaEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/alistirma_mod.png'));
  });

  testWidgets('alistirma gorev', (t) async {
    SharedPreferences.setMockInitialValues({
      'alistirma_v1':
          '{"mod":"gecmis","tarih":"2026-04-28","bakiye":10000.0,'
          '"pozisyonlar":[],"kapali":[],"gorevler":["g01","g02"]}',
    });
    await depo.yukle();
    await kum.yukle();
    Depo.apiUretici = _SahteApi.new;
    addTearDown(() => Depo.apiUretici = null);

    await t.binding.setSurfaceSize(const Size(420, 1500));
    await t.pumpWidget(_sarmala(const AlistirmaEkran()));
    await t.pumpAndSettle();
    await expectLater(find.byType(MaterialApp),
        matchesGoldenFile('gorunum/alistirma_gorev.png'));
  });
}
