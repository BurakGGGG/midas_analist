import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'modeller.dart';

/// Python backend istemcisi.
///
/// Tasarım notu: sunucu adresi ayarlardan gelir çünkü geliştirme aşamasında
/// üç farklı adres olur — Android emülatör (10.0.2.2), gerçek telefon
/// (PC'nin yerel IP'si), ve bulut. Sabit yazmak her seferinde yeniden
/// derleme demek olurdu.
class Api {
  String taban;
  /// Boşsa başlık gönderilmez — yerel sunucu anahtar beklemiyor.
  final String anahtar;
  Api(this.taban, {this.anahtar = ''});

  Map<String, String> get _basliklar => {
        if (anahtar.isNotEmpty) 'X-API-Anahtar': anahtar,
      };

  static const _kisa = Duration(seconds: 20);
  static const _uzun = Duration(seconds: 240);   // tarama/finansal ilk çekim

  Uri _u(String yol, [Map<String, dynamic>? sorgu]) {
    final t = taban.endsWith('/') ? taban.substring(0, taban.length - 1) : taban;
    return Uri.parse('$t$yol').replace(
      queryParameters: sorgu?.map((k, v) => MapEntry(k, '$v')),
    );
  }

  Never _cevir(Object e) {
    final m = e.toString();
    if (e is TimeoutException) {
      throw const ApiHata('Sunucu zaman aşımına uğradı',
          oneri: 'İlk çalıştırmada veri indirilirken uzun sürebilir. '
              'Birkaç dakika sonra tekrar dene.');
    }
    // Flutter web'de bağlantı hatası SocketException DEĞİL, tarayıcının
    // fetch hatası olarak gelir: "ClientException: Failed to fetch".
    // Bu kalıp eşleşmezse kullanıcı ham istisna metni görür.
    if (m.contains('SocketException') ||
        m.contains('Connection refused') ||
        m.contains('Failed host lookup') ||
        m.contains('Failed to fetch') ||
        m.contains('ClientException') ||
        m.contains('XMLHttpRequest')) {
      throw ApiHata('Sunucuya bağlanılamıyor',
          oneri: 'Sunucu adresi: $taban\n'
              '• PC\'de sunucu çalışıyor mu?\n'
              '• Telefon ve PC aynı Wi-Fi\'da mı?\n'
              '• Ayarlar\'dan adresi kontrol et.');
    }
    throw ApiHata('Beklenmeyen hata', oneri: m.length > 200 ? m.substring(0, 200) : m);
  }

  Future<dynamic> _get(String yol,
      {Map<String, dynamic>? sorgu, bool uzun = false}) async {
    try {
      final c = await http
          .get(_u(yol, sorgu), headers: _basliklar)
          .timeout(uzun ? _uzun : _kisa);
      if (c.statusCode == 200) return jsonDecode(utf8.decode(c.bodyBytes));
      if (c.statusCode == 404) {
        throw ApiHata('Bulunamadı', kod: 404,
            oneri: _detay(c.body) ?? 'Bu hisse için veri yok olabilir.');
      }
      if (c.statusCode == 401) {
        throw const ApiHata('API anahtarı geçersiz',
            kod: 401,
            oneri: 'Sunucu anahtar istiyor. Ayarlar > API anahtarı alanına '
                'dağıtım sırasında verilen anahtarı gir.');
      }
      throw ApiHata('Sunucu hatası (${c.statusCode})',
          kod: c.statusCode, oneri: _detay(c.body));
    } on ApiHata {
      rethrow;
    } catch (e) {
      _cevir(e);
    }
  }

  Future<dynamic> _post(String yol, Map<String, dynamic> govde,
      {bool uzun = false}) async {
    try {
      final c = await http
          .post(_u(yol),
              headers: {'Content-Type': 'application/json', ..._basliklar},
              body: jsonEncode(govde))
          .timeout(uzun ? _uzun : _kisa);
      if (c.statusCode == 200) return jsonDecode(utf8.decode(c.bodyBytes));
      throw ApiHata('Sunucu hatası (${c.statusCode})',
          kod: c.statusCode, oneri: _detay(c.body));
    } on ApiHata {
      rethrow;
    } catch (e) {
      _cevir(e);
    }
  }

  String? _detay(String govde) {
    try {
      final j = jsonDecode(govde);
      return j is Map && j['detail'] != null ? '${j['detail']}' : null;
    } catch (_) {
      return null;
    }
  }

