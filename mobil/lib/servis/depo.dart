import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api.dart';
import 'modeller.dart';

/// Uygulama durumu ve kalıcı depo.
///
/// POZİSYONLAR: tek kaynak sunucudaki KARAR DEFTERİ. Telefon yerel bir
/// kopya saklar ama o yalnızca çevrimdışı okumak içindir; ekleme ve
/// kapatma sunucuya yazar, sonra kopya tazelenir.
///
/// Neden değişti: pozisyonlar hem telefonda hem defterde tutulunca iki
/// kaynak birbirinden sapıyordu ve hangisinin doğru olduğu bilinmiyordu.
/// Sunucu artık 7/24 açık (bulut), yani "sunucu çökerse geçmişini
/// göremezsin" gerekçesi de ortadan kalktı.
///
/// TEZLER ve AYARLAR hâlâ cihazda: onlar hesaplama girdisi değil, senin
/// yazdığın metinler.
class Depo extends ChangeNotifier {
  static const _kPoz = 'pozisyonlar_v1';
  static const _kTez = 'tezler_v1';
  static const _kAyar = 'ayarlar_v1';
  static const _kPara = 'para_hareketleri_v1';

  SharedPreferences? _p;
  Ayarlar _ayarlar = Ayarlar();
  List<Pozisyon> _pozisyonlar = [];
  List<Tez> _tezler = [];
  List<ParaHareketi> _hareketler = [];
  List<Map<String, String>> tezSorulari = [];

  Ayarlar get ayarlar => _ayarlar;
  List<Pozisyon> get pozisyonlar => List.unmodifiable(_pozisyonlar);
  List<Tez> get tezler => List.unmodifiable(_tezler);
  List<Tez> get acikTezler => _tezler.where((t) => t.acik).toList();
  List<Tez> get kapaliTezler => _tezler.where((t) => !t.acik).toList();

  Api get api => Api(_ayarlar.sunucu, anahtar: _ayarlar.apiAnahtar);

  List<ParaHareketi> get hareketler => List.unmodifiable(_hareketler);

  double get toplamMaliyet =>
      _pozisyonlar.fold(0.0, (a, p) => a + p.maliyet);
  double get nakit => (_ayarlar.sermaye - toplamMaliyet).clamp(0, double.infinity);

  /// Sermaye defterden türer: tüm hareketlerin toplamı.
  /// Ayarlar.sermaye bunun yazılmış kopyasıdır (eski kod bozulmasın diye).
  double get _defterToplami =>
      _hareketler.fold(0.0, (a, h) => a + h.tutar);

  /// Senin cebinden koyduğun net para. Kâr/zarar buna DAHİL DEĞİL.
  double get netYatirilan => _hareketler
      .where((h) => h.sermayeGirisi)
      .fold(0.0, (a, h) => a + h.tutar);

  /// Kapanmış pozisyonlardan gelen gerçekleşen kâr/zarar.
  double get gerceklesenKar => _hareketler
      .where((h) => h.tur == HareketTur.kar || h.tur == HareketTur.zarar)
      .fold(0.0, (a, h) => a + h.tutar);

  /// Sermayenin yatırdığın paraya göre yüzde getirisi.
  /// Açık pozisyonların değer artışı BURADA YOK — o gerçekleşmedi.
  double? get gerceklesenGetiriYuzde {
    final y = netYatirilan;
    if (y <= 0) return null;
    return gerceklesenKar / y * 100;
  }

  bool tezVarMi(String sembol) =>
      _tezler.any((t) => t.sembol == sembol.toUpperCase() && t.acik);

  Tez? acikTez(String sembol) {
    final s = sembol.toUpperCase();
    for (final t in _tezler) {
      if (t.sembol == s && t.acik) return t;
    }
    return null;
  }

  Pozisyon? pozisyon(String sembol) {
    final s = sembol.toUpperCase();
    for (final p in _pozisyonlar) {
      if (p.sembol == s) return p;
    }
    return null;
  }

  Future<void> yukle() async {
    _p = await SharedPreferences.getInstance();
    try {
      final a = _p!.getString(_kAyar);
      if (a != null) _ayarlar = Ayarlar.fromJson(jsonDecode(a));
    } catch (_) {}
    try {
      final s = _p!.getString(_kPoz);
      if (s != null) {
        _pozisyonlar = (jsonDecode(s) as List)
            .map((e) => Pozisyon.fromJson(Map<String, dynamic>.from(e)))
            .toList();
      }
    } catch (_) {}
    try {
      final s = _p!.getString(_kTez);
      if (s != null) {
        _tezler = (jsonDecode(s) as List)
            .map((e) => Tez.fromJson(Map<String, dynamic>.from(e)))
            .toList();
      }
    } catch (_) {}
    try {
      final s = _p!.getString(_kPara);
      if (s != null) {
        _hareketler = (jsonDecode(s) as List)
            .map((e) => ParaHareketi.fromJson(Map<String, dynamic>.from(e)))
            .toList();
      }
    } catch (_) {}
    // Defteri olmayan eski kurulum: mevcut sermayeyi ilk yatırma say.
    // Aksi halde "net yatırılan 0" çıkar ve getiri yüzdesi sonsuza gider.
    if (_hareketler.isEmpty && _ayarlar.sermaye > 0) {
      _hareketler = [
        ParaHareketi(
          tarih: DateTime.now().toIso8601String().substring(0, 10),
          tutar: _ayarlar.sermaye,
          tur: HareketTur.yatirma,
          not: 'başlangıç sermayesi',
        )
      ];
      await _kaydetPara(bildir: false);
    }
    notifyListeners();
  }

