
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:midas_analist/servis/api.dart';
import 'package:midas_analist/servis/depo.dart';
import 'package:midas_analist/servis/hesap.dart';
import 'package:midas_analist/parca/ipucu.dart';
import 'package:midas_analist/servis/sanal.dart';

/// Sanal hesap — telefonda tutulan durum.
///
/// Sunucu fiyatı ve kuralları biliyor; buradaki iş nakit muhasebesi,
/// ortalama maliyet ve kalıcılık. Hepsi sessizce yanlış olabilecek
/// şeyler: bir kuruş kayıp fark edilmez ama simülasyonun tamamını
/// yanlış öğretir.

class _SahteApi extends Api {
  _SahteApi() : super('http://sahte');

  /// Sunucunun döndüreceği alım cevabı — testler bunu değiştirir.
  static Map<String, dynamic> alCevap = {};
  static Map<String, dynamic> satCevap = {};
  static Map<String, dynamic> adimCevap = {};
  static Map<String, dynamic> degerCevap = {'ozkaynak': 0.0};

  @override
  Future<Map<String, dynamic>> sanalAl(
          String sembol, String tarih, int adet, double nakit) async =>
      alCevap;

  @override
  Future<Map<String, dynamic>> sanalSat(
          String tarih, Map<String, dynamic> pozisyon,
          {int adet = 0}) async =>
      satCevap;

  @override
  Future<Map<String, dynamic>> sanalAdim(String tarih, double nakit,
          List<Map<String, dynamic>> pozisyonlar,
          {int adim = 1, List<String> izlenen = const []}) async =>
      adimCevap;

  @override
  Future<Map<String, dynamic>> sanalDeger(String tarih, double nakit,
          List<Map<String, dynamic>> pozisyonlar) async =>
      degerCevap;
}

Map<String, dynamic> _alGecti(double fiyat, int adet) => {
      'gecti': true, 'fiyat': fiyat, 'maliyet': fiyat * adet,
      'ham_fiyat': fiyat, 'kayma': 0.0, 'tarih': '2024-06-12', 'sebep': '',
    };

Future<void> _kur({double sermaye = 10000}) async {
  SharedPreferences.setMockInitialValues({});
  Depo.apiUretici = _SahteApi.new;
  _SahteApi.degerCevap = {'ozkaynak': sermaye, 'satirlar': []};
  await sanal.yukle();
  await sanal.basla('2024-06-12', sermaye);
}

