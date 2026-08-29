import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'depo.dart';

/// Sanal İşlem — sanal parayla gerçek fiyatlardan işlem.
///
/// GERÇEK PORTFÖYDEN TAMAMEN AYRI: kendi bakiyesi var, sıfırlanabilir,
/// karar defterine ve sermaye defterine hiç dokunmuyor. Öğrenmek için
/// batırabilmek şart; batırdığın hesap ölçülen hesap olmamalı.
///
/// DURUM TELEFONDA: nakit, pozisyonlar, kapanan işlemler ve özkaynak
/// geçmişi burada yaşıyor ve bulut yedeğine dahil. Sunucu yalnızca fiyat
/// biliyor ve kuralları uyguluyor — API durumsuz kalıyor.
///
/// FİYATLAR DONDURULMUYOR AMA GİRİŞ DONDURULUYOR: sistem temettüye göre
/// düzeltilmiş fiyat saklıyor ve düzeltme katsayısı her yeni temettüde
/// değişiyor. Girişini kaydettiğimiz an sabitliyoruz; kâr/zarar hesabı
/// hep aynı giriş üzerinden gidiyor. Yine de güncel fiyat kayabilir —
/// bu yüzden `baslangicOzkaynak` da saklanıyor ve toplam getiri ondan
/// ölçülüyor, gün gün fiyat farkından değil.
class SanalPozisyon {
  final String sembol, tarih;
  final int adet;
  final double giris, stop, hedef;

  const SanalPozisyon({
    required this.sembol, required this.adet, required this.giris,
    required this.stop, required this.hedef, required this.tarih,
  });

  double get maliyet => adet * giris;
  double get riskTl => adet * (giris - stop);

  SanalPozisyon kopya({int? adet, double? giris, double? stop, double? hedef}) =>
      SanalPozisyon(
        sembol: sembol, adet: adet ?? this.adet, giris: giris ?? this.giris,
        stop: stop ?? this.stop, hedef: hedef ?? this.hedef, tarih: tarih,
      );

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris,
        'stop': stop, 'hedef': hedef, 'tarih': tarih,
      };

  factory SanalPozisyon.fromJson(Map<String, dynamic> j) => SanalPozisyon(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        stop: ((j['stop'] ?? 0) as num).toDouble(),
        hedef: ((j['hedef'] ?? 0) as num).toDouble(),
        tarih: '${j['tarih'] ?? ''}',
      );
}

class SanalIslem {
  final String sembol, girisTarih, cikisTarih, sebep;
  final int adet;
  final double giris, cikis;

  const SanalIslem({
    required this.sembol, required this.adet, required this.giris,
    required this.cikis, required this.girisTarih,
    required this.cikisTarih, required this.sebep,
  });

  double get kar => (cikis - giris) * adet;
  double get karYuzde => giris > 0 ? (cikis / giris - 1) * 100 : 0;

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris, 'cikis': cikis,
        'girisTarih': girisTarih, 'cikisTarih': cikisTarih, 'sebep': sebep,
      };

  factory SanalIslem.fromJson(Map<String, dynamic> j) => SanalIslem(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        cikis: ((j['cikis'] ?? 0) as num).toDouble(),
        girisTarih: '${j['girisTarih'] ?? ''}',
        cikisTarih: '${j['cikisTarih'] ?? ''}',
        sebep: '${j['sebep'] ?? ''}',
      );
}

class SanalHesap extends ChangeNotifier {
  static const anahtar = 'sanal_islem_v1';

  String tarih = '';
  double nakit = 0;
  double baslangicSermaye = 0;
  String baslangicTarih = '';
  List<SanalPozisyon> pozisyonlar = [];
  List<SanalIslem> kapali = [];

  /// Gün gün portföy değeri — grafiğin kaynağı. Her ilerletme adımında
  /// sunucudan gelen noktalar buraya ekleniyor.
  List<Map<String, dynamic>> ozkaynak = [];

  /// Son değerleme (sunucudan). Ekran bunu çiziyor.
  Map<String, dynamic>? sonDeger;

  bool get basladi => tarih.isNotEmpty && baslangicSermaye > 0;

  double get maliyetToplam =>
      pozisyonlar.fold(0.0, (a, p) => a + p.maliyet);

  double get gerceklesenKar => kapali.fold(0.0, (a, i) => a + i.kar);

  /// Anlık toplam değer. Sunucu değerlemesi varsa ONDAN, yoksa
  /// maliyetten — açık pozisyonu sıfır saymak sahte bir çöküş gösterir.
  double get ozkaynakSimdi {
    final d = (sonDeger?['ozkaynak'] as num?)?.toDouble();
    return d ?? (nakit + maliyetToplam);
  }

