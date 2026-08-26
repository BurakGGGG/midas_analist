import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../tema.dart';

/// API'den gelen [{t: "2026-08-24", d: 300.75}] listesini noktalara çevirir.
List<FlSpot> noktalar(dynamic seri) {
  if (seri is! List) return const [];
  final out = <FlSpot>[];
  for (var i = 0; i < seri.length; i++) {
    final d = seri[i];
    if (d is Map && d['d'] != null) {
      out.add(FlSpot(i.toDouble(), (d['d'] as num).toDouble()));
    }
  }
  return out;
}

List<String> tarihler(dynamic seri) {
  if (seri is! List) return const [];
  return seri.map((d) => (d is Map ? '${d['t']}' : '')).toList();
}

/// Fiyat grafiği: kapanış + isteğe bağlı ortalamalar.
/// Renk kararı: ortalamalar soluk, fiyat baskın — göz önce fiyatı bulmalı.
class FiyatGrafik extends StatelessWidget {
  final dynamic kapanis, ema20, sma200;
  final double yukseklik;
  const FiyatGrafik(this.kapanis,
      {super.key, this.ema20, this.sma200, this.yukseklik = 190});

  @override
  Widget build(BuildContext c) {
    final k = noktalar(kapanis);
    if (k.length < 3) {
      return SizedBox(
        height: yukseklik,
        child: Center(
          child: Text('Grafik verisi yok',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
        ),
      );
    }
    final e = noktalar(ema20), s = noktalar(sma200);
    final sem = Sem(c);
    final hepsi = [...k, ...e, ...s].map((p) => p.y);
    final enAz = hepsi.reduce((a, b) => a < b ? a : b);
    final enCok = hepsi.reduce((a, b) => a > b ? a : b);
    final pay = (enCok - enAz) * 0.08;
    final artiyor = k.last.y >= k.first.y;
    final ana = artiyor ? sem.arti : sem.eksi;
    final tar = tarihler(kapanis);

    return SizedBox(
      height: yukseklik,
      child: LineChart(
        LineChartData(
          minY: enAz - pay,
          maxY: enCok + pay,
          gridData: FlGridData(
            show: true, drawVerticalLine: false, horizontalInterval: (enCok - enAz) / 3,
            getDrawingHorizontalLine: (_) => const FlLine(
                color: Renk.cizgi, strokeWidth: 1, dashArray: [1, 3]),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true, reservedSize: 46, interval: (enCok - enAz) / 3,
                getTitlesWidget: (v, _) => Padding(
                  padding: const EdgeInsets.only(left: 5),
                  child: Text(tl(v, basamak: v < 20 ? 1 : 0),
                      style: TextStyle(
                          fontSize: 10,
                          color: Theme.of(c).colorScheme.onSurfaceVariant)),
                ),
              ),
            ),
            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true, reservedSize: 22,
                interval: (k.length / 3).floorToDouble().clamp(1, 999),
                getTitlesWidget: (v, _) {
                  final i = v.toInt();
                  if (i < 0 || i >= tar.length) return const SizedBox();
                  final p = tar[i].split('-');
                  if (p.length < 2) return const SizedBox();
                  return Text('${p[2].padLeft(2, '0')}.${p[1]}',
                      style: TextStyle(
                          fontSize: 10,
                          color: Theme.of(c).colorScheme.onSurfaceVariant));
                },
              ),
            ),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (_) => Renk.panelUst,
              tooltipBorder: const BorderSide(color: Renk.cizgiParlak),
              getTooltipItems: (list) => list.map((t) {
                final i = t.x.toInt();
                final gun = (i >= 0 && i < tar.length) ? tar[i] : '';
                return LineTooltipItem(
                  '${tl(t.y)} ₺\n$gun',
                  const TextStyle(
                      color: Renk.metin, fontFamily: 'Piksel',
                      fontSize: 12, fontWeight: FontWeight.w700),
                );
              }).toList(),
            ),
          ),
          lineBarsData: [
            if (s.length > 2)
              LineChartBarData(
                spots: s, isCurved: false, barWidth: 1, dotData: const FlDotData(show: false),
                color: Renk.metinSonuk,
                dashArray: const [3, 3],
              ),
            if (e.length > 2)
              LineChartBarData(
                spots: e, isCurved: false, barWidth: 1, dotData: const FlDotData(show: false),
                color: Renk.aksanKoyu, dashArray: const [2, 2],
              ),
            // Basamaklı çizgi: piksel ızgarasına oturur ve her barın
            // kapanışını tek tek gösterir — kavisli çizgi ara değer uydurur.
            LineChartBarData(
              spots: k, isCurved: false, isStepLineChart: true,
              barWidth: 2, color: ana,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: ana.withValues(alpha: 0.13),   // düz dolgu, degrade yok
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// RSI paneli — 30/70 bantları çizili, çünkü RSI'nin anlamı o bantlarda.
class RsiGrafik extends StatelessWidget {
  final dynamic rsi;
  const RsiGrafik(this.rsi, {super.key});

  @override
  Widget build(BuildContext c) {
    final p = noktalar(rsi);
    if (p.length < 3) return const SizedBox.shrink();
    final sem = Sem(c);
    return SizedBox(
      height: 76,
      child: LineChart(
        LineChartData(
          minY: 0, maxY: 100,
          gridData: FlGridData(
            show: true, drawVerticalLine: false, horizontalInterval: 35,
            checkToShowHorizontalLine: (v) => v == 30 || v == 70,
            getDrawingHorizontalLine: (v) => FlLine(
                color: (v == 70 ? sem.eksi : sem.arti).withValues(alpha: 0.35),
                strokeWidth: 1, dashArray: const [3, 3]),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true, reservedSize: 46, interval: 35,
                getTitlesWidget: (v, _) => (v == 30 || v == 70)
                    ? Padding(
                        padding: const EdgeInsets.only(left: 5),
                        child: Text(v.toInt().toString(),
                            style: TextStyle(
                                fontSize: 9.5,
                                color: Theme.of(c).colorScheme.onSurfaceVariant)))
                    : const SizedBox(),
              ),
            ),
          ),
          lineTouchData: const LineTouchData(enabled: false),
          lineBarsData: [
            LineChartBarData(
              spots: p, isCurved: false, isStepLineChart: true,
              barWidth: 1.6, color: sem.aksan,
              dotData: const FlDotData(show: false),
            ),
          ],
        ),
      ),
    );
  }
}

/// Yatay karşılaştırma çubuğu — sektör göreli gücü, oran kıyası gibi yerlerde.
class YatayCubuk extends StatelessWidget {
  final double deger, enBuyuk;
  final Color? renk;
  final double yukseklik;
  const YatayCubuk(this.deger, this.enBuyuk,
      {super.key, this.renk, this.yukseklik = 8});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final r = renk ?? (deger >= 0 ? sem.arti : sem.eksi);
    final oran = (enBuyuk == 0 ? 0.0 : (deger.abs() / enBuyuk)).clamp(0.0, 1.0);
    return LayoutBuilder(
      builder: (_, k) {
        final yari = k.maxWidth / 2;
        return SizedBox(
          height: yukseklik,
          child: Stack(
            children: [
              Positioned(
                left: yari - 0.5, top: 0, bottom: 0,
                child: Container(width: 1, color: Renk.cizgiParlak),
              ),
              Positioned(
                left: deger >= 0 ? yari : yari - yari * oran,
                width: yari * oran,
                top: 0, bottom: 0,
                child: Container(color: r),
              ),
            ],
          ),
        );
      },
    );
  }
}
