import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

class MakroEkran extends StatefulWidget {
  const MakroEkran({super.key});
  @override
  State<MakroEkran> createState() => _MakroDurum();
}

class _MakroDurum extends State<MakroEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.makro();
      if (mounted) setState(() { _v = r; _yukleniyor = false; });
    } catch (e) {
      if (mounted) setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  static const _grupAd = {
    'kur': 'DÖVİZ', 'emtia': 'EMTİA', 'faiz': 'FAİZ',
    'risk': 'RİSK İŞTAHI', 'kuresel': 'KÜRESEL', 'yerel': 'YEREL',
  };

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Makro'), actions: [
        IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
      ]),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Makro veriler alınıyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : _icerik(c, sem),
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final g = (_v!['gostergeler'] as Map?) ?? {};
    final rejim = _v!['rejim'] as Map<String, dynamic>?;
    final enf = _v!['enflasyon'] as Map<String, dynamic>?;
    final reel = (_v!['bist_reel_getiri_1y'] as num?)?.toDouble();

    final gruplar = <String, List<MapEntry<String, dynamic>>>{};
    g.forEach((k, v) {
      gruplar.putIfAbsent('${v['grup']}', () => []).add(MapEntry(k, v));
    });

    final ad = '${rejim?['rejim']}';
    final renk = ad.contains('AÇIK')
        ? sem.arti : ad.contains('SAVUNMA') ? sem.eksi : sem.uyari;

    return RefreshIndicator(
      onRefresh: _getir,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Rozet(ad, renk: renk, dolu: true),
                  const Spacer(),
                  if (enf != null)
                    Text('TÜFE ${yzd(enf['yillik'] as num?, isaret: false)} · '
                        '${enf['donem']}',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(
                            color: Theme.of(c).colorScheme.onSurfaceVariant)),
                ]),
                const SizedBox(height: 10),
                Text('${rejim?['aciklama']}'),
                const SizedBox(height: 10),
                ...((rejim?['notlar'] as List?) ?? []).map((n) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('· ', style: TextStyle(color: sem.aksan)),
                          Expanded(child: Text('$n',
                              style: Theme.of(c).textTheme.bodySmall)),
                        ]),
                    )),
                if (reel != null) ...[
                  const SizedBox(height: 12),
                  Not(
                    'BIST 100 son 1 yıl: nominal getiri ${yzd((g['xu100']?['g365']) as num?)}, '
                    'enflasyon ${yzd(enf?['yillik'] as num?, isaret: false)} → '
                    'REEL ${yzd(reel)}.',
                    ikon: reel < 0 ? Icons.trending_down_sharp : Icons.trending_up_sharp,
                    renk: reel < 0 ? sem.eksi : sem.arti,
                    baslik: 'Bakılacak sayı bu',
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 6),
          ...gruplar.entries.map((grp) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Baslik(_grupAd[grp.key] ?? grp.key),
                  Kutu(
                    child: Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(children: [
                            const Expanded(flex: 3, child: SizedBox()),
                            ...['1 ay', '3 ay', '1 yıl'].map((e) => Expanded(
                                flex: 2,
                                child: Text(e, textAlign: TextAlign.right,
                                    style: Theme.of(c).textTheme.bodySmall
                                        ?.copyWith(fontSize: 10.5,
                                        color: Theme.of(c)
                                            .colorScheme.onSurfaceVariant)))),
                          ]),
                        ),
                        const Divider(),
                        ...grp.value.map((e) {
                          final v = e.value as Map;
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 7),
                            child: Row(children: [
                              Expanded(flex: 3,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${v['ad']}',
                                        style: Theme.of(c).textTheme.bodyMedium),
                                    Text(tl(v['son'] as num?),
                                        style: TextStyle(fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            color: Theme.of(c)
                                                .colorScheme.onSurfaceVariant)),
                                  ],
                                )),
                              ...['g30', 'g90', 'g365'].map((k) => Expanded(
                                  flex: 2,
                                  child: Text(yzd(v[k] as num?, basamak: 1),
                                      textAlign: TextAlign.right,
                                      style: TextStyle(fontSize: 12.5,
                                          fontWeight: FontWeight.w600,
                                          color: sem.yon(v[k] as num?))))),
                            ]),
                          );
                        }),
                      ],
                    ),
                  ),
                ],
              )),
        ],
      ),
    );
  }
}
