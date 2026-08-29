import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:midas_analist/servis/hesap.dart';
import 'package:midas_analist/ekran/oyun_kabuk.dart';
import 'package:midas_analist/servis/oyun.dart';
import 'package:midas_analist/tema.dart';

/// Sanal İşlem oyunu — telefonda çalışan mantık.
///
/// Oyun çevrimdışı oynanıyor: çıkış kuralları, kayma ve nakit muhasebesi
/// burada. Hepsi sessizce yanlış olabilecek şeyler — bir kuruş kayıp fark
/// edilmez ama oyunun tamamını yanlış öğretir.

OyunBar _bar(double a, double y, double d, double k) => OyunBar(a, y, d, k, 1000);

OyunPozisyon _poz({double stop = 95, double hedef = 110, int adet = 10,
        double giris = 100}) =>
    OyunPozisyon(sembol: 'X', adet: adet, giris: giris, stop: stop,
        hedef: hedef, acilisGunu: 0);

/// Elde piyasa varmış gibi kurar — ağ yok.
Oyun _oyunKur({double sermaye = 10000, double kaymaBp = 0,
    List<List<double>>? barlar}) {
  final o = Oyun();
  final b = barlar ??
      List.generate(20, (i) => [100.0, 101.0, 99.0, 100.0 + i.toDouble()]);
  o.hisseler = [
    OyunHisse(
      kod: 'X', ad: 'Test A.Ş.', sektor: 'Sanayi',
      barlar: b.map((x) => OyunBar(x[0], x[1], x[2], x[3], 1000)).toList(),
    ),
  ];
  o.isinma = 0;
  o.gunSayisi = b.length;
  o.kaymaBp = kaymaBp;
  o.tohum = 1;
  o.zorluk = 'normal';
  o.gun = 0;
  o.nakit = sermaye;
  o.baslangicSermaye = sermaye;
  o.ozkaynak = [sermaye];
  return o;
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  // ── çıkış kuralları: Python ile birebir ─────────────────────────────────

  group('çıkış kuralları', () {
    test('ORTAK ÖRNEK DOSYASININ her satırı aynı çıkmalı', () {
      // cekirdek/alistirma.py `cikis_kontrol` burada Dart'ta yeniden
      // yazıldı (çevrimdışı çalışması gerekiyor). İkisi ayrışırsa oyun
      // stopu backtest'ten farklı işletir ve kullanıcı yanlış şey öğrenir.
      final dosya = File('test/veri/cikis_ornekleri.json');
      expect(dosya.existsSync(), isTrue,
          reason: 'örnek dosyası yok — Python tarafı üretiyor');
      final ornekler = jsonDecode(dosya.readAsStringSync()) as List;
      expect(ornekler.length, greaterThanOrEqualTo(10));

      final farklar = <String>[];
      for (final o in ornekler) {
        final p = OyunPozisyon(
            sembol: 'X', adet: 1, giris: 100,
            stop: (o['stop'] as num).toDouble(),
            hedef: (o['hedef'] as num).toDouble(), acilisGunu: 0);
        final b = _bar((o['acilis'] as num).toDouble(),
            (o['yuksek'] as num).toDouble(),
            (o['dusuk'] as num).toDouble(),
            (o['kapanis'] as num).toDouble());
        final c = cikisKontrol(p, b);
        final sebep = c?.sebep ?? '';
        final fiyat = c?.fiyat ?? 0.0;
        if (sebep != '${o['sebep']}' ||
            (fiyat - (o['fiyat'] as num).toDouble()).abs() > 1e-6) {
          farklar.add('${o['ad']}: python=${o['sebep']}/${o['fiyat']} '
              'dart=$sebep/$fiyat');
        }
      }
      expect(farklar, isEmpty,
          reason: 'çıkış kuralı iki dilde ayrışmış:\n${farklar.join('\n')}');
    });

    test('aynı gün ikisi de görüldüyse STOP', () {
      final c = cikisKontrol(_poz(), _bar(100, 112, 94, 105));
      expect(c?.sebep, 'stop');
    });

    test('boşluklu açılışta AÇILIŞTAN çıkar', () {
      final c = cikisKontrol(_poz(), _bar(88, 92, 86, 90));
      expect(c?.fiyat, 88);
    });

    test('hedefin üstünde açış HEDEFTEN çıkar', () {
      final c = cikisKontrol(_poz(), _bar(115, 118, 114, 117));
      expect(c?.fiyat, 110);
    });
  });

  // ── alım / satım ────────────────────────────────────────────────────────

  group('alım', () {
    test('nakitten maliyet düşülür', () {
      final o = _oyunKur();
      expect(o.al('X', 10, 90, 130), isNull);
      expect(o.nakit, 10000 - 10 * 100);
      expect(o.pozisyonlar.single.adet, 10);
    });

    test('kayma alışta YUKARI', () {
      final o = _oyunKur(kaymaBp: 100);   // %1
      o.al('X', 1, 90, 130);
      expect(o.pozisyonlar.single.giris, closeTo(101, 0.001));
    });

    test('nakit yetmezse alınamaz ve durum değişmez', () {
      final o = _oyunKur(sermaye: 500);
      final h = o.al('X', 10, 90, 130);
      expect(h, contains('Nakit yetmiyor'));
      expect(o.nakit, 500);
      expect(o.pozisyonlar, isEmpty);
    });

    test('stop girişin üstündeyse reddedilir', () {
      final o = _oyunKur();
      expect(o.al('X', 1, 150, 200), isNotNull);
    });

    test('EKLEME ortalama maliyet yapar', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100], [200, 201, 199, 200], [200, 201, 199, 200],
      ]);
      // Hedef bilerek çok uzakta: 130 olsaydı ikinci günün yükseğinde
      // pozisyon kapanır ve ekleme hiç denenmemiş olurdu.
      o.al('X', 2, 90, 900);           // 2 × 100
      o.ilerlet();                      // fiyat 200'e çıktı
      o.al('X', 2, 180, 900);          // 2 × 200
      expect(o.pozisyonlar.single.adet, 4);
      expect(o.pozisyonlar.single.giris, 150.0);
    });
  });

  group('satış', () {
    test('kısmi satış kalanı bırakır', () {
      final o = _oyunKur();
      o.al('X', 10, 90, 130);
      expect(o.sat('X', adet: 4), isNull);
      expect(o.pozisyonlar.single.adet, 6);
      expect(o.kapali.single.adet, 4);
    });

    test('kayma satışta AŞAĞI', () {
      final o = _oyunKur(kaymaBp: 100);
      o.al('X', 1, 90, 130);
      o.sat('X');
      expect(o.kapali.single.cikis, closeTo(99, 0.001));
    });

    test('olmayan pozisyon satılamaz', () {
      expect(_oyunKur().sat('YOK'), 'Açık pozisyon yok.');
    });
  });

  group('stop çekme', () {
    test('yukarı serbest, aşağı YASAK', () {
      final o = _oyunKur();
      o.al('X', 1, 90, 130);
      expect(o.stopCek('X', 95), isNull);
      expect(o.pozisyonlar.single.stop, 95);
      expect(o.stopCek('X', 80), contains('YUKARI'));
      expect(o.pozisyonlar.single.stop, 95, reason: 'stop değişmemeli');
    });
  });

  // ── zaman ───────────────────────────────────────────────────────────────

  group('gün ilerletme', () {
    test('stop çalışınca pozisyon kapanır ve nakde döner', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100],
        [100, 101, 80, 85],     // stop 90'a değdi
      ]);
      o.al('X', 10, 90, 130);
      final ozet = o.ilerlet();
      expect(ozet.kapananlar.single.sebep, 'stop');
      expect(o.pozisyonlar, isEmpty);
      expect(o.nakit, closeTo(10000 - 1000 + 900, 0.001));
    });

    test('hedef çalışınca kâr yazılır', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100],
        [100, 135, 99, 132],
      ]);
      o.al('X', 10, 90, 130);
      final ozet = o.ilerlet();
      expect(ozet.kapananlar.single.sebep, 'hedef');
      expect(ozet.kapananlar.single.kar,
          closeTo((130 - 100) * 10, 0.001));
    });

    test('her gün için özkaynak noktası eklenir', () {
      final o = _oyunKur();
      o.ilerlet(adim: 5);
      expect(o.ozkaynak.length, 6, reason: 'başlangıç + 5 gün');
      expect(o.gun, 5);
    });

    test('kapanana kadar: pozisyon kapanınca durur', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100], [100, 101, 99, 100],
        [100, 101, 80, 85], [100, 101, 99, 100], [100, 101, 99, 100],
      ]);
      o.al('X', 10, 90, 130);
      o.ilerlet(adim: 0);
      expect(o.pozisyonlar, isEmpty);
      expect(o.gun, 2, reason: 'stop günü durmalı, sonuna kadar gitmemeli');
    });

    test('son güne gelince ilerlemez', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100], [100, 101, 99, 100],
      ]);
      o.ilerlet(adim: 50);
      expect(o.gun, 1);
      expect(o.bitti, isTrue);
    });

    test('oyun bittiğinde alım yapılamaz', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100], [100, 101, 99, 100],
      ]);
      o.ilerlet(adim: 5);
      expect(o.al('X', 1, 90, 130), 'Oyun bitti.');
    });
  });

  // ── değerleme ───────────────────────────────────────────────────────────

  test('toplam değer nakit artı pozisyon', () {
    final o = _oyunKur(barlar: [
      [100, 101, 99, 100], [120, 121, 119, 120],
    ]);
    o.al('X', 10, 90, 500);
    o.ilerlet();
    expect(o.pozisyonDegeri, 10 * 120);
    expect(o.toplamDeger, closeTo(9000 + 1200, 0.001));
    expect(o.getiriYuzde, closeTo(2.0, 0.001));
  });

  // ── kalıcılık ───────────────────────────────────────────────────────────

  group('kalıcılık', () {
    test('durum yazılıp geri okunur, piyasa yazılmaz', () async {
      final o = _oyunKur();
      o.al('X', 5, 90, 130);
      await Future.delayed(Duration.zero);

      final taze = Oyun();
      await taze.yukle();
      expect(taze.tohum, 1);
      expect(taze.pozisyonlar.single.sembol, 'X');
      expect(taze.piyasaHazir, isFalse,
          reason: 'piyasa diske yazılmamalı — tohumdan yeniden üretilir');
    });

    test('bozuk kayıt oyunu açılmaz yapmaz', () async {
      SharedPreferences.setMockInitialValues({Oyun.anahtar: 'json değil'});
      final o = Oyun();
      await o.yukle();
      expect(o.basladi, isFalse);
    });
  });

  test('bulut yedeği oyunu KAPSIYOR', () {
    // Tohum kaybolursa yarısına gelinen oyun bir daha açılmaz.
    expect(Hesap.yedeklenen, contains(Oyun.anahtar));
  });

  // ── limit emirleri ──────────────────────────────────────────────────────

  group('limit emri', () {
    test('nakit BLOKE ediliyor', () {
      // Bloke etmeseydik oyuncu aynı parayla beş emir verip hepsinin
      // dolmasını izlerdi.
      final o = _oyunKur();
      expect(o.emirVer('X', 10, 90, 80, 130), isNull);
      expect(o.blokeNakit, 900);
      expect(o.kullanilabilirNakit, 10000 - 900);
      expect(o.nakit, 10000, reason: 'para henüz çıkmadı, yalnızca bloke');
    });

    test('bloke edilen parayla ikinci emir verilemez', () {
      final o = _oyunKur(sermaye: 1000);
      o.emirVer('X', 10, 90, 80, 130);          // 900 bloke
      expect(o.emirVer('X', 5, 90, 80, 130), contains('Nakit yetmiyor'));
      expect(o.al('X', 5, 80, 130), contains('Nakit yetmiyor'));
    });

    test('limit fiyatı bugünkü fiyatın ÜSTÜNDE olamaz', () {
      // Üstündeyse zaten piyasa emriyle alınır; limit emri anlamsız.
      final o = _oyunKur();
      expect(o.emirVer('X', 1, 120, 80, 200), contains('altında olmalı'));
    });

    test('fiyat gelince DOLAR', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100],
        [95, 96, 88, 92],        // düşük 88 → 90 limitine değdi
      ]);
      o.emirVer('X', 10, 90, 80, 130);
      final ozet = o.ilerlet();
      expect(ozet.dolanlar.single.sembol, 'X');
      expect(o.emirler, isEmpty);
      expect(o.pozisyonlar.single.adet, 10);
      expect(o.pozisyonlar.single.giris, 90);
      expect(o.nakit, 10000 - 900);
    });

    test('boşluklu açılışta DAHA İYİ fiyattan dolar', () {
      // Emrin bekliyor, piyasa limitinin altında açtı — sen kazandın.
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100],
        [85, 90, 84, 88],        // açılış 85, limit 90
      ]);
      o.emirVer('X', 10, 90, 80, 130);
      o.ilerlet();
      expect(o.pozisyonlar.single.giris, 85);
    });

    test('limit emrinde KAYMA YOK', () {
      // Limit emrinin bütün mesele bu.
      final o = _oyunKur(kaymaBp: 100, barlar: [
        [100, 101, 99, 100],
        [95, 96, 88, 92],
      ]);
      o.emirVer('X', 1, 90, 80, 130);
      o.ilerlet();
      expect(o.pozisyonlar.single.giris, 90,
          reason: 'kayma uygulanmamalı');
    });

    test('süresi dolunca İPTAL olur ve bloke çözülür', () {
      final o = _oyunKur(barlar: List.generate(
          10, (i) => [100.0, 101.0, 99.0, 100.0]));
      o.emirVer('X', 10, 90, 80, 130, gecerlilik: 3);
      final ozet = o.ilerlet(adim: 4);
      expect(ozet.iptaller.single.sembol, 'X');
      expect(o.emirler, isEmpty);
      expect(o.blokeNakit, 0);
      expect(o.pozisyonlar, isEmpty);
    });

    test('elle iptal blokeyi çözer', () {
      final o = _oyunKur();
      o.emirVer('X', 10, 90, 80, 130);
      o.emirIptal(o.emirler.single);
      expect(o.emirler, isEmpty);
      expect(o.blokeNakit, 0);
    });

    test('emirler diske yazılır', () async {
      final o = _oyunKur();
      o.emirVer('X', 10, 90, 80, 130);
      await Future.delayed(Duration.zero);
      final taze = Oyun();
      await taze.yukle();
      expect(taze.emirler.single.fiyat, 90);
    });
  });

  // ── gün özeti ───────────────────────────────────────────────────────────

  group('gün özeti', () {
    test('hiçbir şey olmadıysa SESSİZ', () {
      // Boş bildirim gürültüdür.
      final o = _oyunKur();
      expect(o.ilerlet().sessiz, isTrue);
    });

    test('değer değişimini taşır', () {
      final o = _oyunKur(barlar: [
        [100, 101, 99, 100], [120, 121, 119, 120],
      ]);
      o.al('X', 10, 90, 500);
      final ozet = o.ilerlet();
      expect(ozet.fark, closeTo(200, 0.001));
    });
  });

  // ── karne ───────────────────────────────────────────────────────────────

  test('karne endeksle kıyaslar', () {
    // Kazanmak yetmiyor; endeksi geçmek gerekiyor.
    final o = _oyunKur(barlar: [
      [100, 101, 99, 100], [110, 111, 109, 110],
    ]);
    o.endeks = [100.0, 105.0];
    o.al('X', 50, 90, 500);
    o.ilerlet();
    final k = o.karne();
    expect(k.endeksGetiri, closeTo(5.0, 0.01));
    expect(k.getiri, greaterThan(0));
  });

  test('karne en iyi ve en kötü işlemi bulur', () {
    final o = _oyunKur();
    o.kapali = [
      const OyunIslem(sembol: 'A', adet: 1, giris: 100, cikis: 130,
          girisGunu: 0, cikisGunu: 3, sebep: 'hedef'),
      const OyunIslem(sembol: 'B', adet: 1, giris: 100, cikis: 82,
          girisGunu: 0, cikisGunu: 2, sebep: 'stop'),
    ];
    final k = o.karne();
    expect(k.enIyiKod, 'A');
    expect(k.enKotuKod, 'B');
    expect(k.kazanan, 1);
    expect(k.islem, 2);
  });

  // ── kabuk ───────────────────────────────────────────────────────────────

  group('oyun kabuğu', () {
    testWidgets('başlangıçta zorluk seçimi çıkar', (t) async {
      SharedPreferences.setMockInitialValues({});
      await oyun.yukle();
      await t.pumpWidget(MaterialApp(
          theme: temaOyun,
          home: OyunKabuk(key: UniqueKey())));
      await t.pumpAndSettle();
      expect(find.text('ZORLUK SEÇ'), findsOneWidget);
      expect(find.text('Kolay'), findsOneWidget);
      expect(find.text('Zor'), findsOneWidget);
    });

    testWidgets('oyun sürerken BEŞ sekme ve gün şeridi var', (t) async {
      SharedPreferences.setMockInitialValues({});
      await oyun.yukle();
      final o = _oyunKur();
      oyun
        ..tohum = o.tohum
        ..zorluk = 'normal'
        ..hisseler = o.hisseler
        ..isinma = 0
        ..gunSayisi = o.gunSayisi
        ..gun = 0
        ..nakit = 10000
        ..baslangicSermaye = 10000
        ..ozkaynak = [10000];

      t.view.physicalSize = const Size(1100, 2600);
      t.view.devicePixelRatio = 1.0;
      addTearDown(t.view.reset);

      await t.pumpWidget(MaterialApp(
          theme: temaOyun, home: OyunKabuk(key: UniqueKey())));
      await t.pumpAndSettle();

      for (final ad in ['Portföy', 'Borsa', 'Emirler', 'Analist',
                        'Haberler']) {
        expect(find.text(ad), findsWidgets, reason: '$ad sekmesi yok');
      }
      expect(find.text('OYUN'), findsOneWidget,
          reason: 'oyun rozeti kalıcı olmalı');
      expect(find.text('+1 GÜN'), findsOneWidget);
      expect(find.text('KAPANANA KADAR'), findsOneWidget);
    });
  });
}
