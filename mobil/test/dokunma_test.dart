// Kart dokunma hedefleri — CİHAZ GEREKTİRMEZ.
//
// Bugün ekranındaki Portföy kartı hem kendisi tıklanabilir hem de İÇİNDE
// ayrı bir "SERMAYE +/-" düğmesi taşıyor. Dıştaki dokunma içtekini
// yutarsa, düğmeye basan kullanıcı Sermaye ekranı yerine Portföy
// sekmesine düşer — sessiz ve rahatsız edici bir hata.
//
// Ayrıca sekme geçişi global bir ValueNotifier üzerinden yapılıyor;
// Kabuk'un onu dinlediği ve enum sırasının NavigationBar sırasıyla
// örtüştüğü de burada kilitli.
//
// Çalıştır:  flutter test
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:midas_analist/ekran/kabuk.dart';
import 'package:midas_analist/parca/kart.dart';

void main() {
  group('iç içe dokunma hedefi', () {
    testWidgets('içteki düğme dıştaki karta rağmen çalışır', (t) async {
      var dis = 0, ic = 0;
      await t.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Kutu(
            tikla: () => dis++,
            child: Row(children: [
              const Text('PORTFÖY'),
              const Spacer(),
              InkWell(
                onTap: () => ic++,
                child: const Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('SERMAYE +/-'),
                ),
              ),
            ]),
          ),
        ),
      ));

      await t.tap(find.text('SERMAYE +/-'));
      await t.pumpAndSettle();
      expect(ic, 1, reason: 'içteki düğme çalışmalı');
      expect(dis, 0, reason: 'dıştaki kart tetiklenmemeli');
    });

    testWidgets('kartın boş yerine dokunmak dıştakini çalıştırır', (t) async {
      var dis = 0, ic = 0;
      await t.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Kutu(
            tikla: () => dis++,
            child: Row(children: [
              const Text('PORTFÖY'),
              const Spacer(),
              InkWell(onTap: () => ic++, child: const Text('SERMAYE +/-')),
            ]),
          ),
        ),
      ));

      await t.tap(find.text('PORTFÖY'));
      await t.pumpAndSettle();
      expect(dis, 1);
      expect(ic, 0);
    });

    testWidgets('tikla verilmeyen kutu dokunmayı yutmaz', (t) async {
      var ic = 0;
      await t.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Kutu(
            child: InkWell(onTap: () => ic++, child: const Text('düğme')),
          ),
        ),
      ));
      await t.tap(find.text('düğme'));
      await t.pumpAndSettle();
      expect(ic, 1);
    });
  });

  group('sekme geçişi', () {
    setUp(() => sekme.value = Sekme.bugun);

    test('enum sırası NavigationBar sırasıyla aynı', () {
      // Kabuk selectedIndex olarak enum index'ini veriyor; sıra kayarsa
      // Portföy'e gitmek isteyen kullanıcı Tezler'e düşer.
      expect(Sekme.values.map((e) => e.name).toList(),
          ['bugun', 'tarama', 'portfoy', 'tezler', 'daha']);
      expect(Sekme.portfoy.index, 2);
      expect(Sekme.tarama.index, 1);
    });

    test('notifier değişimi dinleyiciye ulaşır', () {
      var bildirim = 0;
      void dinle() => bildirim++;
      sekme.addListener(dinle);
      sekme.value = Sekme.tarama;
      sekme.removeListener(dinle);
      expect(bildirim, 1);
      expect(sekme.value, Sekme.tarama);
    });

    testWidgets('sekmeyeGit üstteki sayfayı kapatır', (t) async {
      // Sekme değişip açık sayfa kapanmazsa, kullanıcı sekmeyi değiştirir
      // ama ekranda hâlâ eski sayfayı görür.
      await t.pumpWidget(MaterialApp(
        home: Builder(
          builder: (c) => Scaffold(
            body: TextButton(
              onPressed: () => Navigator.push(c,
                  MaterialPageRoute(builder: (_) => Builder(
                      builder: (c2) => Scaffold(
                            body: TextButton(
                              onPressed: () => sekmeyeGit(c2, Sekme.portfoy),
                              child: const Text('git'),
                            ),
                          )))),
              child: const Text('aç'),
            ),
          ),
        ),
      ));

      await t.tap(find.text('aç'));
      await t.pumpAndSettle();
      expect(find.text('git'), findsOneWidget);

      await t.tap(find.text('git'));
      await t.pumpAndSettle();
      expect(sekme.value, Sekme.portfoy);
      expect(find.text('git'), findsNothing, reason: 'üstteki sayfa kapanmalı');
      expect(find.text('aç'), findsOneWidget);
    });
  });
}
