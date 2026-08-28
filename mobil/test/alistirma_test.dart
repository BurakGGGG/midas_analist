import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:midas_analist/ekran/alistirma.dart';
import 'package:midas_analist/servis/alistirma.dart';
import 'package:midas_analist/servis/api.dart';
import 'package:midas_analist/servis/depo.dart';
import 'package:midas_analist/tema.dart';

/// İki görevlik sahte bir görev listesi. İkisi de `sayi` türünde ve
/// AYRI cevapları var — testin yakaladığı hata tam olarak "önceki görevin
/// durumu sonrakine sızıyor mu" sorusu.
const _gorevler = [
  {
    'kod': 'g01', 'baslik': 'Birinci görev', 'amac': 'toplama',
    'anlatim': 'Birinci anlatım.', 'tur': 'sayi',
    'soru': '2 + 2 kaç eder?', 'dogru': 4.0, 'tolerans': 0.01,
    'birim': '₺', 'ipucu': 'topla', 'aciklama': 'BİRİNCİ AÇIKLAMA', 'ders': '',
  },
  {
    'kod': 'g02', 'baslik': 'İkinci görev', 'amac': 'çarpma',
    'anlatim': 'İkinci anlatım.', 'tur': 'sayi',
    'soru': '3 × 3 kaç eder?', 'dogru': 9.0, 'tolerans': 0.01,
    'birim': '₺', 'ipucu': 'çarp', 'aciklama': 'İKİNCİ AÇIKLAMA', 'ders': '',
  },
];

class _SahteApi extends Api {
  _SahteApi() : super('http://sahte');

  @override
  Future<Map<String, dynamic>> alistirmaGorevler() async =>
      {'gorevler': _gorevler};
}

/// Kum havuzunu başlamış ve rehberli halde kurar.
Future<void> _kur({List<String> biten = const []}) async {
  SharedPreferences.setMockInitialValues({
    KumHavuzu.anahtar: jsonEncode({
      'mod': 'gecmis', 'rehber': 'rehberli', 'tarih': '2026-05-01',
      'bakiye': 10000.0, 'pozisyonlar': [], 'kapali': [],
      'gorevler': biten, 'puan': 0, 'rozetler': [], 'denemeler': {},
    }),
  });
  await kum.yukle();
}

Future<void> _ac(WidgetTester t) async {
  // Uzun bir test yüzeyi: varsayılan 800x600'de görev kartının alt yarısı
  // (KONTROL ET düğmesi dahil) görünür alanın dışında kalıyor ve dokunma
  // isabet etmiyor. Kaydırmakla uğraşmak yerine ekranı büyütüyoruz.
  t.view.physicalSize = const Size(1100, 3200);
  t.view.devicePixelRatio = 1.0;
  addTearDown(t.view.reset);

  await t.pumpWidget(MaterialApp(
      theme: temaKoyu, home: const AlistirmaEkran()));
  await t.pumpAndSettle();
}

/// Görünür alana getirip dokunur.
Future<void> _tikla(WidgetTester t, Finder f) async {
  await t.ensureVisible(f);
  await t.pumpAndSettle();
  await t.tap(f);
  await t.pumpAndSettle();
}