void main() {
  tearDown(() => Depo.apiUretici = null);

  group('kurulum', () {
    test('başlangıç durumu', () async {
      await _kur();
      expect(sanal.basladi, isTrue);
      expect(sanal.nakit, 10000);
      expect(sanal.tarih, '2024-06-12');
      expect(sanal.ozkaynak.length, 1,
          reason: 'başlangıç noktası grafiğin ilk noktası olmalı');
    });

    test('sıfırlama her şeyi siler', () async {
      await _kur();
      await sanal.sifirla();
      expect(sanal.basladi, isFalse);
      expect(sanal.pozisyonlar, isEmpty);
      expect(sanal.ozkaynak, isEmpty);
    });
  });

  group('alım', () {
    test('nakitten maliyet düşülür', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 4);
      final h = await sanal.al('THYAO', 4, 280, 340);
      expect(h, isNull);
      expect(sanal.nakit, 10000 - 1200);
      expect(sanal.pozisyonlar.single.adet, 4);
      expect(sanal.pozisyonlar.single.giris, 300.0);
    });

    test('sunucu reddederse HİÇBİR ŞEY değişmez', () async {
      await _kur();
      _SahteApi.alCevap = {'gecti': false, 'sebep': 'tavanda açtı'};
      final h = await sanal.al('THYAO', 4, 280, 340);
      expect(h, 'tavanda açtı');
      expect(sanal.nakit, 10000);
      expect(sanal.pozisyonlar, isEmpty);
    });

    test('AYNI hisseye ekleme ortalama maliyet yapar', () async {
      // Gerçekte yapabilirsin; "düşen hisseye ekleme" en pahalı
      // alışkanlıklardan biri ve burası onu bedava öğreneceğin yer.
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 2);   // 2 × 300 = 600
      await sanal.al('THYAO', 2, 280, 340);
      _SahteApi.alCevap = _alGecti(200.0, 2);   // 2 × 200 = 400
      await sanal.al('THYAO', 2, 190, 260);

      final p = sanal.pozisyonlar.single;
      expect(p.adet, 4);
      expect(p.giris, 250.0, reason: '(300×2 + 200×2) / 4');
      expect(p.maliyet, 1000.0);
      expect(sanal.nakit, 10000 - 1000);
    });

    test('ekleme stop ve hedefi günceller', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 2);
      await sanal.al('THYAO', 2, 280, 340);
      _SahteApi.alCevap = _alGecti(200.0, 2);
      await sanal.al('THYAO', 2, 190, 260);
      expect(sanal.pozisyonlar.single.stop, 190);
      expect(sanal.pozisyonlar.single.hedef, 260);
    });
  });

  group('satış', () {
    test('kısmi satış kalanı bırakır ve nakde ekler', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 10);
      await sanal.al('THYAO', 10, 280, 340);
      _SahteApi.satCevap = {
        'gecti': true, 'sembol': 'THYAO', 'adet': 4, 'fiyat': 320.0,
        'hasilat': 1280.0, 'kalan_adet': 6, 'tarih': '2024-06-20',
      };
      final h = await sanal.sat('THYAO', adet: 4);
      expect(h, isNull);
      expect(sanal.pozisyonlar.single.adet, 6);
      expect(sanal.nakit, 10000 - 3000 + 1280);
      expect(sanal.kapali.single.adet, 4);
      expect(sanal.kapali.single.kar, (320 - 300) * 4);
    });

    test('tamamı satılınca pozisyon kapanır', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 5);
      await sanal.al('THYAO', 5, 280, 340);
      _SahteApi.satCevap = {
        'gecti': true, 'sembol': 'THYAO', 'adet': 5, 'fiyat': 310.0,
        'hasilat': 1550.0, 'kalan_adet': 0, 'tarih': '2024-06-20',
      };
      await sanal.sat('THYAO');
      expect(sanal.pozisyonlar, isEmpty);
    });

    test('olmayan pozisyon satılamaz', () async {
      await _kur();
      expect(await sanal.sat('YOKBU'), 'Açık pozisyon yok.');
    });
  });

  group('stop çekme', () {
    test('yukarı çekilebilir', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 4);
      await sanal.al('THYAO', 4, 280, 340);
      expect(await sanal.stopCek('THYAO', 295), isNull);
      expect(sanal.pozisyonlar.single.stop, 295);
    });

    test('AŞAĞI çekilemez', () async {
      // Stopu gevşetmek ("biraz daha alan vereyim") en yaygın ve en
      // pahalı alışkanlık. Simülatörde serbest bırakmak onu öğretmek olur.
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 4);
      await sanal.al('THYAO', 4, 280, 340);
      final h = await sanal.stopCek('THYAO', 270);
      expect(h, isNotNull);
      expect(h, contains('YUKARI'));
      expect(sanal.pozisyonlar.single.stop, 280, reason: 'stop değişmemeli');
    });
  });

  group('zaman ilerletme', () {
    test('çıkışlar kapananlara taşınır ve nakit güncellenir', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 4);
      await sanal.al('THYAO', 4, 280, 340);

      _SahteApi.adimCevap = {
        'tarih': '2024-06-20',
        'gunler': ['2024-06-13', '2024-06-20'],
        'nakit': 10000 - 1200 + 1120.0,
        'pozisyonlar': [],
        'cikislar': [
          {'sembol': 'THYAO', 'adet': 4, 'fiyat': 280.0, 'sebep': 'stop',
           'tarih': '2024-06-20', 'giris': 300.0, 'giris_tarih': '2024-06-12'},
        ],
        'ozkaynak_noktalari': [
          {'t': '2024-06-13', 'd': 9900.0},
          {'t': '2024-06-20', 'd': 9920.0},
        ],
        'deger': {'ozkaynak': 9920.0, 'satirlar': []},
      };
      final kapanan = await sanal.ilerlet(adim: 5);

      expect(kapanan.single.sebep, 'stop');
      expect(sanal.tarih, '2024-06-20');
      expect(sanal.pozisyonlar, isEmpty);
      expect(sanal.kapali.single.kar, (280 - 300) * 4);
      expect(sanal.ozkaynak.length, 3, reason: 'başlangıç + iki gün');
      expect(sanal.ozkaynakSimdi, 9920.0);
    });

    test('özkaynak noktaları BİRİKİR, ezilmez', () async {
      // Grafiğin kaynağı bu. Ezilirse geçmiş geri üretilemez.
      await _kur();
      _SahteApi.adimCevap = {
        'tarih': '2024-06-13', 'gunler': ['2024-06-13'],
        'nakit': 10000.0, 'pozisyonlar': [], 'cikislar': [],
        'ozkaynak_noktalari': [{'t': '2024-06-13', 'd': 10000.0}],
        'deger': {'ozkaynak': 10000.0},
      };
      await sanal.ilerlet();
      _SahteApi.adimCevap = {
        ..._SahteApi.adimCevap,
        'tarih': '2024-06-14',
        'ozkaynak_noktalari': [{'t': '2024-06-14', 'd': 10100.0}],
      };
      await sanal.ilerlet();
      expect(sanal.ozkaynak.map((e) => e['t']).toList(),
          ['2024-06-12', '2024-06-13', '2024-06-14']);
    });
  });

  group('kalıcılık', () {
    test('durum diske yazılıp geri okunur', () async {
      await _kur();
      _SahteApi.alCevap = _alGecti(300.0, 4);
      await sanal.al('THYAO', 4, 280, 340);

      final taze = SanalHesap();
      await taze.yukle();
      expect(taze.tarih, '2024-06-12');
      expect(taze.nakit, 8800);
      expect(taze.pozisyonlar.single.sembol, 'THYAO');
      expect(taze.baslangicSermaye, 10000);
    });

    test('bozuk kayıt ekranı kilitlemez', () async {
      SharedPreferences.setMockInitialValues(
          {SanalHesap.anahtar: 'bu json değil'});
      final h = SanalHesap();
      await h.yukle();
      expect(h.basladi, isFalse);
    });

    test('kayıt yokken durum SIFIRLANIR', () async {
      // Erken dönüp bellekteki eski durumu bırakmak, çağıranın
      // "yükledim" sandığı şeyin önceki hâl olması demek.
      await _kur();
      SharedPreferences.setMockInitialValues({});
      await sanal.yukle();
      expect(sanal.basladi, isFalse);
      expect(sanal.nakit, 0);
    });
  });

  test('bulut yedeği sanal işlemi KAPSIYOR', () {
    // Özkaynak eğrisi gün gün biriktiriliyor; kaybolursa geriye
    // üretilemez.
    expect(Hesap.yedeklenen, contains(SanalHesap.anahtar));
  });

  test('toplam getiri başlangıç sermayesinden ölçülür', () async {
    await _kur(sermaye: 5000);
    _SahteApi.degerCevap = {'ozkaynak': 5500.0, 'satirlar': []};
    await sanal.degerle();
    expect(sanal.toplamGetiriYuzde, closeTo(10.0, 0.001));
  });

  _ipucuTestleri();
}

