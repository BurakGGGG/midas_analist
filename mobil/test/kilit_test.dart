// Uygulama kilidi — CİHAZ ve AĞ GEREKTİRMEZ.
//
// Kilidin sessizce bozulabileceği üç yer var ve üçü de burada kilitli:
//   · PIN düz saklanırsa, cihaz verisini gören herkes okur
//   · Deneme sayacı bellekte tutulursa, uygulamayı öldürmek sıfırlar ve
//     kaba kuvvet sınırı hiç devreye girmez
//   · Bekleme süresi diske yazılmazsa aynı şey
//
// Çalıştır:  flutter test
import 'package:flutter_test/flutter_test.dart';
import 'package:midas_analist/servis/kilit.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  group('PIN biçimi', () {
    test('tam 6 hane kabul edilir', () {
      expect(Kilit.gecerliMi('123456'), isTrue);
      expect(Kilit.gecerliMi('000000'), isTrue);
    });

    test('kısa, uzun ve rakam olmayan reddedilir', () {
      for (final p in ['', '1', '12345', '1234567', 'abcdef', '12345a', '12 456']) {
        expect(Kilit.gecerliMi(p), isFalse, reason: p);
      }
    });

    test('geçersiz PIN kurulamaz', () async {
      final k = Kilit();
      expect(() => k.kur('123'), throwsArgumentError);
    });
  });

  group('kurma ve doğrulama', () {
    test('doğru PIN açar, yanlış açmaz', () async {
      final k = Kilit();
      await k.kur('428913');
      expect(k.kuruldu, isTrue);
      expect(await k.dogrula('000000'), isFalse);
      expect(await k.dogrula('428913'), isTrue);
      expect(k.kilitli, isFalse);
    });

    test('PIN düz metin olarak saklanmaz', () async {
      final k = Kilit();
      await k.kur('428913');
      final p = await SharedPreferences.getInstance();
      final hepsi = p.getKeys().map((x) => '${p.get(x)}').join(' ');
      expect(hepsi.contains('428913'), isFalse);
    });

    test('aynı PIN farklı cihazda farklı özet üretir (tuz)', () async {
      final a = Kilit();
      await a.kur('428913');
      final ozetA = (await SharedPreferences.getInstance())
          .getString('kilit_ozet_v1');

      SharedPreferences.setMockInitialValues({});
      final b = Kilit();
      await b.kur('428913');
      final ozetB = (await SharedPreferences.getInstance())
          .getString('kilit_ozet_v1');

      expect(ozetA, isNotNull);
      expect(ozetA, isNot(equals(ozetB)));
    });

    test('kurulu değilken doğrulama başarısız', () async {
      expect(await Kilit().dogrula('428913'), isFalse);
    });
  });

  group('kaba kuvvet sınırı', () {
    test('5 yanlış denemeden sonra bekleme başlar', () async {
      final k = Kilit();
      await k.kur('428913');
      for (var i = 0; i < 5; i++) {
        expect(await k.dogrula('000000'), isFalse);
      }
      expect(k.bekleme, greaterThan(0));
      // Bekleme sürerken DOĞRU PIN bile geçmemeli.
      expect(await k.dogrula('428913'), isFalse);
    });

    test('sayaç diskte tutulur — uygulamayı öldürmek sıfırlamaz', () async {
      final k = Kilit();
      await k.kur('428913');
      for (var i = 0; i < 5; i++) {
        await k.dogrula('000000');
      }
      // Yeni örnek = uygulama yeniden başlatıldı.
      final yeni = Kilit();
      await yeni.yukle();
      expect(yeni.deneme, 5);
      expect(yeni.bekleme, greaterThan(0));
    });

    test('doğru PIN sayacı sıfırlar', () async {
      final k = Kilit();
      await k.kur('428913');
      for (var i = 0; i < 3; i++) {
        await k.dogrula('000000');
      }
      expect(k.deneme, 3);
      expect(await k.dogrula('428913'), isTrue);
      expect(k.deneme, 0);
      expect(k.bekleme, 0);
    });

    test('bekleme süresi denemeyle birlikte uzar', () async {
      final k = Kilit();
      await k.kur('428913');
      for (var i = 0; i < 5; i++) {
        await k.dogrula('000000');
      }
      final besinci = k.bekleme;          // beklenen ~30 sn

      // Bekleme bitmiş gibi yap: süreyi geçmişe çek, sonra bir yanlış daha.
      final p = await SharedPreferences.getInstance();
      await p.setString('kilit_beklet_v1',
          DateTime.now().subtract(const Duration(seconds: 1)).toIso8601String());
      await k.yukle();
      // yukle() kilitli'yi geri kaldırır; doğrulama yine denenebilir olmalı.
      expect(k.bekleme, 0);

      await k.dogrula('000000');          // 6. yanlış
      expect(k.deneme, 6);
      expect(k.bekleme, greaterThan(besinci),
          reason: '6. denemede bekleme 5.den uzun olmalı');
    });
  });

  group('yaşam döngüsü', () {
    test('kurulu kilit varsa uygulama kilitli açılır', () async {
      final k = Kilit();
      await k.kur('428913');
      final yeni = Kilit();
      await yeni.yukle();
      expect(yeni.kuruldu, isTrue);
      expect(yeni.kilitli, isTrue);
    });

    test('kilit kurulu değilse açılışta kilitli değil', () async {
      final k = Kilit();
      await k.yukle();
      expect(k.kuruldu, isFalse);
      expect(k.kilitli, isFalse);
    });

    test('kısa arka plan kilitlemez', () async {
      final k = Kilit();
      await k.kur('428913');
      k.arkaPlanaGitti();
      k.oneCikti();
      expect(k.kilitli, isFalse);
    });

    test('kilitle() kurulu değilken bir şey yapmaz', () async {
      final k = Kilit();
      k.kilitle();
      expect(k.kilitli, isFalse);
    });
  });

  group('kaldırma', () {
    test('doğru PIN ile kaldırılır', () async {
      final k = Kilit();
      await k.kur('428913');
      expect(await k.kaldir('000000'), isFalse);
      expect(await k.kaldir('428913'), isTrue);
      expect(k.kuruldu, isFalse);
    });

    test('zorlaKaldir izleri siler', () async {
      final k = Kilit();
      await k.kur('428913');
      await k.zorlaKaldir();
      final p = await SharedPreferences.getInstance();
      expect(p.getString('kilit_ozet_v1'), isNull);
      expect(p.getString('kilit_tuz_v1'), isNull);
      expect(k.kuruldu, isFalse);
    });
  });
}
