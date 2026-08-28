import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'tez_yaz.dart';

class TezlerEkran extends StatefulWidget {
  const TezlerEkran({super.key});
  @override
  State<TezlerEkran> createState() => _TezlerDurum();
}

class _TezlerDurum extends State<TezlerEkran> {
  final Map<String, List<String>> _bozulmalar = {};
  bool _kontrolEdiliyor = false;

  @override
  void initState() {
    super.initState();
    _sorulariGetir();
  }

  /// Tez soruları eskiden YALNIZCA "Tez yaz" ekranında yükleniyordu.
  /// Bu sekmeye oradan geçmeden giren kullanıcıda liste boş kalıyor ve
  /// hiçbir tezin tam olup olmadığı bilinemiyordu. Ekranın tek işi bunu
  /// söylemek olduğu için listeyi kendisi çekiyor.
  Future<void> _sorulariGetir() async {
    if (depo.tezSorulari.isNotEmpty) return;
    try {
      final r = await depo.api.tezSorulari();
      if (!mounted) return;
      depo.tezSorulari = r
          .map((e) => Map<String, String>.from(
              (e as Map).map((k, v) => MapEntry('$k', '$v'))))
          .toList();
      setState(() {});
    } catch (_) {
      // Ağ yoksa rozet "tam" demiyor, sessizce eksik sayıyor — yanlış
      // güven vermekten iyi.
    }
  }