  double get toplamGetiriYuzde => baslangicSermaye > 0
      ? (ozkaynakSimdi / baslangicSermaye - 1) * 100
      : 0;

  // ── kalıcılık ────────────────────────────────────────────────────────────

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    try {
      final ham = p.getString(anahtar);
      if (ham == null) {
        _varsayilana();
      } else {
        final j = jsonDecode(ham) as Map<String, dynamic>;
        tarih = '${j['tarih'] ?? ''}';
        baslangicTarih = '${j['baslangicTarih'] ?? ''}';
        nakit = ((j['nakit'] ?? 0) as num).toDouble();
        baslangicSermaye = ((j['baslangicSermaye'] ?? 0) as num).toDouble();
        pozisyonlar = ((j['pozisyonlar'] ?? []) as List)
            .map((e) => SanalPozisyon.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        kapali = ((j['kapali'] ?? []) as List)
            .map((e) => SanalIslem.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        ozkaynak = ((j['ozkaynak'] ?? []) as List)
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        sonDeger = j['sonDeger'] == null
            ? null
            : Map<String, dynamic>.from(j['sonDeger'] as Map);
      }
    } catch (_) {
      // Bozuk kayıt ekranı açılmaz hale getirmemeli.
      _varsayilana();
    }
    notifyListeners();
  }

  void _varsayilana() {
    tarih = '';
    baslangicTarih = '';
    nakit = 0;
    baslangicSermaye = 0;
    pozisyonlar = [];
    kapali = [];
    ozkaynak = [];
    sonDeger = null;
  }

  Future<void> _kaydet() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(
        anahtar,
        jsonEncode({
          'tarih': tarih, 'baslangicTarih': baslangicTarih,
          'nakit': nakit, 'baslangicSermaye': baslangicSermaye,
          'pozisyonlar': pozisyonlar.map((x) => x.toJson()).toList(),
          'kapali': kapali.map((x) => x.toJson()).toList(),
          'ozkaynak': ozkaynak,
          'sonDeger': sonDeger,
        }));
    notifyListeners();
  }

  // ── kurulum ──────────────────────────────────────────────────────────────

  Future<void> basla(String baslangicTarihi, double sermaye) async {
    _varsayilana();
    tarih = baslangicTarihi;
    baslangicTarih = baslangicTarihi;
    nakit = sermaye;
    baslangicSermaye = sermaye;
    ozkaynak = [{'t': baslangicTarihi, 'd': sermaye}];
    await _kaydet();
    await degerle();
  }

  Future<void> sifirla() async {
    _varsayilana();
    await _kaydet();
  }

  // ── işlem ────────────────────────────────────────────────────────────────

  /// Alım. Sunucu tavan kuralını ve bakiyeyi kontrol ediyor; burada
  /// tekrar kontrol edilmiyor — iki yerde kopyalanan kural sapar.
  ///
  /// Aynı hisseden ikinci alım SERBEST: ortalama maliyet hesaplanıyor.
  /// Gerçekte yapabilirsin ve "düşen hisseye ekleme" en pahalı
  /// alışkanlıklardan biri — burası onu bedava öğreneceğin yer.
  Future<String?> al(String sembol, int adet, double stop,
      double hedef) async {
    final r = await depo.api.sanalAl(sembol, tarih, adet, nakit);
    if (r['gecti'] != true) return '${r['sebep']}';
    final fiyat = (r['fiyat'] as num).toDouble();
    final maliyet = (r['maliyet'] as num).toDouble();

    final mevcut = pozisyonlar.where((p) => p.sembol == sembol).firstOrNull;
    if (mevcut == null) {
      pozisyonlar = [
        ...pozisyonlar,
        SanalPozisyon(sembol: sembol, adet: adet, giris: fiyat,
            stop: stop, hedef: hedef, tarih: tarih),
      ];
    } else {
      final yeniAdet = mevcut.adet + adet;
      final ortalama =
          (mevcut.giris * mevcut.adet + fiyat * adet) / yeniAdet;
      pozisyonlar = pozisyonlar
          .map((p) => p.sembol == sembol
              ? p.kopya(adet: yeniAdet, giris: ortalama,
                  stop: stop, hedef: hedef)
              : p)
          .toList();
    }
    nakit -= maliyet;
    await _kaydet();
    await degerle();
    return null;
  }