  // ───────────────────────────────────────────── uç noktalar

  Future<Map<String, dynamic>> saglik() async =>
      Map<String, dynamic>.from(await _get('/saglik'));

  Future<Map<String, dynamic>> tarama({
    required double sermaye, bool sadeceSinyal = false,
    String evren = 'bist100', double riskYuzde = 1.5,
    double azamiPozisyon = 35, int adet = 40,
  }) async =>
      Map<String, dynamic>.from(await _get('/tarama', uzun: true, sorgu: {
        'sermaye': sermaye, 'sadece_sinyal': sadeceSinyal,
        'evren_adi': evren, 'risk_yuzde': riskYuzde,
        'azami_pozisyon': azamiPozisyon, 'adet': adet,
      }));

  Future<Map<String, dynamic>> hisse(String sembol,
          {required double sermaye, bool grafik = true}) async =>
      Map<String, dynamic>.from(await _get('/hisse/$sembol',
          uzun: true, sorgu: {'sermaye': sermaye, 'grafik': grafik}));

  Future<Map<String, dynamic>> yapi(String sembol) async =>
      Map<String, dynamic>.from(await _get('/hisse/$sembol/yapi', uzun: true));

  Future<Map<String, dynamic>> sirket(String sembol,
          {bool sektorKiyas = true}) async =>
      Map<String, dynamic>.from(await _get('/hisse/$sembol/sirket',
          uzun: true, sorgu: {'sektor_kiyas': sektorKiyas}));

  /// Bugünün durumuna bağlı tek ders. Sunucu durumsuz olduğu için
  /// okunmuş ders kodları istemciden gider.
  Future<Map<String, dynamic>> gununDersi(
          {int portfoyAdet = 0, List<String> okunan = const []}) async =>
      Map<String, dynamic>.from(await _get('/egitmen/gunun-dersi', sorgu: {
        'portfoy_adet': portfoyAdet,
        'okunan': okunan.join(','),
      }) as Map);

  /// Dersin görseli — canlı veriden. Ayrı çağrı: bazıları yavaş,
  /// ders metni onları beklemesin.
  Future<Map<String, dynamic>> dersGorseli(String kod) async =>
      Map<String, dynamic>.from(
          await _get('/egitmen/gorsel/$kod', uzun: true) as Map);

  // ── Karar defteri. Sunucu pozisyonlar için TEK KAYNAK; telefon
  // yerel kopyayı yalnızca çevrimdışı okumak için saklar.
  Future<Map<String, dynamic>> defter() async =>
      Map<String, dynamic>.from(await _get('/defter') as Map);

  Future<Map<String, dynamic>> defterAlim(Pozisyon p,
          {bool kagit = true, String gerekce = ''}) async =>
      Map<String, dynamic>.from(await _post('/defter/alim', {
        'sembol': p.sembol, 'fiyat': p.giris, 'adet': p.adet,
        'kagit': kagit, 'stop': p.stop, 'hedef': p.hedef, 'gerekce': gerekce,
      }) as Map);

  Future<Map<String, dynamic>> defterSatim(String sembol, double fiyat,
          {int adet = 0, String gerekce = ''}) async =>
      Map<String, dynamic>.from(await _post('/defter/satim', {
        'sembol': sembol, 'fiyat': fiyat, 'adet': adet, 'gerekce': gerekce,
      }) as Map);

  Future<Map<String, dynamic>> makro({bool grafik = false}) async =>
      Map<String, dynamic>.from(
          await _get('/makro', uzun: true, sorgu: {'grafik': grafik}));

  Future<Map<String, dynamic>> sektor() async =>
      Map<String, dynamic>.from(await _get('/sektor', uzun: true));

  Future<Map<String, dynamic>> risk({required double sermaye}) async =>
      Map<String, dynamic>.from(
          await _get('/risk', uzun: true, sorgu: {'sermaye': sermaye}));

  Future<Map<String, dynamic>> dagitim(
          {required double sermaye, String profil = 'dengeli'}) async =>
      Map<String, dynamic>.from(await _get('/dagitim',
          uzun: true, sorgu: {'sermaye': sermaye, 'profil': profil}));

  Future<List<dynamic>> ogrenListe() async =>
      (await _get('/ogren'))['konular'] as List<dynamic>;

  Future<Map<String, dynamic>> ogrenKonu(String konu) async =>
      Map<String, dynamic>.from(await _get('/ogren/$konu'));

