import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Karar defteri — SENİN sicilin.
///
/// "Sistemin sicili" ekranı sistemin sinyallerini ölçer. Bu ekran senin
/// kararlarını ölçer. İkisi ayrı, çünkü ölçülmek istenen şey aradaki
/// farktır: sistem 7 sinyal üretir, sen 2'sini alırsın — beceri o seçimde.
class DefterEkran extends StatefulWidget {
  const DefterEkran({super.key});
  @override
  State<DefterEkran> createState() => _DefterDurum();
}

class _DefterDurum extends State<DefterEkran> {
  Map<String, dynamic>? _d;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final d = await depo.api.defter();
      if (!mounted) return;
      setState(() { _d = d; _yukleniyor = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Karar defterin'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
        ],
      ),
      body: _yukleniyor
          ? const Center(child: CircularProgressIndicator())
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : RefreshIndicator(
                  onRefresh: _getir,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
                    children: _icerik(c, sem),
                  ),
                ),
    );
  }

  List<Widget> _icerik(BuildContext c, Sem sem) {
    final k = (_d?['karne'] as Map?)?.cast<String, dynamic>() ?? {};
    final kapali = (_d?['kapali'] as List?) ?? [];

    if (k['not'] != null) {
      return [
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.menu_book_sharp, color: sem.aksan),
                const SizedBox(width: 10),
                Expanded(child: Text('${k['not']}')),
              ]),
              const SizedBox(height: 14),
              const Divider(),
              const SizedBox(height: 12),
              Text(
                'Sistem kendi sinyallerini ölçüyor; bu defter SENİN '
                'kararlarını ölçer. Aradaki fark, seçim becerindir.\n\n'
                'Kayıtları Telegram botundan girebilirsin:\n'
                '/aldim THYAO 302 3\n'
                '/sattim THYAO 315\n\n'
                'Ya da bir hisse sayfasından "Alım kaydı" ile.',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      ];
    }

    final w = <Widget>[];

    // ── üst özet
    final kazanma = (k['kazanma_orani'] as num?)?.toDouble();
    w.add(Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: _sayi(c, '${k['alim_sayisi'] ?? 0}', 'alım kararı'),
            ),
            _ayrac(c),
            Expanded(child: _sayi(c, '${k['kapanan'] ?? 0}', 'kapandı')),
            _ayrac(c),
            Expanded(child: _sayi(c, '${k['acik'] ?? 0}', 'açık')),
          ]),
          if (kazanma != null) ...[
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: _sayi(c, '%${kazanma.toStringAsFixed(0)}', 'kazanma',
                    renk: kazanma >= 50 ? sem.arti : sem.uyari),
              ),
              _ayrac(c),
              Expanded(
                child: _sayi(
                    c,
                    '${((k['ortalama_getiri'] as num?) ?? 0).toStringAsFixed(1)}%',
                    'ortalama',
                    renk: ((k['ortalama_getiri'] as num?) ?? 0) >= 0
                        ? sem.arti
                        : sem.eksi),
              ),
            ]),
          ],
        ],
      ),
    ));

    // ── sistemi ne kadar takip ettin
    final takip = (k['sistem_takip_orani'] as num?)?.toDouble() ?? 0;
    w.add(const SizedBox(height: 14));
    w.add(const Baslik('Sistemi takip'));
    w.add(Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: Text('${k['sinyalli_alim'] ?? 0}/${k['alim_sayisi']} alım '
                  'sistem sinyaliyle'),
            ),
            Text('%${takip.toStringAsFixed(0)}',
                style: TextStyle(
                    fontWeight: FontWeight.w800, color: sem.aksan)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: kose,
            child: LinearProgressIndicator(
              value: takip / 100, minHeight: 8,
              backgroundColor: Theme.of(c).dividerColor,
              valueColor: AlwaysStoppedAnimation(sem.aksan),
            ),
          ),
          if (((k['karantinali_alim'] as num?) ?? 0) > 0) ...[
            const SizedBox(height: 10),
            Text('⚠️ ${k['karantinali_alim']} alım karantinadaki stratejiden',
                style: Theme.of(c).textTheme.bodySmall
                    ?.copyWith(color: sem.uyari)),
          ],
        ],
      ),
    ));

    // ── sinyalli vs kendi fikrin: asıl ölçüm
    final sinyalli = (k['sinyalli'] as Map?)?.cast<String, dynamic>();
    final kendi = (k['kendi_fikrin'] as Map?)?.cast<String, dynamic>();
    if (sinyalli != null || kendi != null) {
      w.add(const SizedBox(height: 14));
      w.add(const Baslik('Sinyalli vs kendi fikrin'));
      w.add(Kutu(
        child: Column(
          children: [
            if (sinyalli != null) _kiyas(c, sem, 'Sinyalli alımlar', sinyalli),
            if (sinyalli != null && kendi != null) const Divider(height: 22),
            if (kendi != null) _kiyas(c, sem, 'Kendi fikrin', kendi),
            const SizedBox(height: 10),
            // Kıyas notu YALNIZCA iki taraf da varken: tek taraf varken
            // "hangisinde daha iyisin" diye sormak anlamsız.
            if (sinyalli != null && kendi != null)
              Not(
                'Hangisinde daha iyisin? Bunu bilmeden hangisini '
                'geliştireceğini de bilemezsin.',
                ikon: Icons.compare_arrows_sharp,
              )
            else
              Not(
                'İki taraf da birikince burada karşılaştırma çıkar: '
                'sistemi takip ettiğinde mi, kendi fikrinle mi daha iyisin?',
                ikon: Icons.compare_arrows_sharp,
              ),
          ],
        ),
      ));
    }

    // ── stop disiplini
    final sd = (k['stop_disiplini'] as Map?)?.cast<String, dynamic>();
    if (sd != null) {
      final asildi = ((sd['stopun_altinda_kapanan'] as num?) ?? 0) > 0;
      w.add(const SizedBox(height: 14));
      w.add(const Baslik('Stop disiplini'));
      w.add(Kutu(
        child: Row(children: [
          Icon(asildi ? Icons.warning_sharp : Icons.verified_sharp,
              color: asildi ? sem.uyari : sem.arti),
          const SizedBox(width: 12),
          Expanded(child: Text('${sd['not']}')),
        ]),
      ));
    }

    // ── kapanan işlemler
    if (kapali.isNotEmpty) {
      w.add(const SizedBox(height: 14));
      w.add(const Baslik('Kapanan işlemler'));
      w.add(Kutu(
        child: Column(
          children: [
            for (final x in kapali.reversed) _islem(c, sem, x as Map),
          ],
        ),
      ));
    }

    if (k['uyari'] != null) {
      w.add(const SizedBox(height: 14));
      w.add(Not('${k['uyari']}',
          ikon: Icons.info_outline_sharp, renk: sem.uyari));
    }
    return w;
  }

  Widget _kiyas(BuildContext c, Sem sem, String ad, Map<String, dynamic> x) {
    final ort = ((x['ortalama'] as num?) ?? 0).toDouble();
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(ad, style: const TextStyle(fontWeight: FontWeight.w600)),
              Text('${x['n']} işlem',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
            ],
          ),
        ),
        Text('%${((x['kazanma'] as num?) ?? 0).toStringAsFixed(0)}',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(width: 14),
        SizedBox(
          width: 62,
          child: Text('${ort >= 0 ? '+' : ''}${ort.toStringAsFixed(2)}%',
              textAlign: TextAlign.right,
              style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: ort >= 0 ? sem.arti : sem.eksi)),
        ),
      ],
    );
  }

  Widget _islem(BuildContext c, Sem sem, Map x) {
    final g = ((x['getiri'] as num?) ?? 0).toDouble();
    final sinyalli = ((x['sinyal_var'] as num?) ?? 0) == 1;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text('${x['sembol']}',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(width: 7),
                  if (sinyalli)
                    Rozet('${x['strateji'] ?? 'sinyal'}', renk: sem.aksan)
                  else
                    Rozet('kendi fikrin', renk: Renk.metinSolgun),
                ]),
                Text(
                    '${((x['giris'] as num?) ?? 0).toStringAsFixed(2)} → '
                    '${((x['cikis'] as num?) ?? 0).toStringAsFixed(2)} ₺  ·  '
                    '${x['alim_tarih']}',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant)),
              ],
            ),
          ),
          Text('${g >= 0 ? '+' : ''}${g.toStringAsFixed(2)}%',
              style: TextStyle(
                  fontWeight: FontWeight.w800,
                  color: g >= 0 ? sem.arti : sem.eksi)),
        ],
      ),
    );
  }

  Widget _sayi(BuildContext c, String deger, String etiket, {Color? renk}) =>
      Column(
        children: [
          Text(deger,
              style: Theme.of(c).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800, color: renk)),
          Text(etiket,
              textAlign: TextAlign.center,
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
        ],
      );

  Widget _ayrac(BuildContext c) =>
      Container(width: 1, height: 34, color: Theme.of(c).dividerColor);
}
