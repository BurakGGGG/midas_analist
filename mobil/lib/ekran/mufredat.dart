import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/egitmen.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'ders.dart';

class MufredatEkran extends StatefulWidget {
  const MufredatEkran({super.key});
  @override
  State<MufredatEkran> createState() => _MufredatDurum();
}

class _MufredatDurum extends State<MufredatEkran> {
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
        try {
          await egitmen.bankaKaydet(await depo.api.egitmenSorular());
        } catch (_) {}
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
      appBar: AppBar(title: const Text('Müfredat')),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Müfredat indiriliyor...\nBir kez indirilir, sonra çevrimdışı okunur.')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _hazirla)
              : _icerik(c, sem),
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final d = egitmen.durum();
    final isaretli = egitmen.isaretliDersler;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
      children: [
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Expanded(
                  child: Text('${d.dersOkunan}/${d.dersToplam} ders',
                      style: Theme.of(c).textTheme.headlineSmall),
                ),
                Rozet(d.unvan, renk: sem.aksan, dolu: true),
              ]),
              const SizedBox(height: 6),
              Text('${d.dakikaKalan} dakika okuma kaldı',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: kose,
                child: LinearProgressIndicator(
                  value: d.dersToplam == 0 ? 0 : d.dersOkunan / d.dersToplam,
                  minHeight: 9,
                  backgroundColor: Theme.of(c).dividerColor,
                  valueColor: AlwaysStoppedAnimation(sem.aksan),
                ),
              ),
            ],
          ),
        ),
        if (isaretli.isNotEmpty) ...[
          const Baslik('İşaretlediklerin'),
          ...isaretli.map((x) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Kutu(
                  ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  tikla: () => Navigator.push(c,
                          MaterialPageRoute(builder: (_) => DersEkran(x.kod)))
                      .then((_) => setState(() {})),
                  child: Row(children: [
                    Icon(Icons.bookmark_sharp, size: 17, color: sem.uyari),
                    const SizedBox(width: 10),
                    Expanded(child: Text(x.baslik)),
                  ]),
                ),
              )),
        ],
        const Baslik('12 modül'),
        ...egitmen.moduller.map((m) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _modulKart(c, sem, m),
            )),
      ],
    );
  }

  Widget _modulKart(BuildContext c, Sem sem, EgitmenModul m) {
    final okunan = m.dersler.where((d) => egitmen.okundu(d.kod)).length;
    final yuzde = m.dersler.isEmpty ? 0.0 : okunan / m.dersler.length;
    final bitti = okunan == m.dersler.length && m.dersler.isNotEmpty;
    final sv = {1: 'giriş', 2: 'orta', 3: 'ileri'}[m.seviye] ?? '';

    return Card(
      child: Theme(
        data: Theme.of(c).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          childrenPadding: const EdgeInsets.only(bottom: 8),
          leading: SizedBox(
            width: 38, height: 38,
            child: Stack(alignment: Alignment.center, children: [
              CircularProgressIndicator(
                value: yuzde, strokeWidth: 3.5,
                backgroundColor: sem.aksan.withValues(alpha: 0.15),
                valueColor: AlwaysStoppedAnimation(bitti ? sem.arti : sem.aksan),
              ),
              bitti
                  ? Icon(Icons.check_sharp, size: 17, color: sem.arti)
                  : Text('$okunan',
                      style: const TextStyle(
                          fontSize: 12.5, fontWeight: FontWeight.w700)),
            ]),
          ),
          title: Text(m.ad,
              style: Theme.of(c).textTheme.titleMedium?.copyWith(fontSize: 15.5)),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Text('${m.dersler.length} ders · ~${m.dakika} dk · $sv',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Text(m.aciklama,
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant,
                      height: 1.5)),
            ),
            ...m.dersler.map((x) {
              final ok = egitmen.okundu(x.kod);
              final im = egitmen.dersKayit[x.kod]?.isaretli ?? false;
              return ListTile(
                dense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                leading: Icon(
                    ok ? Icons.check_circle_sharp : Icons.circle_sharp,
                    size: 19,
                    color: ok ? sem.arti : Theme.of(c).colorScheme.onSurfaceVariant),
                title: Text(x.baslik,
                    style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: ok ? FontWeight.w400 : FontWeight.w600)),
                subtitle: Text(x.ozet,
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        fontSize: 12, height: 1.35,
                        color: Theme.of(c).colorScheme.onSurfaceVariant)),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  if (im) Icon(Icons.bookmark_sharp, size: 15, color: sem.uyari),
                  const SizedBox(width: 4),
                  Text('${x.sure}dk',
                      style: TextStyle(
                          fontSize: 11.5,
                          color: Theme.of(c).colorScheme.onSurfaceVariant)),
                ]),
                onTap: () => Navigator.push(c,
                        MaterialPageRoute(builder: (_) => DersEkran(x.kod)))
                    .then((_) => setState(() {})),
              );
            }),
          ],
        ),
      ),
    );
  }
}
