import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'ders.dart';

/// Uygulama sözlüğü.
///
/// NEDEN ÖNBELLEKLİ: sözlüğe en çok bakılacak an, tarama ekranında bir
/// sütuna takıldığın andır — ve o an internet olmayabilir. Önce kayıtlı
/// kopya çizilir (anında), arkadan tazesi çekilir. Sunucuya ulaşılamazsa
/// eski kopya kalır; boş ekran göstermek sözlüğün hiç olmamasıdır.
class SozlukEkran extends StatefulWidget {
  const SozlukEkran({super.key});

  @override
  State<SozlukEkran> createState() => _SozlukDurum();
}

class _SozlukDurum extends State<SozlukEkran> {
  static const _anahtar = 'sozluk_v1';

  List<dynamic> _bolumler = [];
  Object? _hata;
  bool _yukleniyor = true;
  String _arama = '';
  final _denetim = TextEditingController();

  @override
  void initState() {
    super.initState();
    _getir();
  }

  @override
  void dispose() {
    _denetim.dispose();
    super.dispose();
  }

  Future<void> _getir() async {
    // 1) kayıtlı kopya — varsa ekran hemen dolar
    try {
      final p = await SharedPreferences.getInstance();
      final ham = p.getString(_anahtar);
      if (ham != null && mounted) {
        final j = jsonDecode(ham) as Map<String, dynamic>;
        setState(() {
          _bolumler = (j['bolumler'] ?? []) as List<dynamic>;
          _yukleniyor = false;
        });
      }
    } catch (_) {}

    // 2) tazesi
    try {
      final j = await depo.api.sozluk();
      final p = await SharedPreferences.getInstance();
      await p.setString(_anahtar, jsonEncode(j));
      if (mounted) {
        setState(() {
          _bolumler = (j['bolumler'] ?? []) as List<dynamic>;
          _yukleniyor = false;
          _hata = null;
        });
      }
    } catch (e) {
      // Kayıtlı kopya varsa hata gösterme — kullanıcı sözlüğü okuyabiliyor.
      if (mounted) {
        setState(() {
          _yukleniyor = false;
          if (_bolumler.isEmpty) _hata = e;
        });
      }
    }
  }

  bool _eslesir(Map<String, dynamic> t) {
    if (_arama.isEmpty) return true;
    final q = _arama.toLowerCase();
    if ('${t['terim']}'.toLowerCase().contains(q)) return true;
    if ('${t['kisa']}'.toLowerCase().contains(q)) return true;
    for (final k in (t['kolonlar'] ?? []) as List) {
      if ('$k'.toLowerCase().contains(q)) return true;
    }
    return false;
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);

    final gruplar = <MapEntry<Map<String, dynamic>, List<Map<String, dynamic>>>>[];
    var bulunan = 0;
    for (final b in _bolumler) {
      final bm = Map<String, dynamic>.from(b as Map);
      final terimler = ((bm['terimler'] ?? []) as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .where(_eslesir)
          .toList();
      bulunan += terimler.length;
      if (terimler.isNotEmpty) gruplar.add(MapEntry(bm, terimler));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Sözlük')),
      body: _hata != null
          ? HataGorunum(_hata!, tekrar: _getir)
          : _yukleniyor && _bolumler.isEmpty
              ? const Yukleniyor()
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                      child: TextField(
                        controller: _denetim,
                        onChanged: (v) => setState(() => _arama = v.trim()),
                        style: Theme.of(c).textTheme.bodyMedium,
                        decoration: InputDecoration(
                          hintText: 'Terim ya da sütun ara',
                          prefixIcon: const Icon(Icons.search_sharp, size: 19),
                          suffixIcon: _arama.isEmpty
                              ? null
                              : IconButton(
                                  icon: const Icon(Icons.close_sharp, size: 18),
                                  onPressed: () {
                                    _denetim.clear();
                                    setState(() => _arama = '');
                                  },
                                ),
                          isDense: true,
                          border: OutlineInputBorder(
                            borderRadius: kose,
                            borderSide: const BorderSide(color: Renk.cizgi),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: kose,
                            borderSide: const BorderSide(color: Renk.cizgi),
                          ),
                        ),
                      ),
                    ),
                    if (_arama.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
                        child: Align(
                          alignment: Alignment.centerLeft,
                          child: Text('$bulunan sonuç',
                              style: Theme.of(c).textTheme.labelSmall),
                        ),
                      ),
                    Expanded(
                      child: gruplar.isEmpty
                          ? const Bos(Icons.search_off_sharp,
                              'Bu terim sözlükte yok',
                              alt: 'Sütun adıyla da arayabilirsin: '
                                  'ATR_yuzde, DON_ust, GG60')
                          : ListView(
                              // Yatay dolgu çocuklarda: bölüm başlığı
                              // uygulamanın Baslik bileşeni ve kendi
                              // dolgusunu taşıyor (bkz. bugun.dart).
                              padding: const EdgeInsets.only(bottom: 28),
                              children: [
                                if (_arama.isEmpty)
                                  Padding(
                                    padding: const EdgeInsets.fromLTRB(
                                        16, 4, 16, 0),
                                    child: Not(
                                      'Ekranlarda geçen her terimin karşılığı '
                                      'burada. Bir terim merak uyandırırsa '
                                      'altındaki ders düğmesi tam o konuyu '
                                      'anlatıyor.',
                                      ikon: Icons.menu_book_sharp,
                                      renk: sem.aksan,
                                    ),
                                  ),
                                for (final g in gruplar) ...[
                                  Baslik(
                                    '${g.key['ad']}',
                                    alt: '${g.key['aciklama']}',
                                    sag: Text('${g.value.length}',
                                        style: Theme.of(c)
                                            .textTheme
                                            .labelSmall),
                                  ),
                                  for (final t in g.value)
                                    Padding(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 16),
                                      child: _TerimKutusu(
                                          t, acik: _arama.isNotEmpty),
                                    ),
                                ],
                              ],
                            ),
                    ),
                  ],
                ),
    );
  }
}

