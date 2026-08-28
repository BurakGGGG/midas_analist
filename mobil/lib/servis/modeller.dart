/// Cihazda saklanan veri modelleri.
/// Sunucu DURUMSUZDUR: pozisyon ve tezler burada yaşar, sunucuya yalnızca
/// hesaplanması için gönderilir. Böylece sunucu kapalıyken de geçmişini görürsün.
library;

import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class Pozisyon {
  final String sembol;
  final int adet;
  final double giris, stop, hedef;
  final String tarih;      // ISO gün
  final String strateji;

  const Pozisyon({
    required this.sembol, required this.adet, required this.giris,
    required this.stop, required this.hedef, required this.tarih,
    this.strateji = 'kirilim',
  });

  double get maliyet => adet * giris;

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris, 'stop': stop,
        'hedef': hedef, 'tarih': tarih, 'strateji': strateji,
      };

  factory Pozisyon.fromJson(Map<String, dynamic> j) => Pozisyon(
        sembol: j['sembol'] as String,
        adet: (j['adet'] as num).toInt(),
        giris: (j['giris'] as num).toDouble(),
        stop: (j['stop'] as num).toDouble(),
        hedef: (j['hedef'] as num).toDouble(),
        tarih: j['tarih'] as String,
        strateji: (j['strateji'] ?? 'kirilim') as String,
      );

  Pozisyon stopIle(double yeniStop) => Pozisyon(
        sembol: sembol, adet: adet, giris: giris, stop: yeniStop,
        hedef: hedef, tarih: tarih, strateji: strateji,
      );
}

class Tez {
  final String sembol, tarih;
  final double fiyat;
  final int adet;
  final Map<String, String> cevaplar;
  final Map<String, dynamic> anlik;   // alım anındaki objektif görüntü
  final Map<String, dynamic>? kapanis;

  const Tez({
    required this.sembol, required this.tarih, required this.fiyat,
    this.adet = 0, this.cevaplar = const {}, this.anlik = const {},
    this.kapanis,
  });

  bool get acik => kapanis == null;

  /// Tezin en kritik alanı. Boşsa, düşüşte neden tuttuğunu bilemezsin.
  String get yanilmaKosulu => cevaplar['yanilma_kosulu'] ?? '';

  List<String> eksikler(List<Map<String, String>> sorular) => sorular
      .where((s) => (cevaplar[s['anahtar']] ?? '').trim().isEmpty)
      .map((s) => s['soru']!)
      .toList();

  /// Tez tam mı? Soru listesi YOKSA cevap "bilinmiyor" — false döner.
  ///
  /// Neden ayrı bir metot: `eksikler(bosListe)` boş liste döndürüyor ve
  /// çağıran bunu "eksik yok, demek ki tam" diye okuyordu. Soru listesi
  /// yalnızca Tez yaz ekranında dolduğu için, Tezler sekmesine oradan
  /// geçmeden giren kullanıcıya BOŞ bir tez bile "TAM" görünüyordu.
  /// Doğrulayamadığın şeye tam demek, eksik demekten kötü.
  bool tamMi(List<Map<String, String>> sorular) =>
      sorular.isNotEmpty && eksikler(sorular).isEmpty;

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'tarih': tarih, 'fiyat': fiyat, 'adet': adet,
        'cevaplar': cevaplar, 'anlik': anlik, 'kapanis': kapanis,
      };

  factory Tez.fromJson(Map<String, dynamic> j) => Tez(
        sembol: j['sembol'] as String,
        tarih: j['tarih'] as String,
        fiyat: (j['fiyat'] as num).toDouble(),
        adet: ((j['adet'] ?? 0) as num).toInt(),
        cevaplar: Map<String, String>.from(j['cevaplar'] ?? {}),
        anlik: Map<String, dynamic>.from(j['anlik'] ?? {}),
        kapanis: j['kapanis'] == null
            ? null
            : Map<String, dynamic>.from(j['kapanis']),
      );

  Tez kapat(double cikis, String sebep, String ders) {
    final getiri = fiyat > 0 ? (cikis / fiyat - 1) * 100 : 0.0;
    return Tez(
      sembol: sembol, tarih: tarih, fiyat: fiyat, adet: adet,
      cevaplar: cevaplar, anlik: anlik,
      kapanis: {
        'tarih': DateTime.now().toIso8601String().substring(0, 10),
        'fiyat': cikis, 'getiri_yuzde': getiri,
        'kar_tl': (cikis - fiyat) * adet, 'sebep': sebep, 'ders': ders,
      },
    );
  }
}

/// Varsayılan sunucu adresi platforma göre değişir:
///   Android emülatör  -> 10.0.2.2  (emülatörden ana makineye giden özel IP)
///   web / masaüstü    -> 127.0.0.1
/// Gerçek telefonda kullanıcı PC'nin yerel IP'sini Ayarlar'dan girer.
String varsayilanSunucu() {
  if (kIsWeb) return 'http://127.0.0.1:8000';
  try {
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
  } catch (_) {}
  return 'http://127.0.0.1:8000';
}

