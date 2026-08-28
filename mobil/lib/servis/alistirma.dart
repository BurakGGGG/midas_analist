import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'depo.dart';

/// Alıştırma kum havuzu — sanal parayla işlem öğrenme.
///
/// GERÇEK PORTFÖYDEN TAMAMEN AYRI: kendi bakiyesi var, sıfırlanabilir ve
/// karar defterine hiç dokunmuyor. Öğrenmek için batırabilmek şart;
/// batırdığın hesap ölçülen hesap olmamalı. Bu yüzden `defter.alim`
/// çağrılmıyor — burada yapılan hiçbir işlem sicile girmiyor.
///
/// DURUM TELEFONDA: bakiye, pozisyonlar ve görev ilerlemesi burada
/// yaşıyor ve bulut yedeğine dahil (bkz. Hesap.yedeklenen). Sunucu
/// yalnızca fiyat veriyor ve çıkış kurallarını uyguluyor.
///
/// ÇIKIŞ KURALLARI SUNUCUDA: stop/hedef kontrolü burada YAPILMIYOR,
/// `/alistirma/ilerlet` yapıyor. Sebep: aynı kurallar backtest'te de var
/// ve iki yerde kopyalanırsa biri sessizce kayar. Alıştırmada stop başka
/// türlü çalışırsa kullanıcı yanlış şey öğrenir.
class KumPozisyon {
  final String sembol, tarih;
  final int adet;
  final double giris, stop, hedef;

  const KumPozisyon({
    required this.sembol, required this.adet, required this.giris,
    required this.stop, required this.hedef, required this.tarih,
  });

  double get maliyet => adet * giris;
  double get riskTl => adet * (giris - stop);

  Map<String, dynamic> toJson() => {
        'sembol': sembol, 'adet': adet, 'giris': giris,
        'stop': stop, 'hedef': hedef, 'tarih': tarih,
      };

  factory KumPozisyon.fromJson(Map<String, dynamic> j) => KumPozisyon(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        stop: ((j['stop'] ?? 0) as num).toDouble(),
        hedef: ((j['hedef'] ?? 0) as num).toDouble(),
        tarih: '${j['tarih'] ?? ''}',
      );
}

class KumIslem {
  final String sembol, girisTarih, cikisTarih, sebep;
  final int adet;
  final double giris, cikis;