/// Kapalıyken tek satır karşılık, açıkken mekanizma. Sözlüğün işi 30
/// saniyede cevap vermek — herkesin her maddeyi baştan okuması gerekmez.
class _TerimKutusu extends StatefulWidget {
  final Map<String, dynamic> terim;
  final bool acik;
  const _TerimKutusu(this.terim, {this.acik = false});

  @override
  State<_TerimKutusu> createState() => _TerimKutusuDurum();
}

class _TerimKutusuDurum extends State<_TerimKutusu> {
  late bool _acik = widget.acik;

  @override
  void didUpdateWidget(covariant _TerimKutusu eski) {
    super.didUpdateWidget(eski);
    if (widget.acik != eski.acik) _acik = widget.acik;
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final t = widget.terim;
    final aciklama = '${t['aciklama'] ?? ''}';
    final nerede = '${t['nerede'] ?? ''}';
    final ders = '${t['ders'] ?? ''}';
    final kolonlar = ((t['kolonlar'] ?? []) as List).map((e) => '$e').toList();

    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Kutu(
        tikla: () => setState(() => _acik = !_acik),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text('${t['terim']}',
                      style: Theme.of(c).textTheme.bodyLarge
                          ?.copyWith(fontWeight: FontWeight.w600)),
                ),
                Icon(_acik ? Icons.expand_less_sharp : Icons.expand_more_sharp,
                    size: 19, color: Renk.metinSonuk),
              ],
            ),
            const SizedBox(height: 5),
            Text('${t['kisa']}',
                style: Theme.of(c).textTheme.bodyMedium
                    ?.copyWith(height: 1.55, color: Renk.metinSolgun)),

            if (kolonlar.isNotEmpty) ...[
              const SizedBox(height: 9),
              Wrap(
                spacing: 6, runSpacing: 6,
                children: [for (final k in kolonlar) Rozet(k)],
              ),
            ],

            if (_acik && aciklama.isNotEmpty) ...[
              const SizedBox(height: 13),
              Container(height: 1, color: Renk.cizgi),
              const SizedBox(height: 13),
              Text(aciklama,
                  style: Theme.of(c).textTheme.bodyMedium
                      ?.copyWith(height: 1.62)),
            ],

            if (_acik && nerede.isNotEmpty) ...[
              const SizedBox(height: 13),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.my_location_sharp, size: 15, color: Renk.metinSonuk),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(nerede,
                        style: Theme.of(c).textTheme.bodySmall
                            ?.copyWith(color: Renk.metinSolgun, height: 1.5)),
                  ),
                ],
              ),
            ],

            // Ders bağlantısı yalnızca ders kodu olan terimlerde. Sözlük
            // merak uyandırır, ders cevaplar.
            if (_acik && ders.startsWith('d')) ...[
              const SizedBox(height: 13),
              InkWell(
                onTap: () => Navigator.push(
                    c, MaterialPageRoute(builder: (_) => DersEkran(ders))),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.school_sharp, size: 15, color: sem.aksan),
                      const SizedBox(width: 8),
                      Text('Bu konunun dersi',
                          style: Theme.of(c).textTheme.bodySmall
                              ?.copyWith(color: sem.aksan)),
                      const SizedBox(width: 3),
                      Icon(Icons.chevron_right_sharp, size: 16, color: sem.aksan),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
