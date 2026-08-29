import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'depo.dart';

/// Hisse arama — "thy" yazınca THYAO çıkar.
///
/// LİSTE BİR KEZ İNİYOR, ARAMA TELEFONDA. Tuş başına ağ isteği kabul
/// edilemez: sunucu Oracle ARM'da, telefon mobil şebekede; ilk harfte
/// 200 ms gecikme aramayı ölü hissettirir. Liste gzip'li ~21 KB ve
/// çevrimdışı da çalışıyor.
///
/// `surum` sunucudan geliyor; sabitten büyükse liste yeniden iniyor.
/// (Sözlük ve müfredat ile aynı kalıp.)
class Sembol {
  final String kod;      // THYAO
  final String ad;       // Türk Hava Yolları
  final bool izleniyor;  // sistemin takip ettiği evrende mi
  final List<String> terimler;   // SUNUCUDA normalize edilmiş arama metinleri

  const Sembol({
    required this.kod, required this.ad,
    required this.izleniyor, required this.terimler,
  });

  factory Sembol.fromJson(Map<String, dynamic> j) => Sembol(
        kod: '${j['k']}',
        ad: '${j['a']}',
        izleniyor: ((j['i'] ?? 0) as num).toInt() == 1,
        terimler: ((j['n'] ?? []) as List).map((e) => '$e').toList(),
      );

  Map<String, dynamic> toJson() =>
      {'k': kod, 'a': ad, 'i': izleniyor ? 1 : 0, 'n': terimler};
}

/// Türkçe sadeleştirme — SORGU İÇİN.
///
/// Kayıtlardaki `terimler` sunucuda normalize edilmiş halde geliyor;
/// burada yalnızca kullanıcının yazdığı sorgu sadeleştiriliyor. Sebep
/// ölçüldü: Python'da `'İ'.lower()` İKİ kod noktası üretiyor (i +
/// birleşen nokta), Dart'ta TEK rune. Aynı işlemi iki dilde ayrı yazmak
/// sessizce farklı sonuç verir.
///
/// Bu yüzden `.toUpperCase()`'e güvenilmiyor: harf harf açık eşleme
/// yapılıyor ve çıktının Python'unkiyle birebir aynı olduğu
/// test/semboller_test.dart'ta ORTAK bir örnek dosyasıyla kilitleniyor
/// (testler/normalize_ornekleri.json).
String normalize(String metin) {
  if (metin.isEmpty) return '';
  const harita = {
    'İ': 'I', 'ı': 'I', 'i': 'I', 'I': 'I',
    'Ş': 'S', 'ş': 'S',
    'Ğ': 'G', 'ğ': 'G',
    'Ü': 'U', 'ü': 'U',
    'Ö': 'O', 'ö': 'O',
    'Ç': 'C', 'ç': 'C',
    // Şapkalı ünlüler: Python tarafında NFKD ile düşüyor, burada elle.
    'Â': 'A', 'â': 'A', 'Î': 'I', 'î': 'I', 'Û': 'U', 'û': 'U',
  };
  final b = StringBuffer();
  for (final r in metin.runes) {
    final k = String.fromCharCode(r);
    b.write(harita[k] ?? k.toUpperCase());
  }
  return b.toString().replaceAll(RegExp(r'\s+'), ' ');
}

class SembolDeposu extends ChangeNotifier {
  static const anahtar = 'semboller_v1';
  static const surumAnahtar = 'semboller_surum_v1';

  /// Sunucudaki `surum` bundan büyükse liste yeniden iner.
  /// ARTIRMAYI UNUTMA: yeni hisse eklendiğinde telefon eski listeyle
  /// kalır ve kullanıcı aradığını bulamaz.
  static const beklenenSurum = 1;

  List<Sembol> hisseler = [];
  int surum = 0;

  bool get hazir => hisseler.isNotEmpty && surum >= beklenenSurum;

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    try {
      final ham = p.getString(anahtar);
      if (ham != null) {
        hisseler = (jsonDecode(ham) as List)
            .map((e) => Sembol.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        surum = p.getInt(surumAnahtar) ?? 0;
      }
    } catch (_) {
      hisseler = [];
      surum = 0;
    }
    notifyListeners();
  }

  /// Gerekiyorsa sunucudan indirir. Ağ hatasında SESSİZ kalır:
  /// eski liste, hiç liste olmamasından iyidir ve arama kutusu
  /// bir ağ hatası yüzünden kırmızıya dönmemeli.
  Future<void> tazele({bool zorla = false}) async {
    if (hazir && !zorla) return;
    try {
      final r = await depo.api.semboller();
      final gelen = ((r['hisseler'] ?? []) as List)
          .map((e) => Sembol.fromJson(Map<String, dynamic>.from(e)))
          .toList();
      if (gelen.isEmpty) return;
      hisseler = gelen;
      surum = ((r['surum'] ?? 0) as num).toInt();
      final p = await SharedPreferences.getInstance();
      await p.setString(
          anahtar, jsonEncode(hisseler.map((x) => x.toJson()).toList()));
      await p.setInt(surumAnahtar, surum);
      notifyListeners();
    } catch (_) {
      // sessiz
    }
  }

  /// Arama. SIRALAMA KURALLARI SUNUCUDAKİYLE AYNI
  /// (cekirdek/semboller.py `ara`/`_puan`/`_sira`). İkisi ayrışırsa
  /// aynı sorgu iki yerde farklı sonuç verir; iki testte de aynı
  /// örnekler kullanılıyor.
  List<Sembol> ara(String sorgu, {int azami = 10}) {
    final q = normalize(sorgu).trim();
    if (q.isEmpty) return const [];

    final puanli = <({List<Object> sira, Sembol s})>[];
    for (final s in hisseler) {
      final p = _puan(q, s);
      if (p == null) continue;
      puanli.add((
        sira: [p == 0 ? 0 : 1, s.izleniyor ? -1 : 0, p, s.kod],
        s: s,
      ));
    }
    puanli.sort((a, b) => _karsilastir(a.sira, b.sira));
    return puanli.take(azami).map((e) => e.s).toList();
  }

  static int _karsilastir(List<Object> a, List<Object> b) {
    for (var i = 0; i < a.length; i++) {
      final x = a[i], y = b[i];
      final c = (x is int && y is int)
          ? x.compareTo(y)
          : '$x'.compareTo('$y');
      if (c != 0) return c;
    }
    return 0;
  }

  /// Küçük puan = üstte. null = eşleşmedi.
  static int? _puan(String q, Sembol s) {
    if (s.kod == q) return 0;              // tam kod
    if (s.kod.startsWith(q)) return 1;     // kod ön eki: "thy" → THYAO
    int? enIyi;
    void dene(int p) => enIyi = (enIyi == null || p < enIyi!) ? p : enIyi;
    for (final t in s.terimler) {
      if (t == s.kod) continue;
      if (t == q) {
        dene(2);
      } else if (t.startsWith(q)) {
        dene(3);
      } else if (t.split(' ').any((w) => w.startsWith(q))) {
        dene(4);
      } else if (t.contains(q)) {
        dene(5);
      }
    }
    if (enIyi == null && s.kod.contains(q)) return 6;
    return enIyi;
  }
}

final semboller = SembolDeposu();
