
import 'package:flutter/material.dart';

import '../parca/kart.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../servis/semboller.dart';
import '../tema.dart';
import 'hisse.dart';

/// İzleme listesi — sahip OLMADIĞIN, beklediğin hisseler.
///
/// NEDEN VAR: sistem sana ne zaman gireceğini söylüyor ama beklediğin
/// seviyeyi takip edemiyordun. Portföydeki hisselerin stop/hedef alarmı
/// zaten vardı; bu, henüz almadıkların için.
///
/// SUNUCUDA YAŞIYOR: alarm 5 dakikalık işte kontrol ediliyor ve telefon
/// kapalıyken de çalışması gerekiyor.
class IzlemeEkran extends StatefulWidget {
  const IzlemeEkran({super.key});
  @override
  State<IzlemeEkran> createState() => _IzlemeDurum();
}

class _IzlemeDurum extends State<IzlemeEkran> {
  List<dynamic> _izleme = [];
  List<dynamic> _pozisyon = [];
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() {
    super.initState();
    semboller.tazele();
    _getir();
  }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.izlemeListesi();
      if (!mounted) return;
      setState(() {
        _izleme = (r['izleme'] ?? []) as List;
        _pozisyon = (r['pozisyon'] ?? []) as List;
      });
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    } finally {
      if (mounted) setState(() => _yukleniyor = false);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('İzleme listesi')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _ekleSayfasi,
        icon: const Icon(Icons.add_sharp),
        label: const Text('HİSSE EKLE'),
      ),
      body: _hata != null && _izleme.isEmpty
          ? HataGorunum(_hata!, tekrar: _getir)
          : RefreshIndicator(
              onRefresh: _getir,
              child: ListView(
                padding: const EdgeInsets.only(top: 8, bottom: 90),
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Not(
                      'Buradaki seviyeler SENİN koyduğun seviyeler — '
                      'sistemin sinyali değil. Fiyat değince haber gelir, '
                      'ama alıp almamaya yine sen karar verirsin.',
                      ikon: Icons.visibility_sharp, renk: sem.aksan,
                    ),
                  ),

                  const Baslik('İzlediklerin', alt: 'gün içinde 5 dakikada bir kontrol edilir'),
                  if (_yukleniyor && _izleme.isEmpty)
                    const Yukleniyor(mesaj: 'Liste alınıyor')
                  else if (_izleme.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Kutu(
                        child: Text(
                            'Henüz hisse eklemedin.\n\n'
                            'Bir hisse ekleyip "şu fiyata inerse haber ver" '
                            'dersen, seans içinde fiyat oraya değdiğinde '
                            'bildirim gelir.',
                            style: Theme.of(c).textTheme.bodyMedium
                                ?.copyWith(color: Renk.metinSolgun, height: 1.55)),
                      ),
                    )
                  else
                    ..._izleme.map((x) => Padding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                          child: _kart(c, sem,
                              Map<String, dynamic>.from(x as Map)),
                        )),

                  if (_pozisyon.isNotEmpty) ...[
                    const Baslik('Pozisyonların',
                        alt: 'karar defterinden otomatik · stop ve hedef izleniyor'),
                    ..._pozisyon.map((x) {
                      final p = Map<String, dynamic>.from(x as Map);
                      return Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                        child: Kutu(
                          ic: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          child: Row(children: [
                            Expanded(
                              child: Text('${p['sembol']}',
                                  style: Theme.of(c).textTheme.titleMedium),
                            ),
                            Text('stop ${tl(p['stop'] as num?)}',
                                style: TextStyle(
                                    color: sem.eksi, fontSize: 12)),
                            const SizedBox(width: 12),
                            Text('hedef ${tl(p['hedef'] as num?)}',
                                style: TextStyle(
                                    color: sem.arti, fontSize: 12)),
                          ]),
                        ),
                      );
                    }),
                  ],
                ],
              ),
            ),
    );
  }

  Widget _kart(BuildContext c, Sem sem, Map<String, dynamic> x) {
    final kod = '${x['sembol']}';
    final ad = semboller.hisseler
        .where((s) => s.kod == kod).firstOrNull?.ad ?? '';
    final alt = (x['alt'] as num?)?.toDouble() ?? 0;
    final ust = (x['ust'] as num?)?.toDouble() ?? 0;
    final not = '${x['not'] ?? ''}';

    return Kutu(
      tikla: () => Navigator.push(
          c, MaterialPageRoute(builder: (_) => HisseEkran(kod))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(kod, style: Theme.of(c).textTheme.titleMedium),
            if (ad.isNotEmpty) ...[
              const SizedBox(width: 8),
              Expanded(
                child: Text(ad,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(c).textTheme.bodySmall),
              ),
            ] else
              const Spacer(),
            IconButton(
              icon: const Icon(Icons.close_sharp, size: 18),
              tooltip: 'İzlemeden çıkar',
              visualDensity: VisualDensity.compact,
              onPressed: () => _cikar(kod),
            ),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            if (alt > 0)
              Expanded(
                child: Text('${tl(alt)} ₺\'ye inerse',
                    style: TextStyle(color: sem.uyari, fontSize: 12.5)),
              ),
            if (ust > 0)
              Expanded(
                child: Text('${tl(ust)} ₺\'yi geçerse',
                    textAlign: alt > 0 ? TextAlign.end : TextAlign.start,
                    style: TextStyle(color: sem.arti, fontSize: 12.5)),
              ),
          ]),
          if (not.isNotEmpty) ...[
            const SizedBox(height: 7),
            Text(not,
                style: Theme.of(c).textTheme.bodySmall
                    ?.copyWith(color: Renk.metinSonuk, height: 1.4)),
          ],
        ],
      ),
    );
  }

  Future<void> _cikar(String kod) async {
    try {
      await depo.api.izlemeSil(kod);
      await _getir();
    } on ApiHata catch (e) {
      if (mounted) _uyar(e.oneri ?? e.mesaj);
    }
  }

  void _uyar(String m) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(m)));

  Future<void> _ekleSayfasi() async {
    final ok = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => const IzlemeEkleEkran()));
    if (ok == true) await _getir();
  }
}

