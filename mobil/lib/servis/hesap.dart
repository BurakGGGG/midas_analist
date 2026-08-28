import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'alistirma.dart' show kum;
import 'depo.dart';
import 'egitmen.dart';
import 'modeller.dart';

/// Hesap ve bulut yedeği.
///
/// NEDEN: telefon yeniden kurulduğunda portföy, tezler, karar defteri,
/// sermaye defteri ve eğitim ilerlemesi gidiyordu. Bunlar yeniden
/// üretilemeyen veriler.
///
/// NE YEDEKLENİR: ham SharedPreferences metinleri. Model nesnelerini
/// yeniden serileştirmek yerine kayıtlı JSON'u olduğu gibi taşımak, model
/// alanları değiştikçe yedeği bozulmaktan kurtarır — geri yükleme, uygulama
/// kapanıp açılmış gibi davranır.
///
/// NE YEDEKLENMEZ: müfredat, soru bankası ve sözlük. Üçü de sunucudan
/// yeniden inebiliyor; yedekte yer kaplamaları anlamsız ve sürümleri
/// eskiterek zarar bile verebilir.
///
/// API ANAHTARI YEDEĞE GİRMEZ. Yeni telefonda sunucuya ulaşmak için onu
/// zaten elle giriyorsun; buluta koymak fayda getirmeden bir kimlik
/// bilgisini daha çoğaltırdı.
class Hesap extends ChangeNotifier {
  static const _kJeton = 'hesap_jeton_v1';
  static const _kEposta = 'hesap_eposta_v1';
  static const _kSurum = 'hesap_yedek_surum_v1';
  static const _kSonYedek = 'hesap_son_yedek_v1';

  /// Buluta taşınan anahtarlar. Sıralama önemsiz, kapsam önemli.
  static const yedeklenen = <String>[
    'pozisyonlar_v1',
    'tezler_v1',
    'ayarlar_v1',
    'para_hareketleri_v1',
    'egitmen_ilerleme_v1',
    'egitmen_ders_v1',
    // Alıştırma kum havuzu: sanal bakiye, pozisyonlar ve görev
    // ilerlemesi. Yeniden üretilemez — telefonu değiştirince görevleri
    // baştan yapmak istemezsin.
    'alistirma_v1',
  ];

  String? jeton;
  String? eposta;
  int surum = 0;
  String? sonYedek;
  bool yedekleniyor = false;

  bool get girisli => (jeton ?? '').isNotEmpty;

