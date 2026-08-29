import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'depo.dart';

/// Sanal İşlem oyunu — üretilmiş piyasada işlem.
///
/// PİYASA SUNUCUDA ÜRETİLİYOR, OYUN TELEFONDA OYNANIYOR. Bütün günler,
/// haberler ve analist sinyalleri tek çağrıda iniyor; gün ilerletmek,
/// alım, satım, değerleme hepsi çevrimdışı. "+1 gün" düğmesine her
/// basışta ağ beklemek oyunu oynanmaz yapardı.
///
/// SAKLANAN ŞEY TOHUM. Piyasanın kendisi (150-220 KB) diske yazılmıyor;
/// tohum + zorluk aynı piyasayı birebir yeniden üretiyor. Yedeğe giden
/// kayıt bir kaç kilobayt.
///
/// ÇIKIŞ KURALLARI PYTHON'DAKİYLE AYNI (cekirdek/alistirma.cikis_kontrol).
/// Burada yeniden yazıldı çünkü çevrimdışı çalışması gerekiyor; ikisinin
/// ayrışmaması test/oyun_test.dart'ta ORTAK bir örnek dosyasıyla
/// kilitli (testler/cikis_ornekleri.json).

class OyunBar {
  final double acilis, yuksek, dusuk, kapanis;
  final int hacim;
  const OyunBar(this.acilis, this.yuksek, this.dusuk, this.kapanis,
      this.hacim);

  factory OyunBar.fromListe(List l) => OyunBar(
        (l[0] as num).toDouble(), (l[1] as num).toDouble(),
        (l[2] as num).toDouble(), (l[3] as num).toDouble(),
        (l[4] as num).toInt(),
      );
}

class OyunHisse {
  final String kod, ad, sektor;
  final List<OyunBar> barlar;
  const OyunHisse({
    required this.kod, required this.ad, required this.sektor,
    required this.barlar,
  });

  factory OyunHisse.fromJson(Map<String, dynamic> j) => OyunHisse(
        kod: '${j['kod']}', ad: '${j['ad']}', sektor: '${j['sektor']}',
        barlar: ((j['barlar'] ?? []) as List)
            .map((e) => OyunBar.fromListe(e as List))
            .toList(),
      );
}

class OyunPozisyon {
  final String sembol;
  final int adet, acilisGunu;
  final double giris, stop, hedef;

  const OyunPozisyon({
    required this.sembol, required this.adet, required this.giris,
    required this.stop, required this.hedef, required this.acilisGunu,
  });

  double get maliyet => adet * giris;
  double get riskTl => adet * (giris - stop);

  OyunPozisyon kopya({int? adet, double? giris, double? stop, double? hedef}) =>
      OyunPozisyon(
        sembol: sembol, adet: adet ?? this.adet, giris: giris ?? this.giris,
        stop: stop ?? this.stop, hedef: hedef ?? this.hedef,
        acilisGunu: acilisGunu,
      );

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris, 'stop': stop,
        'hedef': hedef, 'gun': acilisGunu,
      };

  factory OyunPozisyon.fromJson(Map<String, dynamic> j) => OyunPozisyon(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        stop: ((j['stop'] ?? 0) as num).toDouble(),
        hedef: ((j['hedef'] ?? 0) as num).toDouble(),
        acilisGunu: ((j['gun'] ?? 0) as num).toInt(),
      );
}

/// Bekleyen limit emri.
///
/// NEDEN VAR: piyasa emri "kaç liraya olursa olsun al" demek ve kayma
/// yersin. Limit emri fiyatı sen belirlersin — ama gerçekleşmeyebilir.
/// İkisi arasındaki bu takas, borsanın ilk öğrenilmesi gereken
/// mekaniklerinden biri ve ancak yaşayarak öğreniliyor.
///
/// NAKİT BLOKE EDİLİYOR: bekleyen emir parayı bağlar. Gerçekte de öyle;
/// bloke etmeseydik oyuncu aynı parayla beş emir verip hepsinin
/// dolmasını izlerdi.
class OyunEmir {
  final String sembol;
  final int adet, verilenGun, gecerlilik;
  final double fiyat, stop, hedef;

