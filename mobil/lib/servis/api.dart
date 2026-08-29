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
      {Map<String, dynamic>? sorgu, bool uzun = false, String? jeton}) async {
    try {
      final c = await http
          .get(_u(yol, sorgu), headers: {
            ..._basliklar,
            if (jeton != null) 'Authorization': 'Bearer $jeton',
          })
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
      {bool uzun = false, String? jeton}) async {
    try {
      final c = await http
          .post(_u(yol),
              headers: {
                'Content-Type': 'application/json',
                ..._basliklar,
                if (jeton != null) 'Authorization': 'Bearer $jeton',
              },
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

  Future<dynamic> _sil(String yol) async {
    try {
      final c = await http
          .delete(_u(yol), headers: _basliklar)
          .timeout(_kisa);
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

  // ── hesap ve bulut yedeği
  //
  // Hepsi API anahtarının ARKASINDA: anahtar başlığı _basliklar'dan gelir,
  // jeton onun üstüne eklenir. İkisinden biri eksikse sunucu 401 döner.

  Future<Map<String, dynamic>> hesapKayit(
          String eposta, String parola, String cihaz) async =>
      Map<String, dynamic>.from(await _post('/hesap/kayit',
          {'eposta': eposta, 'parola': parola, 'cihaz': cihaz}, uzun: true));

  Future<Map<String, dynamic>> hesapGiris(
          String eposta, String parola, String cihaz) async =>
      Map<String, dynamic>.from(await _post('/hesap/giris',
          {'eposta': eposta, 'parola': parola, 'cihaz': cihaz}, uzun: true));

  Future<void> hesapCikis(String jeton) async =>
      await _post('/hesap/cikis', const {}, jeton: jeton);

  Future<Map<String, dynamic>> hesapBilgi(String jeton) async =>
      Map<String, dynamic>.from(await _get('/hesap', jeton: jeton));

  Future<Map<String, dynamic>> hesapParola(
          String jeton, String eski, String yeni) async =>
      Map<String, dynamic>.from(await _post(
          '/hesap/parola', {'eski': eski, 'yeni': yeni},
          jeton: jeton, uzun: true));

  Future<Map<String, dynamic>> widgetVeri(
          List<Pozisyon> pozlar, double sermaye) async =>
      Map<String, dynamic>.from(await _post('/widget', {
        'pozisyonlar': pozlar.map((p) => p.toJson()).toList(),
        'sermaye': sermaye,
      }, uzun: true));

  // ── alıştırma kum havuzu
  Future<Map<String, dynamic>> alistirmaGun(String sembol,
          {String? tarih}) async =>
      Map<String, dynamic>.from(await _get('/alistirma/gun', uzun: true,
          sorgu: {'sembol': sembol, if (tarih != null) 'tarih': tarih}));

  Future<Map<String, dynamic>> alistirmaAdet(
          double bakiye, double fiyat, double stop) async =>
      Map<String, dynamic>.from(await _get('/alistirma/adet',
          sorgu: {'bakiye': bakiye, 'fiyat': fiyat, 'stop': stop}));

  Future<Map<String, dynamic>> cihazKaydet(
          String oturum, String pushJetonu, String platform) async =>
      Map<String, dynamic>.from(await _post(
          '/cihaz', {'jeton': pushJetonu, 'platform': platform},
          jeton: oturum));

  Future<void> cihazSil(String oturum, String pushJetonu) async {
    final c = await http.delete(
        _u('/cihaz', {'jeton': pushJetonu}),
        headers: {..._basliklar, 'Authorization': 'Bearer $oturum'}).timeout(_kisa);
    if (c.statusCode != 200) {
      throw ApiHata('Cihaz kaydı silinemedi (${c.statusCode})', kod: c.statusCode);
    }
  }

  Future<Map<String, dynamic>> bildirimDurum(String oturum) async =>
      Map<String, dynamic>.from(await _get('/bildirim/durum', jeton: oturum));

  Future<Map<String, dynamic>> yedekGetir(String jeton) async =>
      Map<String, dynamic>.from(await _get('/yedek', jeton: jeton, uzun: true));

  Future<Map<String, dynamic>> yedekKoy(String jeton, Map<String, dynamic> icerik,
      {required String cihaz, int? beklenenSurum}) async {
    final c = await http
        .put(_u('/yedek'),
            headers: {
              'Content-Type': 'application/json',
              ..._basliklar,
              'Authorization': 'Bearer $jeton',
            },
            body: jsonEncode({
              'icerik': icerik,
              'cihaz': cihaz,
              if (beklenenSurum != null) 'beklenen_surum': beklenenSurum,
            }))
        .timeout(_uzun);
    if (c.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(utf8.decode(c.bodyBytes)));
    }
    throw ApiHata('Yedek gönderilemedi (${c.statusCode})',
        kod: c.statusCode, oneri: _detay(c.body));
  }

  Future<Map<String, dynamic>> sozluk() async =>
      Map<String, dynamic>.from(await _get('/sozluk'));

  /// Aranabilir hisse listesi. Sözlük gibi bir kez inip saklanır.
  Future<Map<String, dynamic>> semboller() async =>
      Map<String, dynamic>.from(await _get('/semboller'));

  // ── izleme listesi ───────────────────────────────────────────────────
  // Sahip OLMADIĞIN, beklediğin hisseler. Sunucuda yaşıyor: alarm
  // 5 dakikalık işte kontrol ediliyor ve telefon kapalıyken de
  // çalışması gerekiyor.

  Future<Map<String, dynamic>> izlemeListesi() async =>
      Map<String, dynamic>.from(await _get('/izleme'));

  Future<Map<String, dynamic>> izlemeEkle(String sembol,
          {double alt = 0, double ust = 0, String not = ''}) async =>
      Map<String, dynamic>.from(await _post('/izleme', {
        'sembol': sembol, 'alt': alt, 'ust': ust, 'not': not,
      }));

  Future<void> izlemeSil(String sembol) async =>
      _sil('/izleme/$sembol');

  /// Haber sicili — haber fiyatı gerçekten hareket ettiriyor mu?
  Future<Map<String, dynamic>> haberSicil({int gun = 180}) async =>
      Map<String, dynamic>.from(
          await _get('/haber-sicil', uzun: true, sorgu: {'gun': '$gun'}));

  /// Bilanço, temettü, genel kurul ve ekonomi takvimi.
  Future<Map<String, dynamic>> takvim(
          {List<String> semboller = const [], int gun = 120}) async =>
      Map<String, dynamic>.from(await _get('/takvim', sorgu: {
        if (semboller.isNotEmpty) 'semboller': semboller.join(','),
        'gun': '$gun',
      }));

  /// Bedelsiz / sermaye artırımı bildirimleri. `semboller` boşsa
  /// sunucunun izlediği hisseler kullanılır.
  Future<Map<String, dynamic>> sermayeIslemleri(
          {List<String> semboller = const [], int gun = 30}) async =>
      Map<String, dynamic>.from(await _get('/sermaye-islemleri', sorgu: {
        if (semboller.isNotEmpty) 'semboller': semboller.join(','),
        'gun': '$gun',
      }));

  // ── Sanal İşlem oyunu ────────────────────────────────────────────────

  Future<Map<String, dynamic>> oyunZorluklar() async =>
      Map<String, dynamic>.from(await _get('/oyun/zorluklar'));

  /// Bir oyunun tamamı. `tohum` verilmezse yeni oyun üretilir.
  Future<Map<String, dynamic>> oyunUret({int? tohum,
          String zorluk = 'normal'}) async =>
      Map<String, dynamic>.from(await _get('/oyun/uret', uzun: true, sorgu: {
        if (tohum != null) 'tohum': '$tohum',
        'zorluk': zorluk,
      }));

  // ── Sanal İşlem ──────────────────────────────────────────────────────
  // Hepsi durumsuz: bakiye ve pozisyonlar gövdede gidiyor.

  Future<Map<String, dynamic>> sanalAralik() async =>
      Map<String, dynamic>.from(await _get('/alistirma/aralik'));

  Future<Map<String, dynamic>> sanalAdim(
          String tarih, double nakit, List<Map<String, dynamic>> pozisyonlar,
          {int adim = 1, List<String> izlenen = const []}) async =>
      Map<String, dynamic>.from(await _post('/alistirma/adim', {
        'tarih': tarih, 'nakit': nakit, 'adim': adim,
        'pozisyonlar': pozisyonlar, 'izlenen': izlenen,
      }, uzun: true));

  Future<Map<String, dynamic>> sanalDeger(String tarih, double nakit,
          List<Map<String, dynamic>> pozisyonlar) async =>
      Map<String, dynamic>.from(await _post('/alistirma/deger', {
        'tarih': tarih, 'nakit': nakit, 'pozisyonlar': pozisyonlar,
      }, uzun: true));

  Future<Map<String, dynamic>> sanalAl(
          String sembol, String tarih, int adet, double nakit) async =>
      Map<String, dynamic>.from(await _post('/alistirma/al', {
        'sembol': sembol, 'tarih': tarih, 'adet': adet, 'nakit': nakit,
      }, uzun: true));

  Future<Map<String, dynamic>> sanalSat(
          String tarih, Map<String, dynamic> pozisyon, {int adet = 0}) async =>
      Map<String, dynamic>.from(await _post('/alistirma/sat', {
        'tarih': tarih, 'pozisyon': pozisyon, 'adet': adet,
      }, uzun: true));

  Future<Map<String, dynamic>> sanalSeri(String sembol,
          {String? baslangic, String? bitis, int azami = 120}) async =>
      Map<String, dynamic>.from(await _get('/alistirma/seri', uzun: true,
          sorgu: {
            'sembol': sembol,
            if (baslangic != null) 'baslangic': baslangic,
            if (bitis != null) 'bitis': bitis,
            'azami': '$azami',
          }));

  Future<Map<String, dynamic>> sanalSinyaller(String tarih,
          {double sermaye = 10000, int azami = 8}) async =>
      Map<String, dynamic>.from(await _get('/alistirma/sinyaller', uzun: true,
          sorgu: {'tarih': tarih, 'sermaye': '$sermaye', 'azami': '$azami'}));

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
