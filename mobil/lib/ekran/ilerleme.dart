import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/egitmen.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'ogret.dart';
import 'mufredat.dart';
import 'alistirma.dart';

class IlerlemeEkran extends StatefulWidget {
  const IlerlemeEkran({super.key});
  @override
  State<IlerlemeEkran> createState() => _IlerlemeDurum();
}

class _IlerlemeDurum extends State<IlerlemeEkran> {
  bool _yukleniyor = true;
  Object? _hata;

  @override
  void initState() { super.initState(); _hazirla(); }

  Future<void> _hazirla() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      if (!egitmen.mufredatVar) {
        await egitmen.mufredatKaydet(await depo.api.egitmenMufredat());
      }
      if (!egitmen.bankaVar) {
        await egitmen.bankaKaydet(await depo.api.egitmenSorular());
      }
      if (mounted) setState(() => _yukleniyor = false);
    } catch (e) {
      if (mounted) setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Eğitim ilerlemen'), actions: [
        if (egitmen.ilerleme.isNotEmpty)
          IconButton(
            icon: const Icon(Icons.restart_alt_sharp),
            tooltip: 'İlerlemeyi sıfırla',
            onPressed: () async {
              final onay = await showDialog<bool>(
                context: c,
                builder: (d) => AlertDialog(
                  title: const Text('İlerlemeyi sıfırla'),
                  content: const Text(
                      'Tüm çalışma geçmişin ve tekrar takvimin silinir. '
                      'Bu geri alınamaz.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(d, false),
                        child: const Text('Vazgeç')),
                    FilledButton(onPressed: () => Navigator.pop(d, true),
                        child: const Text('Sıfırla')),
                  ],
                ),
              );
              if (onay == true) {
                await egitmen.sifirla();
                if (mounted) setState(() {});
              }
            },
          ),
      ]),
      body: _yukleniyor
          ? const Yukleniyor()
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _hazirla)
              : _icerik(c, sem),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.push(c,
                MaterialPageRoute(builder: (_) => const OgretEkran()))
            .then((_) => setState(() {})),
        icon: const Icon(Icons.school_sharp),
        label: const Text('Bugünkü oturum'),
      ),
    );
  }

  /// Yüzdeyi halka olarak çizer. fl_chart'a gerek yok: tek değerli bir
  /// gösterge için pasta grafiği aşırıya kaçmak olur.
  Widget _halka(BuildContext c, Sem sem, double yuzde) {
    final oran = (yuzde / 100).clamp(0.0, 1.0);
    final renk = yuzde >= 70 ? sem.arti : (yuzde >= 35 ? sem.uyari : sem.aksan);
    return SizedBox(
      width: 74, height: 74,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 74, height: 74,
            child: CircularProgressIndicator(
              value: oran, strokeWidth: 7,
              backgroundColor: Theme.of(c).dividerColor,
              valueColor: AlwaysStoppedAnimation(renk),
            ),
          ),
          Text(yuzde.toStringAsFixed(0),
              style: Theme.of(c).textTheme.titleLarge?.copyWith(
                  color: renk, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }

  /// Modül modül hakimiyet. Tek bir yüzde "nerede zayıfım" sorusunu
  /// cevaplamaz; asıl işe yarayan harita budur.
  Widget _modulHaritasi(BuildContext c, Sem sem) {
    final moduller = egitmen.moduller;
    if (moduller.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const Baslik('Konu haritası'),
        Kutu(
          child: Column(
            children: [
              for (final m in moduller)
                Builder(builder: (_) {
                  final n = m.dersler.length;
                  final okunan =
                      m.dersler.where((x) => egitmen.okundu(x.kod)).length;
                  final oran = n == 0 ? 0.0 : okunan / n;
                  final renk = oran >= 0.99
                      ? sem.arti
                      : (oran > 0 ? sem.uyari : Theme.of(c).dividerColor);
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 9),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 30,
                          child: Text(m.kod,
                              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                                  color: Theme.of(c)
                                      .colorScheme.onSurfaceVariant)),
                        ),
                        Expanded(
                          flex: 4,
                          child: Text(m.ad,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(c).textTheme.bodyMedium),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 3,
                          child: ClipRRect(
                            borderRadius: kose,
                            child: LinearProgressIndicator(
                              value: oran, minHeight: 7,
                              backgroundColor: Theme.of(c).dividerColor,
                              valueColor: AlwaysStoppedAnimation(renk),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        SizedBox(
                          width: 34,
                          child: Text('$okunan/$n',
                              textAlign: TextAlign.right,
                              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                                  fontFeatures: const [
                                    FontFeature.tabularFigures()
                                  ])),
                        ),
                      ],
                    ),
                  );
                }),
            ],
          ),
        ),
      ],
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final d = egitmen.durum();
    final ist = egitmen.istatistik();
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 90),
      children: [
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                // Tek bakışta "ne kadarına hakimim" — halka, çubuktan
                // daha okunur çünkü yüzde ortada rakamla duruyor.
                _halka(c, sem, d.bilesikYuzde),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('%${d.bilesikYuzde.toStringAsFixed(0)} hakimsin',
                          style: Theme.of(c).textTheme.headlineSmall),
                      const SizedBox(height: 2),
                      Text('${d.unvan} · seviye ${d.seviye}/3',
                          style: Theme.of(c).textTheme.bodySmall?.copyWith(
                              color: Theme.of(c).colorScheme.onSurfaceVariant)),
                      const SizedBox(height: 6),
                      // Yüzde tek başına soyut; neyden geldiği yazmazsa
                      // kullanıcı sayıya güvenmez.
                      Text('derslerin 2/3, soruların 1/3 ağırlığıyla',
                          style: Theme.of(c).textTheme.bodySmall?.copyWith(
                              color: Theme.of(c).colorScheme.onSurfaceVariant)),
                    ],
                  ),
                ),
              ]),
              const SizedBox(height: 18),
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      const Expanded(child: Text('Dersler',
                          style: TextStyle(fontWeight: FontWeight.w600))),
                      Text('${d.dersOkunan}/${d.dersToplam}',
                          style: TextStyle(
                              fontWeight: FontWeight.w700, color: sem.aksan,
                              fontFeatures: const [FontFeature.tabularFigures()])),
                    ]),
                    const SizedBox(height: 5),
                    ClipRRect(
                      borderRadius: kose,
                      child: LinearProgressIndicator(
                        value: d.dersToplam == 0 ? 0 : d.dersOkunan / d.dersToplam,
                        minHeight: 8,
                        backgroundColor: Theme.of(c).dividerColor,
                        valueColor: AlwaysStoppedAnimation(sem.aksan),
                      ),
                    ),
                  ],
                ),
              ),
              ...[
                ('Temel sorular', 'temel'), ('Orta sorular', 'orta'),
                ('Usta soruları', 'usta'),
              ].map((e) {
                final k = d.katmanlar[e.$2]!;
                final renk = k.yuzde >= 70
                    ? sem.arti
                    : k.yuzde >= 35
                        ? sem.uyari
                        : Theme.of(c).colorScheme.onSurfaceVariant;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(children: [
                        Expanded(child: Text(e.$1,
                            style: const TextStyle(fontWeight: FontWeight.w600))),
                        Text('${k.ogrenilen}/${k.toplam}  (%${k.yuzde})',
                            style: TextStyle(
                                fontWeight: FontWeight.w700, color: renk,
                                fontFeatures: const [FontFeature.tabularFigures()])),
                      ]),
                      const SizedBox(height: 5),
                      ClipRRect(
                        borderRadius: kose,
                        child: LinearProgressIndicator(
                          value: k.yuzde / 100, minHeight: 8,
                          backgroundColor: Theme.of(c).dividerColor,
                          valueColor: AlwaysStoppedAnimation(renk),
                        ),
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 4),
              Not(d.sonrakiSeviye, ikon: Icons.trending_up_sharp, renk: sem.aksan),
              const SizedBox(height: 14),
              FilledButton.tonalIcon(
                onPressed: () => Navigator.push(c,
                        MaterialPageRoute(builder: (_) => const MufredatEkran()))
                    .then((_) => setState(() {})),
                icon: const Icon(Icons.menu_book_sharp, size: 18),
                label: Text('Müfredat · ${d.dersOkunan}/${d.dersToplam} ders'),
                style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(46)),
              ),
              const SizedBox(height: 9),
              // Müfredatın hemen ALTINDA: okumakla yapmak farklı şeyler ve
              // ikisi yan yana durmalı. Dersi okuyup hemen uygulayabilmek,
              // eğitimin ayrı bir iş gibi durmasını engelliyor.
              OutlinedButton.icon(
                onPressed: () => Navigator.push(c,
                        MaterialPageRoute(builder: (_) => const AlistirmaEkran()))
                    .then((_) => setState(() {})),
                icon: const Icon(Icons.science_sharp, size: 18),
                label: const Text('Alıştırma · sanal parayla dene'),
                style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(46)),
              ),
            ],
          ),
        ),
        _modulHaritasi(c, sem),
        if ((ist['calisilan'] as int? ?? 0) > 0) ...[
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('İSTATİSTİK',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 8),
                Satir('Çalışılan soru',
                    '${ist['calisilan']}/${d.toplamSoru}'),
                Satir('Öğrenilen', '${ist['ogrenilen']}',
                    not: '3 kez üst üste doğru + 21 gün aralık'),
                Satir('Doğru oranı',
                    '%${tl(ist['dogruOrani'] as num?, basamak: 1)}'),
                Satir('Bugün vadesi gelen', '${ist['vadesiGelen']}',
                    renk: (ist['vadesiGelen'] as int) > 0 ? sem.uyari : null),
              ],
            ),
          ),
          if ((ist['zorlar'] as List?)?.isNotEmpty ?? false) ...[
            const SizedBox(height: 14),
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('EN ÇOK ZORLANDIKLARIN',
                      style: Theme.of(c).textTheme.labelSmall?.copyWith(
                          color: sem.eksi, letterSpacing: 1.1)),
                  const SizedBox(height: 4),
                  Text('Bu sorular daha sık karşına gelecek.',
                      style: Theme.of(c).textTheme.bodySmall?.copyWith(
                          color: Theme.of(c).colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 10),
                  ...(ist['zorlar'] as List).map((z) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2),
                              decoration: BoxDecoration(
                                color: sem.eksi.withValues(alpha: 0.13),
                                borderRadius: kose,
                              ),
                              child: Text('${z['yanlis']}✗ ${z['dogru']}✓',
                                  style: TextStyle(
                                      fontSize: 11, fontWeight: FontWeight.w700,
                                      color: sem.eksi)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                                child: Text('${z['soru']}',
                                    style: Theme.of(c).textTheme.bodySmall
                                        ?.copyWith(height: 1.4))),
                          ],
                        ),
                      )),
                ],
              ),
            ),
          ],
        ],
        const SizedBox(height: 14),
        Kutu(
          child: Column(
            children: [
              Text(egitmen.ilkeGunun(),
                  textAlign: TextAlign.center,
                  style: Theme.of(c).textTheme.titleMedium?.copyWith(
                      fontStyle: FontStyle.italic, height: 1.5,
                      color: sem.aksan)),
            ],
          ),
        ),
      ],
    );
  }
}
