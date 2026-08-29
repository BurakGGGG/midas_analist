import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Sistemin canlı sicili.
///
/// Backtest geçmişe uydurulmuş olabilir; canlı sicil uydurulamaz. Bu ekran
/// rahatsız edici sonuçları gizlemez — sistemin kendini ölçmesinin anlamı budur.
class KarneEkran extends StatefulWidget {
  const KarneEkran({super.key});
  @override
  State<KarneEkran> createState() => _KarneDurum();
}

class _KarneDurum extends State<KarneEkran> {
  Map<String, dynamic>? _v;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() { super.initState(); _getir(); }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api.gunlukKarne();
      if (mounted) setState(() { _v = r; _yukleniyor = false; });
    } catch (e) {
      if (mounted) setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Sistemin sicili')),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Sicil hesaplanıyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : _icerik(c, sem),
    );
  }

  Widget _icerik(BuildContext c, Sem sem) {
    final karne = (_v!['karne'] ?? {}) as Map<String, dynamic>;
    final vadeler = (karne['vadeler'] ?? {}) as Map<String, dynamic>;
    final stratejiler = (karne['stratejiler'] ?? {}) as Map<String, dynamic>;
    final kayma = (_v!['kayma'] as List?) ?? [];
    final kapsam = (_v!['kapsam'] ?? {}) as Map<String, dynamic>;
    final uyarilar = (_v!['uyarilar'] as List?) ?? [];
    final filtre = (_v!['filtre'] ?? {}) as Map<String, dynamic>;
    final ay = ((kapsam['ay'] ?? 0) as num).toDouble();
    final kapaliListe =
        ((_v!['kapali_stratejiler'] as List?) ?? []).map((e) => '$e').toSet();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
      children: [
        Not(
          'Bu backtest DEĞİL. Sistemin gerçekte ürettiği sinyallerin sonucu. '
          'Backtest geçmişe uydurulmuş olabilir; canlı sicil uydurulamaz.',
          ikon: Icons.fact_check_sharp, renk: sem.aksan,
        ),
        if ((kapsam['sinyal'] ?? 0) != 0) ...[
          const SizedBox(height: 12),
          Kutu(
            ic: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('KAPSAM',
                    style: Theme.of(c).textTheme.labelSmall
                        ?.copyWith(color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 6),
                Text('${kapsam['ilk']} → ${kapsam['son']}  ·  '
                    '$ay ay  ·  ${kapsam['sinyal']} sinyal',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                if (ay < 12) ...[
                  const SizedBox(height: 8),
                  Text('Bu süre tek bir piyasa rejimini kapsıyor olabilir — '
                      'yorumu buna göre yap.',
                      style: Theme.of(c).textTheme.bodySmall
                          ?.copyWith(color: sem.uyari, height: 1.4)),
                ],
              ],
            ),
          ),
        ],
        const Baslik('Vadelere göre', alt: 'stop ve hedef uygulanmış'),
        ...vadeler.entries.map((e) {
          final v = e.value as Map<String, dynamic>;
          if ((v['sinyal'] ?? 0) == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Kutu(
                ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Text('${e.key} gün — henüz sonuçlanmış sinyal yok',
                    style: Theme.of(c).textTheme.bodySmall),
              ),
            );
          }
          final ort = (v['ortalama_getiri'] as num?)?.toDouble() ?? 0;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text('${e.key} günlük vade',
                        style: Theme.of(c).textTheme.titleMedium),
                    const Spacer(),
                    Text('${v['sinyal']} sinyal',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(
                            color: Theme.of(c).colorScheme.onSurfaceVariant)),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: [
                    _kutucuk(c, 'Kazanma', '%${tl(v['kazanma_orani'] as num?, basamak: 1)}'),
                    _kutucuk(c, 'Ortalama', yzd(ort), renk: sem.yon(ort)),
                    _kutucuk(c, 'Ort. kazanç', yzd(v['ort_kazanc'] as num?),
                        renk: sem.arti),
                    _kutucuk(c, 'Ort. kayıp', yzd(v['ort_kayip'] as num?),
                        renk: sem.eksi),
                  ]),
                  if (v['cikis_dagilimi'] != null) ...[
                    const SizedBox(height: 10),
                    Text('Çıkış: ${(v['cikis_dagilimi'] as Map).entries
                        .map((x) => '${x.key} ${x.value}').join(' · ')}',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(
                            color: Theme.of(c).colorScheme.onSurfaceVariant)),
                  ],
                ],
              ),
            ),
          );
        }),
        if (stratejiler.isNotEmpty) ...[
          const Baslik('Stratejiye göre', alt: '20 günlük vade'),
          ...stratejiler.entries.map((e) {
            final v = e.value as Map<String, dynamic>;
            final ort = (v['ortalama_getiri'] as num?)?.toDouble() ?? 0;
            // KAPATILAN strateji burada işaretsiz kalırsa kullanıcı onu
            // hâlâ çalışıyor sanıyor — ve karnede en iyi görünen
            // strateji kapatılmış olabilir.
            final kapali = kapaliListe.contains(e.key);
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Kutu(
                ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(children: [
                  Expanded(
                    child: Row(children: [
                      Flexible(
                        child: Text(e.key,
                            style: Theme.of(c).textTheme.titleMedium?.copyWith(
                                fontSize: 15,
                                color: kapali ? Renk.metinSonuk : null)),
                      ),
                      if (kapali) ...[
                        const SizedBox(width: 8),
                        const Rozet('KAPALI', renk: Renk.metinSolgun),
                      ],
                    ]),
                  ),
                  Text('${v['sinyal']} sinyal · %${tl(v['kazanma_orani'] as num?, basamak: 1)}',
                      style: Theme.of(c).textTheme.bodySmall),
                  const SizedBox(width: 10),
                  Text(yzd(ort),
                      style: TextStyle(fontWeight: FontWeight.w700, color: sem.yon(ort))),
                ]),
              ),
            );
          }),
        ],
        const Baslik('Canlı vs backtest', alt: 'kenar aşınıyor mu?'),
        ...kayma.map((x) {
          final m = x as Map<String, dynamic>;
          if (m['yeterli_mi'] != true) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Kutu(
                ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text('${m['strateji']}',
                          style: Theme.of(c).textTheme.titleMedium
                              ?.copyWith(fontSize: 15)),
                      if (kapaliListe.contains('${m['strateji']}')) ...[
                        const SizedBox(width: 8),
                        const Rozet('KAPALI', renk: Renk.metinSolgun),
                      ],
                    ]),
                    const SizedBox(height: 4),
                    Text('${m['not']}',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.4)),
                  ],
                ),
              ),
            );
          }
          final durum = '${m['durum']}';
          final renk = durum.contains('İYİ')
              ? sem.arti : durum.contains('KÖTÜ') ? sem.eksi : sem.uyari;
          // Rozet KISA etiket için: "TUT", "KIRILIM" gibi. Sunucudan gelen
          // `durum` ise tam cümle ("canlı DAHA KÖTÜ — beklenen aralığın
          // altında") ve rozete basılınca satırı taşırıyordu. Rozet
          // taranmak, cümle anlaşılmak için — ikisi ayrı satırda.
          final kisaDurum = durum.contains('İYİ')
              ? 'İYİ' : durum.contains('KÖTÜ') ? 'KÖTÜ' : 'BEKLENEN';
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text('${m['strateji']}',
                        style: Theme.of(c).textTheme.titleMedium?.copyWith(
                            fontSize: 15,
                            color: kapaliListe.contains('${m['strateji']}')
                                ? Renk.metinSonuk : null)),
                    if (kapaliListe.contains('${m['strateji']}')) ...[
                      const SizedBox(width: 8),
                      const Rozet('KAPALI', renk: Renk.metinSolgun),
                    ],
                    const Spacer(),
                    Rozet(kisaDurum, renk: renk),
                  ]),
                  const SizedBox(height: 6),
                  Text(durum,
                      style: Theme.of(c).textTheme.bodySmall
                          ?.copyWith(color: renk, height: 1.4)),
                  const SizedBox(height: 6),
                  Text('Canlı kazanma %${tl((m['canli'] as Map)['kazanma_orani'] as num?, basamak: 1)}'
                      '  ·  backtest %${tl((m['backtest'] as Map)['kazanma_orani'] as num?, basamak: 1)}'
                      '  ·  fark ${(m['kazanma_farki'] as num?)?.toStringAsFixed(1)} puan',
                      style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.4)),
                ],
              ),
            ),
          );
        }),
        if (filtre['yeterli_mi'] == true) ...[
          // HABER SİCİLİ: haberleri hisseye eşleştiriyorduk ama
          // sonucunu hiç ölçmüyorduk. Sinyal sicilinin hemen yanında
          // duruyor çünkü aynı soruyu soruyor: bu şey işe yarıyor mu?
          const _HaberSicili(),
          const Baslik('Filtreler iş görüyor mu?'),
          Kutu(
            child: Column(
              children: [
                ...[
                  ('SMA200 üstü', 'sma200_ustu'), ('SMA200 altı', 'sma200_alti'),
                  ('Alınabilir', 'alinabilir'), ('Alınamaz', 'alinamaz'),
                ].where((e) => filtre[e.$2] != null).map((e) {
                  final v = filtre[e.$2] as Map<String, dynamic>;
                  final ort = (v['ortalama'] as num?)?.toDouble() ?? 0;
                  return Satir(e.$1, yzd(ort),
                      renk: sem.yon(ort),
                      not: '${v['n']} sinyal · kazanma %${tl(v['kazanma'] as num?, basamak: 1)}');
                }),
              ],
            ),
          ),
        ],
        if (uyarilar.isNotEmpty) ...[
          const Baslik('Bu kıyası okurken'),
          ...uyarilar.map((u) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Not('$u', ikon: Icons.info_outline_sharp),
              )),
        ],
      ],
    );
  }

  Widget _kutucuk(BuildContext c, String etiket, String deger, {Color? renk}) =>
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(etiket,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    fontSize: 10.5,
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 2),
            Text(deger,
                style: TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 13, color: renk,
                    fontFeatures: const [FontFeature.tabularFigures()])),
          ],
        ),
      );
}


