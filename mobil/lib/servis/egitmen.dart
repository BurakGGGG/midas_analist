import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Eğitmen motoru — telefonda çalışır.
///
/// Soru bankası sunucudan bir kez indirilip saklanır; aralıklı tekrar hesabı
/// burada yapılır. Böylece internet olmadan da çalışabilirsin. Sadece CANLI
/// sorular (bugünkü piyasa verisinden üretilenler) bağlantı ister.

/// Bir ders — müfredatın temel birimi.
class Ders {
  final String kod, baslik, ozet, icerik, bist, tuzak, ornek;
  final List<String> sorular;
  final int sure;

  const Ders({
    required this.kod, required this.baslik, required this.ozet,
    required this.icerik, this.bist = '', this.tuzak = '', this.ornek = '',
    this.sorular = const [], this.sure = 6,
  });

  factory Ders.fromJson(Map<String, dynamic> j) => Ders(
        kod: '${j['kod']}',
        baslik: '${j['baslik']}',
        ozet: '${j['ozet'] ?? ''}',
        icerik: '${j['icerik'] ?? ''}',
        bist: '${j['bist'] ?? ''}',
        tuzak: '${j['tuzak'] ?? ''}',
        ornek: '${j['ornek'] ?? ''}',
        sorular: ((j['sorular'] ?? []) as List).map((e) => '$e').toList(),
        sure: ((j['sure'] ?? 6) as num).toInt(),
      );
}

class EgitmenModul {
  final String kod, ad, aciklama;
  final int seviye, dakika;
  final List<Ders> dersler;

  const EgitmenModul({
    required this.kod, required this.ad, required this.aciklama,
    this.seviye = 1, this.dakika = 0, this.dersler = const [],
  });

  factory EgitmenModul.fromJson(Map<String, dynamic> j) => EgitmenModul(
        kod: '${j['kod']}',
        ad: '${j['ad']}',
        aciklama: '${j['aciklama'] ?? ''}',
        seviye: ((j['seviye'] ?? 1) as num).toInt(),
        dakika: ((j['dakika'] ?? 0) as num).toInt(),
        dersler: ((j['dersler'] ?? []) as List)
            .map((e) => Ders.fromJson(Map<String, dynamic>.from(e)))
            .toList(),
      );
}

/// Bir dersin okunma durumu. Sorulardan farklı: ders unutma eğrisiyle değil,
/// ihtiyaç duyulduğunda tekrar edilir.
class DersKaydi {
  final String kod, ilkOkuma, sonOkuma;
  final bool okundu, isaretli;
  final int okumaSayisi;

  const DersKaydi({
    required this.kod, this.okundu = false, this.ilkOkuma = '',
    this.sonOkuma = '', this.okumaSayisi = 0, this.isaretli = false,
  });

  Map<String, dynamic> toJson() => {
        'kod': kod, 'okundu': okundu, 'ilkOkuma': ilkOkuma,
        'sonOkuma': sonOkuma, 'okumaSayisi': okumaSayisi, 'isaretli': isaretli,
      };

  factory DersKaydi.fromJson(Map<String, dynamic> j) => DersKaydi(
        kod: '${j['kod']}',
        okundu: (j['okundu'] ?? false) as bool,
        ilkOkuma: '${j['ilkOkuma'] ?? ''}',
        sonOkuma: '${j['sonOkuma'] ?? ''}',
        okumaSayisi: ((j['okumaSayisi'] ?? 0) as num).toInt(),
        isaretli: (j['isaretli'] ?? false) as bool,
      );
}

class EgitmenSoru {
  final String kod, kategori, soru, cevap, tuzak;
  final int seviye;
  final List<String> anahtar;
  final bool canli;

  const EgitmenSoru({
    required this.kod, required this.kategori, required this.soru,
    required this.cevap, this.tuzak = '', this.seviye = 1,
    this.anahtar = const [], this.canli = false,
  });