  Future<void> _kaydetPara({bool bildir = true}) async {
    await _p?.setString(
        _kPara, jsonEncode(_hareketler.map((h) => h.toJson()).toList()));
    // Ayarlar.sermaye defterin yazılmış kopyası — pozisyon boyutu, nakit ve
    // tarama hep oradan okuyor, tek kaynağı bozmayalım.
    final yeni = _defterToplami;
    if ((yeni - _ayarlar.sermaye).abs() > 0.005) {
      _ayarlar = _ayarlar.kopya(sermaye: yeni);
      await _p?.setString(_kAyar, jsonEncode(_ayarlar.toJson()));
    }
    if (bildir) notifyListeners();
  }

  /// Deftere kayıt ekler ve sermayeyi günceller.
  Future<void> paraEkle(ParaHareketi h) async {
    _hareketler.add(h);
    await _kaydetPara();
  }

  Future<void> paraSil(int sira) async {
    if (sira < 0 || sira >= _hareketler.length) return;
    _hareketler.removeAt(sira);
    await _kaydetPara();
  }

  /// "Toplam sermayem şu kadar" — farkı deftere yazar.
  ///
  /// [sebep] ZORUNLU çünkü farkın NEDEN oluştuğu sonucu değiştirir:
  /// uygulama dışında para yatırdıysan bu yatırdığın parayı büyütmeli,
  /// uygulama dışında işlem yaptıysan kâr/zarar sayılmalı. İkisini
  /// ayırmazsak "yatırdığın para" ile toplam arasındaki bağ kopar ve
  /// ekranda olmayan bir zarar görünür.
  ///
  /// [HareketTur.duzeltme] son çare: nedenini bilmediğin küçük farklar için.
  Future<void> sermayeyiAyarla(double yeniToplam,
      {HareketTur sebep = HareketTur.duzeltme, String not = ''}) async {
    final fark = yeniToplam - _defterToplami;
    if (fark.abs() < 0.005) return;
    // Yön ile tür tutarlı olmalı: eksi fark "kâr" diye yazılamaz.
    final tur = switch (sebep) {
      HareketTur.yatirma || HareketTur.cekme =>
        fark >= 0 ? HareketTur.yatirma : HareketTur.cekme,
      HareketTur.kar || HareketTur.zarar =>
        fark >= 0 ? HareketTur.kar : HareketTur.zarar,
      HareketTur.duzeltme => HareketTur.duzeltme,
    };
    await paraEkle(ParaHareketi(
      tarih: DateTime.now().toIso8601String().substring(0, 10),
      tutar: fark,
      tur: tur,
      not: not.isEmpty
          ? 'toplam ${yeniToplam.toStringAsFixed(0)} TL olarak hizalandı'
          : not,
    ));
  }

  /// Defterin kendi içinde tutarlı olup olmadığı.
  /// Düzeltme kayıtları "yatırdığın para" hesabına girmez; çok birikirse
  /// getiri yüzdesi anlamını yitirir ve kullanıcı uyarılmalıdır.
  double get duzeltmeToplami => _hareketler
      .where((h) => h.tur == HareketTur.duzeltme)
      .fold(0.0, (a, h) => a + h.tutar);

  Future<void> _kaydetPoz() async {
    await _p?.setString(
        _kPoz, jsonEncode(_pozisyonlar.map((p) => p.toJson()).toList()));
    notifyListeners();
  }

  Future<void> _kaydetTez() async {
    await _p?.setString(
        _kTez, jsonEncode(_tezler.map((t) => t.toJson()).toList()));
    notifyListeners();
  }

  Future<void> ayarKaydet(Ayarlar a) async {
    _ayarlar = a;
    await _p?.setString(_kAyar, jsonEncode(a.toJson()));
    notifyListeners();
  }

  /// Yerel kopyayı sunucudaki defterden tazeler.
  ///
  /// Ağ hatasında SESSİZ kalır ve eldeki kopya durur: çevrimdışıyken
  /// pozisyonlarını görebilmelisin. Boş liste göstermek, "hiç pozisyonun
  /// yok" demek olurdu — yanlış ve tehlikeli.
  Future<bool> pozisyonlariSenkronla() async {
    try {
      final d = await api.defter();
      final acik = (d['acik'] as List?) ?? [];
      _pozisyonlar = acik.map((e) {
        final m = Map<String, dynamic>.from(e as Map);
        return Pozisyon(
          sembol: '${m['sembol']}',
          adet: ((m['adet'] ?? 0) as num).toInt(),
          giris: ((m['giris'] ?? 0) as num).toDouble(),
          stop: ((m['stop'] ?? 0) as num).toDouble(),
          hedef: ((m['hedef'] ?? 0) as num).toDouble(),
          tarih: '${m['tarih'] ?? ''}',
          strateji: '${m['strateji'] ?? 'kirilim'}',
        );
      }).toList();
      await _kaydetPoz();
      notifyListeners();
      return true;
    } catch (_) {
      return false;   // çevrimdışı: eldeki kopya kalsın
    }
  }