  /// Elle satış. `adet=0` → tamamı.
  Future<String?> sat(String sembol, {int adet = 0}) async {
    final p = pozisyonlar.where((x) => x.sembol == sembol).firstOrNull;
    if (p == null) return 'Açık pozisyon yok.';

    final r = await depo.api.sanalSat(tarih, p.toJson(), adet: adet);
    if (r['gecti'] != true) return '${r['sebep']}';
    final satilan = (r['adet'] as num).toInt();
    final fiyat = (r['fiyat'] as num).toDouble();
    final kalan = (r['kalan_adet'] as num).toInt();

    nakit += (r['hasilat'] as num).toDouble();
    kapali = [
      ...kapali,
      SanalIslem(sembol: sembol, adet: satilan, giris: p.giris,
          cikis: fiyat, girisTarih: p.tarih, cikisTarih: tarih,
          sebep: 'elle'),
    ];
    pozisyonlar = kalan > 0
        ? pozisyonlar
            .map((x) => x.sembol == sembol ? x.kopya(adet: kalan) : x)
            .toList()
        : pozisyonlar.where((x) => x.sembol != sembol).toList();
    await _kaydet();
    await degerle();
    return null;
  }

  /// Stopu yukarı çekme. AŞAĞI ÇEKMEYE İZİN YOK — stopu gevşetmek
  /// ("biraz daha alan vereyim") en yaygın ve en pahalı alışkanlık;
  /// simülatörde serbest bırakmak onu öğretmek olurdu.
  Future<String?> stopCek(String sembol, double yeniStop) async {
    final p = pozisyonlar.where((x) => x.sembol == sembol).firstOrNull;
    if (p == null) return 'Açık pozisyon yok.';
    if (yeniStop <= p.stop) {
      return 'Stop yalnızca YUKARI çekilebilir. '
          'Aşağı çekmek kaybı büyütür — kural bunu engelliyor.';
    }
    pozisyonlar = pozisyonlar
        .map((x) => x.sembol == sembol ? x.kopya(stop: yeniStop) : x)
        .toList();
    await _kaydet();
    return null;
  }

  // ── zaman ────────────────────────────────────────────────────────────────

  /// `adim` işlem günü ilerletir. `adim=0` → pozisyonlar kapanana kadar.
  /// Döner: kapanan işlemlerin listesi (ekran bunu bildirim olarak gösterir).
  Future<List<SanalIslem>> ilerlet({int adim = 1}) async {
    final r = await depo.api.sanalAdim(
        tarih, nakit, pozisyonlar.map((p) => p.toJson()).toList(),
        adim: adim);

    final yeniKapali = <SanalIslem>[];
    for (final c in (r['cikislar'] ?? []) as List) {
      final m = Map<String, dynamic>.from(c as Map);
      final p = pozisyonlar
          .where((x) => x.sembol == '${m['sembol']}')
          .firstOrNull;
      yeniKapali.add(SanalIslem(
        sembol: '${m['sembol']}',
        adet: ((m['adet'] ?? 0) as num).toInt(),
        giris: ((m['giris'] ?? p?.giris ?? 0) as num).toDouble(),
        cikis: ((m['fiyat'] ?? 0) as num).toDouble(),
        girisTarih: '${m['giris_tarih'] ?? p?.tarih ?? ''}',
        cikisTarih: '${m['tarih']}',
        sebep: '${m['sebep']}',
      ));
    }

    tarih = '${r['tarih']}';
    nakit = ((r['nakit'] ?? nakit) as num).toDouble();
    pozisyonlar = ((r['pozisyonlar'] ?? []) as List)
        .map((e) => SanalPozisyon.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    kapali = [...kapali, ...yeniKapali];
    ozkaynak = [
      ...ozkaynak,
      ...((r['ozkaynak_noktalari'] ?? []) as List)
          .map((e) => Map<String, dynamic>.from(e)),
    ];
    if (r['deger'] != null) {
      sonDeger = Map<String, dynamic>.from(r['deger'] as Map);
    }
    await _kaydet();
    return yeniKapali;
  }

  /// Portföyü o günkü fiyatlarla değerler. Ağ hatasında SESSİZ: eski
  /// değerleme, hiç değerleme olmamasından iyidir.
  Future<void> degerle() async {
    if (!basladi) return;
    try {
      sonDeger = await depo.api.sanalDeger(
          tarih, nakit, pozisyonlar.map((p) => p.toJson()).toList());
      await _kaydet();
    } catch (_) {
      // sessiz
    }
  }
}

final sanal = SanalHesap();