  const OyunEmir({
    required this.sembol, required this.adet, required this.fiyat,
    required this.stop, required this.hedef, required this.verilenGun,
    this.gecerlilik = 5,
  });

  double get bloke => adet * fiyat;
  int sonGun() => verilenGun + gecerlilik;
  int kalanGun(int bugun) => sonGun() - bugun;

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'fiyat': fiyat, 'stop': stop,
        'hedef': hedef, 'gun': verilenGun, 'gecerlilik': gecerlilik,
      };

  factory OyunEmir.fromJson(Map<String, dynamic> j) => OyunEmir(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        fiyat: ((j['fiyat'] ?? 0) as num).toDouble(),
        stop: ((j['stop'] ?? 0) as num).toDouble(),
        hedef: ((j['hedef'] ?? 0) as num).toDouble(),
        verilenGun: ((j['gun'] ?? 0) as num).toInt(),
        gecerlilik: ((j['gecerlilik'] ?? 5) as num).toInt(),
      );
}

/// Bir günün sonunda ne olduğu — ilerletme sonrası gösterilen özet.
class GunOzeti {
  final int gun;
  final List<OyunIslem> kapananlar;
  final List<OyunEmir> dolanlar;
  final List<OyunEmir> iptaller;
  final double oncekiDeger, yeniDeger;

  const GunOzeti({
    required this.gun, required this.kapananlar, required this.dolanlar,
    required this.iptaller, required this.oncekiDeger,
    required this.yeniDeger,
  });

  double get fark => yeniDeger - oncekiDeger;
  double get farkYuzde =>
      oncekiDeger > 0 ? (yeniDeger / oncekiDeger - 1) * 100 : 0;
  bool get sessiz =>
      kapananlar.isEmpty && dolanlar.isEmpty && iptaller.isEmpty;
}

class OyunIslem {
  final String sembol, sebep;
  final int adet, girisGunu, cikisGunu;
  final double giris, cikis;

  const OyunIslem({
    required this.sembol, required this.adet, required this.giris,
    required this.cikis, required this.girisGunu, required this.cikisGunu,
    required this.sebep,
  });

  double get kar => (cikis - giris) * adet;
  double get karYuzde => giris > 0 ? (cikis / giris - 1) * 100 : 0;

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris, 'cikis': cikis,
        'girisGunu': girisGunu, 'cikisGunu': cikisGunu, 'sebep': sebep,
      };

  factory OyunIslem.fromJson(Map<String, dynamic> j) => OyunIslem(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        cikis: ((j['cikis'] ?? 0) as num).toDouble(),
        girisGunu: ((j['girisGunu'] ?? 0) as num).toInt(),
        cikisGunu: ((j['cikisGunu'] ?? 0) as num).toInt(),
        sebep: '${j['sebep'] ?? ''}',
      );
}

/// Bir barda stop ya da hedef çalıştı mı.
///
/// PYTHON'DAKİYLE BİREBİR (cekirdek/alistirma.py `cikis_kontrol`).
/// Sıra önemli:
///   1) boşluklu açılış: açılış stopun altındaysa çıkış AÇILIŞTAN
///   2) gün içi stop, hedeften ÖNCE — aynı gün ikisi de görüldüyse
///      kötümser varsayım
///   3) hedefin ÜSTÜNDE açan hisse yine HEDEF fiyatından çıkar
({String sebep, double fiyat})? cikisKontrol(OyunPozisyon p, OyunBar b) {
  if (p.stop > 0 && b.acilis <= p.stop) {
    return (sebep: 'stop', fiyat: b.acilis);
  }
  if (p.stop > 0 && b.dusuk <= p.stop) {
    return (sebep: 'stop', fiyat: p.stop);
  }
  if (p.hedef > 0 && b.yuksek >= p.hedef) {
    return (sebep: 'hedef', fiyat: p.hedef);
  }
  return null;
}

class Oyun extends ChangeNotifier {
  static const anahtar = 'oyun_v1';

  // ── kalıcı durum (yedeğe giden) ─────────────────────────────────────────
  int tohum = 0;
  String zorluk = '';
  int gun = 0;
  double nakit = 0;
  double baslangicSermaye = 0;
  List<OyunPozisyon> pozisyonlar = [];
  List<OyunIslem> kapali = [];
  List<OyunEmir> emirler = [];
  List<double> ozkaynak = [];
  int okunanHaber = 0;