  factory EgitmenSoru.fromJson(Map<String, dynamic> j) => EgitmenSoru(
        kod: '${j['kod']}',
        kategori: '${j['kategori'] ?? ''}',
        soru: '${j['soru']}',
        cevap: '${j['cevap']}',
        tuzak: '${j['tuzak'] ?? ''}',
        seviye: ((j['seviye'] ?? 1) as num).toInt(),
        anahtar: ((j['anahtar'] ?? []) as List).map((e) => '$e').toList(),
        canli: (j['canli'] ?? false) as bool,
      );

  Map<String, dynamic> toJson() => {
        'kod': kod, 'kategori': kategori, 'soru': soru, 'cevap': cevap,
        'tuzak': tuzak, 'seviye': seviye, 'anahtar': anahtar, 'canli': canli,
      };
}

/// Tek bir sorunun öğrenme durumu (SM-2).
class Kayit {
  final String kod;
  final int tekrar;
  final double kolaylik;
  final int aralik;
  final String son, sonraki;
  final int dogru, yanlis;

  const Kayit({
    required this.kod, this.tekrar = 0, this.kolaylik = 2.5, this.aralik = 0,
    this.son = '', this.sonraki = '', this.dogru = 0, this.yanlis = 0,
  });

  /// Üç kez üst üste doğru VE aralık 21 günü geçmişse öğrenilmiş sayılır.
  bool get ogrenildi => tekrar >= 3 && aralik >= 21;

  DateTime? get sonrakiTarih => DateTime.tryParse(sonraki);

  bool vadesiGeldi(DateTime bugun) {
    final t = sonrakiTarih;
    return t == null || !t.isAfter(bugun);
  }

  Map<String, dynamic> toJson() => {
        'kod': kod, 'tekrar': tekrar, 'kolaylik': kolaylik, 'aralik': aralik,
        'son': son, 'sonraki': sonraki, 'dogru': dogru, 'yanlis': yanlis,
      };

  factory Kayit.fromJson(Map<String, dynamic> j) => Kayit(
        kod: '${j['kod']}',
        tekrar: ((j['tekrar'] ?? 0) as num).toInt(),
        kolaylik: ((j['kolaylik'] ?? 2.5) as num).toDouble(),
        aralik: ((j['aralik'] ?? 0) as num).toInt(),
        son: '${j['son'] ?? ''}',
        sonraki: '${j['sonraki'] ?? ''}',
        dogru: ((j['dogru'] ?? 0) as num).toInt(),
        yanlis: ((j['yanlis'] ?? 0) as num).toInt(),
      );

  /// SM-2. Kalite < 3 ise sıfırdan başlar — yanlış hatırlanan bilgi,
  /// hiç hatırlanmayandan daha tehlikelidir çünkü ona güvenirsin.
  Kayit guncelle(int kalite) {
    final bugun = DateTime.now();
    int yTekrar = tekrar, yAralik = aralik, yDogru = dogru, yYanlis = yanlis;

    if (kalite < 3) {
      yTekrar = 0;
      yAralik = 1;
      yYanlis += 1;
    } else {
      yDogru += 1;
      if (tekrar == 0) {
        yAralik = 1;
      } else if (tekrar == 1) {
        yAralik = 6;
      } else {
        yAralik = (aralik * kolaylik).round();
      }
      yTekrar += 1;
    }

    var yKolaylik =
        kolaylik + (0.1 - (5 - kalite) * (0.08 + (5 - kalite) * 0.02));
    if (yKolaylik < 1.3) yKolaylik = 1.3;

    final sonrakiG = bugun.add(Duration(days: yAralik < 1 ? 1 : yAralik));
    String gun(DateTime d) => d.toIso8601String().substring(0, 10);

    return Kayit(
      kod: kod, tekrar: yTekrar, kolaylik: yKolaylik, aralik: yAralik,
      son: gun(bugun), sonraki: gun(sonrakiG), dogru: yDogru, yanlis: yYanlis,
    );
  }
}

class SeviyeDurum {
  final int seviye;
  final String unvan, sonrakiSeviye;
  final Map<String, ({int ogrenilen, int toplam, int yuzde})> katmanlar;
  final int calisilan, toplamSoru;
  final double bilesikYuzde;
  final int dersOkunan, dersToplam, dakikaKalan;

