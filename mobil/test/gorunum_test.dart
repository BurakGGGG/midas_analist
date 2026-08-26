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
import 'package:midas_analist/ekran/sermaye.dart';
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
}
