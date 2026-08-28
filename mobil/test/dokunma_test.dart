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
import 'package:midas_analist/servis/modeller.dart';

void main() {
  _tezTestleri();
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

// ── tez tamlığı ────────────────────────────────────────────────────────────
//
// Sessiz bir doğruluk hatasıydı: tez soruları yalnızca "Tez yaz" ekranında
// yükleniyor, Tezler sekmesine oradan geçmeden girilince liste boş
// kalıyordu. eksikler(bosListe) boş liste döndüğü için TAMAMEN BOŞ bir tez
// bile "TAM" rozetiyle görünüyordu — ekranın tek işi bunu söylemekken.

void _tezTestleri() {
  group('tez tamlığı', () {
    final sorular = [
      {'anahtar': 'ne', 'soru': 'Ne alıyorum?'},
      {'anahtar': 'yanilma_kosulu', 'soru': 'Hangi durumda yanıldığımı kabul ederim?'},
    ];

    Tez tez(Map<String, String> cevaplar) => Tez(
        sembol: 'THYAO', tarih: '2026-08-14', fiyat: 300, cevaplar: cevaplar);

    test('soru listesi boşken TAM denmez', () {
      expect(tez(const {}).tamMi(const []), isFalse);
      expect(tez(const {'ne': 'x', 'yanilma_kosulu': 'y'}).tamMi(const []),
          isFalse,
          reason: 'doğrulanamayan şeye tam demek, eksik demekten kötü');
    });

    test('tüm cevaplar doluysa tam', () {
      expect(tez(const {'ne': 'x', 'yanilma_kosulu': 'y'}).tamMi(sorular),
          isTrue);
    });

    test('eksik cevap varsa tam değil', () {
      expect(tez(const {'ne': 'x'}).tamMi(sorular), isFalse);
      expect(tez(const {'ne': 'x', 'yanilma_kosulu': '   '}).tamMi(sorular),
          isFalse, reason: 'boşluk dolu sayılmamalı');
    });
  });
}