  const KumIslem({
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

  factory KumIslem.fromJson(Map<String, dynamic> j) => KumIslem(
        sembol: '${j['sembol']}',
        adet: ((j['adet'] ?? 0) as num).toInt(),
        giris: ((j['giris'] ?? 0) as num).toDouble(),
        cikis: ((j['cikis'] ?? 0) as num).toDouble(),
        girisTarih: '${j['girisTarih'] ?? ''}',
        cikisTarih: '${j['cikisTarih'] ?? ''}',
        sebep: '${j['sebep'] ?? ''}',
      );
}

class KumHavuzu extends ChangeNotifier {
  static const anahtar = 'alistirma_v1';
  static const baslangicBakiye = 10000.0;

  /// '' = henüz mod seçilmedi · 'gecmis' · 'canli'
  String mod = '';

  /// '' = sorulmadı · 'rehberli' = görevler sırayla · 'serbest' = doğrudan
  /// kum havuzu. Ayrı bir alan çünkü ikisi FARKLI sorular: "hangi zamanda"
  /// ile "yardım ister misin" birbirine karıştırılırsa dört kutucuk çıkar
  /// ve seçim kararı verilemez hale gelir.
  String rehber = '';

  String tarih = '';
  double bakiye = baslangicBakiye;
  List<KumPozisyon> pozisyonlar = [];
  List<KumIslem> kapali = [];
  List<String> bitenGorevler = [];

  /// Görev başına kaç denemede bilindi. Puanı bu belirliyor: bir soruyu
  /// beşinci denemede bilmek ile ilkinde bilmek aynı şey değil.
  Map<String, int> denemeler = {};

  int puan = 0;
  List<String> rozetler = [];

  bool get basladi => mod.isNotEmpty && rehber.isNotEmpty;
  bool get rehberli => rehber == 'rehberli';

  /// İlk denemede 10, ikincide 6, sonrasında 3 puan. Yanlış cevap
  /// cezalandırılmıyor — sadece daha az ödüllendiriliyor; yanlış yapmaktan
  /// korkan biri tahmin etmeyi bırakır ve tahmin etmek öğrenmenin kendisi.
  static int puanHesapla(int deneme) =>
      deneme <= 1 ? 10 : (deneme == 2 ? 6 : 3);

  int get azamiPuan => 80;   // 8 görev x 10
  bool get gecmisModu => mod == 'gecmis';
  double get maliyetToplam =>
      pozisyonlar.fold(0.0, (a, p) => a + p.maliyet);

  /// Kapanmış işlemlerin toplam kâr/zararı. Açık pozisyonların anlık
  /// değeri BİLEREK sayılmıyor: kum havuzunda fiyat ancak "sonraki gün"
  /// basılınca ilerliyor, aradaki değer yanıltıcı olurdu.
  double get gerceklesenKar => kapali.fold(0.0, (a, i) => a + i.kar);

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    try {
      final ham = p.getString(anahtar);
      if (ham == null) {
        // Kayıt yoksa alanları VARSAYILANA döndür, sadece çıkma.
        // Erken dönüş bellekteki eski durumu olduğu gibi bırakıyordu;
        // yükleyicinin okumadığı bir durumu ayakta tutması, çağıranın
        // "yükledim" sandığı şeyin gerçekte önceki hâl olması demek.
        _varsayilana();
        notifyListeners();
        return;
      }
      final j = jsonDecode(ham) as Map<String, dynamic>;
      mod = '${j['mod'] ?? ''}';
      tarih = '${j['tarih'] ?? ''}';
      bakiye = ((j['bakiye'] ?? baslangicBakiye) as num).toDouble();
      pozisyonlar = ((j['pozisyonlar'] ?? []) as List)
          .map((e) => KumPozisyon.fromJson(Map<String, dynamic>.from(e)))
          .toList();
      kapali = ((j['kapali'] ?? []) as List)
          .map((e) => KumIslem.fromJson(Map<String, dynamic>.from(e)))
          .toList();
      bitenGorevler =
          ((j['gorevler'] ?? []) as List).map((e) => '$e').toList();
      // Eski kayıtlarda bu alanlar yok. Varsayılanları, "rehberi hiç
      // görmemiş" değil "eskiden beri rehberli" olacak şekilde seçiyorum:
      // görev ilerlemesi olan biri zaten rehberdeydi, ona mod sorusunu
      // yeniden sormak ilerlemesini kaybettiğini düşündürür.
      rehber = '${j['rehber'] ?? (bitenGorevler.isNotEmpty ? 'rehberli' : '')}';
      if (mod.isNotEmpty && rehber.isEmpty) rehber = 'rehberli';
      puan = ((j['puan'] ?? 0) as num).toInt();
      rozetler = ((j['rozetler'] ?? []) as List).map((e) => '$e').toList();
      denemeler = ((j['denemeler'] ?? {}) as Map)
          .map((k, v) => MapEntry('$k', (v as num).toInt()));
    } catch (_) {
      // Bozuk kayıt kum havuzunu açılmaz hale getirmemeli; sıfırdan başla.
    }
    notifyListeners();
  }

  Future<void> _kaydet() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(
        anahtar,
        jsonEncode({
          'mod': mod, 'tarih': tarih, 'bakiye': bakiye,
          'pozisyonlar': pozisyonlar.map((x) => x.toJson()).toList(),
          'kapali': kapali.map((x) => x.toJson()).toList(),
          'gorevler': bitenGorevler,
          'rehber': rehber, 'puan': puan, 'rozetler': rozetler,
          'denemeler': denemeler,
        }));
    notifyListeners();
  }

  Future<void> basla(String yeniMod, String baslangicTarihi,
      String yeniRehber) async {
    mod = yeniMod;
    tarih = baslangicTarihi;
    rehber = yeniRehber;
    await _kaydet();
  }

  /// Rehberi sonradan açıp kapatmak. "Kendi başıma" diyen biri takılırsa
  /// baştan başlamak zorunda kalmamalı; ilerlemesi duruyor.
  Future<void> rehberDegistir(String yeni) async {
    rehber = yeni;
    await _kaydet();
  }

  void _varsayilana() {
    mod = '';
    rehber = '';
    tarih = '';
    bakiye = baslangicBakiye;
    pozisyonlar = [];
    kapali = [];
    bitenGorevler = [];
    denemeler = {};
    puan = 0;
    rozetler = [];
  }

  /// Her şeyi siler. Görev ilerlemesi de gider — alıştırmayı baştan
  /// yapmak isteyen biri görevleri de baştan istiyordur.
  Future<void> sifirla() async {
    _varsayilana();
    await _kaydet();
  }

