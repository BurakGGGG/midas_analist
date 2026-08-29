
import 'package:flutter/material.dart';

import '../parca/grafik.dart';
import '../parca/kart.dart';
import '../servis/oyun.dart';
import '../tema.dart';

/// Sanal İşlem'in dört sekmesi. Hepsi `oyun` durumundan besleniyor ve
/// hiçbiri ağ kullanmıyor — piyasa zaten telefonda.

// ══════════════════════════════════════════════════════════ PORTFÖY

class OyunPortfoy extends StatelessWidget {
  const OyunPortfoy({super.key});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return ListView(
      padding: const EdgeInsets.only(top: 6, bottom: 24),
      children: [
        if (oyun.ozkaynak.length >= 3) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('PORTFÖY DEĞERİ',
                      style: TextStyle(
                          color: OyunRenk.aksan, fontSize: 10.5,
                          letterSpacing: 1.3)),
                  const SizedBox(height: 10),
                  FiyatGrafik(
                    [
                      for (var i = 0; i < oyun.ozkaynak.length; i++)
                        {'t': 'G${i + 1}', 'd': oyun.ozkaynak[i]}
                    ],
                    yukseklik: 145,
                  ),
                ],
              ),
            ),
          ),
        ],

        const Baslik('Açık pozisyonlar'),
        if (oyun.pozisyonlar.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Kutu(
              child: Text('Pozisyonun yok. Borsa sekmesinden hisse al ya da '
                  'Analist\'in önerisine bak.',
                  style: TextStyle(color: OyunRenk.metinSolgun, height: 1.5)),
            ),
          )
        else
          ...oyun.pozisyonlar.map((p) => Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                child: _PozisyonKarti(p),
              )),

        if (oyun.kapali.isNotEmpty) ...[
          Baslik('Kapanan işlemler',
              alt: '${oyun.kapali.length} işlem · gerçekleşen '
                  '${tl(oyun.gerceklesenKar)} ₺'),
          ...oyun.kapali.reversed.map((i) => Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Kutu(
                  ic: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                  child: Row(children: [
                    Rozet(i.sebep.toUpperCase(),
                        renk: i.kar >= 0 ? sem.arti : sem.eksi),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(i.sembol,
                              style: Theme.of(c).textTheme.bodyLarge),
                          Text('${tl(i.giris)} → ${tl(i.cikis)} ₺ · '
                              '${i.adet} adet · ${i.cikisGunu - i.girisGunu} gün',
                              style: const TextStyle(
                                  color: OyunRenk.metinSonuk, fontSize: 11)),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('${i.kar >= 0 ? '+' : ''}${tl(i.kar)} ₺',
                            style: TextStyle(
                                color: sem.yon(i.kar),
                                fontWeight: FontWeight.w700)),
                        Text(yzd(i.karYuzde, basamak: 1),
                            style: TextStyle(
                                color: sem.yon(i.kar), fontSize: 11)),
                      ],
                    ),
                  ]),
                ),
              )),
        ],
      ],
    );
  }
}

