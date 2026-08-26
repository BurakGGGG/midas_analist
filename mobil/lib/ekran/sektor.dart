import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../parca/grafik.dart';
import '../tema.dart';

class SektorEkran extends StatefulWidget {
  const SektorEkran({super.key});
  @override
  State<SektorEkran> createState() => _SektorDurum();
}

class _SektorDurum extends State<SektorEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.sektor();
      if (mounted) setState(() { _v = r; _yukleniyor = false; });
    } catch (e) {
      if (mounted) setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Sektörler'), actions: [
        IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
      ]),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Sektör haritası kuruluyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : _icerik(c, sem),
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final tablo = (_v!['tablo'] as List?) ?? [];
    if (tablo.isEmpty) return const Bos(Icons.donut_large_sharp, 'Sektör verisi yok');
    final enBuyuk = tablo
        .map((t) => ((t['gg60'] as num?) ?? 0).abs().toDouble())
        .reduce((a, b) => a > b ? a : b);

    return RefreshIndicator(
      onRefresh: _getir,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Not(
            'Sektör serileri BİLEŞENLERDEN kuruldu (piyasa değeri ağırlıklı) — '
            'yfinance BIST sektör endekslerinin geçmişini taşımıyor.',
            ikon: Icons.build_sharp,
          ),
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('60 GÜNLÜK GÖRELİ GÜÇ (XU100\'e göre)',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 12),
                ...tablo.map((t) {
                  final gg = ((t['gg60'] as num?) ?? 0).toDouble();
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 11),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(
                            child: Row(children: [
                              Text('${t['sektor']}',
                                  style: Theme.of(c).textTheme.bodyMedium
                                      ?.copyWith(fontWeight: FontWeight.w600)),
                              const SizedBox(width: 6),
                              Text('${t['hisse']}',
                                  style: TextStyle(fontSize: 10.5,
                                      color: Theme.of(c)
                                          .colorScheme.onSurfaceVariant)),
                            ]),
                          ),
                          Text(yzd(gg, basamak: 1),
                              style: TextStyle(fontWeight: FontWeight.w700,
                                  fontSize: 13, color: sem.yon(gg))),
                        ]),
                        const SizedBox(height: 5),
                        YatayCubuk(gg, enBuyuk),
                        const SizedBox(height: 4),
                        Row(children: [
                          Text('20g ${yzd(t['g20'] as num?, basamak: 1)}',
                              style: TextStyle(fontSize: 11,
                                  color: sem.yon(t['g20'] as num?))),
                          const SizedBox(width: 12),
                          Text('60g ${yzd(t['g60'] as num?, basamak: 1)}',
                              style: TextStyle(fontSize: 11,
                                  color: sem.yon(t['g60'] as num?))),
                          const SizedBox(width: 12),
                          Text('120g ${yzd(t['g120'] as num?, basamak: 1)}',
                              style: TextStyle(fontSize: 11,
                                  color: sem.yon(t['g120'] as num?))),
                        ]),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Not('${_v!['yorum']}', ikon: Icons.school_sharp, renk: sem.aksan),
        ],
      ),
    );
  }
}
