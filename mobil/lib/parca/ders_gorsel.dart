import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../tema.dart';
import 'kart.dart';
import 'grafik.dart';
import 'sema.dart';

/// Ders görselleri — sunucudan CANLI veriyle gelir.
///
/// Neden canlı: ders kitabındaki uydurma grafik, öğrenilen şeyin gerçek
/// piyasada nasıl göründüğünü göstermez. "RSI 70 üstü sat" ezberinin
/// yanlışlığını gerçek bir BIST hissesinin gerçek RSI'sinde görmek,
/// çizilmiş bir örnekten başka bir şeydir.
///
/// Veri gelmezse HİÇBİR ŞEY çizilmez — boş bir grafik kutusu, grafik
/// olmamasından kötüdür.
class DersGorsel extends StatelessWidget {
  final Map<String, dynamic> g;
  const DersGorsel(this.g, {super.key});

  @override
  Widget build(BuildContext c) {
    if (g['yok'] == true) return const SizedBox.shrink();
    final sem = Sem(c);
    final govde = _govde(c, sem);
    if (govde == null) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
      child: Kutu(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.insights_sharp, size: 17, color: sem.aksan),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('${g['baslik']}',
                      style: Theme.of(c).textTheme.titleSmall),
                ),
              ],
            ),
            if ('${g['aciklama'] ?? ''}'.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('${g['aciklama']}',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
            ],
            const SizedBox(height: 12),
            govde,
            if ('${g['sonuc'] ?? ''}'.isNotEmpty) ...[
              const SizedBox(height: 12),
              // Grafik tek başına yorumlanmaz. "Ne görmeliyim" cümlesi
              // olmadan çoğu okuyucu grafiğe bakıp geçer.
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                    border: Border(
                        left: BorderSide(color: sem.aksan, width: 3))),
                child: Text('${g['sonuc']}',
                    style: Theme.of(c).textTheme.bodySmall),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget? _govde(BuildContext c, Sem sem) {
    switch ('${g['tur']}') {
      case 'sema':
        // Öğretici çizim: canlı veri değil, kavramın kendisi.
        return SemaGrafik(g);
      case 'fiyat':
        return FiyatGrafik(g['kapanis'],
            ema20: g['ema20'], sma200: g['sma200'], yukseklik: 175);
      case 'rsi':
        return RsiGrafik(g['rsi']);
      case 'tek_seri':
        return _cizgi(c, sem, [
          ['', g['seri'], sem.aksan]
        ]);
      case 'cift_seri':
        final s1 = g['seri1'] as Map?, s2 = g['seri2'] as Map?;
        if (s1 == null || s2 == null) return null;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _cizgi(c, sem, [
              ['${s1['ad']}', s1['veri'], sem.aksan],
              ['${s2['ad']}', s2['veri'], sem.uyari],
            ]),
            const SizedBox(height: 8),
            Row(children: [
              _lejant(c, '${s1['ad']}', sem.aksan),
              const SizedBox(width: 14),
              _lejant(c, '${s2['ad']}', sem.uyari),
            ]),
          ],
        );
      case 'cubuk':
        return _cubuklar(c, sem);
    }
    return null;
  }

  Widget _lejant(BuildContext c, String ad, Color renk) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 12, height: 3, color: renk),
          const SizedBox(width: 6),
          Text(ad, style: Theme.of(c).textTheme.bodySmall),
        ],
      );

  Widget _cizgi(BuildContext c, Sem sem, List<List<dynamic>> seriler) {
    final cizgiler = <LineChartBarData>[];
    final hepsi = <double>[];
    for (final s in seriler) {
      final p = noktalar(s[1]);
      if (p.length < 3) continue;
      hepsi.addAll(p.map((e) => e.y));
      cizgiler.add(LineChartBarData(
        spots: p,
        isCurved: false,
        color: s[2] as Color,
        barWidth: 1.6,
        dotData: const FlDotData(show: false),
      ));
    }
    if (cizgiler.isEmpty) {
      return SizedBox(
        height: 120,
        child: Center(
          child: Text('Grafik verisi yok',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
        ),
      );
    }
    final enAz = hepsi.reduce((a, b) => a < b ? a : b);
    final enCok = hepsi.reduce((a, b) => a > b ? a : b);
    final pay = (enCok - enAz) * 0.08;
    return SizedBox(
      height: 175,
      child: LineChart(LineChartData(
        minY: enAz - pay,
        maxY: enCok + pay,
        lineBarsData: cizgiler,
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineTouchData: const LineTouchData(enabled: false),
      )),
    );
  }

  Widget _cubuklar(BuildContext c, Sem sem) {
    final etiketler = (g['etiketler'] as List?) ?? const [];
    final degerler = (g['degerler'] as List?) ?? const [];
    if (etiketler.isEmpty || degerler.isEmpty) return const SizedBox.shrink();
    final sayilar = degerler.map((v) => (v as num).toDouble()).toList();
    final enBuyuk = sayilar
        .map((v) => v.abs())
        .reduce((a, b) => a > b ? a : b);
    final ref = (g['referans'] as num?)?.toDouble();
    return Column(
      children: [
        for (var i = 0; i < etiketler.length && i < degerler.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(
              children: [
                SizedBox(
                  width: 96,
                  child: Text('${etiketler[i]}',
                      style: Theme.of(c).textTheme.bodySmall,
                      overflow: TextOverflow.ellipsis),
                ),
                Expanded(
                  // FractionallySizedBox kullanılıyor, Align+widthFactor
                  // DEĞİL: çocuğu genişliksiz bir Container olduğunda Align
                  // oranı uygulayamıyor ve bütün çubuklar aynı boyda
                  // çiziliyordu — bu grafikte anlatılmak istenen tam da
                  // uzunluk farkıyken.
                  child: SizedBox(
                    height: 11,
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: enBuyuk == 0
                          ? 0
                          : (sayilar[i].abs() / enBuyuk).clamp(0.015, 1.0),
                      child: Container(
                        // Referans varsa altında kalanlar uyarı rengine döner:
                        // "hangisi beklentinin altında" tek bakışta görünsün.
                        color: ref != null && sayilar[i] < ref
                            ? sem.uyari
                            : sem.aksan,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 46,
                  child: Text(
                      sayilar[i] == sayilar[i].roundToDouble()
                          ? '${sayilar[i].toInt()}'
                          : sayilar[i].toStringAsFixed(2),
                      textAlign: TextAlign.right,
                      style: Theme.of(c).textTheme.bodySmall),
                ),
              ],
            ),
          ),
        if (ref != null) ...[
          const SizedBox(height: 4),
          Row(children: [
            Container(width: 12, height: 3, color: sem.uyari),
            const SizedBox(width: 6),
            Expanded(
              child: Text('turuncu = tarihsel ortalamanın (%${ref.toStringAsFixed(1)}) altı',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
            ),
          ]),
        ],
      ],
    );
  }
}