class _PozisyonKarti extends StatelessWidget {
  final OyunPozisyon p;
  const _PozisyonKarti(this.p);

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final f = oyun.fiyat(p.sembol) ?? p.giris;
    final kar = (f - p.giris) * p.adet;
    final karY = p.giris > 0 ? (f / p.giris - 1) * 100 : 0.0;
    final stopUzak = f > 0 ? (f - p.stop) / f * 100 : 0.0;
    final ad = oyun.hisse(p.sembol)?.ad ?? '';

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(p.sembol, style: Theme.of(c).textTheme.titleMedium),
            const SizedBox(width: 8),
            Expanded(
              child: Text(ad,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: OyunRenk.metinSonuk, fontSize: 11)),
            ),
            Text('${tl(f)} ₺',
                style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()])),
          ]),
          const SizedBox(height: 3),
          Row(children: [
            Text('${p.adet} adet · giriş ${tl(p.giris)}',
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 11.5)),
            const Spacer(),
            Text('${kar >= 0 ? '+' : ''}${tl(kar)} ₺  '
                '${yzd(karY, basamak: 1)}',
                style: TextStyle(
                    color: sem.yon(kar), fontWeight: FontWeight.w700,
                    fontSize: 12.5)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(
                child: Text('stop ${tl(p.stop)}',
                    style: TextStyle(color: sem.eksi, fontSize: 11.5))),
            Expanded(
                child: Text('hedef ${tl(p.hedef)}',
                    textAlign: TextAlign.end,
                    style: TextStyle(color: sem.arti, fontSize: 11.5))),
          ]),
          if (stopUzak > 0 && stopUzak <= 2.5) ...[
            const SizedBox(height: 6),
            Row(children: [
              Icon(Icons.warning_amber_sharp, size: 13, color: sem.uyari),
              const SizedBox(width: 6),
              Text('stop\'a %${stopUzak.toStringAsFixed(1)} kaldı',
                  style: TextStyle(color: sem.uyari, fontSize: 11.5)),
            ]),
          ],
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
              child: _kucukDugme(c, 'SAT',
                  () => _satSor(c, p)),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: _kucukDugme(c, 'STOP ÇEK',
                  () => _stopSor(c, p, f)),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: _kucukDugme(c, 'EKLE', () => Navigator.push(c,
                  MaterialPageRoute(
                      builder: (_) => OyunAlim(kod: p.sembol)))),
            ),
          ]),
        ],
      ),
    );
  }
}

Widget _kucukDugme(BuildContext c, String etiket, VoidCallback bas) =>
    SizedBox(
      height: 32,
      child: OutlinedButton(
        onPressed: bas,
        style: OutlinedButton.styleFrom(
            padding: EdgeInsets.zero,
            foregroundColor: OyunRenk.metin,
            side: const BorderSide(color: OyunRenk.cizgiParlak),
            shape: const RoundedRectangleBorder(borderRadius: kose)),
        child: Text(etiket, style: const TextStyle(fontSize: 11)),
      ),
    );

Future<void> _satSor(BuildContext c, OyunPozisyon p) async {
  final adet = await showDialog<int>(
    context: c,
    builder: (d) => _AdetDialog(baslik: '${p.sembol} sat', azami: p.adet),
  );
  if (adet == null) return;
  final h = oyun.sat(p.sembol, adet: adet >= p.adet ? 0 : adet);
  if (h != null && c.mounted) _uyar(c, h);
}

Future<void> _stopSor(BuildContext c, OyunPozisyon p, double fiyat) async {
  final v = await showDialog<double>(
    context: c,
    builder: (d) => _StopDialog(pozisyon: p, fiyat: fiyat),
  );
  if (v == null) return;
  final h = oyun.stopCek(p.sembol, v);
  if (h != null && c.mounted) _uyar(c, h);
}

void _uyar(BuildContext c, String m) =>
    ScaffoldMessenger.of(c).showSnackBar(SnackBar(
      backgroundColor: OyunRenk.panelUst,
      content: Text(m, style: const TextStyle(color: OyunRenk.metin)),
    ));

// ══════════════════════════════════════════════════════════ BORSA

class OyunBorsa extends StatefulWidget {
  const OyunBorsa({super.key});
  @override
  State<OyunBorsa> createState() => _OyunBorsaDurum();
}