  Future<void> _bozulmaKontrol() async {
    setState(() => _kontrolEdiliyor = true);
    for (final t in depo.acikTezler) {
      try {
        final r = await depo.api
            .tezKontrol(t.sembol, t.anlik, depo.ayarlar.sermaye);
        _bozulmalar[t.sembol] =
            ((r['bozulmalar'] as List?) ?? []).map((e) => '$e').toList();
      } catch (_) {}
    }
    if (mounted) setState(() => _kontrolEdiliyor = false);
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return ListenableBuilder(
      listenable: depo,
      builder: (_, __) {
        final acik = depo.acikTezler;
        final karne = depo.karne();
        return Scaffold(
          appBar: AppBar(
            title: const Text('Tezler'),
            actions: [
              IconButton(
                icon: _kontrolEdiliyor
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.fact_check_sharp),
                tooltip: 'Bozulma kontrolü',
                onPressed: _kontrolEdiliyor || acik.isEmpty ? null : _bozulmaKontrol,
              ),
            ],
          ),
          body: acik.isEmpty && depo.kapaliTezler.isEmpty
              ? Bos(Icons.description_sharp, 'Henüz tez yazmadın',
                  alt: 'Bir hisse alırken neden aldığını yaz.\n'
                      'Düştüğünde neden tuttuğunu ancak böyle bilirsin.')
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                  children: [
                    if (acik.isNotEmpty) ...[
                      Text('AÇIK (${acik.length})',
                          style: Theme.of(c).textTheme.labelSmall?.copyWith(
                              color: sem.aksan, letterSpacing: 1.1)),
                      const SizedBox(height: 10),
                      ...acik.map((t) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: _acikKart(c, sem, t),
                          )),
                    ],
                    if ((karne['islem'] as int? ?? 0) > 0) ...[
                      const SizedBox(height: 12),
                      _karneKart(c, sem, karne),
                    ],
                  ],
                ),
        );
      },
    );
  }

  Widget _acikKart(BuildContext c, Sem sem, Tez t) {
    final eksik = t.eksikler(depo.tezSorulari);
    final tam = t.tamMi(depo.tezSorulari);
    final boz = _bozulmalar[t.sembol] ?? [];
    return Kutu(
      tikla: () => Navigator.push(c,
              MaterialPageRoute(builder: (_) => TezYazEkran(t.sembol, fiyat: t.fiyat)))
          .then((_) => setState(() {})),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(t.sembol, style: Theme.of(c).textTheme.titleMedium),
              const SizedBox(width: 10),
              Text('${tl(t.fiyat)} ₺ · ${t.tarih}',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
              const Spacer(),
              // Üç hâl, ikisi değil: soru listesi yüklenmediyse "0 soru
              // boş" YANLIŞ okunuyor — "eksik yok" gibi duruyor, oysa
              // kastedilen "bilmiyorum". Bilinmeyeni eksik gibi
              // göstermek de tam gibi göstermek kadar yanlış.
              if (depo.tezSorulari.isEmpty)
                Rozet('kontrol edilemedi', renk: Renk.metinSonuk)
              else if (tam)
                Rozet('tam', renk: sem.arti)
              else
                Rozet('${eksik.length} soru boş', renk: sem.uyari),
            ],
          ),
          const SizedBox(height: 10),
          Text('YANILMA KOŞULUN',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: t.yanilmaKosulu.isEmpty ? sem.eksi : sem.aksan,
                  letterSpacing: 1)),
          const SizedBox(height: 3),
          Text(
              t.yanilmaKosulu.isEmpty
                  ? 'Yazılmamış — bu tezin en zayıf noktası.'
                  : t.yanilmaKosulu,
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  height: 1.45,
                  fontStyle: t.yanilmaKosulu.isEmpty
                      ? FontStyle.italic : FontStyle.normal,
                  color: t.yanilmaKosulu.isEmpty ? sem.eksi : null)),
          if (boz.isNotEmpty) ...[
            const SizedBox(height: 10),
            ...boz.map((b) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Not(b, ikon: Icons.trending_down_sharp, renk: sem.eksi),
                )),
          ] else if (_bozulmalar.containsKey(t.sembol)) ...[
            const SizedBox(height: 10),
            Not('Tezde ölçülebilir bozulma yok.',
                ikon: Icons.check_circle_outline_sharp, renk: sem.arti),
          ],
        ],
      ),
    );
  }

  Widget _karneKart(BuildContext c, Sem sem, Map<String, dynamic> k) {
    final tamOrt = k['tamOrt'] as double?;
    final eksikOrt = k['eksikOrt'] as double?;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('KARNEN · ${k['islem']} kapanmış işlem',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 10),
          Satir('Kazanma oranı', '%${tl(k['kazanma'] as num?, basamak: 0)}'),
          Satir('Ortalama getiri', yzd(k['ortalama'] as num?),
              renk: sem.yon(k['ortalama'] as num?)),
          Satir('En iyi', yzd(k['enIyi'] as num?), renk: sem.arti),
          Satir('En kötü', yzd(k['enKotu'] as num?), renk: sem.eksi),
          if (tamOrt != null && eksikOrt != null) ...[
            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 8),
            Satir('Tam tez yazdıkların (${k['tamSayi']})', yzd(tamOrt),
                renk: sem.yon(tamOrt), kalin: true),
            Satir('Eksik tezliler (${k['eksikSayi']})', yzd(eksikOrt),
                renk: sem.yon(eksikOrt), kalin: true),
            const SizedBox(height: 10),
            Not(
              'Bu iki satır arasındaki fark, disiplinin sana ne kazandırdığının '
              'ölçüsüdür.',
              ikon: Icons.insights_sharp, renk: sem.aksan,
            ),
          ],
          if ((k['dersler'] as List?)?.isNotEmpty ?? false) ...[
            const SizedBox(height: 14),
            Text('KENDİ DERSLERİN',
                style: Theme.of(c).textTheme.labelSmall?.copyWith(
                    color: sem.aksan, letterSpacing: 1.1)),
            const SizedBox(height: 6),
            ...(k['dersler'] as List).take(6).map((d) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('· ', style: TextStyle(color: sem.aksan)),
                      Expanded(
                          child: Text('$d',
                              style: Theme.of(c).textTheme.bodySmall)),
                    ],
                  ),
                )),
          ],
        ],
      ),
    );
  }
}