  const SeviyeDurum({
    required this.seviye, required this.unvan, required this.sonrakiSeviye,
    required this.katmanlar, required this.calisilan, required this.toplamSoru,
    this.bilesikYuzde = 0, this.dersOkunan = 0, this.dersToplam = 0,
    this.dakikaKalan = 0,
  });
}

class Egitmen {
  static const _kBanka = 'egitmen_banka_v1';
  static const _kIlerleme = 'egitmen_ilerleme_v1';
  static const _kMufredat = 'egitmen_mufredat_v1';
  static const _kDers = 'egitmen_ders_v1';

  /// Sunucudaki banka bu sürümden yeniyse yeniden indirilir. Sürüm artmadan
  /// içerik değişirse telefon eski metni göstermeye devam eder — bu yüzden
  /// soru bankasına dokunan her değişiklikte sunucudaki `surum` artırılmalı.
  static const surum = 4;
  // 3: m13 grafik okuma modülü eklendi (7 ders + şemalar).
  // Bu sayı artmazsa telefondaki eski banka kullanılmaya devam eder.
  static const mufredatSurum = 3;

  List<EgitmenModul> moduller = [];
  Map<String, DersKaydi> dersKayit = {};
  int mufredatBankaSurum = 0;

  List<EgitmenSoru> sorular = [];
  List<Map<String, String>> sirketOkuma = [];
  List<String> ilkeler = [];
  Map<String, Kayit> ilerleme = {};
  int bankaSurum = 0;

  bool get bankaVar => sorular.isNotEmpty && bankaSurum >= surum;
  bool get mufredatVar =>
      moduller.isNotEmpty && mufredatBankaSurum >= mufredatSurum;

  List<Ders> get tumDersler => [for (final m in moduller) ...m.dersler];

  Ders? ders(String kod) {
    for (final m in moduller) {
      for (final d in m.dersler) {
        if (d.kod == kod) return d;
      }
    }
    return null;
  }

  EgitmenModul? dersModulu(String kod) {
    for (final m in moduller) {
      if (m.dersler.any((d) => d.kod == kod)) return m;
    }
    return null;
  }