class _OyunBorsaDurum extends State<OyunBorsa> {
  String _sira = 'degisim';

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final liste = [...oyun.hisseler];
    liste.sort((a, b) {
      if (_sira == 'kod') return a.kod.compareTo(b.kod);
      final da = oyun.gunlukDegisim(a.kod) ?? 0;
      final db = oyun.gunlukDegisim(b.kod) ?? 0;
      return db.compareTo(da);
    });

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
          child: Row(children: [
            const Text('SIRALA',
                style: TextStyle(
                    color: OyunRenk.metinSonuk, fontSize: 10,
                    letterSpacing: 1.2)),
            const SizedBox(width: 10),
            _siraDugme('degisim', 'Değişim'),
            const SizedBox(width: 6),
            _siraDugme('kod', 'Kod'),
          ]),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.only(bottom: 24),
            itemCount: liste.length,
            itemBuilder: (_, i) {
              final h = liste[i];
              final f = oyun.fiyat(h.kod);
              final d = oyun.gunlukDegisim(h.kod);
              final acik = oyun.pozisyonlar.any((p) => p.sembol == h.kod);
              return InkWell(
                onTap: () => Navigator.push(c, MaterialPageRoute(
                    builder: (_) => OyunHisseEkran(kod: h.kod))),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                  decoration: const BoxDecoration(
                    border: Border(
                        bottom: BorderSide(color: OyunRenk.cizgi, width: 0.5)),
                  ),
                  child: Row(children: [
                    SizedBox(
                      width: 62,
                      child: Text(h.kod,
                          style: TextStyle(
                              fontWeight: FontWeight.w700,
                              color: acik ? OyunRenk.aksan : OyunRenk.metin)),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(h.ad,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: OyunRenk.metinSolgun, fontSize: 11.5)),
                          Text(h.sektor,
                              style: const TextStyle(
                                  color: OyunRenk.metinSonuk, fontSize: 10)),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('${tl(f)} ₺',
                            style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontFeatures: [
                                  FontFeature.tabularFigures()
                                ])),
                        Text(yzd(d, basamak: 1),
                            style: TextStyle(
                                color: sem.yon(d), fontSize: 11.5,
                                fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ]),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _siraDugme(String kod, String etiket) {
    final secili = _sira == kod;
    return InkWell(
      onTap: () => setState(() => _sira = kod),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(
          border: Border.all(
              color: secili ? OyunRenk.aksan : OyunRenk.cizgiParlak),
          color: secili ? OyunRenk.aksanKoyu : null,
        ),
        child: Text(etiket,
            style: TextStyle(
                fontSize: 10.5,
                color: secili ? OyunRenk.aksan : OyunRenk.metinSolgun)),
      ),
    );
  }
}

// ══════════════════════════════════════════════════════════ HİSSE

class OyunHisseEkran extends StatelessWidget {
  final String kod;
  const OyunHisseEkran({super.key, required this.kod});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final h = oyun.hisse(kod);
    if (h == null) {
      return const Scaffold(body: Center(child: Text('Hisse yok')));
    }
    final f = oyun.fiyat(kod);
    final d = oyun.gunlukDegisim(kod);
    final poz = oyun.pozisyonlar.where((p) => p.sembol == kod).firstOrNull;

    // GELECEĞİ GÖSTERME: grafik yalnızca bugüne kadar. Tüm seri
    // telefonda duruyor ama ilerisini çizmek oyunu bitirirdi.
    final gorunen = h.barlar.take(oyun.barIndeks + 1).toList();
    final nokta = [
      for (var i = 0; i < gorunen.length; i++)
        {'t': 'G${i - oyun.isinma + 1}', 'd': gorunen[i].kapanis}
    ];

    return Theme(
      data: temaOyun,
      child: Scaffold(
        appBar: AppBar(title: Text(kod)),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          children: [
            Text(h.ad, style: Theme.of(c).textTheme.titleMedium),
            Text(h.sektor,
                style: const TextStyle(
                    color: OyunRenk.metinSonuk, fontSize: 11)),
            const SizedBox(height: 12),
            Row(crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic, children: [
              Text('${tl(f)} ₺',
                  style: Theme.of(c).textTheme.headlineSmall),
              const SizedBox(width: 10),
              Text(yzd(d, basamak: 1),
                  style: TextStyle(
                      color: sem.yon(d), fontSize: 15,
                      fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 14),
            Kutu(child: FiyatGrafik(nokta, yukseklik: 190)),
            const SizedBox(height: 14),

            if (poz != null) ...[
              Kutu(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('POZİSYONUN',
                        style: TextStyle(
                            color: OyunRenk.aksan, fontSize: 10.5,
                            letterSpacing: 1.3)),
                    const SizedBox(height: 8),
                    Satir('Adet', '${poz.adet}'),
                    Satir('Giriş', '${tl(poz.giris)} ₺'),
                    Satir('Stop', '${tl(poz.stop)} ₺', renk: sem.eksi),
                    Satir('Hedef', '${tl(poz.hedef)} ₺', renk: sem.arti),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: _kucukDugme(c, 'SAT', () async {
                  await _satSor(c, poz);
                  if (c.mounted) Navigator.pop(c);
                })),
                const SizedBox(width: 8),
                Expanded(child: _kucukDugme(c, 'EKLE', () => Navigator.push(c,
                    MaterialPageRoute(builder: (_) => OyunAlim(kod: kod))))),
              ]),
            ] else
              SizedBox(
                width: double.infinity,
                height: 44,
                child: FilledButton(
                  onPressed: oyun.bitti ? null : () => Navigator.push(c,
                      MaterialPageRoute(builder: (_) => OyunAlim(kod: kod))),
                  style: FilledButton.styleFrom(
                      backgroundColor: OyunRenk.aksan,
                      foregroundColor: OyunRenk.zemin,
                      shape:
                          const RoundedRectangleBorder(borderRadius: kose)),
                  child: const Text('AL'),
                ),
              ),

            // Bu hisseyle ilgili haberler
            Builder(builder: (_) {
              final hb = oyun.akanHaberler
                  .where((x) => x['sembol'] == kod)
                  .take(6)
                  .toList();
              if (hb.isEmpty) return const SizedBox.shrink();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Baslik('Bu hisseyle ilgili'),
                  ...hb.map((x) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _HaberSatiri(x),
                      )),
                ],
              );
            }),
          ],
        ),
      ),
    );
  }
}

