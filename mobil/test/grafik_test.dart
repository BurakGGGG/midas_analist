import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:midas_analist/parca/grafik.dart';
import 'package:midas_analist/tema.dart';

/// Grafik bileşeni — ÇÖKMEMESİ öncelikli.
///
/// Bu dosya bir çökmeden sonra yazıldı: eksen etiketi korumasında
/// `p.length < 2` yazıyordu ama `p[2]`ye erişiliyordu. İki parçalı bir
/// etiket (Sanal İşlem'in "G-45" gün numaraları) korumadan geçip
/// RangeError ile bütün ekranı düşürüyordu. Ekranda görünmeyen bir
/// eksen etiketi, çöken bir ekrandan iyidir.

Future<void> _ciz(WidgetTester t, dynamic seri) async {
  await t.pumpWidget(MaterialApp(
    theme: temaKoyu,
    home: Scaffold(body: SizedBox(height: 220, child: FiyatGrafik(seri))),
  ));
  await t.pumpAndSettle();
}

void main() {
  testWidgets('ISO tarihli seri çizilir', (t) async {
    await _ciz(t, [
      for (var i = 1; i <= 40; i++)
        {'t': '2026-08-${i.toString().padLeft(2, '0')}', 'd': 100.0 + i}
    ]);
    expect(cizimHatasi, isNull);
  });

  testWidgets('GÜN NUMARALI etiket çökertmez', (t) async {
    // Sanal İşlem böyle etiket veriyor: takvim tarihi yok, gün numarası var.
    await _ciz(t, [
      for (var i = -45; i <= 20; i++) {'t': 'G$i', 'd': 100.0 + i}
    ]);
    expect(cizimHatasi, isNull);
  });

  testWidgets('etiketsiz seri çökertmez', (t) async {
    await _ciz(t, [for (var i = 0; i < 30; i++) {'t': '', 'd': 100.0 + i}]);
    expect(cizimHatasi, isNull);
  });

  testWidgets('tek parçalı etiket çökertmez', (t) async {
    await _ciz(t, [for (var i = 0; i < 30; i++) {'t': 'gun$i', 'd': 100.0 + i}]);
    expect(cizimHatasi, isNull);
  });

  testWidgets('düz seri (hiç oynamayan) çökertmez', (t) async {
    // enCok == enAz olunca aralık sıfır; bölme hatası riski.
    await _ciz(t, [for (var i = 0; i < 30; i++) {'t': 'G$i', 'd': 100.0}]);
    expect(cizimHatasi, isNull);
  });

  testWidgets('üç noktadan az veri "grafik yok" gösterir', (t) async {
    await _ciz(t, [{'t': 'G1', 'd': 100.0}, {'t': 'G2', 'd': 101.0}]);
    expect(find.textContaining('Grafik'), findsOneWidget);
  });

  testWidgets('boş seri çökertmez', (t) async {
    await _ciz(t, const []);
    expect(cizimHatasi, isNull);
  });
}

/// Test sırasında yakalanan çizim hatası.
Object? get cizimHatasi {
  final h = TestWidgetsFlutterBinding.instance.takeException();
  return h;
}