  /// Alımı DEFTERE yazar, sonra yerel kopyayı tazeler.
  /// Sunucuya yazılamazsa yerel kayıt da yapılmaz — yoksa telefonda olup
  /// defterde olmayan bir pozisyon oluşur ve ölçüm bozulur.
  Future<void> pozisyonEkle(Pozisyon p, {bool kagit = true}) async {
    await api.defterAlim(p, kagit: kagit);
    await pozisyonlariSenkronla();
  }

  Future<void> pozisyonGuncelle(Pozisyon p) async {
    final i = _pozisyonlar.indexWhere((x) => x.sembol == p.sembol);
    if (i >= 0) {
      _pozisyonlar[i] = p;
      await _kaydetPoz();
    }
  }

  /// Pozisyonu kapatır ve varsa tezini de sonuçlandırır.
  /// İkisi birlikte kapanmalı: kapanış notu olmayan işlem, tekrarlanacak hatadır.
  Future<void> pozisyonKapat(String sembol, double cikis,
      {String sebep = 'elle', String ders = ''}) async {
    final s = sembol.toUpperCase();
    final poz = pozisyon(s);
    // Önce deftere yaz: sunucu kabul etmezse yerelde de kapatma.
    await api.defterSatim(s, cikis, gerekce: sebep);
    await pozisyonlariSenkronla();
    final i = _tezler.indexWhere((t) => t.sembol == s && t.acik);
    if (i >= 0) _tezler[i] = _tezler[i].kapat(cikis, sebep, ders);
    await _kaydetTez();
    // Gerçekleşen kâr/zarar sermayeye yazılmazsa kazancın uygulamanın
    // hesabından kaybolur ve bir sonraki pozisyon boyutu yanlış çıkar.
    if (poz != null) {
      final fark = (cikis - poz.giris) * poz.adet;
      if (fark.abs() > 0.005) {
        await paraEkle(ParaHareketi(
          tarih: DateTime.now().toIso8601String().substring(0, 10),
          tutar: fark,
          tur: fark >= 0 ? HareketTur.kar : HareketTur.zarar,
          not: '$s ${poz.adet} adet · ${poz.giris.toStringAsFixed(2)} → '
              '${cikis.toStringAsFixed(2)}',
        ));
      }
    }
  }

  Future<void> tezEkle(Tez t) async {
    _tezler.removeWhere((x) => x.sembol == t.sembol && x.acik);
    _tezler.add(t);
    await _kaydetTez();
  }

  Future<void> tezSil(String sembol) async {
    _tezler.removeWhere((t) => t.sembol == sembol.toUpperCase() && t.acik);
    await _kaydetTez();
  }

  /// Kapanmış tezlerden çıkan karne. Tam tez yazdıklarınla yazmadıkların
  /// arasındaki fark, disiplinin ölçüsüdür.
  Map<String, dynamic> karne() {
    final k = kapaliTezler;
    if (k.isEmpty) return {'islem': 0};
    double g(Tez t) => ((t.kapanis!['getiri_yuzde'] ?? 0) as num).toDouble();
    final getiriler = k.map(g).toList();
    final kazanan = getiriler.where((x) => x > 0).length;
    final tam = k.where((t) => t.eksikler(tezSorulari).isEmpty).toList();
    final eksik = k.where((t) => t.eksikler(tezSorulari).isNotEmpty).toList();
    double ort(List<Tez> l) =>
        l.isEmpty ? 0 : l.map(g).reduce((a, b) => a + b) / l.length;
    return {
      'islem': k.length,
      'kazanma': kazanan / k.length * 100,
      'ortalama': getiriler.reduce((a, b) => a + b) / getiriler.length,
      'enIyi': getiriler.reduce((a, b) => a > b ? a : b),
      'enKotu': getiriler.reduce((a, b) => a < b ? a : b),
      'tamSayi': tam.length, 'eksikSayi': eksik.length,
      'tamOrt': tam.isEmpty ? null : ort(tam),
      'eksikOrt': eksik.isEmpty ? null : ort(eksik),
      'dersler': k
          .where((t) => ((t.kapanis!['ders'] ?? '') as String).trim().isNotEmpty)
          .map((t) => t.kapanis!['ders'] as String)
          .toList(),
    };
  }

  /// Davranışsal taramaya gönderilecek geçmiş — son kapanışlar.
  List<Map<String, dynamic>> gecmisGetiriler() => kapaliTezler
      .map((t) => {
            'kapanis': {
              'tarih': t.kapanis!['tarih'],
              'getiri_yuzde': t.kapanis!['getiri_yuzde'],
            },
            'adet': t.adet, 'fiyat': t.fiyat,
          })
      .toList();
}

/// Tek örnek — uygulama boyunca aynı depo.
final depo = Depo();
