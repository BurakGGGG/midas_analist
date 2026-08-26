import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'depo.dart';
import 'hesap.dart';

/// Uygulama kilidi — 6 haneli PIN.
///
/// NEYİ KORUR: telefonun açıkken elden ele geçtiği anı. Birinin telefonunu
/// alıp uygulamayı açması, portföyünü, kararlarını ve sermayeni görmesi.
///
/// NEYİ KORUMAZ — ve bunu abartmamak önemli: 6 hane 1.000.000 ihtimal
/// demektir. Cihazın verisini çıkarabilen biri (root'lu telefon, adli
/// kopya) özeti alıp çevrimdışı deneyebilir ve yeterli donanımla kırar.
/// Oradaki asıl koruma Android'in uygulama kumu ve cihaz şifrelemesidir,
/// bu PIN değil. Bu katman bir EKRAN KİLİDİ, şifreleme değil.
///
/// Yine de ucuz savunmalar yapılıyor:
///   · PIN düz saklanmaz — PBKDF2-HMAC-SHA256, rastgele tuz
///   · Deneme sayacı DİSKTE tutulur; uygulamayı öldürmek sıfırlamaz
///   · Yanlış denemede bekleme süresi katlanarak artar
///   · Sabit zamanlı karşılaştırma
///
/// BULUTA GİTMEZ: PIN cihaza özeldir, yedeğe konmaz. Yeni telefonda
/// yeniden kurulur — bir cihaz sırrını sunucuya taşımanın faydası yok.
class Kilit extends ChangeNotifier {
  static const _kTuz = 'kilit_tuz_v1';
  static const _kOzet = 'kilit_ozet_v1';
  static const _kDeneme = 'kilit_deneme_v1';
  static const _kBeklet = 'kilit_beklet_v1';

  static const basamak = 6;

  /// PBKDF2 yineleme sayısı. Telefonda ~yarım saniye: girişi yavaşlatmayacak
  /// ama kaba kuvveti pahalılaştıracak kadar. Daha yükseği PIN ekranını
  /// hissedilir şekilde geciktirirdi ve 6 hanelik bir sırrı yine kurtarmazdı.
  static const _tur = 50000;

  /// Arka planda bu kadar dakikadan uzun kalınca yeniden kilitlenir.
  /// Yalnızca soğuk açılışta kilitlemek işe yaramaz: uygulama günlerce
  /// bellekte kalır ve kilit hiç görünmez.
  static const arkaPlanDakika = 2;

  bool kuruldu = false;
  bool kilitli = false;
  int deneme = 0;
  DateTime? bekletBitis;
  DateTime? _arkaPlan;