// ══════════════════════════════════════════════════════════ ANALİST

class OyunAnalist extends StatelessWidget {
  const OyunAnalist({super.key});

  @override
  Widget build(BuildContext c) {
    final bugun = oyun.bugunSinyaller;
    // Sicil: analistin verdiği sinyallerden kaçı işe yaradı.
    final sicil = oyun.analistSicili;

    return ListView(
      padding: const EdgeInsets.only(top: 6, bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('ANALİSTİN SİCİLİ',
                    style: TextStyle(
                        color: OyunRenk.aksan, fontSize: 10.5,
                        letterSpacing: 1.3)),
                const SizedBox(height: 8),
                Satir('Hedefe giden', '${sicil.hedef}',
                    renk: Sem(c).arti),
                Satir('Stopa giden', '${sicil.stop}', renk: Sem(c).eksi),
                Satir('Hâlâ açık', '${sicil.acik}'),
                if (sicil.hedef + sicil.stop > 0) ...[
                  const SizedBox(height: 4),
                  Satir('Tutturma oranı',
                      '%${sicil.oran.toStringAsFixed(0)}', kalin: true),
                ],
                const SizedBox(height: 8),
                const Text(
                    'Analist Midas\'ın gerçek stratejileriyle çalışıyor. '
                    'Her sinyali uygulamak zorunda değilsin — hangisine '
                    'güveneceğini burada öğren.',
                    style: TextStyle(
                        color: OyunRenk.metinSolgun, fontSize: 11.5,
                        height: 1.5)),
              ],
            ),
          ),
        ),

        Baslik('Bugünün sinyalleri', alt: 'gün ${oyun.gun + 1}'),
        if (bugun.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Kutu(
              child: Text('Bugün sinyal yok. Nakitte beklemek de bir '
                  'pozisyondur.',
                  style: TextStyle(color: OyunRenk.metinSolgun)),
            ),
          )
        else
          ...bugun.map((s) => Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                child: _SinyalKarti(s),
              )),
      ],
    );
  }

}

