import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

class OgrenEkran extends StatefulWidget {
  const OgrenEkran({super.key});
  @override
  State<OgrenEkran> createState() => _OgrenDurum();
}

class _OgrenDurum extends State<OgrenEkran> {
  List<dynamic>? _konular;
  Object? _hata;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() => _hata = null);
    try {
      final r = await depo.api.ogrenListe();
      if (mounted) setState(() => _konular = r);
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Öğren')),
      body: _hata != null
          ? HataGorunum(_hata!, tekrar: _getir)
          : _konular == null
              ? const Yukleniyor()
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                  children: [
                    Not(
                      'Çoğu kaynak göstergenin NE olduğunu anlatır, ne zaman '
                      'işe yaramadığını anlatmaz. Her konuda "tuzak" bölümü var.',
                      ikon: Icons.lightbulb_outline_sharp, renk: sem.aksan,
                    ),
                    const SizedBox(height: 14),
                    ..._konular!.map((k) => Padding(
                          padding: const EdgeInsets.only(bottom: 9),
                          child: Kutu(
                            tikla: () => Navigator.push(c, MaterialPageRoute(
                                builder: (_) => KonuEkran('${k['anahtar']}'))),
                            child: Row(children: [
                              Expanded(
                                child: Text('${k['baslik']}',
                                    style: Theme.of(c).textTheme.bodyLarge
                                        ?.copyWith(fontWeight: FontWeight.w600)),
                              ),
                              const Icon(Icons.chevron_right_sharp),
                            ]),
                          ),
                        )),
                  ],
                ),
    );
  }
}

class KonuEkran extends StatefulWidget {
  final String konu;
  const KonuEkran(this.konu, {super.key});
  @override
  State<KonuEkran> createState() => _KonuDurum();
}

class _KonuDurum extends State<KonuEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    try {
      final r = await depo.api.ogrenKonu(widget.konu);
      if (mounted) setState(() => _v = r);
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: Text(_v?['baslik'] ?? 'Öğren')),
      body: _hata != null
          ? HataGorunum(_hata!, tekrar: _getir)
          : _v == null
              ? const Yukleniyor()
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
                  children: [
                    Kutu(child: Text('${_v!['ozet']}',
                        style: Theme.of(c).textTheme.bodyMedium
                            ?.copyWith(height: 1.62))),
                    if ('${_v!['bist_ozel'] ?? ''}'.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Kutu(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('BIST / MİDAS ÖZELİ',
                                style: Theme.of(c).textTheme.labelSmall
                                    ?.copyWith(color: sem.aksan, letterSpacing: 1.1)),
                            const SizedBox(height: 8),
                            Text('${_v!['bist_ozel']}',
                                style: Theme.of(c).textTheme.bodyMedium
                                    ?.copyWith(height: 1.62)),
                          ],
                        ),
                      ),
                    ],
                    if ('${_v!['tuzak'] ?? ''}'.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: sem.eksi.withValues(alpha: 0.08),
                          borderRadius: kose,
                          border: Border.all(color: sem.eksi.withValues(alpha: 0.3)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(children: [
                              Icon(Icons.dangerous_sharp, size: 18, color: sem.eksi),
                              const SizedBox(width: 8),
                              Text('TUZAK',
                                  style: Theme.of(c).textTheme.labelSmall
                                      ?.copyWith(color: sem.eksi, letterSpacing: 1.2)),
                            ]),
                            const SizedBox(height: 10),
                            Text('${_v!['tuzak']}',
                                style: Theme.of(c).textTheme.bodyMedium
                                    ?.copyWith(height: 1.62)),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
    );
  }
}