  Timer? _gecikme;

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    jeton = p.getString(_kJeton);
    eposta = p.getString(_kEposta);
    surum = p.getInt(_kSurum) ?? 0;
    sonYedek = p.getString(_kSonYedek);
    notifyListeners();
  }

  Future<void> _oturumYaz(Map<String, dynamic> o) async {
    final p = await SharedPreferences.getInstance();
    jeton = '${o['jeton']}';
    eposta = '${o['eposta']}';
    await p.setString(_kJeton, jeton!);
    await p.setString(_kEposta, eposta!);
    notifyListeners();
  }

  // ── oturum ───────────────────────────────────────────────────────────────

  Future<void> kayit(String e, String parola) async =>
      _oturumYaz(await depo.api.hesapKayit(e, parola, _cihaz));

  Future<void> giris(String e, String parola) async =>
      _oturumYaz(await depo.api.hesapGiris(e, parola, _cihaz));

  Future<void> cikis() async {
    final j = jeton;
    // Sunucuya haber vermek en iyi çabadır: ulaşılamıyorsa da yerel
    // oturum düşmeli, yoksa kullanıcı çıkamaz.
    if (j != null) {
      try {
        await depo.api.hesapCikis(j);
      } catch (_) {}
    }
    final p = await SharedPreferences.getInstance();
    await p.remove(_kJeton);
    await p.remove(_kEposta);
    await p.remove(_kSurum);
    await p.remove(_kSonYedek);
    jeton = eposta = sonYedek = null;
    surum = 0;
    notifyListeners();
  }

  Future<Map<String, dynamic>> bilgi() async {
    if (!girisli) throw const ApiHata('Önce giriş yap');
    return depo.api.hesapBilgi(jeton!);
  }

  Future<void> parolaDegistir(String eski, String yeni) async {
    if (!girisli) throw const ApiHata('Önce giriş yap');
    await depo.api.hesapParola(jeton!, eski, yeni);
    // Sunucu tüm oturumları düşürdü; elimizdeki jeton artık ölü.
    await cikis();
  }

  // ── yedekleme ────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> _topla() async {
    final p = await SharedPreferences.getInstance();
    final icerik = <String, dynamic>{};
    for (final k in yedeklenen) {
      final v = p.getString(k);
      if (v == null) continue;
      if (k == 'ayarlar_v1') {
        // API anahtarını buluta taşıma — bkz. sınıf notu.
        try {
          final a = Map<String, dynamic>.from(jsonDecode(v) as Map);
          a.remove('apiAnahtar');
          icerik[k] = jsonEncode(a);
          continue;
        } catch (_) {}
      }
      icerik[k] = v;
    }
    return icerik;
  }

  /// Buluta yazar. Sunucudaki sürüm daha yeniyse yazmaz ve `cakisma: true`
  /// döner — çağıran kullanıcıya sorar.
  Future<Map<String, dynamic>> yedekle({bool zorla = false}) async {
    if (!girisli) throw const ApiHata('Önce giriş yap');
    yedekleniyor = true;
    notifyListeners();
    try {
      final r = await depo.api.yedekKoy(jeton!, await _topla(),
          cihaz: _cihaz, beklenenSurum: zorla ? null : surum);
      if (r['yazildi'] == true) {
        final p = await SharedPreferences.getInstance();
        surum = (r['surum'] as num).toInt();
        sonYedek = '${r['guncelleme']}';
        await p.setInt(_kSurum, surum);
        await p.setString(_kSonYedek, sonYedek!);
      }
      return r;
    } finally {
      yedekleniyor = false;
      notifyListeners();
    }
  }

  /// Buluttaki yedeği telefona yazar ve servisleri yeniden yükler.
  /// ÜZERİNE YAZAR — çağıran onay almış olmalı.
  Future<Map<String, dynamic>> geriYukle() async {
    if (!girisli) throw const ApiHata('Önce giriş yap');
    final y = await depo.api.yedekGetir(jeton!);
    if (y['var'] != true) return {'geri_yuklendi': false, 'not': 'Bulutta yedek yok'};

    final icerik = Map<String, dynamic>.from(y['icerik'] as Map);
    final p = await SharedPreferences.getInstance();
    var yazilan = 0;
    for (final k in yedeklenen) {
      final v = icerik[k];
      if (v is! String) continue;
      if (k == 'ayarlar_v1') {
        // Yedekte API anahtarı yok; mevcut anahtarı KORU, yoksa geri
        // yükledikten sonra uygulama sunucuya ulaşamaz hale gelir.
        try {
          final yeni = Map<String, dynamic>.from(jsonDecode(v) as Map);
          yeni['apiAnahtar'] = depo.ayarlar.apiAnahtar;
          await p.setString(k, jsonEncode(yeni));
          yazilan++;
          continue;
        } catch (_) {}
      }
      await p.setString(k, v);
      yazilan++;
    }

    surum = (y['surum'] as num?)?.toInt() ?? 0;
    sonYedek = '${y['guncelleme']}';
    await p.setInt(_kSurum, surum);
    await p.setString(_kSonYedek, sonYedek!);

    // Bellekteki durumu tazele: yoksa ekranlar eski veriyi göstermeye
    // devam eder ve bir sonraki yazma geri yüklenen veriyi ezer.
    await depo.yukle();
    await egitmen.yukle();
    // Sanal hesap da tazelenmeli. Bu satır yokken buluttan geri yükleme
    // sonrası sanal portföy bellekte ESKİ hâlinde kalıyordu ve bir
    // sonraki yazma geri yüklenen veriyi eziyordu.
    await kum.yukle();
    notifyListeners();
    return {'geri_yuklendi': true, 'anahtar': yazilan, 'surum': surum};
  }

  // ── otomatik yedek ───────────────────────────────────────────────────────

  /// `depo` her değiştiğinde geciktirmeli yedek alır.
  ///
  /// GECİKME ŞART: alım kaydederken depo birkaç kez arka arkaya bildirim
  /// yayar (pozisyon, para hareketi, tez). Her birinde ağ isteği atmak
  /// hem pili hem sunucuyu yorar; 6 saniyelik sessizlik beklemek bir
  /// kullanıcı eylemini tek yazmaya indirir.
  void otomatikBasla() {
    depo.addListener(_degisti);
  }

  void _degisti() {
    if (!girisli) return;
    _gecikme?.cancel();
    _gecikme = Timer(const Duration(seconds: 6), () async {
      try {
        await yedekle();
      } catch (_) {
        // Sessiz: otomatik yedek başarısız diye kullanıcının işi
        // bölünmemeli. Hesap ekranı son yedek zamanını gösteriyor.
      }
    });
  }

  @override
  void dispose() {
    _gecikme?.cancel();
    depo.removeListener(_degisti);
    super.dispose();
  }

  String get _cihaz => defaultTargetPlatform.name;
}

final hesap = Hesap();