class _SinyalKarti extends StatelessWidget {
  final Map<String, dynamic> s;
  const _SinyalKarti(this.s);

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final kod = '${s['sembol']}';
    final alinabilir = s['alinabilir'] == true &&
        ((s['adet'] as num?) ?? 0) >= 1 && !oyun.bitti;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            SkorHalka(s['skor'] as num?, boyut: 36),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(kod, style: Theme.of(c).textTheme.titleMedium),
                    const SizedBox(width: 8),
                    Rozet('${s['strateji']}', renk: OyunRenk.aksan),
                  ]),
                  if ('${s['vade'] ?? ''}'.isNotEmpty)
                    Text('tipik tutma: ${s['vade']}',
                        style: const TextStyle(
                            color: OyunRenk.metinSonuk, fontSize: 11)),
                ],
              ),
            ),
            Text('${tl(oyun.fiyat(kod))} ₺',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
                child: Text('stop ${tl(s['stop'] as num?)}',
                    style: TextStyle(color: sem.eksi, fontSize: 11.5))),
            Expanded(
                child: Text('hedef ${tl(s['hedef'] as num?)}',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: sem.arti, fontSize: 11.5))),
            Expanded(
                child: Text('${s['adet']} adet',
                    textAlign: TextAlign.end,
                    style: const TextStyle(fontSize: 11.5))),
          ]),
          const SizedBox(height: 11),
          SizedBox(
            width: double.infinity,
            // 38 pikselde yazı dikey kırpılıyordu — goldene bakınca görüldü.
            height: 46,
            child: FilledButton(
              onPressed: alinabilir
                  ? () => Navigator.push(c, MaterialPageRoute(
                      builder: (_) => OyunAlim(kod: kod, oneri: s)))
                  : null,
              style: FilledButton.styleFrom(
                  backgroundColor: OyunRenk.aksan,
                  foregroundColor: OyunRenk.zemin,
                  disabledBackgroundColor: OyunRenk.panelUst,
                  disabledForegroundColor: OyunRenk.metinSonuk,
                  shape: const RoundedRectangleBorder(borderRadius: kose)),
              child: Text(alinabilir
                  ? 'BU EMRİ UYGULA'
                  : '${s['uyari'] ?? 'uygulanamaz'}',
                  maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
          ),
        ],
      ),
    );
  }
}

// ══════════════════════════════════════════════════════════ HABERLER

class OyunHaberler extends StatelessWidget {
  const OyunHaberler({super.key});

  @override
  Widget build(BuildContext c) {
    final h = oyun.akanHaberler;
    if (h.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Henüz haber yok.',
              style: TextStyle(color: OyunRenk.metinSolgun)),
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      itemCount: h.length,
      itemBuilder: (_, i) => Padding(
        padding: const EdgeInsets.only(bottom: 9),
        child: _HaberSatiri(h[i]),
      ),
    );
  }
}

class _HaberSatiri extends StatelessWidget {
  final Map<String, dynamic> h;
  const _HaberSatiri(this.h);

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final yon = ((h['yon'] ?? 0) as num).toInt();
    final sembol = '${h['sembol'] ?? ''}';
    final gun = ((h['gun'] ?? 0) as num).toInt();
    final renk = yon > 0 ? sem.arti : sem.eksi;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: OyunRenk.panel,
        border: Border(
          left: BorderSide(color: renk, width: 3),
          top: const BorderSide(color: OyunRenk.cizgi),
          right: const BorderSide(color: OyunRenk.cizgi),
          bottom: const BorderSide(color: OyunRenk.cizgi),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('GÜN ${gun + 1}',
                style: const TextStyle(
                    color: OyunRenk.metinSonuk, fontSize: 9.5,
                    letterSpacing: 1.1)),
            if (sembol.isNotEmpty) ...[
              const SizedBox(width: 8),
              Rozet(sembol, renk: OyunRenk.aksan),
            ],
            const Spacer(),
            Icon(yon > 0 ? Icons.trending_up_sharp : Icons.trending_down_sharp,
                size: 14, color: renk),
          ]),
          const SizedBox(height: 7),
          Text('${h['baslik']}',
              style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.45)),
        ],
      ),
    );
  }
}

// ══════════════════════════════════════════════════════════ ALIM

class OyunAlim extends StatefulWidget {
  final String kod;
  final Map<String, dynamic>? oneri;
  const OyunAlim({super.key, required this.kod, this.oneri});

  @override
  State<OyunAlim> createState() => _OyunAlimDurum();
}

class _OyunAlimDurum extends State<OyunAlim> {
  final _adet = TextEditingController();
  final _stop = TextEditingController();
  final _hedef = TextEditingController();
  String? _hata;

  /// Sistemin kendi kuralı: stop 2 ATR altı, hedef 3,5 ATR üstü.
  /// ATR yerine son 14 günün ortalama gerçek aralığı hesaplanıyor —
  /// oyun barları elimizde, sunucuya sormaya gerek yok.
  double get _atr {
    final h = oyun.hisse(widget.kod);
    if (h == null) return 0;
    final son = oyun.barIndeks;
    var toplam = 0.0;
    var n = 0;
    for (var i = son - 13; i <= son; i++) {
      if (i <= 0 || i >= h.barlar.length) continue;
      final b = h.barlar[i];
      final onceki = h.barlar[i - 1].kapanis;
      final gercek = [
        b.yuksek - b.dusuk,
        (b.yuksek - onceki).abs(),
        (b.dusuk - onceki).abs(),
      ].reduce((a, x) => a > x ? a : x);
      toplam += gercek;
      n++;
    }
    return n > 0 ? toplam / n : 0;
  }