  bool okundu(String kod) => dersKayit[kod]?.okundu ?? false;

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    try {
      final b = p.getString(_kBanka);
      if (b != null) _bankaAyikla(jsonDecode(b) as Map<String, dynamic>);
    } catch (_) {}
    try {
      final i = p.getString(_kIlerleme);
      if (i != null) {
        final m = jsonDecode(i) as Map<String, dynamic>;
        ilerleme = m.map((k, v) =>
            MapEntry(k, Kayit.fromJson(Map<String, dynamic>.from(v))));
      }
    } catch (_) {}
    try {
      final f = p.getString(_kMufredat);
      if (f != null) _mufredatAyikla(jsonDecode(f) as Map<String, dynamic>);
    } catch (_) {}
    try {
      final d = p.getString(_kDers);
      if (d != null) {
        final m = jsonDecode(d) as Map<String, dynamic>;
        dersKayit = m.map((k, v) =>
            MapEntry(k, DersKaydi.fromJson(Map<String, dynamic>.from(v))));
      }
    } catch (_) {}
  }

  void _mufredatAyikla(Map<String, dynamic> j) {
    mufredatBankaSurum = ((j['surum'] ?? 0) as num).toInt();
    moduller = ((j['moduller'] ?? []) as List)
        .map((e) => EgitmenModul.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  Future<void> mufredatKaydet(Map<String, dynamic> j) async {
    _mufredatAyikla(j);
    final p = await SharedPreferences.getInstance();
    await p.setString(_kMufredat, jsonEncode(j));
  }

  Future<void> _dersKaydet() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kDers,
        jsonEncode(dersKayit.map((k, v) => MapEntry(k, v.toJson()))));
  }

  Future<void> dersOkundu(String kod) async {
    final e = dersKayit[kod];
    final bugun = DateTime.now().toIso8601String().substring(0, 10);
    dersKayit[kod] = DersKaydi(
      kod: kod, okundu: true,
      ilkOkuma: (e?.ilkOkuma.isNotEmpty ?? false) ? e!.ilkOkuma : bugun,
      sonOkuma: bugun,
      okumaSayisi: (e?.okumaSayisi ?? 0) + 1,
      isaretli: e?.isaretli ?? false,
    );
    await _dersKaydet();
  }

  Future<void> dersIsaretle(String kod, bool deger) async {
    final e = dersKayit[kod] ?? DersKaydi(kod: kod);
    dersKayit[kod] = DersKaydi(
      kod: kod, okundu: e.okundu, ilkOkuma: e.ilkOkuma, sonOkuma: e.sonOkuma,
      okumaSayisi: e.okumaSayisi, isaretli: deger,
    );
    await _dersKaydet();
  }

  /// Müfredat sırasına göre okunmamış ilk ders(ler).
  List<Ders> gunlukDers({int adet = 1}) {
    final cikti = <Ders>[];
    for (final d in tumDersler) {
      if (!okundu(d.kod)) {
        cikti.add(d);
        if (cikti.length >= adet) break;
      }
    }
    return cikti;
  }

  List<Ders> get isaretliDersler => [
        for (final e in dersKayit.entries)
          if (e.value.isaretli && ders(e.key) != null) ders(e.key)!
      ];

  void _bankaAyikla(Map<String, dynamic> j) {
    bankaSurum = ((j['surum'] ?? 0) as num).toInt();
    sorular = ((j['sorular'] ?? []) as List)
        .map((e) => EgitmenSoru.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    sirketOkuma = ((j['sirket_okuma'] ?? []) as List)
        .map((e) => {
              'anahtar': '${e['anahtar']}',
              'soru': '${e['soru']}',
              'aciklama': '${e['aciklama']}',
            })
        .toList();
    ilkeler = ((j['ilkeler'] ?? []) as List).map((e) => '$e').toList();
  }

  Future<void> bankaKaydet(Map<String, dynamic> j) async {
    _bankaAyikla(j);
    final p = await SharedPreferences.getInstance();
    await p.setString(_kBanka, jsonEncode(j));
  }

  Future<void> _ilerlemeKaydet() async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kIlerleme,
        jsonEncode(ilerleme.map((k, v) => MapEntry(k, v.toJson()))));
  }

  Future<void> cevapla(String kod, int kalite) async {
    final eski = ilerleme[kod] ?? Kayit(kod: kod);
    ilerleme[kod] = eski.guncelle(kalite);
    await _ilerlemeKaydet();
  }

  Future<void> sifirla() async {
    ilerleme = {};
    dersKayit = {};
    await _ilerlemeKaydet();
    await _dersKaydet();
  }

  /// Seviye artık ders okumaya dayanır (2/3 ağırlık), sorular ikincildir (1/3).
  /// Sebep: bu bir sınav değil, bir müfredat.
  SeviyeDurum durum() {
    ({int ogrenilen, int toplam, int yuzde}) say(int sv) {
      final liste = sorular.where((s) => s.seviye == sv).toList();
      final o = liste.where((s) => ilerleme[s.kod]?.ogrenildi ?? false).length;
      final t = liste.isEmpty ? 1 : liste.length;
      return (ogrenilen: o, toplam: liste.length, yuzde: (o / t * 100).round());
    }

    final t = say(1), o = say(2), u = say(3);
    final tumD = tumDersler;
    final okunanD = tumD.where((d) => okundu(d.kod)).length;
    final dersYuzde = tumD.isEmpty ? 0.0 : okunanD / tumD.length * 100;
    final soruOgrenilen = t.ogrenilen + o.ogrenilen + u.ogrenilen;
    final soruYuzde =
        sorular.isEmpty ? 0.0 : soruOgrenilen / sorular.length * 100;
    final bilesik = dersYuzde * (2 / 3) + soruYuzde * (1 / 3);

    var seviye = 1;
    if (bilesik >= 35) seviye = 2;
    if (bilesik >= 70) seviye = 3;
    var unvan = {1: 'Çırak', 2: 'Kalfa', 3: 'Usta'}[seviye]!;
    if (bilesik >= 90) unvan = 'Usta (tamamlandı)';

    final kalanDk = tumD
        .where((d) => !okundu(d.kod))
        .fold(0, (a, d) => a + d.sure);

    return SeviyeDurum(
      seviye: seviye, unvan: unvan,
      sonrakiSeviye: tumD.isEmpty
          ? 'Müfredat henüz indirilmedi.'
          : 'Derslerin %${dersYuzde.round()}\'ini okudun · $kalanDk dakika kaldı',
      katmanlar: {'temel': t, 'orta': o, 'usta': u},
      calisilan: ilerleme.length, toplamSoru: sorular.length,
      bilesikYuzde: bilesik,
      dersOkunan: okunanD, dersToplam: tumD.length, dakikaKalan: kalanDk,
    );
  }

  /// Bugünün soruları: önce vadesi gelen tekrarlar, sonra yeni sorular.
  /// Tekrar olmadan öğrenme kalıcı olmaz, yeni soru olmadan ilerleme olmaz.
  List<EgitmenSoru> gunlukSecim({int adet = 5}) {
    if (sorular.isEmpty) return [];
    final bugun = DateTime.now();
    final d = durum();
    final acik = List.generate(d.seviye, (i) => i + 1);

    // Ders okumadan o dersin sorusu sorulmaz — bu bir sınav değil, pekiştirme.
    final okunanSorular = <String>{};
    for (final d in tumDersler) {
      if (okundu(d.kod)) okunanSorular.addAll(d.sorular);
    }

    final vadesi = <EgitmenSoru>[], yeni = <EgitmenSoru>[];
    for (final s in sorular) {
      if (okunanSorular.isNotEmpty && !okunanSorular.contains(s.kod)) continue;
      final k = ilerleme[s.kod];
      if (k == null) {
        if (acik.contains(s.seviye)) yeni.add(s);
      } else if (k.vadesiGeldi(bugun)) {
        vadesi.add(s);
      }
    }
    vadesi.sort((a, b) =>
        (ilerleme[a.kod]!.sonraki).compareTo(ilerleme[b.kod]!.sonraki));
    yeni.sort((a, b) => a.seviye != b.seviye
        ? a.seviye.compareTo(b.seviye)
        : a.kod.compareTo(b.kod));

    final tekrarPayi =
        vadesi.isEmpty ? 0 : (adet ~/ 2).clamp(1, vadesi.length);
    final secim = <EgitmenSoru>[...vadesi.take(tekrarPayi)];
    secim.addAll(yeni.take(adet - secim.length));
    if (secim.length < adet) {
      secim.addAll(vadesi.skip(tekrarPayi).take(adet - secim.length));
    }
    return secim.take(adet).toList();
  }

  Map<String, dynamic> istatistik() {
    if (ilerleme.isEmpty) return {'calisilan': 0};
    final d = ilerleme.values.fold(0, (a, k) => a + k.dogru);
    final y = ilerleme.values.fold(0, (a, k) => a + k.yanlis);
    final bugun = DateTime.now();
    final zorlar = ilerleme.values.where((k) => k.yanlis > 0).toList()
      ..sort((a, b) => b.yanlis != a.yanlis
          ? b.yanlis.compareTo(a.yanlis)
          : a.kolaylik.compareTo(b.kolaylik));
    String soruMetni(String kod) =>
        sorular.where((s) => s.kod == kod).firstOrNull?.soru ?? kod;
    return {
      'calisilan': ilerleme.length,
      'ogrenilen': ilerleme.values.where((k) => k.ogrenildi).length,
      'toplamCevap': d + y,
      'dogruOrani': (d + y) == 0 ? 0.0 : d / (d + y) * 100,
      'vadesiGelen':
          ilerleme.values.where((k) => k.vadesiGeldi(bugun)).length,
      'zorlar': zorlar.take(5).map((k) => {
            'soru': soruMetni(k.kod), 'yanlis': k.yanlis, 'dogru': k.dogru,
          }).toList(),
    };
  }

  String ilkeGunun() {
    if (ilkeler.isEmpty) return '';
    final g = DateTime.now();
    final i = (g.year * 372 + g.month * 31 + g.day) % ilkeler.length;
    return ilkeler[i];
  }
}

final egitmen = Egitmen();