  /// Kalan bekleme süresi (saniye). 0 ise giriş denenebilir.
  int get bekleme {
    final b = bekletBitis;
    if (b == null) return 0;
    final k = b.difference(DateTime.now()).inSeconds;
    return k > 0 ? k : 0;
  }

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    kuruldu = (p.getString(_kOzet) ?? '').isNotEmpty;
    deneme = p.getInt(_kDeneme) ?? 0;
    final b = p.getString(_kBeklet);
    bekletBitis = b == null ? null : DateTime.tryParse(b);
    // Kurulu bir kilit varsa uygulama KİLİTLİ açılır. Varsayılanın açık
    // olması, kilidi kurmuş olmanın anlamını yok ederdi.
    kilitli = kuruldu;
    notifyListeners();
  }

  // ── kurma / kaldırma ─────────────────────────────────────────────────────

  static bool gecerliMi(String pin) =>
      pin.length == basamak && RegExp(r'^\d+$').hasMatch(pin);

  Future<void> kur(String pin) async {
    if (!gecerliMi(pin)) throw ArgumentError('PIN $basamak haneli olmalı.');
    final tuz = _tuzUret();
    final p = await SharedPreferences.getInstance();
    await p.setString(_kTuz, base64Encode(tuz));
    await p.setString(_kOzet, base64Encode(_turet(pin, tuz)));
    await _sayaciSifirla(p);
    kuruldu = true;
    kilitli = false;
    notifyListeners();
  }

  Future<bool> degistir(String eski, String yeni) async {
    if (!await dogrula(eski)) return false;
    await kur(yeni);
    return true;
  }

  Future<bool> kaldir(String pin) async {
    if (!await dogrula(pin)) return false;
    final p = await SharedPreferences.getInstance();
    await p.remove(_kTuz);
    await p.remove(_kOzet);
    await _sayaciSifirla(p);
    kuruldu = false;
    kilitli = false;
    notifyListeners();
    return true;
  }

  /// PIN sorulmadan kaldırır. YALNIZCA doğrulanmış bir oturumda
  /// çağrılmalı — `kaldir` bilerek PIN ister, bu ise kullanıcı kilidi az
  /// önce açtıysa aynı şeyi ikinci kez sormamak için var.
  Future<void> zorlaKaldir() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_kTuz);
    await p.remove(_kOzet);
    await _sayaciSifirla(p);
    kuruldu = false;
    kilitli = false;
    notifyListeners();
  }

  /// PIN'i unutanlar için tek çıkış: bulut hesabının parolası.
  /// Hesap yoksa bu yol da yoktur — o durumda uygulamayı kaldırıp
  /// kurmak gerekir ve veri gider. Hesap ekranı bunu söylüyor.
  Future<bool> hesapParolasiylaSifirla(String parola) async {
    final e = hesap.eposta;
    if (e == null || e.isEmpty) return false;
    try {
      // Sunucu doğrularsa yeni bir oturum döner; kilidi açmak için yeterli.
      await depo.api.hesapGiris(e, parola, 'kilit-sifirlama');
    } catch (_) {
      return false;
    }
    final p = await SharedPreferences.getInstance();
    await p.remove(_kTuz);
    await p.remove(_kOzet);
    await _sayaciSifirla(p);
    kuruldu = false;
    kilitli = false;
    notifyListeners();
    return true;
  }

  // ── doğrulama ────────────────────────────────────────────────────────────

  Future<bool> dogrula(String pin) async {
    final p = await SharedPreferences.getInstance();
    if (bekleme > 0) return false;

    final tuzB64 = p.getString(_kTuz);
    final ozetB64 = p.getString(_kOzet);
    if (tuzB64 == null || ozetB64 == null) return false;

    final beklenen = base64Decode(ozetB64);
    final hesaplanan = _turet(pin, base64Decode(tuzB64));

    if (!_esit(beklenen, hesaplanan)) {
      deneme += 1;
      await p.setInt(_kDeneme, deneme);
      final saniye = _bekleme(deneme);
      if (saniye > 0) {
        bekletBitis = DateTime.now().add(Duration(seconds: saniye));
        await p.setString(_kBeklet, bekletBitis!.toIso8601String());
      }
      notifyListeners();
      return false;
    }

    await _sayaciSifirla(p);
    kilitli = false;
    notifyListeners();
    return true;
  }

  /// Yanlış denemede bekleme, katlanarak. İlk dördü serbest — parmak kayar,
  /// insanı ilk hatada 30 saniye bekletmek kilidi düşmanlaştırır.
  static int _bekleme(int deneme) {
    if (deneme < 5) return 0;
    if (deneme == 5) return 30;
    if (deneme == 6) return 60;
    if (deneme == 7) return 300;
    if (deneme == 8) return 900;
    return 1800;
  }

  Future<void> _sayaciSifirla(SharedPreferences p) async {
    deneme = 0;
    bekletBitis = null;
    await p.remove(_kDeneme);
    await p.remove(_kBeklet);
  }

  // ── yaşam döngüsü ────────────────────────────────────────────────────────

  void kilitle() {
    if (!kuruldu) return;
    kilitli = true;
    notifyListeners();
  }

  void arkaPlanaGitti() => _arkaPlan = DateTime.now();

  void oneCikti() {
    if (!kuruldu || kilitli) return;
    final a = _arkaPlan;
    if (a == null) return;
    if (DateTime.now().difference(a).inMinutes >= arkaPlanDakika) kilitle();
    _arkaPlan = null;
  }

  // ── kripto ───────────────────────────────────────────────────────────────

  static Uint8List _tuzUret() {
    final r = Random.secure();
    return Uint8List.fromList(List.generate(16, (_) => r.nextInt(256)));
  }

  /// PBKDF2-HMAC-SHA256. `crypto` paketi HMAC veriyor, türetme döngüsü
  /// burada — RFC 8018'deki tanımın birebir karşılığı.
  static Uint8List _turet(String pin, Uint8List tuz) {
    final hmac = Hmac(sha256, utf8.encode(pin));
    // Tek blok yeterli: SHA-256 zaten 32 bayt üretiyor.
    final ilk = hmac.convert([...tuz, 0, 0, 0, 1]).bytes;
    final sonuc = List<int>.from(ilk);
    var u = ilk;
    for (var i = 1; i < _tur; i++) {
      u = hmac.convert(u).bytes;
      for (var j = 0; j < sonuc.length; j++) {
        sonuc[j] ^= u[j];
      }
    }
    return Uint8List.fromList(sonuc);
  }

  /// Sabit zamanlı karşılaştırma: erken çıkış, doğru basamak sayısını
  /// yanıt süresinden okunur hale getirirdi.
  static bool _esit(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    var fark = 0;
    for (var i = 0; i < a.length; i++) {
      fark |= a[i] ^ b[i];
    }
    return fark == 0;
  }
}

final kilit = Kilit();