  Future<String?> al(KumPozisyon p) async {
    if (p.adet < 1) return 'Adet en az 1 olmalı.';
    if (p.stop <= 0 || p.stop >= p.giris) {
      return 'Stop giriş fiyatının altında olmalı.';
    }
    if (p.maliyet > bakiye) {
      return 'Bakiye yetmiyor: ${p.maliyet.toStringAsFixed(2)} ₺ gerekiyor, '
          '${bakiye.toStringAsFixed(2)} ₺ var.';
    }
    if (pozisyonlar.any((x) => x.sembol == p.sembol)) {
      return '${p.sembol} zaten açık. Önce onu kapat.';
    }
    bakiye -= p.maliyet;
    pozisyonlar = [...pozisyonlar, p];
    await _kaydet();
    return null;
  }

  /// Elle kapatma (stop/hedef beklemeden).
  Future<void> kapat(String sembol, double fiyat, String sebep) async {
    final p = pozisyonlar.where((x) => x.sembol == sembol).firstOrNull;
    if (p == null) return;
    bakiye += p.adet * fiyat;
    kapali = [
      ...kapali,
      KumIslem(sembol: p.sembol, adet: p.adet, giris: p.giris, cikis: fiyat,
          girisTarih: p.tarih, cikisTarih: tarih, sebep: sebep),
    ];
    pozisyonlar = pozisyonlar.where((x) => x.sembol != sembol).toList();
    await _kaydet();
  }

  /// Bir işlem günü ilerler. Stop/hedef kontrolünü SUNUCU yapıyor.
  /// Döner: {tarih, fiyatlar, cikislar} ya da hata mesajı.
  Future<Map<String, dynamic>> ilerlet({List<String> izlenen = const []}) async {
    final r = await depo.api.alistirmaIlerlet(
        tarih, pozisyonlar.map((p) => p.toJson()).toList(), izlenen);

    tarih = '${r['tarih']}';
    for (final c in (r['cikislar'] ?? []) as List) {
      final m = Map<String, dynamic>.from(c as Map);
      final sem = '${m['sembol']}';
      final p = pozisyonlar.where((x) => x.sembol == sem).firstOrNull;
      if (p == null) continue;
      final fiyat = (m['fiyat'] as num).toDouble();
      bakiye += p.adet * fiyat;
      kapali = [
        ...kapali,
        KumIslem(sembol: sem, adet: p.adet, giris: p.giris, cikis: fiyat,
            girisTarih: p.tarih, cikisTarih: '${m['tarih']}',
            sebep: '${m['sebep']}'),
      ];
      pozisyonlar = pozisyonlar.where((x) => x.sembol != sem).toList();
    }
    await _kaydet();
    return r;
  }

  /// Bir denemeyi kaydeder ve o görevin kaçıncı denemesi olduğunu döner.
  Future<int> denemeEkle(String kod) async {
    final n = (denemeler[kod] ?? 0) + 1;
    denemeler = {...denemeler, kod: n};
    await _kaydet();
    return n;
  }

  Future<void> gorevBitir(String kod, {int toplamGorev = 8}) async {
    if (bitenGorevler.contains(kod)) return;
    bitenGorevler = [...bitenGorevler, kod];
    puan += puanHesapla(denemeler[kod] ?? 1);
    _rozetleriTazele(toplamGorev);
    await _kaydet();
  }

  void _rozetleriTazele(int toplamGorev) {
    void ver(String r) {
      if (!rozetler.contains(r)) rozetler = [...rozetler, r];
    }
    final n = bitenGorevler.length;
    if (n >= 1) ver('ilk_adim');
    if (n >= (toplamGorev / 2).ceil()) ver('yarim_yol');
    if (n >= toplamGorev) {
      ver('mezun');
      // Kusursuz: HER görev ilk denemede. Sonda veriliyor çünkü erken
      // verilirse sonraki hatada geri almak gerekirdi ve kazanılmış bir
      // rozeti geri almak, hiç vermemekten daha kötü.
      if (bitenGorevler.every((k) => (denemeler[k] ?? 1) <= 1)) {
        ver('kusursuz');
      }
    }
    if (kapali.isNotEmpty) ver('ilk_islem');
    if (kapali.any((i) => i.kar > 0)) ver('ilk_kar');
    if (kapali.any((i) => i.sebep == 'stop')) ver('ilk_stop');
  }

  /// İşlem sonrası rozet kontrolü — alım/çıkış görevden bağımsız olabilir.
  Future<void> islemRozetleri({int toplamGorev = 8}) async {
    final onceki = rozetler.length;
    _rozetleriTazele(toplamGorev);
    if (rozetler.length != onceki) await _kaydet();
  }
}

final kum = KumHavuzu();
