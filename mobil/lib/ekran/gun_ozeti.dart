import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'hisse.dart';
import 'karne.dart';

/// Gün özeti — backend'in akşam topladığı verinin görünümü.
///
/// "Dün 100 TL, bugün 103 TL" tam olarak burada: her hissenin önceki kapanışı
/// ve bugünkü kapanışı ambarda saklanır, buradan okunur.
class GunOzetiEkran extends StatefulWidget {
  const GunOzetiEkran({super.key});
  @override
  State<GunOzetiEkran> createState() => _GunOzetiDurum();
}

class _GunOzetiDurum extends State<GunOzetiEkran> {
  Map<String, dynamic>? _v;
  List<dynamic> _haberler = [];
  Object? _hata;
  bool _yukleniyor = true;
  String? _tarih;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.gunlukOzet(tarih: _tarih);
      List<dynamic> h = [];
      try {
        h = (await depo.api.gunlukHaberler(azami: 25))['haberler'] as List? ?? [];
      } catch (_) {}
      if (!mounted) return;
      setState(() { _v = r; _haberler = h; _yukleniyor = false; });
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
        title: const Text('Gün özeti'),
        actions: [
          IconButton(
            icon: const Icon(Icons.fact_check_sharp),
            tooltip: 'Sistemin sicili',
            onPressed: () => Navigator.push(c,
                MaterialPageRoute(builder: (_) => const KarneEkran())),
          ),
          IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
        ],
      ),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Gün özeti alınıyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : _icerik(c, sem),
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final o = (_v!['ozet'] ?? {}) as Map<String, dynamic>;
    final tarihler = (_v!['tarihler'] as List?) ?? [];
    final yuk = ((o['yukselen'] ?? 0) as num).toInt();
    final dus = ((o['dusen'] ?? 0) as num).toInt();
    final genislik = ((o['genislik'] ?? 0) as num).toDouble();
    final rejim = o['rejim'] as Map<String, dynamic>?;

    return RefreshIndicator(
      onRefresh: _getir,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
        children: [
          if (tarihler.length > 1)
            SizedBox(
              height: 38,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: tarihler.take(12).map((t) {
                  final secili = (_tarih ?? tarihler.first) == t;
                  return Padding(
                    padding: const EdgeInsets.only(right: 7),
                    child: ChoiceChip(
                      label: Text('$t'.substring(5), style: const TextStyle(fontSize: 12)),
                      selected: secili,
                      onSelected: (_) {
                        setState(() => _tarih = '$t');
                        _getir();
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
          const SizedBox(height: 12),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('XU100',
                            style: Theme.of(c).textTheme.labelSmall
                                ?.copyWith(color: sem.aksan, letterSpacing: 1.1)),
                        Text(tl(o['endeks'] as num?),
                            style: Theme.of(c).textTheme.headlineSmall),
                      ],
                    ),
                  ),
                  Text(yzd(o['endeks_degisim'] as num?),
                      style: TextStyle(
                          fontSize: 19, fontWeight: FontWeight.w800,
                          color: sem.yon(o['endeks_degisim'] as num?))),
                ]),
                const SizedBox(height: 16),
                Text('PİYASA GENİŞLİĞİ',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant,
                        letterSpacing: 1.1)),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: kose,
                  child: Row(children: [
                    Expanded(
                      flex: (genislik * 10).round().clamp(1, 1000),
                      child: Container(height: 10, color: sem.arti),
                    ),
                    Expanded(
                      flex: ((100 - genislik) * 10).round().clamp(1, 1000),
                      child: Container(height: 10, color: sem.eksi),
                    ),
                  ]),
                ),
                const SizedBox(height: 7),
                Row(children: [
                  Text('$yuk yükselen',
                      style: TextStyle(color: sem.arti, fontWeight: FontWeight.w600,
                          fontSize: 13)),
                  const Spacer(),
                  Text('$dus düşen',
                      style: TextStyle(color: sem.eksi, fontWeight: FontWeight.w600,
                          fontSize: 13)),
                ]),
                if (o['bist_reel_1y'] != null) ...[
                  const SizedBox(height: 14),
                  Not('BIST 1 yıl REEL getiri: ${yzd(o['bist_reel_1y'] as num?)}',
                      ikon: Icons.trending_down_sharp,
                      renk: ((o['bist_reel_1y'] as num?) ?? 0) < 0 ? sem.eksi : sem.arti),
                ],
              ],
            ),
          ),
          if (rejim != null) ...[
            const SizedBox(height: 12),
            Kutu(
              ic: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
              child: Row(children: [
                Rozet('${rejim['ad']}',
                    renk: '${rejim['ad']}'.contains('AÇIK')
                        ? sem.arti
                        : '${rejim['ad']}'.contains('SAVUNMA') ? sem.eksi : sem.uyari,
                    dolu: true),
                const SizedBox(width: 12),
                Expanded(child: Text('${rejim['aciklama']}',
                    style: Theme.of(c).textTheme.bodySmall)),
              ]),
            ),
          ],
          const Baslik('En çok hareket edenler', alt: 'dün → bugün'),
          ...[
            ...((o['en_cok_artan'] as List?) ?? []),
            ...((o['en_cok_azalan'] as List?) ?? []),
          ].map((x) => _hareketSatiri(c, sem, x as Map<String, dynamic>)),
          if ((o['sinyal_veren'] as List?)?.isNotEmpty ?? false) ...[
            const Baslik('Sinyal verenler'),
            ...(o['sinyal_veren'] as List).map((s) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Kutu(
                    ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    tikla: () => Navigator.push(c, MaterialPageRoute(
                        builder: (_) => HisseEkran('${s['sembol']}'))),
                    child: Row(children: [
                      SkorHalka(s['skor'] as num?, boyut: 38),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${s['sembol']}',
                                style: Theme.of(c).textTheme.titleMedium),
                            // Karantinadaki strateji uyarı rengiyle ve
                            // işaretli: gün özeti ayrı bir ekran, burada
                            // işaretlenmezse sinyal onaylanmış görünür.
                            Builder(builder: (_) {
                              final kar =
                                  (s['karantina'] as List?) ?? const [];
                              final ad =
                                  (s['sinyaller'] as List?)?.join(", ") ?? '';
                              return Text(kar.isEmpty ? ad : '$ad ⚠ sicili zayıf',
                                  style: Theme.of(c).textTheme.bodySmall
                                      ?.copyWith(color: kar.isEmpty
                                          ? sem.aksan : sem.uyari));
                            }),
                          ],
                        ),
                      ),
                      Text('${tl(s['fiyat'] as num?)} ₺',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      if (s['alinabilir'] != true) ...[
                        const SizedBox(width: 8),
                        Icon(Icons.block_sharp, size: 15, color: sem.uyari),
                      ],
                    ]),
                  ),
                )),
          ],
          if (_haberler.isNotEmpty) ...[
            const Baslik('Haberler', alt: 'Türkçe finans beslemeleri'),
            ..._haberler.take(12).map((h) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Kutu(
                    ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Text('${h['kaynak']}',
                              style: Theme.of(c).textTheme.labelSmall
                                  ?.copyWith(color: sem.aksan)),
                          const Spacer(),
                          ...((h['hisseler'] as List?) ?? [])
                              .take(3)
                              .map((s) => Padding(
                                    padding: const EdgeInsets.only(left: 5),
                                    child: Rozet(s.toString()),
                                  )),
                        ]),
                        const SizedBox(height: 6),
                        Text('${h['baslik']}',
                            style: Theme.of(c).textTheme.bodyMedium
                                ?.copyWith(height: 1.4)),
                      ],
                    ),
                  ),
                )),
            const SizedBox(height: 8),
            Not(
              'Türkçe finans beslemeleri genel ekonomi yayınlar; çoğu gün çoğu '
              'hisse için haber çıkmaz. KAP entegre değildir — şirkete özel '
              'resmi açıklamalar için kap.org.tr\'ye elle bakman gerekir.',
              ikon: Icons.info_outline_sharp,
            ),
          ],
        ],
      ),
    );
  }

  Widget _hareketSatiri(BuildContext c, Sem sem, Map<String, dynamic> x) {
    final d = (x['degisim'] as num?)?.toDouble() ?? 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Kutu(
        ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        tikla: () => Navigator.push(c,
            MaterialPageRoute(builder: (_) => HisseEkran('${x['sembol']}'))),
        child: Row(children: [
          Icon(d >= 0 ? Icons.arrow_upward_sharp : Icons.arrow_downward_sharp,
              size: 16, color: sem.yon(d)),
          const SizedBox(width: 10),
          Expanded(
            child: Text('${x['sembol']}',
                style: Theme.of(c).textTheme.titleMedium?.copyWith(fontSize: 15)),
          ),
          Text(tl(x['onceki'] as num?),
              style: TextStyle(
                  fontSize: 13, color: Theme.of(c).colorScheme.onSurfaceVariant,
                  fontFeatures: const [FontFeature.tabularFigures()])),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: Icon(Icons.arrow_right_alt_sharp, size: 15,
                color: Theme.of(c).colorScheme.onSurfaceVariant),
          ),
          Text(tl(x['kapanis'] as num?),
              style: const TextStyle(
                  fontWeight: FontWeight.w700, fontSize: 13,
                  fontFeatures: [FontFeature.tabularFigures()])),
          const SizedBox(width: 10),
          SizedBox(
            width: 62,
            child: Text(yzd(d), textAlign: TextAlign.right,
                style: TextStyle(
                    fontWeight: FontWeight.w700, color: sem.yon(d), fontSize: 13)),
          ),
        ]),
      ),
    );
  }
}
