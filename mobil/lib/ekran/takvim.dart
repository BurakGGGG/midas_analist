import 'package:flutter/material.dart';

import '../parca/kart.dart';
import '../servis/depo.dart';
import '../tema.dart';
import 'hisse.dart';

/// Bilanço, temettü, genel kurul ve ekonomi takvimi.
///
/// NEDEN VAR: bilanço günü pozisyon taşımak AYRI BİR RİSKTİR — sonuç
/// seans dışında açıklanıyor ve ertesi gün boşluklu açılış stopu
/// atlıyor. Temettüde son alım günü kaçarsa temettü alınamaz.
///
/// İKİ TÜR KAYIT AYRI GÖSTERİLİYOR:
///   duyurulan — KAP bildiriminde tarih yazılı, güne göre plan yapılır
///   beklenen  — mevzuattan hesaplanan son tarih, yalnızca dikkat
///
/// Ayrımı gizlemek, hesaplanmış bir tarihi duyurulmuş gibi göstermek
/// olurdu; kullanıcı ona göre gün planlar ve yanılır.
class TakvimEkran extends StatefulWidget {
  const TakvimEkran({super.key});
  @override
  State<TakvimEkran> createState() => _TakvimDurum();
}

class _TakvimDurum extends State<TakvimEkran> {
  List<dynamic> _olaylar = const [];
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
      final r = await depo.api.takvim(
          semboller: depo.pozisyonlar.map((x) => x.sembol).toList());
      if (!mounted) return;
      setState(() => _olaylar = (r['olaylar'] ?? []) as List);
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    } finally {
      if (mounted) setState(() => _yukleniyor = false);
    }
  }

  /// Olayları "bu hafta / bu ay / sonrası" diye kümeler.
  ///
  /// Düz bir liste 120 günü tek akışta veriyor ve "yakın olan hangisi"
  /// sorusu kaybolıyor. Asıl karar değiştiren şey yakın olanlar.
  Map<String, List<Map<String, dynamic>>> _kumele() {
    final k = <String, List<Map<String, dynamic>>>{
      'Bu hafta': [], 'Bu ay': [], 'Sonrası': [],
    };
    for (final x in _olaylar) {
      final m = Map<String, dynamic>.from(x as Map);
      final gun = ((m['kalan_gun'] ?? 0) as num).toInt();
      k[gun <= 7 ? 'Bu hafta' : (gun <= 31 ? 'Bu ay' : 'Sonrası')]!.add(m);
    }
    k.removeWhere((_, v) => v.isEmpty);
    return k;
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    if (_hata != null && _olaylar.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Takvim')),
        body: HataGorunum(_hata!, tekrar: _getir),
      );
    }
    final kumeler = _kumele();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Takvim'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _getir,
        child: ListView(
          padding: const EdgeInsets.only(top: 8, bottom: 28),
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Not(
                'Bilanço günü pozisyon taşımak ayrı bir risktir: sonuç '
                'seans dışında açıklanır ve ertesi gün boşluklu açılış '
                'stopunu atlayabilir.',
                ikon: Icons.event_sharp, renk: sem.aksan,
              ),
            ),
            if (_yukleniyor && _olaylar.isEmpty)
              const Yukleniyor(mesaj: 'Takvim hazırlanıyor')
            else if (_olaylar.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Kutu(
                  child: Text('Önümüzdeki dönemde takvim kaydı yok.',
                      style: Theme.of(c).textTheme.bodyMedium
                          ?.copyWith(color: Renk.metinSolgun)),
                ),
              )
            else
              ...kumeler.entries.expand((e) => [
                    Baslik(e.key, alt: '${e.value.length} kayıt'),
                    ...e.value.map((m) => Padding(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                          child: _kart(c, sem, m),
                        )),
                  ]),
          ],
        ),
      ),
    );
  }

  static const _ikon = {
    'bilanço': Icons.assessment_sharp,
    'temettü': Icons.payments_sharp,
    'genel_kurul': Icons.groups_sharp,
    'ekonomi': Icons.public_sharp,
  };

  Widget _kart(BuildContext c, Sem sem, Map<String, dynamic> m) {
    final tur = '${m['tur']}';
    final kod = '${m['sembol'] ?? ''}';
    final gun = ((m['kalan_gun'] ?? 0) as num).toInt();
    final duyurulan = m['kaynak'] == 'duyurulan';

    return Kutu(
      tikla: kod.isEmpty
          ? null
          : () => Navigator.push(
              c, MaterialPageRoute(builder: (_) => HisseEkran(kod))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(_ikon[tur] ?? Icons.event_sharp, size: 16,
                color: duyurulan ? sem.aksan : Renk.metinSonuk),
            const SizedBox(width: 10),
            Expanded(
              child: Text('${m['baslik']}',
                  style: Theme.of(c).textTheme.bodyLarge),
            ),
            const SizedBox(width: 8),
            Text(gun == 0 ? 'bugün' : '$gun gün',
                style: TextStyle(
                    color: gun <= 3 ? sem.uyari : Renk.metinSolgun,
                    fontSize: 12, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 7),
          Row(children: [
            // "Beklenen" ile "duyurulan" ayrımı GÖRÜNÜR olmalı:
            // hesaplanmış bir tarihe göre gün planlanmaz.
            Rozet(duyurulan ? 'DUYURULDU' : 'BEKLENEN',
                renk: duyurulan ? sem.aksan : Renk.metinSonuk),
            const SizedBox(width: 8),
            Text('${m['tarih']}',
                style: Theme.of(c).textTheme.bodySmall),
          ]),
          if ('${m['aciklama'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 7),
            Text('${m['aciklama']}',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.45)),
          ],
        ],
      ),
    );
  }
}
