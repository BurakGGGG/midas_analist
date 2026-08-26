import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// "Bu şirketi bana 10 dakikada anlat" egzersizi.
///
/// 16 adım. Her adımda ÖNCE kendi cevabını kurarsın, sonra sistemin ölçtüğü
/// rakama bakarsın. Amaç doğru hisseyi seçmen değil, doğru düşünce sürecini
/// kurman.
class SirketOkuEkran extends StatefulWidget {
  final String sembol;
  const SirketOkuEkran(this.sembol, {super.key});
  @override
  State<SirketOkuEkran> createState() => _SirketOkuDurum();
}

class _SirketOkuDurum extends State<SirketOkuEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;
  int _adim = 0;
  final Set<int> _acilan = {};

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() => _hata = null);
    try {
      final r = await depo.api.egitmenSirketOku(widget.sembol);
      if (mounted) setState(() => _v = r);
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    if (_hata != null) {
      return Scaffold(
        appBar: AppBar(title: Text('${widget.sembol} okuma')),
        body: HataGorunum(_hata!, tekrar: _getir),
      );
    }
    if (_v == null) {
      return Scaffold(
        appBar: AppBar(title: Text('${widget.sembol} okuma')),
        body: const Yukleniyor(mesaj: 'Finansallar hazırlanıyor...'),
      );
    }
    final adimlar = (_v!['adimlar'] as List?) ?? [];
    final bitti = _adim >= adimlar.length;

    return Scaffold(
      appBar: AppBar(
        title: Text('${_v!['sembol']} okuma'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(3),
          child: LinearProgressIndicator(
            value: adimlar.isEmpty ? 0 : _adim / adimlar.length, minHeight: 3,
            backgroundColor: Theme.of(c).dividerColor,
          ),
        ),
      ),
      body: bitti
          ? _bitis(c, sem)
          : _adimGorunum(c, sem, adimlar[_adim] as Map<String, dynamic>,
              adimlar.length),
    );
  }

  Widget _adimGorunum(BuildContext c, Sem sem, Map<String, dynamic> a, int toplam) {
    final acik = _acilan.contains(_adim);
    final veri = a['veri'];
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
      children: [
        Text('ADIM ${_adim + 1} / $toplam',
            style: Theme.of(c).textTheme.labelSmall?.copyWith(
                color: sem.aksan, letterSpacing: 1.1)),
        const SizedBox(height: 12),
        Kutu(
          ic: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${a['soru']}',
                  style: Theme.of(c).textTheme.titleLarge?.copyWith(
                      fontSize: 19, height: 1.35)),
              const SizedBox(height: 10),
              Text('${a['aciklama']}',
                  style: Theme.of(c).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant,
                      height: 1.5)),
            ],
          ),
        ),
        const SizedBox(height: 18),
        if (!acik) ...[
          Not('Önce kendi cevabını kur. Sistemin ölçtüğü rakama sonra bak — '
              'sırayı bozarsan düşünmüş olmazsın, sadece okumuş olursun.',
              ikon: Icons.psychology_sharp, renk: sem.aksan),
          const SizedBox(height: 14),
          FilledButton.tonal(
            onPressed: () => setState(() => _acilan.add(_adim)),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            child: Text(veri == null
                ? 'Bu adımda sayı yok — devam'
                : 'Sistemin ölçtüğünü gör'),
          ),
        ] else ...[
          if (veri != null)
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SİSTEM NE ÖLÇÜYOR',
                      style: Theme.of(c).textTheme.labelSmall?.copyWith(
                          color: sem.arti, letterSpacing: 1.1)),
                  const SizedBox(height: 8),
                  Text('$veri',
                      style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.55)),
                ],
              ),
            )
          else
            Not('Bu adımda sistemin ölçtüğü bir sayı yok — kendi araştırman '
                'gerekiyor. Rakipler, yönetim ve rekabet avantajı, bilançoda '
                'görünmez.',
                ikon: Icons.travel_explore_sharp, renk: sem.uyari),
          const SizedBox(height: 18),
          FilledButton(
            onPressed: () => setState(() => _adim++),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            child: Text(_adim + 1 >= toplam ? 'Bitir' : 'Sonraki adım'),
          ),
        ],
      ],
    );
  }

  Widget _bitis(BuildContext c, Sem sem) {
    final kalite = _v!['kalite'] as Map<String, dynamic>?;
    final bayrak = (_v!['bayraklar'] as List?) ?? [];
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 24, 16, 30),
      children: [
        Icon(Icons.fact_check_sharp, size: 54, color: sem.aksan),
        const SizedBox(height: 16),
        Text('${_v!['ad']}',
            textAlign: TextAlign.center,
            style: Theme.of(c).textTheme.titleLarge),
        const SizedBox(height: 20),
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('SİSTEMİN ÖZETİ',
                  style: Theme.of(c).textTheme.labelSmall?.copyWith(
                      color: sem.aksan, letterSpacing: 1.1)),
              const SizedBox(height: 12),
              Row(children: [
                SkorHalka(kalite?['skor'] as num?, boyut: 58, alt: 'kalite'),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                      bayrak.isEmpty
                          ? 'Kırmızı bayrak yok.'
                          : '${bayrak.length} kırmızı bayrak var.',
                      style: Theme.of(c).textTheme.bodyMedium),
                ),
              ]),
              if (bayrak.isNotEmpty) ...[
                const SizedBox(height: 12),
                ...bayrak.map((b) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.priority_high_sharp, size: 15, color: sem.eksi),
                          const SizedBox(width: 8),
                          Expanded(child: Text('$b',
                              style: Theme.of(c).textTheme.bodySmall
                                  ?.copyWith(height: 1.45))),
                        ],
                      ),
                    )),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        Not(
          'Son soru: bu şirketi neden ALIRSIN, neden ALMAZSIN?\n\n'
          'İkisini de yazamıyorsan yeterince düşünmemişsindir. Kendi fikrinin '
          'esiri olmamanın tek yolu, karşı argümanı da kurmaktır.',
          ikon: Icons.balance_sharp, renk: sem.uyari,
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: () => Navigator.pop(c),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          child: const Text('Bitir'),
        ),
      ],
    );
  }
}