// ── ipucu balonları ────────────────────────────────────────────────────────

void _ipucuTestleri() {
  group('ipucu', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      await ipucu.yukle();
    });

    test('okunmamış ipucu görünür, okunan görünmez', () async {
      expect(ipucu.gorunur('stop'), isTrue);
      await ipucu.okundu('stop');
      expect(ipucu.gorunur('stop'), isFalse);
    });

    test('SIRAYLA: yalnızca ilk okunmamış olan', () async {
      // Dört balon birden açılınca ekran metin duvarına dönüyordu.
      const akis = ['kayma', 'stop', 'hedef', 'adet'];
      expect(ipucu.siradaki(akis), 'kayma');
      await ipucu.okundu('kayma');
      expect(ipucu.siradaki(akis), 'stop');
      await ipucu.okundu('stop');
      await ipucu.okundu('hedef');
      expect(ipucu.siradaki(akis), 'adet');
      await ipucu.okundu('adet');
      expect(ipucu.siradaki(akis), isNull);
    });

    test('okundu bilgisi diske yazılır', () async {
      await ipucu.okundu('stop');
      final taze = IpucuDeposu();
      await taze.yukle();
      expect(taze.gorunur('stop'), isFalse);
    });

    test('hepsi geri getirilebilir', () async {
      await ipucu.okundu('stop');
      await ipucu.okundu('hedef');
      await ipucu.hepsiniGeriGetir();
      expect(ipucu.gorunur('stop'), isTrue);
      expect(ipucu.gorunur('hedef'), isTrue);
    });

    test('her ipucunun metni var', () {
      // Kod yazılıp metni unutulursa balon sessizce hiç çıkmaz.
      for (final k in ['stop', 'hedef', 'adet', 'kayma', 'tavan',
                       'ilerlet', 'sinyal']) {
        expect(ipucuMetni.containsKey(k), isTrue, reason: '$k metni yok');
        expect(ipucuMetni[k]!.$2.length, greaterThan(60),
            reason: '$k metni fazla kısa — tanım değil mekanizma anlatmalı');
      }
    });

    test('bulut yedeği ipuçlarını KAPSIYOR', () {
      expect(Hesap.yedeklenen, contains(IpucuDeposu.anahtar));
    });
  });
}