  @override
  void initState() {
    super.initState();
    final o = widget.oneri;
    final f = oyun.fiyat(widget.kod) ?? 0;
    if (o != null) {
      _stop.text = _ond((o['stop'] as num?)?.toDouble() ?? 0);
      _hedef.text = _ond((o['hedef'] as num?)?.toDouble() ?? 0);
      _adet.text = '${(o['adet'] as num?)?.toInt() ?? 1}';
    } else if (f > 0 && _atr > 0) {
      _stop.text = _ond(f - 2 * _atr);
      _hedef.text = _ond(f + 3.5 * _atr);
      _adet.text = '${_onerilenAdet(f, f - 2 * _atr)}';
    }
  }

  /// Adet = risk bütçesi ÷ hisse başına risk. Sermayenin %1,5'i.
  int _onerilenAdet(double fiyat, double stop) {
    if (fiyat <= 0 || stop <= 0 || stop >= fiyat) return 0;
    final butce = oyun.baslangicSermaye * 0.015;
    final riskten = butce / (fiyat - stop);
    final nakitten = oyun.nakit / fiyat;
    final tavandan = (oyun.baslangicSermaye * 0.35) / fiyat;
    return [riskten, nakitten, tavandan]
        .reduce((a, b) => a < b ? a : b)
        .floor()
        .clamp(0, 999999);
  }

  @override
  void dispose() {
    for (final x in [_adet, _stop, _hedef]) {
      x.dispose();
    }
    super.dispose();
  }

  double? _oku(TextEditingController k) =>
      double.tryParse(k.text.trim().replaceAll(',', '.'));

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final h = oyun.hisse(widget.kod);
    final f = oyun.fiyat(widget.kod);
    final adet = int.tryParse(_adet.text.trim()) ?? 0;
    final stop = _oku(_stop);
    final hedef = _oku(_hedef);
    final kaymali = f == null ? null : f * (1 + oyun.kaymaBp / 10000.0);