// ── ekleme ─────────────────────────────────────────────────────────────────

class IzlemeEkleEkran extends StatefulWidget {
  const IzlemeEkleEkran({super.key});
  @override
  State<IzlemeEkleEkran> createState() => _IzlemeEkleDurum();
}

class _IzlemeEkleDurum extends State<IzlemeEkleEkran> {
  final _arama = TextEditingController();
  final _alt = TextEditingController();
  final _ust = TextEditingController();
  final _not = TextEditingController();
  Sembol? _secili;
  List<Sembol> _sonuc = const [];
  bool _mesgul = false;
  String? _hata;

  @override
  void dispose() {
    for (final x in [_arama, _alt, _ust, _not]) {
      x.dispose();
    }
    super.dispose();
  }

  double? _oku(TextEditingController k) =>
      double.tryParse(k.text.trim().replaceAll(',', '.'));

  Future<void> _kaydet() async {
    final s = _secili;
    if (s == null) {
      setState(() => _hata = 'Önce bir hisse seç.');
      return;
    }
    final alt = _oku(_alt) ?? 0, ust = _oku(_ust) ?? 0;
    if (alt <= 0 && ust <= 0) {
      setState(() => _hata =
          'En az bir seviye gir — yoksa hiç haber gelmez.');
      return;
    }
    setState(() { _mesgul = true; _hata = null; });
    try {
      await depo.api.izlemeEkle(s.kod, alt: alt, ust: ust,
          not: _not.text.trim());
      if (mounted) Navigator.pop(context, true);
    } on ApiHata catch (e) {
      if (mounted) setState(() => _hata = e.oneri ?? e.mesaj);
    } catch (e) {
      if (mounted) setState(() => _hata = '$e');
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('İzlemeye ekle')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
        children: [
          TextField(
            controller: _arama,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              labelText: 'Hisse',
              hintText: 'thy · iş bankası · EREGL',
              prefixIcon: const Icon(Icons.search_sharp, size: 20),
              suffixIcon: _secili == null
                  ? null
                  : Icon(Icons.check_sharp, size: 18, color: sem.aksan),
            ),
            onChanged: (q) => setState(() {
              _secili = null;
              _sonuc = semboller.ara(q, azami: 6);
            }),
          ),
          if (_sonuc.isNotEmpty && _secili == null)
            Container(
              margin: const EdgeInsets.only(top: 4),
              decoration: BoxDecoration(
                color: Renk.panelUst,
                border: Border.all(color: Renk.cizgi),
              ),
              child: Column(
                children: _sonuc.map((s) => InkWell(
                      onTap: () => setState(() {
                        _secili = s;
                        _arama.text = s.kod;
                        _sonuc = const [];
                      }),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 13, vertical: 11),
                        child: Row(children: [
                          SizedBox(
                            width: 62,
                            child: Text(s.kod,
                                style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: s.izleniyor ? sem.aksan : null)),
                          ),
                          Expanded(
                            child: Text(s.ad,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(c).textTheme.bodySmall),
                          ),
                        ]),
                      ),
                    )).toList(),
              ),
            ),

          const SizedBox(height: 18),
          TextField(
            controller: _alt,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Bu fiyata inerse haber ver',
                helperText: 'Beklediğin giriş seviyesi. Boş bırakabilirsin.'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _ust,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Bu fiyatı geçerse haber ver',
                helperText: 'Kırılımı kaçırmak istemiyorsan. Boş bırakabilirsin.'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _not,
            maxLength: 120,
            decoration: const InputDecoration(
                labelText: 'Not (isteğe bağlı)',
                helperText: 'Neden izliyorsun? Bildirimde de görünür.'),
          ),

          if (_hata != null) ...[
            const SizedBox(height: 8),
            Not(_hata!, ikon: Icons.error_outline_sharp, renk: sem.eksi),
          ],

          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _mesgul ? null : _kaydet,
              child: const Text('İZLEMEYE AL'),
            ),
          ),
          const SizedBox(height: 10),
          Text(
              'Seans içinde 5 dakikada bir kontrol edilir. Her seviye için '
              'günde en fazla bir bildirim gelir — yoksa fiyat seviyenin '
              'etrafında dolaşırken telefon susmaz.',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),
        ],
      ),
    );
  }
}
