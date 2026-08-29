import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:midas_analist/servis/semboller.dart';

/// Python'un `cekirdek/semboller.py` dosyasındaki kurallar burada
/// yeniden yazıldı. İkisi ayrışırsa aynı sorgu iki yerde farklı sonuç
/// verir — ve bu ancak "neden İŞ BANKASI çıkmıyor" şikâyetiyle görünür.
///
/// Bu yüzden iki taraf AYNI örneklerle sınanıyor:
///   normalize → testler/normalize_ornekleri.json (Python üretiyor)
///   sıralama  → aşağıdaki ORNEK listesi, testler/test_semboller.py ile
///               birebir aynı

final _ornek = [
  {'k': 'THYAO', 'a': 'Türk Hava Yolları', 'i': 1,
   'n': ['THYAO', 'TURK HAVA YOLLARI', 'THY']},
  {'k': 'TSKB', 'a': 'Türkiye Sınai Kalkınma Bankası', 'i': 1,
   'n': ['TSKB', 'TURKIYE SINAI KALKINMA BANKASI']},
  {'k': 'ISCTR', 'a': 'Türkiye İş Bankası', 'i': 1,
   'n': ['ISCTR', 'TURKIYE IS BANKASI']},
  {'k': 'ISATR', 'a': 'Türkiye İş Bankası', 'i': 0,
   'n': ['ISATR', 'TURKIYE IS BANKASI']},
  {'k': 'KCHOL', 'a': 'Koç Holding', 'i': 1,
   'n': ['KCHOL', 'KOC HOLDING']},
  {'k': 'KOCFN', 'a': 'Koç Finansman', 'i': 0,
   'n': ['KOCFN', 'KOC FINANSMAN']},
  {'k': 'EREGL', 'a': 'Ereğli Demir ve Çelik', 'i': 1,
   'n': ['EREGL', 'EREGLI DEMIR VE CELIK', 'ERDEMIR']},
];

SembolDeposu _depo() {
  final d = SembolDeposu();
  d.hisseler = _ornek
      .map((e) => Sembol.fromJson(Map<String, dynamic>.from(e)))
      .toList();
  return d;
}

String? _ilk(String sorgu) {
  final r = _depo().ara(sorgu, azami: 5);
  return r.isEmpty ? null : r.first.kod;
}

void main() {
  group('normalize — Python ile birebir', () {
    test('ortak örnek dosyasının HER satırı aynı çıkmalı', () {
      final dosya = File('test/veri/normalize_ornekleri.json');
      expect(dosya.existsSync(), isTrue,
          reason: 'örnek dosyası yok — Python tarafı üretiyor');
      final ornekler = jsonDecode(dosya.readAsStringSync()) as List;
      expect(ornekler.length, greaterThan(20));

      final farklar = <String>[];
      for (final o in ornekler) {
        final girdi = '${o['girdi']}';
        final beklenen = '${o['cikti']}';
        final bizim = normalize(girdi);
        if (bizim != beklenen) {
          farklar.add('"$girdi": python="$beklenen" dart="$bizim"');
        }
      }
      expect(farklar, isEmpty,
          reason: 'normalize iki dilde ayrışmış:\n${farklar.join('\n')}');
    });

    test('I/İ/ı/i dörtlüsü tek harfe iner', () {
      expect(normalize('ışık'), normalize('IŞIK'));
      expect(normalize('izmir'), normalize('İZMİR'));
      expect(normalize('İş'), 'IS');
    });

    test('boşluklar tekleşir', () {
      expect(normalize('türk   hava    yolları'), 'TURK HAVA YOLLARI');
    });
  });

  group('arama sırası — Python ile aynı kurallar', () {
    final beklenenler = {
      'thy': 'THYAO',            // kod ön eki
      'THYAO': 'THYAO',          // tam kod
      'türk hava': 'THYAO',      // ad, Türkçe karakterli
      'turk hava': 'THYAO',      // ad, sadeleştirilmiş
      'erdemir': 'EREGL',        // takma ad
      'koç': 'KCHOL',            // takip edilen, kod ön ekini yener
      'KOCFN': 'KOCFN',          // tam kod her şeyi yener
      'iş bankası': 'ISCTR',     // doğru Türkçe
      'is bankasi': 'ISCTR',     // ASCII
      'ıs bankası': 'ISCTR',     // noktasız ı
      'İŞ BANKASI': 'ISCTR',     // tümü büyük
    };
    beklenenler.forEach((sorgu, beklenen) {
      test('"$sorgu" → $beklenen', () => expect(_ilk(sorgu), beklenen));
    });

    test('takip edilen kod ön ekini YENER', () {
      final r = _depo().ara('koç').map((e) => e.kod).toList();
      expect(r.take(2).toList(), ['KCHOL', 'KOCFN']);
    });

    test('aynı unvanda takip edilen önce', () {
      final r = _depo().ara('is bankasi').map((e) => e.kod).toList();
      expect(r.indexOf('ISCTR'), lessThan(r.indexOf('ISATR')));
    });

    test('boş sorgu boş sonuç', () {
      expect(_depo().ara(''), isEmpty);
      expect(_depo().ara('   '), isEmpty);
    });

    test('eşleşmeyen sorgu boş sonuç', () {
      expect(_depo().ara('zzzqqq'), isEmpty);
    });

    test('azami sınıra uyar', () {
      expect(_depo().ara('t', azami: 2).length, lessThanOrEqualTo(2));
    });
  });
}