  // ── bellekte: piyasanın kendisi ─────────────────────────────────────────
  List<OyunHisse> hisseler = [];
  List<double> endeks = [];
  List<Map<String, dynamic>> sinyaller = [];
  List<Map<String, dynamic>> haberler = [];
  int isinma = 0;
  int gunSayisi = 0;
  double kaymaBp = 0;
  bool yukleniyor = false;
  Object? hata;

  bool get basladi => tohum != 0 && zorluk.isNotEmpty;
  bool get piyasaHazir => hisseler.isNotEmpty;
  bool get bitti => basladi && gun >= gunSayisi - 1;

  int get barIndeks => isinma + gun;

  OyunHisse? hisse(String kod) =>
      hisseler.where((h) => h.kod == kod).firstOrNull;

  double? fiyat(String kod) {
    final h = hisse(kod);
    if (h == null || barIndeks >= h.barlar.length) return null;
    return h.barlar[barIndeks].kapanis;
  }

  double? oncekiFiyat(String kod) {
    final h = hisse(kod);
    final i = barIndeks - 1;
    if (h == null || i < 0 || i >= h.barlar.length) return null;
    return h.barlar[i].kapanis;
  }

  double? gunlukDegisim(String kod) {
    final f = fiyat(kod), o = oncekiFiyat(kod);
    if (f == null || o == null || o == 0) return null;
    return (f / o - 1) * 100;
  }

  double get pozisyonDegeri => pozisyonlar.fold(
      0.0, (a, p) => a + p.adet * (fiyat(p.sembol) ?? p.giris));

  /// Bekleyen emirlerin bağladığı para.
  double get blokeNakit => emirler.fold(0.0, (a, e) => a + e.bloke);

  /// Yeni emir için gerçekten elde olan para.
  double get kullanilabilirNakit => nakit - blokeNakit;

  double get toplamDeger => nakit + pozisyonDegeri;

  double get getiriYuzde => baslangicSermaye > 0
      ? (toplamDeger / baslangicSermaye - 1) * 100
      : 0;

  double get gerceklesenKar => kapali.fold(0.0, (a, i) => a + i.kar);

  List<Map<String, dynamic>> get bugunSinyaller =>
      sinyaller.where((s) => (s['gun'] as num).toInt() == gun).toList();

  /// Bugüne kadarki haberler, en yenisi üstte.
  List<Map<String, dynamic>> get akanHaberler => haberler
      .where((h) => (h['gun'] as num).toInt() <= gun)
      .toList()
      .reversed
      .toList();

  /// Okunmamış haber sayısı — YALNIZCA bugüne kadar çıkmış olanlar.
  ///
  /// Tümünü saymak oyunun geri kalanında kaç haber olduğunu sızdırıyordu:
  /// 29. günde rozet 82 yazıyordu ve bu, oyuncunun bilmemesi gereken bir
  /// bilgi.
  int get okunmamisHaber => haberler.where((h) {
        final g = (h['gun'] as num).toInt();
        return g <= gun && g > okunanHaber;
      }).length;

  /// Analistin sicili: geçmiş sinyalleri ne oldu.
  ///
  /// GELECEĞE BAKMIYOR: yalnızca BUGÜNE KADAR sonuçlanmış sinyaller
  /// sayılıyor. Bütün oyunu tarasaydık, henüz gelmediğin günlerin
  /// sonucunu söylemiş olurduk ve oyun biterdi.
  ///
  /// "Kaç sinyal verdi" tek başına hiçbir şey söylemiyor; asıl soru
  /// hangisinin tuttuğu. Kullanıcı sisteme güvenip güvenmeyeceğini
  /// buradan öğreniyor.
  ({int hedef, int stop, int acik, double oran}) get analistSicili {
    var hedefe = 0, stopa = 0, acikta = 0;
    for (final s in sinyaller) {
      final g = (s['gun'] as num).toInt();
      if (g > gun) continue;                 // henüz verilmemiş
      final h = hisse('${s['sembol']}');
      if (h == null) continue;
      final sanal = OyunPozisyon(
        sembol: h.kod, adet: 1,
        giris: ((s['fiyat'] ?? 0) as num).toDouble(),
        stop: ((s['stop'] ?? 0) as num).toDouble(),
        hedef: ((s['hedef'] ?? 0) as num).toDouble(),
        acilisGunu: g,
      );
      String? sonuc;
      for (var i = g + 1; i <= gun; i++) {
        final j = isinma + i;
        if (j >= h.barlar.length) break;
        final c = cikisKontrol(sanal, h.barlar[j]);
        if (c != null) {
          sonuc = c.sebep;
          break;
        }
      }
      if (sonuc == 'hedef') {
        hedefe++;
      } else if (sonuc == 'stop') {
        stopa++;
      } else {
        acikta++;
      }
    }
    final sonuclanan = hedefe + stopa;
    return (
      hedef: hedefe, stop: stopa, acik: acikta,
      oran: sonuclanan > 0 ? hedefe / sonuclanan * 100 : 0.0,
    );
  }

