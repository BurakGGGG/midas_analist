import 'package:flutter_test/flutter_test.dart';
import 'package:midas_analist/servis/egitmen.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  group('SM-2 aralıklı tekrar', () {
    test('doğru cevaplarda aralık büyür', () {
      var k = const Kayit(kod: 't01');
      k = k.guncelle(5);
      expect(k.tekrar, 1);
      expect(k.aralik, 1);
      k = k.guncelle(5);
      expect(k.aralik, 6);
      k = k.guncelle(5);
      expect(k.aralik, greaterThan(6));
      expect(k.dogru, 3);
      expect(k.yanlis, 0);
    });

    test('yanlış cevap ilerlemeyi sıfırlar', () {
      var k = const Kayit(kod: 't01');
      for (var i = 0; i < 3; i++) {
        k = k.guncelle(5);
      }
      expect(k.aralik, greaterThan(6));
      k = k.guncelle(1);
      expect(k.tekrar, 0, reason: 'yanlış bilinen soru sıfırdan başlamalı');
      expect(k.aralik, 1);
      expect(k.yanlis, 1);
    });

    test('kolaylık faktörü 1.3 altına düşmez', () {
      var k = const Kayit(kod: 't01');
      for (var i = 0; i < 20; i++) {
        k = k.guncelle(1);
      }
      expect(k.kolaylik, greaterThanOrEqualTo(1.3));
    });

    test('öğrenilmiş sayılmak 3 tekrar VE 21 gün aralık ister', () {
      var k = const Kayit(kod: 't01');
      k = k.guncelle(5);
      k = k.guncelle(5);
      expect(k.ogrenildi, isFalse, reason: '2 tekrar yeterli değil');
      k = k.guncelle(5);
      k = k.guncelle(5);
      expect(k.tekrar, greaterThanOrEqualTo(3));
      expect(k.aralik, greaterThanOrEqualTo(21));
      expect(k.ogrenildi, isTrue);
    });

    test('vadesi gelmemiş kayıt bugün seçilmez', () {
      final gelecek = DateTime.now().add(const Duration(days: 10));
      final k = Kayit(
          kod: 't01', sonraki: gelecek.toIso8601String().substring(0, 10));
      expect(k.vadesiGeldi(DateTime.now()), isFalse);
      expect(k.vadesiGeldi(gelecek.add(const Duration(days: 1))), isTrue);
    });
  });

  group('Seviye ve günlük seçim', () {
    late Egitmen e;

    setUp(() {
      e = Egitmen();
      e.sorular = [
        for (var i = 0; i < 10; i++)
          EgitmenSoru(
              kod: 't${i.toString().padLeft(2, '0')}',
              kategori: 'temel', soru: 'soru $i', cevap: 'cevap $i', seviye: 1),
        for (var i = 0; i < 10; i++)
          EgitmenSoru(
              kod: 'o${i.toString().padLeft(2, '0')}',
              kategori: 'orta', soru: 'orta $i', cevap: 'cevap', seviye: 2),
      ];
      e.ilkeler = ['ilke bir', 'ilke iki'];
      // Müfredat: 2 modül × 5 ders. Seviye artık DERSE dayanıyor (2/3 ağırlık).
      e.moduller = [
        EgitmenModul(
          kod: 'm1', ad: 'Modül 1', aciklama: 'test', seviye: 1,
          dersler: [
            for (var i = 0; i < 5; i++)
              Ders(kod: 'd10$i', baslik: 'ders $i', ozet: 'ozet',
                  icerik: 'icerik', sorular: ['t0$i'], sure: 5),
          ],
        ),
        EgitmenModul(
          kod: 'm2', ad: 'Modül 2', aciklama: 'test', seviye: 2,
          dersler: [
            for (var i = 0; i < 5; i++)
              Ders(kod: 'd20$i', baslik: 'ders 2$i', ozet: 'ozet',
                  icerik: 'icerik', sorular: ['o0$i'], sure: 5),
          ],
        ),
      ];
    });

    test('başlangıçta Çırak ve hiç ders okunmamış', () {
      final d = e.durum();
      expect(d.seviye, 1);
      expect(d.unvan, 'Çırak');
      expect(d.dersOkunan, 0);
      expect(d.dersToplam, 10);
      expect(d.dakikaKalan, 50);
    });

    test('günlük ders müfredat sırasıyla gelir', () async {
      expect(e.gunlukDers().first.kod, 'd100');
      await e.dersOkundu('d100');
      expect(e.gunlukDers().first.kod, 'd101');
      expect(e.okundu('d100'), isTrue);
    });

    test('ders okundukça seviye ilerler', () async {
      for (var i = 0; i < 5; i++) {
        await e.dersOkundu('d10$i');
      }
      var d = e.durum();
      expect(d.dersOkunan, 5);
      // 5/10 ders = %50 · 2/3 ağırlık ≈ %33 bileşik → hâlâ Çırak sınırında
      expect(d.bilesikYuzde, closeTo(33.3, 1.0));
      for (var i = 0; i < 5; i++) {
        await e.dersOkundu('d20$i');
      }
      d = e.durum();
      expect(d.dersOkunan, 10);
      expect(d.seviye, greaterThanOrEqualTo(2),
          reason: 'tüm dersler okununca en az Kalfa olunmalı');
      expect(d.dakikaKalan, 0);
    });

    test('okunmamış dersin sorusu sorulmaz', () async {
      await e.dersOkundu('d100');   // sorusu t00
      final secim = e.gunlukSecim(adet: 5);
      expect(secim.map((s) => s.kod), contains('t00'));
      expect(secim.map((s) => s.kod), isNot(contains('t03')),
          reason: 'd103 okunmadı, t03 gelmemeli');
    });

    test('günlük seçim vadesi geleni önceler', () async {
      for (var i = 0; i < 5; i++) {
        await e.dersOkundu('d10$i');
      }
      final dun = DateTime.now().subtract(const Duration(days: 3));
      e.ilerleme['t04'] = Kayit(
          kod: 't04', tekrar: 2, aralik: 6,
          sonraki: dun.toIso8601String().substring(0, 10));
      final secim = e.gunlukSecim(adet: 4);
      expect(secim.map((s) => s.kod), contains('t04'));
    });

    test('ders işaretleme çalışır', () async {
      await e.dersIsaretle('d102', true);
      expect(e.isaretliDersler.map((d) => d.kod), contains('d102'));
      await e.dersIsaretle('d102', false);
      expect(e.isaretliDersler, isEmpty);
    });

    test('istatistik doğru oranını hesaplar', () {
      e.ilerleme['t00'] = const Kayit(kod: 't00', dogru: 3, yanlis: 1);
      e.ilerleme['t01'] = const Kayit(kod: 't01', dogru: 1, yanlis: 0);
      final ist = e.istatistik();
      expect(ist['calisilan'], 2);
      expect(ist['toplamCevap'], 5);
      expect(ist['dogruOrani'], closeTo(80.0, 0.01));
    });

    test('ilke günün boş bankada çökmez', () {
      expect(Egitmen().ilkeGunun(), '');
      expect(e.ilkeGunun(), isNotEmpty);
    });
  });
}