  Future<List<dynamic>> tezSorulari() async =>
      (await _get('/tez/sorular'))['sorular'] as List<dynamic>;

  Future<Map<String, dynamic>> tezAnlik(String sembol,
          {required double sermaye}) async =>
      Map<String, dynamic>.from(await _get('/tez/anlik/$sembol',
          uzun: true, sorgu: {'sermaye': sermaye}));

  Future<Map<String, dynamic>> tezKontrol(
          String sembol, Map<String, dynamic> anlik, double sermaye) async =>
      Map<String, dynamic>.from(await _post('/tez/kontrol', uzun: true,
          {'sembol': sembol, 'anlik': anlik, 'sermaye': sermaye}));

  Future<Map<String, dynamic>> portfoyKontrol(
          List<Pozisyon> pozlar, double sermaye) async =>
      Map<String, dynamic>.from(await _post('/portfoy/kontrol', uzun: true, {
        'pozisyonlar': pozlar.map((p) => p.toJson()).toList(),
        'sermaye': sermaye,
      }));

  Future<Map<String, dynamic>> alimKontrol({
    required String sembol, required int adet, required double fiyat,
    required double sermaye, required bool tezVarMi,
    required List<Pozisyon> acik, List<Map<String, dynamic>> gecmis = const [],
  }) async =>
      Map<String, dynamic>.from(await _post('/alim/kontrol', uzun: true, {
        'sembol': sembol, 'adet': adet, 'fiyat': fiyat, 'sermaye': sermaye,
        'tez_var_mi': tezVarMi,
        'acik_pozisyonlar': acik.map((p) => p.toJson()).toList(),
        'gecmis_getiriler': gecmis,
      }));

  Future<Map<String, dynamic>> riskPortfoy(List<Pozisyon> pozlar) async =>
      Map<String, dynamic>.from(await _post('/risk/portfoy', uzun: true,
          {'pozisyonlar': pozlar.map((p) => p.toJson()).toList()}));

  Future<String> backtestBaslat(
      {String? strateji, required double sermaye, int gun = 1200}) async {
    final r = await _post('/backtest',
        {'strateji': strateji, 'sermaye': sermaye, 'gun': gun});
    return r['is_id'] as String;
  }

  Future<Map<String, dynamic>> backtestSonuc(String isId) async =>
      Map<String, dynamic>.from(await _get('/backtest/$isId', uzun: true));

  // ── eğitmen ──
  Future<Map<String, dynamic>> egitmenSorular() async =>
      Map<String, dynamic>.from(await _get('/egitmen/sorular', uzun: true));

  Future<Map<String, dynamic>> egitmenCanli(
          {required double sermaye, int azami = 3,
          List<Pozisyon> pozisyonlar = const []}) async =>
      Map<String, dynamic>.from(await _post('/egitmen/canli', uzun: true, {
        'sermaye': sermaye, 'azami': azami,
        'pozisyonlar': pozisyonlar.map((p) => p.toJson()).toList(),
      }));

  // ── günlük iş ──
  Future<Map<String, dynamic>> gunlukOzet({String? tarih}) async =>
      Map<String, dynamic>.from(await _get('/gunluk/ozet',
          uzun: true, sorgu: tarih == null ? null : {'tarih': tarih}));

  Future<Map<String, dynamic>> gunlukHisse(String sembol, {int gun = 15}) async =>
      Map<String, dynamic>.from(
          await _get('/gunluk/hisse/$sembol', uzun: true, sorgu: {'gun': gun}));

  Future<Map<String, dynamic>> gunlukKarne() async =>
      Map<String, dynamic>.from(await _get('/gunluk/karne', uzun: true));

  Future<Map<String, dynamic>> gunlukHaberler({int azami = 40}) async =>
      Map<String, dynamic>.from(
          await _get('/gunluk/haberler', uzun: true, sorgu: {'azami': azami}));

  Future<Map<String, dynamic>> egitmenMufredat() async =>
      Map<String, dynamic>.from(await _get('/egitmen/mufredat', uzun: true));

  Future<Map<String, dynamic>> egitmenDers(String kod) async =>
      Map<String, dynamic>.from(await _get('/egitmen/ders/$kod', uzun: true));

  Future<Map<String, dynamic>> egitmenSirketOku(String sembol) async =>
      Map<String, dynamic>.from(
          await _get('/egitmen/sirket-oku/$sembol', uzun: true));
}