// ── haber sicili ───────────────────────────────────────────────────────────

/// Haber fiyatı gerçekten hareket ettiriyor mu?
///
/// Muhtemel cevap: çoğu haber hiçbir şey yapmıyor. Ve bunu GÖRMEK,
/// habere göre alım yapma dürtüsünü kesiyor — sistemin bütün mimarisi
/// zaten bunun üstüne kurulu.
class _HaberSicili extends StatefulWidget {
  const _HaberSicili();
  @override
  State<_HaberSicili> createState() => _HaberSiciliDurum();
}

class _HaberSiciliDurum extends State<_HaberSicili> {
  Map<String, dynamic>? _v;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    try {
      final r = await depo.api.haberSicil();
      if (mounted) setState(() => _v = r);
    } catch (_) {
      // Sessiz: ölçüm gelmemesi karneyi bozmamalı.
    }
  }

  @override
  Widget build(BuildContext c) {
    final v = _v;
    if (v == null) return const SizedBox.shrink();
    final sem = Sem(c);
    final kategoriler = (v['kategoriler'] ?? {}) as Map<String, dynamic>;

    if (kategoriler.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Baslik('Haber işe yarıyor mu?',
              alt: 'haberden sonraki hareket, piyasadan arındırılmış'),
          Kutu(
            ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Text('${v['not'] ?? 'Henüz yeterli haber birikmedi.'}',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),
          ),
        ],
      );
    }

    // Kategoriler 20 günlük etkiye göre sıralı: asıl merak edilen
    // hangi haber türünün gerçekten fark yarattığı.
    final sirali = kategoriler.entries.toList()
      ..sort((a, b) {
        double et(dynamic x) {
          final vd = ((x['vadeler'] ?? {}) as Map)['20'] ??
              ((x['vadeler'] ?? {}) as Map)[20];
          return ((vd?['ortalama'] ?? 0) as num).toDouble();
        }

        return et(b.value).compareTo(et(a.value));
      });

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Baslik('Haber işe yarıyor mu?',
            alt: '${v['olculen']} haber · piyasadan arındırılmış'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Not(
            'Haberden sonraki hareket, aynı günlerde PİYASANIN yaptığı '
            'hareket çıkarılarak ölçülüyor. Borsa yükselirken hissenin '
            'de yükselmesi habere bağlanamaz.',
            ikon: Icons.article_sharp, renk: sem.aksan,
          ),
        ),
        const SizedBox(height: 10),
        ...sirali.map((e) {
          final m = Map<String, dynamic>.from(e.value as Map);
          final vd = (m['vadeler'] ?? {}) as Map;
          return Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Kutu(
              ic: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(e.key,
                      style: Theme.of(c).textTheme.titleMedium
                          ?.copyWith(fontSize: 15)),
                  const SizedBox(height: 8),
                  Row(children: vd.keys.map((k) {
                    final d = Map<String, dynamic>.from(vd[k] as Map);
                    final ort = (d['ortalama'] as num?)?.toDouble() ?? 0;
                    return Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('$k gün',
                              style: Theme.of(c).textTheme.bodySmall
                                  ?.copyWith(fontSize: 10.5)),
                          Text(yzd(ort),
                              style: TextStyle(
                                  color: sem.yon(ort),
                                  fontWeight: FontWeight.w700,
                                  fontSize: 14)),
                          Text('${d['ornek']} haber',
                              style: TextStyle(
                                  color: Renk.metinSonuk, fontSize: 10)),
                        ],
                      ),
                    );
                  }).toList()),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }
}
