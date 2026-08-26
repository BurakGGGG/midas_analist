import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

class RiskEkran extends StatefulWidget {
  const RiskEkran({super.key});
  @override
  State<RiskEkran> createState() => _RiskDurum();
}

class _RiskDurum extends State<RiskEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.risk(sermaye: depo.ayarlar.sermaye);
      if (mounted) setState(() { _v = r; _yukleniyor = false; });
    } catch (e) {
      if (mounted) setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Risk matematiği')),
      body: _yukleniyor
          ? const Yukleniyor()
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                  children: [
                    _beklenenDeger(c, sem),
                    const SizedBox(height: 14),
                    _monteCarlo(c, sem),
                    const SizedBox(height: 14),
                    _cesitlendirme(c, sem),
                  ],
                ),
    );
  }

  Widget _beklenenDeger(BuildContext c, Sem sem) {
    final liste = (_v!['beklenen_deger'] as List?) ?? [];
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('BEKLENEN DEĞER',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 4),
          Text('Yüksek kazanma oranı iyi strateji demek DEĞİLDİR.',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
          const SizedBox(height: 12),
          ...liste.map((b) {
            final karli = b['karli_mi'] as bool? ?? false;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Expanded(child: Text('${b['ad']}',
                        style: const TextStyle(fontWeight: FontWeight.w600))),
                    Rozet(karli ? 'KÂRLI' : 'ZARARLI',
                        renk: karli ? sem.arti : sem.eksi, dolu: true),
                  ]),
                  const SizedBox(height: 4),
                  Text(
                      'Ödül/risk 1:${tl(b['odul_risk'] as num?)} · '
                      'başabaş için %${tl(b['basabas_kazanma_orani'] as num?, basamak: 1)} '
                      'kazanma yeter · beklenti ${yzd(b['beklenen_deger_yuzde'] as num?, basamak: 3)}',
                      style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.45)),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _monteCarlo(BuildContext c, Sem sem) {
    final liste = (_v!['monte_carlo'] as List?) ?? [];
    final kelly = _v!['kelly'] as Map<String, dynamic>?;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('İŞLEM BAŞI RİSK · 200 işlem simülasyonu',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 12),
          Row(children: [
            const Expanded(flex: 2, child: Text('risk',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('batma olasılığı',
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('kötü senaryo',
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('en uzun kayıp',
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
          ]),
          const Divider(),
          ...liste.map((m) {
            final b = (m['batma_olasiligi_yuzde'] as num?)?.toDouble() ?? 0;
            final renk = b < 1 ? sem.arti : (b < 10 ? sem.uyari : sem.eksi);
            final secili = (m['risk_yuzde'] as num?) == depo.ayarlar.riskYuzde;
            return Container(
              color: secili ? sem.aksan.withValues(alpha: 0.09) : null,
              padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 2),
              child: Row(children: [
                Expanded(flex: 2, child: Row(children: [
                  Text('%${tl(m['risk_yuzde'] as num?, basamak: 1)}',
                      style: TextStyle(fontWeight: FontWeight.w700,
                          color: secili ? sem.aksan : null)),
                  if (secili) ...[
                    const SizedBox(width: 4),
                    Icon(Icons.arrow_back_sharp, size: 12, color: sem.aksan),
                  ],
                ])),
                Expanded(flex: 3, child: Text('%${tl(b, basamak: 1)}',
                    textAlign: TextAlign.right,
                    style: TextStyle(fontWeight: FontWeight.w700, color: renk))),
                Expanded(flex: 3, child: Text(
                    '${tl(m['kotu_senaryo_5'] as num?)}x',
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 12.5))),
                Expanded(flex: 3, child: Text('${m['en_uzun_kayip_serisi']} işlem',
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 12.5))),
              ]),
            );
          }),
          const SizedBox(height: 12),
          if (kelly != null) Not('${kelly['yorum']}', ikon: Icons.functions_sharp),
          const SizedBox(height: 10),
          Not(
            'Yukarı taraf rakamlarına güvenme — kenarın 200 işlem boyunca '
            'bozulmadan süreceğini varsayarlar. Bu tablodan alınacak bilgi '
            'AŞAĞI taraftır: batma olasılığı ve kayıp serisi uzunluğu.',
            ikon: Icons.warning_amber_sharp, renk: sem.uyari,
          ),
        ],
      ),
    );
  }

  Widget _cesitlendirme(BuildContext c, Sem sem) {
    final liste = (_v!['cesitlendirme'] as List?) ?? [];
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('NEDEN TÜM PARAYI TEK HİSSEYE YATIRMAMALI',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 12),
          Row(children: [
            const Expanded(flex: 2, child: Text('hisse',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('oynaklık', textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('kötü gün ±', textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
            Expanded(flex: 3, child: Text('biri batarsa',
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700))),
          ]),
          const Divider(),
          ...liste.map((x) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(children: [
                  Expanded(flex: 2, child: Text('${x['hisse_sayisi']}',
                      style: const TextStyle(fontWeight: FontWeight.w700))),
                  Expanded(flex: 3, child: Text(
                      '%${tl(x['yillik_oynaklik'] as num?, basamak: 1)}',
                      textAlign: TextAlign.right,
                      style: const TextStyle(fontSize: 12.5))),
                  Expanded(flex: 3, child: Text(
                      '${tl(x['kotu_gun_2std_tl'] as num?)} ₺',
                      textAlign: TextAlign.right,
                      style: const TextStyle(fontSize: 12.5))),
                  Expanded(flex: 3, child: Text(
                      '${tl(x['tek_hisse_iflas_kaybi_tl'] as num?, basamak: 0)} ₺',
                      textAlign: TextAlign.right,
                      style: TextStyle(fontSize: 12.5, color: sem.eksi,
                          fontWeight: FontWeight.w600))),
                ]),
              )),
          const SizedBox(height: 12),
          Not(
            '1\'den 4 hisseye çıkmak oynaklığı belirgin düşürüyor, ama 8\'den '
            '20\'ye çıkmak neredeyse hiçbir şey kazandırmıyor. Aynı piyasadaki '
            'hisseler birlikte hareket eder — çeşitlendirmenin sınırı budur.',
            ikon: Icons.school_sharp, renk: sem.aksan,
          ),
        ],
      ),
    );
  }
}