    return Theme(
      data: temaOyun,
      child: Scaffold(
        appBar: AppBar(title: Text('${widget.kod} al')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
          children: [
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(h?.ad ?? widget.kod,
                      style: Theme.of(c).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Satir('Kapanış', '${tl(f)} ₺'),
                  if (oyun.kaymaBp > 0) ...[
                    Satir('Kayma (%${(oyun.kaymaBp / 100).toStringAsFixed(2)})',
                        '+${tl((kaymali ?? 0) - (f ?? 0))} ₺'),
                    Satir('Girişin', '${tl(kaymali)} ₺', kalin: true),
                  ],
                  Satir('ATR (günlük tipik hareket)', '${tl(_atr)} ₺'),
                  Satir('Nakit', '${tl(oyun.nakit)} ₺'),
                ],
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _stop,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                  labelText: 'Stop', helperText: 'Önerilen: giriş − 2 ATR'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 11),
            TextField(
              controller: _hedef,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                  labelText: 'Hedef', helperText: 'Önerilen: giriş + 3,5 ATR'),
              onChanged: (_) => setState(() {}),
            ),
            if (kaymali != null && stop != null && hedef != null &&
                stop < kaymali && hedef > kaymali) ...[
              const SizedBox(height: 6),
              Text('ödül/risk: '
                  '${((hedef - kaymali) / (kaymali - stop)).toStringAsFixed(1)}',
                  style: const TextStyle(color: OyunRenk.aksan, fontSize: 12)),
            ],
            const SizedBox(height: 11),
            TextField(
              controller: _adet,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Adet'),
              onChanged: (_) => setState(() {}),
            ),
            if (kaymali != null && adet > 0) ...[
              const SizedBox(height: 6),
              Text('tutar ${tl(adet * kaymali)} ₺'
                  '${stop != null && stop < kaymali
                      ? '  ·  riskin ${tl(adet * (kaymali - stop))} ₺' : ''}',
                  style: const TextStyle(
                      color: OyunRenk.metinSolgun, fontSize: 11.5)),
            ],
            if (_hata != null) ...[
              const SizedBox(height: 12),
              Not(_hata!, ikon: Icons.error_outline_sharp, renk: sem.eksi),
            ],
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              height: 46,
              child: FilledButton(
                onPressed: () {
                  final h = oyun.al(widget.kod, adet, stop ?? 0, hedef ?? 0);
                  if (h != null) {
                    setState(() => _hata = h);
                    return;
                  }
                  Navigator.pop(context);
                },
                style: FilledButton.styleFrom(
                    backgroundColor: OyunRenk.aksan,
                    foregroundColor: OyunRenk.zemin,
                    shape: const RoundedRectangleBorder(borderRadius: kose)),
                child: const Text('AL'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _ond(double v) => v.toStringAsFixed(2).replaceAll('.', ',');

// ══════════════════════════════════════════════════════════ diyaloglar

class _AdetDialog extends StatefulWidget {
  final String baslik;
  final int azami;
  const _AdetDialog({required this.baslik, required this.azami});

  @override
  State<_AdetDialog> createState() => _AdetDialogDurum();
}

class _AdetDialogDurum extends State<_AdetDialog> {
  late double _adet = widget.azami.toDouble();

  @override
  Widget build(BuildContext c) => AlertDialog(
        backgroundColor: OyunRenk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: Text(widget.baslik,
            style: const TextStyle(color: OyunRenk.metin)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${_adet.round()} / ${widget.azami} adet',
                style: const TextStyle(
                    color: OyunRenk.aksan, fontSize: 16,
                    fontWeight: FontWeight.w700)),
            if (widget.azami > 1)
              Slider(
                value: _adet, min: 1, max: widget.azami.toDouble(),
                divisions: widget.azami - 1,
                activeColor: OyunRenk.aksan,
                onChanged: (v) => setState(() => _adet = v),
              ),
            Text(
                _adet.round() >= widget.azami
                    ? 'Pozisyonun tamamı kapanacak.'
                    : 'Kalan ${widget.azami - _adet.round()} adet açık kalacak.',
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 11.5)),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(c, _adet.round()),
              child: const Text('SAT')),
        ],
      );
}

class _StopDialog extends StatefulWidget {
  final OyunPozisyon pozisyon;
  final double fiyat;
  const _StopDialog({required this.pozisyon, required this.fiyat});

  @override
  State<_StopDialog> createState() => _StopDialogDurum();
}

class _StopDialogDurum extends State<_StopDialog> {
  late final _alan =
      TextEditingController(text: _ond(widget.pozisyon.stop));

  @override
  void dispose() {
    _alan.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) => AlertDialog(
        backgroundColor: OyunRenk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: Text('${widget.pozisyon.sembol} stop',
            style: const TextStyle(color: OyunRenk.metin)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _alan,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Yeni stop'),
            ),
            const SizedBox(height: 10),
            Text('Şu an ${tl(widget.fiyat)} ₺ · '
                'giriş ${tl(widget.pozisyon.giris)} ₺',
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 11.5)),
            const SizedBox(height: 6),
            const Text(
                'Stop yalnızca YUKARI çekilebilir. Aşağı çekmek kaybı '
                'büyütür ve bir kere yapan bir daha yapar.',
                style: TextStyle(
                    color: OyunRenk.aksan, fontSize: 11.5, height: 1.45)),
            if (widget.pozisyon.giris > widget.pozisyon.stop) ...[
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: () =>
                    _alan.text = _ond(widget.pozisyon.giris),
                style: OutlinedButton.styleFrom(
                    foregroundColor: OyunRenk.metin,
                    side: const BorderSide(color: OyunRenk.cizgiParlak),
                    shape: const RoundedRectangleBorder(borderRadius: kose)),
                child: const Text('BAŞABAŞA ÇEK'),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c),
              child: const Text('Vazgeç')),
          TextButton(
            onPressed: () => Navigator.pop(
                c, double.tryParse(_alan.text.trim().replaceAll(',', '.'))),
            child: const Text('ÇEK'),
          ),
        ],
      );
}
