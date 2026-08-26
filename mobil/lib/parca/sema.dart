import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../tema.dart';

/// Öğretici şema çizeri — ders kitabı çizimi, veri grafiği değil.
///
/// Sunucudan gelen tarifi çizer. Tarif koordinat uzayında gelir (y YUKARI
/// artar, fiyat gibi); ressam ölçekleyip çevirir. Böylece sunucu tarafı
/// piksel bilmez, istemci tarafı kavram bilmez.
class SemaGrafik extends StatelessWidget {
  final Map<String, dynamic> s;
  final double yukseklik;
  const SemaGrafik(this.s, {super.key, this.yukseklik = 230});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return SizedBox(
      height: yukseklik,
      width: double.infinity,
      child: CustomPaint(
        painter: _SemaRessam(
          s,
          renkler: {
            'aksan': sem.aksan,
            'arti': sem.arti,
            'eksi': sem.eksi,
            'uyari': sem.uyari,
            'solgun': Theme.of(c).colorScheme.onSurfaceVariant,
          },
          metinRengi: Theme.of(c).colorScheme.onSurface,
          solgun: Theme.of(c).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _SemaRessam extends CustomPainter {
  final Map<String, dynamic> s;
  final Map<String, Color> renkler;
  final Color metinRengi, solgun;

  _SemaRessam(this.s,
      {required this.renkler, required this.metinRengi, required this.solgun});

  Color _renk(dynamic ad) => renkler[ad] ?? renkler['aksan']!;

  @override
  void paint(Canvas tuval, Size boyut) {
    final en = ((s['en'] ?? 100) as num).toDouble();
    final boy = ((s['boy'] ?? 60) as num).toDouble();
    // Kenar payı: etiketler taşmasın. Sağda daha çok yer var çünkü
    // seviye adları (Destek/Direnç) çizginin sağ ucuna yazılıyor.
    const solP = 8.0, sagP = 58.0, ustP = 16.0, altP = 16.0;
    final w = boyut.width - solP - sagP;
    final h = boyut.height - ustP - altP;

    Offset p(num x, num y) => Offset(
        solP + (x.toDouble() / en) * w, ustP + h - (y.toDouble() / boy) * h);

    // ── çizgiler
    for (final c in (s['cizgiler'] as List? ?? const [])) {
      final m = c as Map;
      final nokta = (m['nokta'] as List? ?? const []);
      if (nokta.length < 2) continue;
      final boya = Paint()
        ..color = _renk(m['renk'])
        ..strokeWidth = ((m['kalin'] ?? 2) as num).toDouble()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;
      final yol = Path();
      for (var i = 0; i < nokta.length; i++) {
        final n = nokta[i] as List;
        final o = p(n[0] as num, n[1] as num);
        i == 0 ? yol.moveTo(o.dx, o.dy) : yol.lineTo(o.dx, o.dy);
      }
      if (m['kesik'] == true) {
        _kesikCiz(tuval, yol, boya);
      } else {
        tuval.drawPath(yol, boya);
      }
    }

    // ── mumlar
    for (final c in (s['mumlar'] as List? ?? const [])) {
      final m = c as Map;
      final x = (m['x'] as num).toDouble();
      final a = (m['a'] as num).toDouble(), k = (m['k'] as num).toDouble();
      final yu = (m['y'] as num).toDouble(), d = (m['d'] as num).toDouble();
      final g = ((m['genislik'] ?? 10) as num).toDouble();
      final yukselen = k >= a;
      final renk = yukselen ? renkler['arti']! : renkler['eksi']!;
      // Fitil önce: gövde onun üstüne binsin.
      tuval.drawLine(p(x, yu), p(x, d),
          Paint()..color = renk..strokeWidth = 1.6);
      final sol = p(x - g / 2, 0).dx, sag = p(x + g / 2, 0).dx;
      final ust = p(x, yukselen ? k : a).dy, alt = p(x, yukselen ? a : k).dy;
      final govde = Rect.fromLTRB(sol, ust, sag, alt.abs() - ust.abs() < 1.5
          ? ust + 1.5   // doji: gövde neredeyse yok, yine de görünsün
          : alt);
      tuval.drawRect(govde, Paint()..color = renk);
    }

    // ── seviyeler (yatay etiketli çizgi)
    for (final c in (s['seviyeler'] as List? ?? const [])) {
      final m = c as Map;
      final y = (m['y'] as num).toDouble();
      final x1 = ((m['x1'] ?? 0) as num).toDouble();
      final x2 = ((m['x2'] ?? en) as num).toDouble();
      final renk = _renk(m['renk']);
      final yol = Path()
        ..moveTo(p(x1, y).dx, p(x1, y).dy)
        ..lineTo(p(x2, y).dx, p(x2, y).dy);
      _kesikCiz(tuval, yol,
          Paint()..color = renk..strokeWidth = 1.6..style = PaintingStyle.stroke);
      if ('${m['ad'] ?? ''}'.isNotEmpty) {
        _yaz(tuval, '${m['ad']}', p(x2, y) + const Offset(5, -7),
            renk, 10.5, hiza: 'sol');
      }
    }

    // ── oklar
    for (final c in (s['oklar'] as List? ?? const [])) {
      final m = c as Map;
      final b = p(m['x1'] as num, m['y1'] as num);
      final e = p(m['x2'] as num, m['y2'] as num);
      final boya = Paint()
        ..color = _renk(m['renk'])
        ..strokeWidth = 1.4;
      tuval.drawLine(b, e, boya);
      final yon = (e - b);
      final uz = yon.distance == 0 ? const Offset(0, 0) : yon / yon.distance;
      final dik = Offset(-uz.dy, uz.dx);
      tuval.drawPath(
          Path()
            ..moveTo(e.dx, e.dy)
            ..lineTo(e.dx - uz.dx * 7 + dik.dx * 3.5,
                e.dy - uz.dy * 7 + dik.dy * 3.5)
            ..lineTo(e.dx - uz.dx * 7 - dik.dx * 3.5,
                e.dy - uz.dy * 7 - dik.dy * 3.5)
            ..close(),
          Paint()..color = _renk(m['renk']));
    }

    // ── etiketler
    for (final c in (s['etiketler'] as List? ?? const [])) {
      final m = c as Map;
      _yaz(tuval, '${m['ad']}', p(m['x'] as num, m['y'] as num),
          metinRengi, 10.5, hiza: '${m['hiza'] ?? 'orta'}');
    }
  }

  void _kesikCiz(Canvas t, Path yol, Paint boya) {
    boya.style = PaintingStyle.stroke;
    for (final olcum in yol.computeMetrics()) {
      var u = 0.0;
      while (u < olcum.length) {
        final son = (u + 4).clamp(0.0, olcum.length);
        t.drawPath(olcum.extractPath(u, son), boya);
        u += 8;
      }
    }
  }

  void _yaz(Canvas t, String metin, Offset konum, Color renk, double boy,
      {String hiza = 'orta'}) {
    final tp = TextPainter(
      text: TextSpan(
          text: metin,
          style: TextStyle(
              color: renk, fontSize: boy, fontWeight: FontWeight.w600,
              fontFeatures: const [ui.FontFeature.tabularFigures()])),
      textDirection: TextDirection.ltr,
    )..layout();
    final dx = hiza == 'sol'
        ? konum.dx
        : hiza == 'sag'
            ? konum.dx - tp.width
            : konum.dx - tp.width / 2;
    tp.paint(t, Offset(dx, konum.dy - tp.height / 2));
  }

  @override
  bool shouldRepaint(covariant _SemaRessam eski) => eski.s != s;
}