/// Sermaye defteri kaydı.
///
/// Neden defter: "portföyüm 1.400 TL" tek başına hiçbir şey söylemez —
/// 1.000 yatırıp 400 kazanmış da olabilirsin, 1.400 yatırıp sıfır kâr etmiş
/// de. Para giriş/çıkışını gerçekleşen kâr/zarardan AYRI tutmazsan kendi
/// performansını göremezsin. En sık yapılan öz-aldatma budur.
enum HareketTur {
  yatirma,    // hesaba para ekledin
  cekme,      // hesaptan para çektin
  kar,        // pozisyon kârla kapandı (gerçekleşen)
  zarar,      // pozisyon zararla kapandı (gerçekleşen)
  duzeltme,   // "toplamım aslında şu kadar" — elle hizalama
}

class ParaHareketi {
  final String tarih;      // ISO gün
  final double tutar;      // işaretli: +giriş / -çıkış
  final HareketTur tur;
  final String not;

  const ParaHareketi({
    required this.tarih,
    required this.tutar,
    required this.tur,
    this.not = '',
  });

  /// Yalnızca yatırma/çekme "senin koyduğun para"dır.
  /// Kâr/zarar sermayeyi değiştirir ama yatırdığın parayı değiştirmez.
  bool get sermayeGirisi =>
      tur == HareketTur.yatirma || tur == HareketTur.cekme;

  String get etiket => switch (tur) {
        HareketTur.yatirma => 'Para yatırma',
        HareketTur.cekme => 'Para çekme',
        HareketTur.kar => 'Gerçekleşen kâr',
        HareketTur.zarar => 'Gerçekleşen zarar',
        HareketTur.duzeltme => 'Elle düzeltme',
      };

  Map<String, dynamic> toJson() =>
      {'tarih': tarih, 'tutar': tutar, 'tur': tur.name, 'not': not};

  factory ParaHareketi.fromJson(Map<String, dynamic> j) => ParaHareketi(
        tarih: j['tarih'] as String,
        tutar: (j['tutar'] as num).toDouble(),
        tur: HareketTur.values.firstWhere(
          (t) => t.name == j['tur'],
          orElse: () => HareketTur.duzeltme,
        ),
        not: (j['not'] ?? '') as String,
      );
}

class Ayarlar {
  final String sunucu;
  /// Bulut dağıtımında zorunlu, yerel ağda boş kalır.
  final String apiAnahtar;
  final double sermaye;
  final double riskYuzde;
  final double azamiPozisyon;
  final int azamiEsZamanli;

  Ayarlar({
    String? sunucu,
    this.apiAnahtar = '',
    this.sermaye = 1000,
    this.riskYuzde = 1.5,
    this.azamiPozisyon = 35,
    this.azamiEsZamanli = 4,
  }) : sunucu = sunucu ?? _varsayilan;

  static final String _varsayilan = varsayilanSunucu();

  Map<String, dynamic> toJson() => {
        'sunucu': sunucu, 'apiAnahtar': apiAnahtar,
        'sermaye': sermaye, 'riskYuzde': riskYuzde,
        'azamiPozisyon': azamiPozisyon, 'azamiEsZamanli': azamiEsZamanli,
      };

  factory Ayarlar.fromJson(Map<String, dynamic> j) => Ayarlar(
        sunucu: (j['sunucu'] ?? varsayilanSunucu()) as String,
        apiAnahtar: (j['apiAnahtar'] ?? '') as String,
        sermaye: ((j['sermaye'] ?? 1000) as num).toDouble(),
        riskYuzde: ((j['riskYuzde'] ?? 1.5) as num).toDouble(),
        azamiPozisyon: ((j['azamiPozisyon'] ?? 35) as num).toDouble(),
        azamiEsZamanli: ((j['azamiEsZamanli'] ?? 4) as num).toInt(),
      );

  Ayarlar kopya({String? sunucu, String? apiAnahtar, double? sermaye,
      double? riskYuzde, double? azamiPozisyon, int? azamiEsZamanli}) =>
      Ayarlar(
        sunucu: sunucu ?? this.sunucu,
        apiAnahtar: apiAnahtar ?? this.apiAnahtar,
        sermaye: sermaye ?? this.sermaye,
        riskYuzde: riskYuzde ?? this.riskYuzde,
        azamiPozisyon: azamiPozisyon ?? this.azamiPozisyon,
        azamiEsZamanli: azamiEsZamanli ?? this.azamiEsZamanli,
      );
}

/// API hatası — arayüz bunu kullanıcıya anlamlı Türkçe olarak gösterir.
class ApiHata implements Exception {
  final String mesaj;
  final String? oneri;
  final int? kod;
  const ApiHata(this.mesaj, {this.oneri, this.kod});
  @override
  String toString() => mesaj;
}
