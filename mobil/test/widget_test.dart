import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:midas_analist/tema.dart';
import 'package:midas_analist/servis/modeller.dart';

void main() {
  group('Sayı biçimleme', () {
    test('tl() Türkçe ayraçları kullanır', () {
      expect(tl(1234.5), '1.234,50');
      expect(tl(0), '0,00');
      expect(tl(-99.9), '-99,90');
      expect(tl(null), '—');
      expect(tl(1000000, basamak: 0), '1.000.000');
    });

    test('yzd() işareti doğru koyar', () {
      expect(yzd(5.25), '+5,25%');
      expect(yzd(-3.1, basamak: 1), '-3,1%');
      expect(yzd(0), '0,00%');
      expect(yzd(12.0, isaret: false), '12,00%');
    });

    test('buyukTl() büyük sayıları kısaltır', () {
      expect(buyukTl(2500000000), '2,5 mlr');
      expect(buyukTl(412000000), '412,0 mn');
      expect(buyukTl(1500), '2 b');
    });
  });

  // Bu grup tasarım kurallarını KİLİTLER. Biri ileride yuvarlak köşe ya da
  // ikinci bir tema eklerse test düşsün istiyoruz — yorum satırı unutulur,
  // test unutulmaz.
  group('Piksel tema kuralları', () {
    test('yalnızca koyu tema var ve yüzeyler tanımlı', () {
      expect(temaKoyu.brightness, Brightness.dark);
      expect(temaKoyu.colorScheme.brightness, Brightness.dark);
      expect(temaKoyu.scaffoldBackgroundColor, Renk.zemin);
      expect(temaKoyu.colorScheme.onSurface, Renk.metin);
    });

    test('hiçbir bileşende yuvarlak köşe yok', () {
      double enBuyukYaricap(ShapeBorder? s) {
        if (s is RoundedRectangleBorder) {
          final b = s.borderRadius.resolve(TextDirection.ltr);
          return [b.topLeft.x, b.topRight.x, b.bottomLeft.x, b.bottomRight.x]
              .reduce((a, c) => a > c ? a : c);
        }
        return 0;
      }

      expect(kose, BorderRadius.zero);
      expect(enBuyukYaricap(temaKoyu.cardTheme.shape), 0);
      expect(enBuyukYaricap(temaKoyu.chipTheme.shape), 0);
      expect(enBuyukYaricap(temaKoyu.dialogTheme.shape), 0);
      expect(enBuyukYaricap(temaKoyu.snackBarTheme.shape), 0);
      expect(enBuyukYaricap(temaKoyu.bottomSheetTheme.shape), 0);
      expect(enBuyukYaricap(temaKoyu.navigationBarTheme.indicatorShape), 0);
    });

    test('gölge yok, tek sabit genişlikli font var', () {
      expect(temaKoyu.cardTheme.elevation, 0);
      expect(temaKoyu.appBarTheme.elevation, 0);
      expect(temaKoyu.textTheme.bodyMedium?.fontFamily, 'Piksel');
      expect(temaKoyu.appBarTheme.titleTextStyle?.fontFamily, 'Piksel');
    });

    test('aksan rengi piyasa yeşiliyle karışmaz', () {
      // Aksan ile "artı" aynı renk olursa kullanıcı vurguyu kazanç sanır.
      expect(Renk.aksan, isNot(Renk.arti));
    });

    test('blokCubuk() oranı bloklara çevirir', () {
      expect(blokCubuk(0, genislik: 4), '░░░░');
      expect(blokCubuk(1, genislik: 4), '████');
      expect(blokCubuk(0.5, genislik: 4), '██░░');
      expect(blokCubuk(null, genislik: 3), '···');
      expect(blokCubuk(9, genislik: 4), '████'); // taşma kırpılır
    });
  });

  // Defterin tek amacı yatırdığın parayı kazandığından ayırmak.
  // Bu ayrım bozulursa kullanıcı para eklediğinde "kâr ettim" sanır.
  group('Sermaye defteri', () {
    ParaHareketi h(double t, HareketTur tur) =>
        ParaHareketi(tarih: '2026-08-25', tutar: t, tur: tur);

    test('yalnızca yatırma/çekme sermaye girişi sayılır', () {
      expect(h(100, HareketTur.yatirma).sermayeGirisi, isTrue);
      expect(h(-50, HareketTur.cekme).sermayeGirisi, isTrue);
      expect(h(30, HareketTur.kar).sermayeGirisi, isFalse);
      expect(h(-20, HareketTur.zarar).sermayeGirisi, isFalse);
      expect(h(5, HareketTur.duzeltme).sermayeGirisi, isFalse);
    });

    test('para eklemek getiriyi şişirmez', () {
      final defter = [
        h(1000, HareketTur.yatirma),
        h(200, HareketTur.kar),
        h(500, HareketTur.yatirma), // sonradan eklenen para
      ];
      final toplam = defter.fold(0.0, (a, x) => a + x.tutar);
      final yatirilan = defter
          .where((x) => x.sermayeGirisi)
          .fold(0.0, (a, x) => a + x.tutar);
      expect(toplam, 1700);
      expect(yatirilan, 1500);
      // Kâr 200; toplam 1700 olsa da getiri 200/1500 olmalı, 700/1000 değil.
      expect(toplam - yatirilan, 200);
    });

    test('JSON gidiş-dönüşü türü korur', () {
      final k = ParaHareketi(
          tarih: '2026-08-25',
          tutar: -75.5,
          tur: HareketTur.cekme,
          not: 'kira');
      final geri = ParaHareketi.fromJson(k.toJson());
      expect(geri.tutar, -75.5);
      expect(geri.tur, HareketTur.cekme);
      expect(geri.not, 'kira');
    });

    test('bilinmeyen tür düzeltmeye düşer, çökmez', () {
      final geri = ParaHareketi.fromJson(
          {'tarih': '2026-01-01', 'tutar': 10, 'tur': 'uyduruk'});
      expect(geri.tur, HareketTur.duzeltme);
    });
  });

  testWidgets('Tema gerçek bir ekranda çalışır', (t) async {
    await t.pumpWidget(MaterialApp(
      theme: temaKoyu,
      home: Builder(
        builder: (c) =>
            Scaffold(body: Text('x', style: TextStyle(color: Sem(c).arti))),
      ),
    ));
    expect(find.text('x'), findsOneWidget);
  });
}