void main() {
  setUp(() {
    Depo.apiUretici = _SahteApi.new;
  });
  tearDown(() {
    Depo.apiUretici = null;
  });

  testWidgets('görev değişince önceki görevin durumu SIZMAZ', (t) async {
    await _kur();
    await _ac(t);

    // 1. görevi doğru cevapla
    await t.ensureVisible(find.byType(TextField));
    await t.enterText(find.byType(TextField), '4');
    await _tikla(t, find.text('KONTROL ET'));
    expect(find.textContaining('BİRİNCİ AÇIKLAMA'), findsOneWidget);

    // 2. göreve geç
    await _tikla(t, find.text('SONRAKİ GÖREV'));

    // ── ASIL SINAMA ──────────────────────────────────────────────
    // Anahtar olmadan Flutter aynı State'i yeniden kullanıyordu ve
    // üç şey birden bozuluyordu.
    expect(find.text('İkinci görev'), findsOneWidget);

    // (a) önceki görevin açıklaması ekranda kalmamalı
    expect(find.textContaining('BİRİNCİ AÇIKLAMA'), findsNothing);

    // (b) cevap kutusu YAZILABİLİR olmalı
    final kutu = t.widget<TextField>(find.byType(TextField));
    expect(kutu.enabled, isTrue,
        reason: 'cevap kutusu kapalı geliyorsa kullanıcı yazamaz');

    // (c) "KONTROL ET" düğmesi geri gelmiş olmalı
    expect(find.text('KONTROL ET'), findsOneWidget);
  });

  testWidgets('yeni görevde eski cevap kutuda kalmaz', (t) async {
    await _kur();
    await _ac(t);
    await t.ensureVisible(find.byType(TextField));
    await t.enterText(find.byType(TextField), '4');
    await _tikla(t, find.text('KONTROL ET'));
    await _tikla(t, find.text('SONRAKİ GÖREV'));

    final kutu = t.widget<TextField>(find.byType(TextField));
    expect(kutu.controller?.text ?? '', isEmpty,
        reason: '4 yazısı ikinci göreve taşınmamalı');
  });

  testWidgets('yanlış cevap puanı düşürür, doğru cevap ilerletir', (t) async {
    await _kur();
    await _ac(t);

    await t.ensureVisible(find.byType(TextField));
    await t.enterText(find.byType(TextField), '5');
    await _tikla(t, find.text('KONTROL ET'));
    expect(find.text('BİR DAHA DENE'), findsOneWidget);

    await t.ensureVisible(find.byType(TextField));
    await t.enterText(find.byType(TextField), '4');
    await _tikla(t, find.text('KONTROL ET'));
    expect(find.text('DOĞRU — 2. denemede'), findsOneWidget);
    expect(find.text('+6 PUAN'), findsOneWidget);
  });

  testWidgets('ipucu cevaplamadan ÖNCE istenebilir', (t) async {
    await _kur();
    await _ac(t);
    expect(find.text('topla'), findsNothing);
    await _tikla(t, find.text('İPUCU'));
    expect(find.text('topla'), findsOneWidget);
  });

  testWidgets('anlatım katlanabilir — soru ekranda yukarı gelsin', (t) async {
    await _kur();
    await _ac(t);
    expect(find.text('Birinci anlatım.'), findsOneWidget);
    await _tikla(t, find.text('ÖNCE ŞUNU BİL'));
    expect(find.text('Birinci anlatım.'), findsNothing);
    expect(find.text('2 + 2 kaç eder?'), findsOneWidget);
  });

  testWidgets('görevler bitince kutlama ve rozetler çıkar', (t) async {
    await _kur(biten: ['g01', 'g02']);
    await _ac(t);
    expect(find.text('Görevler bitti'), findsWidgets);
    expect(find.text('Mezun'), findsOneWidget);
  });

  test('puan denemeye göre azalır ama sıfırlanmaz', () {
    expect(KumHavuzu.puanHesapla(1), 10);
    expect(KumHavuzu.puanHesapla(2), 6);
    expect(KumHavuzu.puanHesapla(9), 3);
  });

  testWidgets('alım görevi kanıtsız geçilemez ama atlanabilir', (t) async {
    Depo.apiUretici = _IslemApi.new;
    SharedPreferences.setMockInitialValues({
      KumHavuzu.anahtar: jsonEncode({
        'mod': 'gecmis', 'rehber': 'rehberli', 'tarih': '2026-05-01',
        'bakiye': 10000.0, 'pozisyonlar': [], 'kapali': [],
        'gorevler': [], 'puan': 0, 'rozetler': [], 'denemeler': {},
      }),
    });
    await kum.yukle();
    await _ac(t);

    // Pozisyon yokken ilerletme düğmesi KAPALI olmalı
    final dugme = t.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'ÖNCE BİR ALIM YAP'));
    expect(dugme.onPressed, isNull);

    // ama kilitlemiyoruz: atlama yolu hep açık
    expect(find.text('YİNE DE ATLA'), findsOneWidget);
  });

  testWidgets('pozisyon varsa alım görevi ilerletilebilir', (t) async {
    Depo.apiUretici = _IslemApi.new;
    SharedPreferences.setMockInitialValues({
      KumHavuzu.anahtar: jsonEncode({
        'mod': 'gecmis', 'rehber': 'rehberli', 'tarih': '2026-05-01',
        'bakiye': 8000.0,
        'pozisyonlar': [
          {'sembol': 'THYAO', 'adet': 5, 'giris': 300.0, 'stop': 280.0,
           'hedef': 340.0, 'tarih': '2026-05-01'}
        ],
        'kapali': [], 'gorevler': [], 'puan': 0, 'rozetler': [],
        'denemeler': {},
      }),
    });
    await kum.yukle();
    await _ac(t);

    expect(find.text('ÖNCE BİR ALIM YAP'), findsNothing);
    expect(find.text('YİNE DE ATLA'), findsNothing);
    expect(find.text('GÖREVLERİ BİTİR'), findsOneWidget);
  });

  testWidgets('başlangıç iki adım: önce yardım, sonra zaman', (t) async {
    SharedPreferences.setMockInitialValues({});
    await kum.yukle();
    await _ac(t);

    // Adım 1
    expect(find.text('Yardım ister misin?'), findsOneWidget);
    expect(find.text('ADIM 1 / 2'), findsOneWidget);
    expect(find.text('Hangi zamanda?'), findsNothing);

    await _tikla(t, find.text('Elimden tut'));

    // Adım 2 — zaman sorusu, geri dönüş yolu açık
    expect(find.text('ADIM 2 / 2'), findsOneWidget);
    expect(find.text('Hangi zamanda?'), findsOneWidget);
    expect(find.text('GERİ'), findsOneWidget);

    await _tikla(t, find.text('GERİ'));
    expect(find.text('Yardım ister misin?'), findsOneWidget);
  });

  testWidgets('kendi başıma seçilince görev kartı çıkmaz', (t) async {
    SharedPreferences.setMockInitialValues({});
    await kum.yukle();
    await _ac(t);

    await _tikla(t, find.text('Kendi başıma'));
    await _tikla(t, find.text('Geçmiş'));

    expect(kum.rehber, 'serbest');
    expect(find.text('Sıradaki görev'), findsNothing);
    // Kapıyı arkasından kilitlemiyoruz
    expect(find.text('AÇ'), findsOneWidget);
  });

  test('eski kayıtta rehber alanı yoksa rehberli sayılır', () async {
    // Sürüm yükselten kullanıcının ilerlemesi kaybolmamalı: mod seçilmiş
    // ama `rehber` yoksa mod seçim ekranına DÜŞMEMELİ.
    SharedPreferences.setMockInitialValues({
      KumHavuzu.anahtar: jsonEncode({
        'mod': 'gecmis', 'tarih': '2026-05-01', 'bakiye': 9000.0,
        'pozisyonlar': [], 'kapali': [], 'gorevler': ['g01'],
      }),
    });
    await kum.yukle();
    expect(kum.rehber, 'rehberli');
    expect(kum.basladi, isTrue);
  });
}

// ── uygulamalı görevlerde kanıt ────────────────────────────────────────────

const _islemGorevi = [
  {
    'kod': 'i01', 'baslik': 'Alım görevi', 'amac': 'alım yapmak',
    'anlatim': 'Kum havuzunda alım yap.', 'tur': 'islem',
    'soru': 'Bir alım yap.', 'aciklama': 'Alım kaydedildi.', 'ders': '',
  },
];

class _IslemApi extends Api {
  _IslemApi() : super('http://sahte');
  @override
  Future<Map<String, dynamic>> alistirmaGorevler() async =>
      {'gorevler': _islemGorevi};
}