  // ── kalıcılık ───────────────────────────────────────────────────────────

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    try {
      final ham = p.getString(anahtar);
      if (ham == null) {
        _sifirla();
      } else {
        final j = jsonDecode(ham) as Map<String, dynamic>;
        tohum = ((j['tohum'] ?? 0) as num).toInt();
        zorluk = '${j['zorluk'] ?? ''}';
        gun = ((j['gun'] ?? 0) as num).toInt();
        nakit = ((j['nakit'] ?? 0) as num).toDouble();
        baslangicSermaye = ((j['sermaye'] ?? 0) as num).toDouble();
        okunanHaber = ((j['okunanHaber'] ?? 0) as num).toInt();
        pozisyonlar = ((j['pozisyonlar'] ?? []) as List)
            .map((e) => OyunPozisyon.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        kapali = ((j['kapali'] ?? []) as List)
            .map((e) => OyunIslem.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        emirler = ((j['emirler'] ?? []) as List)
            .map((e) => OyunEmir.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        ozkaynak = ((j['ozkaynak'] ?? []) as List)
            .map((e) => (e as num).toDouble())
            .toList();
      }
    } catch (_) {
      _sifirla();
    }
    notifyListeners();
  }

  void _sifirla() {
    tohum = 0;
    zorluk = '';
    gun = 0;
    nakit = 0;
    baslangicSermaye = 0;
    pozisyonlar = [];
    kapali = [];
    emirler = [];
    ozkaynak = [];
    okunanHaber = 0;
    hisseler = [];
    endeks = [];
    sinyaller = [];
    haberler = [];
    isinma = 0;
    gunSayisi = 0;
    kaymaBp = 0;
    hata = null;
  }

  Future<void> _kaydet() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(
        anahtar,
        jsonEncode({
          'tohum': tohum, 'zorluk': zorluk, 'gun': gun, 'nakit': nakit,
          'sermaye': baslangicSermaye, 'okunanHaber': okunanHaber,
          'pozisyonlar': pozisyonlar.map((x) => x.toJson()).toList(),
          'kapali': kapali.map((x) => x.toJson()).toList(),
          'emirler': emirler.map((x) => x.toJson()).toList(),
          'ozkaynak': ozkaynak,
        }));
    notifyListeners();
  }

  // ── piyasa ──────────────────────────────────────────────────────────────

  /// Görsel testler piyasayı ağ olmadan kurabilsin diye.
  @visibleForTesting
  void piyasayiTestIcinAl(Map<String, dynamic> d) => _piyasayiAl(d);

  void _piyasayiAl(Map<String, dynamic> d) {
    hisseler = ((d['hisseler'] ?? []) as List)
        .map((e) => OyunHisse.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    endeks = ((d['endeks'] ?? []) as List)
        .map((e) => (e as num).toDouble())
        .toList();
    sinyaller = ((d['sinyaller'] ?? []) as List)
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    haberler = ((d['haberler'] ?? []) as List)
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    isinma = ((d['isinma'] ?? 0) as num).toInt();
    gunSayisi = ((d['gun_sayisi'] ?? 0) as num).toInt();
    kaymaBp = (((d['ayar'] ?? {})['kayma_bp'] ?? 0) as num).toDouble();
  }

  /// Yeni oyun. Tohum sunucudan geliyor — her oyun bir öncekinden farklı.
  Future<void> basla(String yeniZorluk) async {
    yukleniyor = true;
    hata = null;
    notifyListeners();
    try {
      final d = await depo.api.oyunUret(zorluk: yeniZorluk);
      _sifirla();
      _piyasayiAl(d);
      tohum = ((d['tohum'] ?? 0) as num).toInt();
      zorluk = yeniZorluk;
      gun = 0;
      baslangicSermaye = (((d['ayar'] ?? {})['sermaye'] ?? 0) as num).toDouble();
      nakit = baslangicSermaye;
      ozkaynak = [baslangicSermaye];
      await _kaydet();
    } catch (e) {
      hata = e;
    } finally {
      yukleniyor = false;
      notifyListeners();
    }
  }

  /// Kayıtlı oyunun piyasasını tohumdan yeniden üretir.
  Future<void> piyasayiGetir() async {
    if (!basladi || piyasaHazir || yukleniyor) return;
    yukleniyor = true;
    hata = null;
    notifyListeners();
    try {
      _piyasayiAl(await depo.api.oyunUret(tohum: tohum, zorluk: zorluk));
    } catch (e) {
      hata = e;
    } finally {
      yukleniyor = false;
      notifyListeners();
    }
  }

  Future<void> birak() async {
    _sifirla();
    await _kaydet();
  }

  // ── işlem ───────────────────────────────────────────────────────────────

  double _alisFiyati(double kapanis) => kapanis * (1 + kaymaBp / 10000.0);
  double _satisFiyati(double kapanis) => kapanis * (1 - kaymaBp / 10000.0);

  /// Alım. Aynı hisseye ekleme serbest, ortalama maliyet hesaplanır.
  String? al(String kod, int adet, double stop, double hedef) {
    if (bitti) return 'Oyun bitti.';
    final k = fiyat(kod);
    if (k == null) return 'Fiyat yok.';
    if (adet < 1) return 'Adet en az 1 olmalı.';
    final f = _alisFiyati(k);
    final maliyet = adet * f;
    if (maliyet > kullanilabilirNakit + 1e-9) {
      return 'Nakit yetmiyor: ${maliyet.toStringAsFixed(2)} ₺ gerekiyor, '
          '${kullanilabilirNakit.toStringAsFixed(2)} ₺ kullanılabilir'
          '${blokeNakit > 0 ? ' (${blokeNakit.toStringAsFixed(2)} ₺ bekleyen '
              'emirlerde bloke)' : ''}.';
    }
    if (stop <= 0 || stop >= f) return 'Stop giriş fiyatının altında olmalı.';

    final mevcut = pozisyonlar.where((p) => p.sembol == kod).firstOrNull;
    if (mevcut == null) {
      pozisyonlar = [
        ...pozisyonlar,
        OyunPozisyon(sembol: kod, adet: adet, giris: f, stop: stop,
            hedef: hedef, acilisGunu: gun),
      ];
    } else {
      final yeniAdet = mevcut.adet + adet;
      final ort = (mevcut.giris * mevcut.adet + f * adet) / yeniAdet;
      pozisyonlar = pozisyonlar
          .map((p) => p.sembol == kod
              ? p.kopya(adet: yeniAdet, giris: ort, stop: stop, hedef: hedef)
              : p)
          .toList();
    }
    nakit -= maliyet;
    _kaydet();
    return null;
  }

  /// Elle satış. `adet=0` → tamamı.
  String? sat(String kod, {int adet = 0}) {
    final p = pozisyonlar.where((x) => x.sembol == kod).firstOrNull;
    if (p == null) return 'Açık pozisyon yok.';
    final k = fiyat(kod);
    if (k == null) return 'Fiyat yok.';
    final n = adet <= 0 ? p.adet : min(adet, p.adet);
    final f = _satisFiyati(k);

    nakit += n * f;
    kapali = [
      ...kapali,
      OyunIslem(sembol: kod, adet: n, giris: p.giris, cikis: f,
          girisGunu: p.acilisGunu, cikisGunu: gun, sebep: 'elle'),
    ];
    pozisyonlar = n >= p.adet
        ? pozisyonlar.where((x) => x.sembol != kod).toList()
        : pozisyonlar
            .map((x) => x.sembol == kod ? x.kopya(adet: p.adet - n) : x)
            .toList();
    _kaydet();
    return null;
  }

  /// Stop yalnızca YUKARI çekilebilir — gevşetmek kaybı büyütür.
  String? stopCek(String kod, double yeni) {
    final p = pozisyonlar.where((x) => x.sembol == kod).firstOrNull;
    if (p == null) return 'Açık pozisyon yok.';
    if (yeni <= p.stop) {
      return 'Stop yalnızca YUKARI çekilebilir.';
    }
    pozisyonlar = pozisyonlar
        .map((x) => x.sembol == kod ? x.kopya(stop: yeni) : x)
        .toList();
    _kaydet();
    return null;
  }

  /// Limit alış emri. Fiyat sana gelirse dolar, gelmezse dolmaz.
  ///
  /// Kayma YOK: limit emrinin bütün mesele bu. Piyasa emri kaymayı
  /// yiyor ama kesin doluyor; limit emri kaymadan kaçıyor ama
  /// dolmayabiliyor. Takas ancak yaşayarak öğreniliyor.
  String? emirVer(String kod, int adet, double limitFiyat, double stop,
      double hedef, {int gecerlilik = 5}) {
    if (bitti) return 'Oyun bitti.';
    if (adet < 1) return 'Adet en az 1 olmalı.';
    if (limitFiyat <= 0) return 'Limit fiyatı gir.';
    if (stop <= 0 || stop >= limitFiyat) {
      return 'Stop limit fiyatının altında olmalı.';
    }
    final tutar = adet * limitFiyat;
    if (tutar > kullanilabilirNakit + 1e-9) {
      return 'Nakit yetmiyor: emir ${tutar.toStringAsFixed(2)} ₺ bloke '
          'eder, ${kullanilabilirNakit.toStringAsFixed(2)} ₺ kullanılabilir.';
    }
    final simdi = fiyat(kod);
    if (simdi != null && limitFiyat >= simdi) {
      return 'Limit fiyatı bugünkü fiyatın (${simdi.toStringAsFixed(2)} ₺) '
          'altında olmalı — üstündeyse doğrudan al.';
    }
    emirler = [
      ...emirler,
      OyunEmir(sembol: kod, adet: adet, fiyat: limitFiyat, stop: stop,
          hedef: hedef, verilenGun: gun, gecerlilik: gecerlilik),
    ];
    _kaydet();
    return null;
  }

  void emirIptal(OyunEmir e) {
    emirler = emirler.where((x) => x != e).toList();
    _kaydet();
  }

  // ── zaman ───────────────────────────────────────────────────────────────

  /// `adim` gün ilerletir. `adim=0` → pozisyonlar kapanana kadar.
  ///
  /// Günün sırası GERÇEKÇİ: önce açık pozisyonların stop/hedefi kontrol
  /// ediliyor, sonra bekleyen limit emirleri doluyor. Ters sırada olsa
  /// aynı gün hem dolan hem stoplanan bir emir mümkün olurdu.
  GunOzeti ilerlet({int adim = 1}) {
    final baslangicDeger = toplamDeger;
    final kapananlar = <OyunIslem>[];
    final dolanlar = <OyunEmir>[];
    final iptaller = <OyunEmir>[];
    if (bitti) {
      return GunOzeti(gun: gun, kapananlar: kapananlar, dolanlar: dolanlar,
          iptaller: iptaller, oncekiDeger: baslangicDeger,
          yeniDeger: baslangicDeger);
    }

    final kapanaKadar = adim <= 0;
    var kalan = kapanaKadar ? gunSayisi : adim;

    while (kalan > 0 && gun < gunSayisi - 1) {
      gun += 1;
      kalan -= 1;
      final i = barIndeks;

      // 1) açık pozisyonlar: stop / hedef
      final duran = <OyunPozisyon>[];
      for (final p in pozisyonlar) {
        final h = hisse(p.sembol);
        if (h == null || i >= h.barlar.length) {
          duran.add(p);
          continue;
        }
        final c = cikisKontrol(p, h.barlar[i]);
        if (c == null) {
          duran.add(p);
          continue;
        }
        final f = _satisFiyati(c.fiyat);
        nakit += p.adet * f;
        final islem = OyunIslem(
            sembol: p.sembol, adet: p.adet, giris: p.giris, cikis: f,
            girisGunu: p.acilisGunu, cikisGunu: gun, sebep: c.sebep);
        kapananlar.add(islem);
        kapali = [...kapali, islem];
      }
      pozisyonlar = duran;

      // 2) bekleyen limit emirleri
      final bekleyen = <OyunEmir>[];
      for (final e in emirler) {
        final h = hisse(e.sembol);
        if (h == null || i >= h.barlar.length) {
          bekleyen.add(e);
          continue;
        }
        final b = h.barlar[i];
        if (b.dusuk <= e.fiyat) {
          // Açılış limitin ALTINDAYSA daha iyi fiyattan dolar — gerçekte
          // de öyle: emrin bekliyor, piyasa boşluklu açtı, sen kazandın.
          final dolus = b.acilis < e.fiyat ? b.acilis : e.fiyat;
          nakit -= e.adet * dolus;
          final mevcut =
              pozisyonlar.where((p) => p.sembol == e.sembol).firstOrNull;
          if (mevcut == null) {
            pozisyonlar = [
              ...pozisyonlar,
              OyunPozisyon(sembol: e.sembol, adet: e.adet, giris: dolus,
                  stop: e.stop, hedef: e.hedef, acilisGunu: gun),
            ];
          } else {
            final n = mevcut.adet + e.adet;
            final ort = (mevcut.giris * mevcut.adet + dolus * e.adet) / n;
            pozisyonlar = pozisyonlar
                .map((p) => p.sembol == e.sembol
                    ? p.kopya(adet: n, giris: ort, stop: e.stop,
                        hedef: e.hedef)
                    : p)
                .toList();
          }
          dolanlar.add(e);
        } else if (gun >= e.sonGun()) {
          iptaller.add(e);
        } else {
          bekleyen.add(e);
        }
      }
      emirler = bekleyen;

      ozkaynak = [...ozkaynak, toplamDeger];
      if (kapanaKadar && pozisyonlar.isEmpty && emirler.isEmpty) break;
    }
    _kaydet();
    return GunOzeti(gun: gun, kapananlar: kapananlar, dolanlar: dolanlar,
        iptaller: iptaller, oncekiDeger: baslangicDeger,
        yeniDeger: toplamDeger);
  }

  // ── oyun sonu karnesi ───────────────────────────────────────────────────

  /// Oyun bitince: sen ne yaptın, hiçbir şey yapmasan ne olurdu.
  ///
  /// "HİÇBİR ŞEY YAPMASAN" kıyası asıl öğretici olan: kazanmak yetmiyor,
  /// endeksi geçmek gerekiyor. Endeksin altında kalan bir kâr, aslında
  /// harcanmış emek.
  ({
    double getiri, double endeksGetiri, int islem, int kazanan,
    double enIyi, double enKotu, String enIyiKod, String enKotuKod,
  }) karne() {
    final ilkEndeks = endeks.isNotEmpty ? endeks[isinma] : 0.0;
    final sonEndeks = (isinma + gun) < endeks.length
        ? endeks[isinma + gun]
        : (endeks.isNotEmpty ? endeks.last : 0.0);
    final endeksGetiri =
        ilkEndeks > 0 ? (sonEndeks / ilkEndeks - 1) * 100 : 0.0;

    var enIyi = 0.0, enKotu = 0.0;
    var enIyiKod = '', enKotuKod = '';
    for (final i in kapali) {
      if (i.karYuzde > enIyi) {
        enIyi = i.karYuzde;
        enIyiKod = i.sembol;
      }
      if (i.karYuzde < enKotu) {
        enKotu = i.karYuzde;
        enKotuKod = i.sembol;
      }
    }
    return (
      getiri: getiriYuzde,
      endeksGetiri: endeksGetiri,
      islem: kapali.length,
      kazanan: kapali.where((i) => i.kar > 0).length,
      enIyi: enIyi, enKotu: enKotu,
      enIyiKod: enIyiKod, enKotuKod: enKotuKod,
    );
  }

  Future<void> haberleriOkudum() async {
    if (okunanHaber >= gun) return;
    okunanHaber = gun;
    await _kaydet();
  }
}

final oyun = Oyun();
