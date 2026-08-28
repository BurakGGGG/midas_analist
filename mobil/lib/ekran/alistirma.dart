import 'package:flutter/material.dart';

import '../servis/alistirma.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'ders.dart';

/// Alıştırma kum havuzu ekranı.
///
/// Üç hâli var ve sırayla açılıyor:
///   1. Mod seçimi   — geçmiş mi, canlı mı
///   2. Rehberli görevler — sırayla, her biri bir dersi uygulatıyor
///   3. Serbest mod  — görevler bitince açılan sanal işlem defteri
///
/// Görev kartı listenin ÜSTÜNDE duruyor: sıradaki adım her zaman ilk
/// görülen şey olmalı, yoksa kullanıcı serbest moda kayıp öğrenmeden
/// işlem yapmaya başlar.
class AlistirmaEkran extends StatefulWidget {
  const AlistirmaEkran({super.key});
  @override
  State<AlistirmaEkran> createState() => _AlistirmaDurum();
}

class _AlistirmaDurum extends State<AlistirmaEkran> {
  List<dynamic> _gorevler = [];
  Object? _hata;
  bool _mesgul = false;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    try {
      final r = await depo.api.alistirmaGorevler();
      if (mounted) setState(() => _gorevler = (r['gorevler'] ?? []) as List);
    } catch (e) {
      if (mounted) setState(() => _hata = e);
    }
  }

  Map<String, dynamic>? get _siradaki {
    for (final g in _gorevler) {
      final m = Map<String, dynamic>.from(g as Map);
      if (!kum.bitenGorevler.contains('${m['kod']}')) return m;
    }
    return null;
  }

  Future<void> _calistir(Future<void> Function() is_) async {
    setState(() => _mesgul = true);
    try {
      await is_();
    } on ApiHata catch (e) {
      if (mounted) _uyar(e.oneri ?? e.mesaj);
    } catch (e) {
      if (mounted) _uyar('$e');
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  void _uyar(String m) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext c) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alıştırma'),
        actions: [
          if (kum.basladi)
            IconButton(
              icon: const Icon(Icons.restart_alt_sharp),
              tooltip: 'Sıfırla',
              onPressed: _mesgul ? null : _sifirlaSor,
            ),
        ],
      ),
      body: ListenableBuilder(
        listenable: kum,
        builder: (_, __) => _hata != null && _gorevler.isEmpty
            ? HataGorunum(_hata!, tekrar: _getir)
            : !kum.basladi
                ? _ModSecimi(baslat: (m, t) => _calistir(() => kum.basla(m, t)))
                : _kumHavuzu(c),
      ),
    );
  }

  // ── kum havuzu görünümü ──────────────────────────────────────────────────

  Widget _kumHavuzu(BuildContext c) {
    final sem = Sem(c);
    final g = _siradaki;
    return ListView(
      padding: const EdgeInsets.only(top: 12, bottom: 28),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _ozet(c, sem),
        ),
        if (g != null) ...[
          const Baslik('Sıradaki görev'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _GorevKarti(
              gorev: g,
              sira: kum.bitenGorevler.length + 1,
              toplam: _gorevler.length,
              bitir: () => _calistir(() => kum.gorevBitir('${g['kod']}')),
              alimIste: _alimSayfasi,
              ilerletIste: _ilerlet,
            ),
          ),
        ] else ...[
          const Baslik('Serbest mod'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Not(
              'Görevlerin bitti. Artık istediğin gibi dene — sanal para, '
              'gerçek fiyat, gerçek kurallar.',
              ikon: Icons.check_circle_outline_sharp, renk: sem.arti,
            ),
          ),
        ],

        const Baslik('Açık pozisyonlar'),
        if (kum.pozisyonlar.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Kutu(
              child: Text('Henüz pozisyon yok.',
                  style: Theme.of(c).textTheme.bodyMedium
                      ?.copyWith(color: Renk.metinSolgun)),
            ),
          )
        else
          ...kum.pozisyonlar.map((p) => Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                child: _pozisyonKarti(c, sem, p),
              )),

        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
          child: Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _mesgul ? null : _alimSayfasi,
                icon: const Icon(Icons.add_sharp, size: 18),
                label: const Text('YENİ ALIM'),
              ),
            ),
            if (kum.gecmisModu) ...[
              const SizedBox(width: 9),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _mesgul ? null : _ilerlet,
                  icon: const Icon(Icons.skip_next_sharp, size: 18),
                  label: const Text('SONRAKİ GÜN'),
                ),
              ),
            ],
          ]),
        ),

        if (kum.kapali.isNotEmpty) ...[
          const Baslik('Kapanan işlemler'),
          ...kum.kapali.reversed.map((i) => Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                child: _kapaliKarti(c, sem, i),
              )),
        ],
      ],
    );
  }

  Widget _ozet(BuildContext c, Sem sem) {
    final kar = kum.gerceklesenKar;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('SANAL BAKİYE',
                style: Theme.of(c).textTheme.labelSmall
                    ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
            const Spacer(),
            Rozet(kum.gecmisModu ? 'GEÇMİŞ' : 'CANLI'),
          ]),
          const SizedBox(height: 8),
          Text('${tl(kum.bakiye)} ₺',
              style: Theme.of(c).textTheme.headlineSmall),
          const SizedBox(height: 10),
          Satir('Pozisyonda', '${tl(kum.maliyetToplam)} ₺'),
          Satir('Gerçekleşen kâr/zarar', '${kar >= 0 ? '+' : ''}${tl(kar)} ₺',
              renk: sem.yon(kar)),
          if (kum.gecmisModu) Satir('Simülasyon tarihi', kum.tarih),
        ],
      ),
    );
  }

  Widget _pozisyonKarti(BuildContext c, Sem sem, KumPozisyon p) => Kutu(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Text(p.sembol,
                  style: Theme.of(c).textTheme.titleMedium),
              const Spacer(),
              Text('${p.adet} adet · ${tl(p.maliyet)} ₺',
                  style: Theme.of(c).textTheme.bodySmall),
            ]),
            const SizedBox(height: 8),
            Satir('Giriş', '${tl(p.giris)} ₺'),
            Satir('Stop', '${tl(p.stop)} ₺', renk: sem.eksi),
            Satir('Hedef', '${tl(p.hedef)} ₺', renk: sem.arti),
            Satir('Riskin', '${tl(p.riskTl)} ₺'),
          ],
        ),
      );

  Widget _kapaliKarti(BuildContext c, Sem sem, KumIslem i) => Kutu(
        child: Row(children: [
          Rozet(i.sebep.toUpperCase(),
              renk: i.sebep == 'hedef' ? sem.arti : sem.eksi),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(i.sembol, style: Theme.of(c).textTheme.bodyLarge),
                Text('${tl(i.giris)} → ${tl(i.cikis)} ₺ · ${i.adet} adet',
                    style: Theme.of(c).textTheme.bodySmall
                        ?.copyWith(color: Renk.metinSolgun)),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('${i.kar >= 0 ? '+' : ''}${tl(i.kar)} ₺',
                  style: Theme.of(c).textTheme.bodyLarge
                      ?.copyWith(color: sem.yon(i.kar))),
              Text('${i.karYuzde >= 0 ? '+' : ''}'
                  '${i.karYuzde.toStringAsFixed(1)}%',
                  style: Theme.of(c).textTheme.bodySmall
                      ?.copyWith(color: sem.yon(i.kar))),
            ],
          ),
        ]),
      );

  // ── eylemler ─────────────────────────────────────────────────────────────

  Future<void> _ilerlet() => _calistir(() async {
        final r = await kum.ilerlet();
        final c = (r['cikislar'] ?? []) as List;
        if (!mounted) return;
        if (c.isEmpty) {
          _uyar('${r['tarih']} — pozisyonlarda değişiklik yok');
        } else {
          final s = c.map((x) => '${x['sembol']} ${x['sebep']}').join(', ');
          _uyar('${r['tarih']} — $s');
        }
      });

  Future<void> _alimSayfasi() async {
    final ok = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => const KumAlimEkran()));
    if (ok == true && mounted) setState(() {});
  }

  Future<void> _sifirlaSor() async {
    final onay = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('Alıştırmayı sıfırla'),
        content: const Text(
            'Sanal bakiye, pozisyonlar, kapanan işlemler ve görev '
            'ilerlemen silinecek.\n\n'
            'Gerçek portföyün ve karar defterin etkilenmez.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(d, true),
              child: const Text('Sıfırla')),
        ],
      ),
    );
    if (onay == true) await _calistir(kum.sifirla);
  }
}

// ── mod seçimi ─────────────────────────────────────────────────────────────

class _ModSecimi extends StatelessWidget {
  final void Function(String mod, String tarih) baslat;
  const _ModSecimi({required this.baslat});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final bugun = DateTime.now();
    String iso(DateTime d) =>
        '${d.year}-${d.month.toString().padLeft(2, '0')}-'
        '${d.day.toString().padLeft(2, '0')}';

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
      children: [
        Not(
          'Sanal 10.000 ₺ ile işlem yapacaksın. Gerçek portföyüne, karar '
          'defterine ve sicilinize hiç dokunmaz — istediğin zaman sıfırlarsın.',
          ikon: Icons.science_sharp, renk: sem.aksan,
        ),
        const SizedBox(height: 16),
        Text('Nasıl çalışsın?', style: Theme.of(c).textTheme.titleMedium),
        const SizedBox(height: 12),

        Kutu(
          tikla: () => baslat('gecmis',
              iso(bugun.subtract(const Duration(days: 120)))),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.fast_forward_sharp, size: 19, color: sem.aksan),
                const SizedBox(width: 10),
                Text('Geçmiş modu',
                    style: Theme.of(c).textTheme.titleMedium
                        ?.copyWith(color: sem.aksan)),
              ]),
              const SizedBox(height: 8),
              Text(
                  '4 ay öncesine gidersin, alım yaparsın, "sonraki gün" '
                  'düğmesiyle ilerlersin. 20 günlük sonucu 20 saniyede '
                  'görürsün.\n\nÖğrenmek için en hızlı yol.',
                  style: Theme.of(c).textTheme.bodyMedium
                      ?.copyWith(height: 1.55)),
            ],
          ),
        ),
        const SizedBox(height: 10),

        Kutu(
          tikla: () => baslat('canli', iso(bugun)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                const Icon(Icons.today_sharp, size: 19),
                const SizedBox(width: 10),
                Text('Canlı mod', style: Theme.of(c).textTheme.titleMedium),
              ]),
              const SizedBox(height: 8),
              Text(
                  'Bugünün gerçek fiyatlarından alırsın, sonucu gerçek '
                  'günlerde görürsün.\n\nDaha gerçekçi ama yavaş: bir stopun '
                  'çalıştığını görmen haftalar alabilir.',
                  style: Theme.of(c).textTheme.bodyMedium
                      ?.copyWith(height: 1.55)),
            ],
          ),
        ),
      ],
    );
  }
}

// ── görev kartı ────────────────────────────────────────────────────────────

class _GorevKarti extends StatefulWidget {
  final Map<String, dynamic> gorev;
  final int sira, toplam;
  final VoidCallback bitir;
  final VoidCallback alimIste;
  final VoidCallback ilerletIste;

  const _GorevKarti({
    required this.gorev, required this.sira, required this.toplam,
    required this.bitir, required this.alimIste, required this.ilerletIste,
  });

  @override
  State<_GorevKarti> createState() => _GorevKartiDurum();
}

class _GorevKartiDurum extends State<_GorevKarti> {
  final _cevap = TextEditingController();
  int? _secim;
  bool _dogruMu = false;
  String? _geriBildirim;

  @override
  void dispose() {
    _cevap.dispose();
    super.dispose();
  }

  void _kontrol() {
    final g = widget.gorev;
    final tur = '${g['tur']}';
    bool dogru = false;

    if (tur == 'secim') {
      dogru = _secim == (g['dogru'] as num?)?.toInt();
    } else if (tur == 'sayi') {
      final v = double.tryParse(_cevap.text.trim().replaceAll(',', '.'));
      final beklenen = (g['dogru'] as num?)?.toDouble() ?? 0;
      final tol = (g['tolerans'] as num?)?.toDouble() ?? 0;
      dogru = v != null && (v - beklenen).abs() <= tol;
    }

    setState(() {
      _dogruMu = dogru;
      _geriBildirim = dogru
          ? '${g['aciklama']}'
          : 'Henüz değil. ${g['ipucu'] ?? ''}'.trim();
    });
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final g = widget.gorev;
    final tur = '${g['tur']}';
    final ders = '${g['ders'] ?? ''}';

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('GÖREV ${widget.sira}/${widget.toplam}',
                style: Theme.of(c).textTheme.labelSmall
                    ?.copyWith(color: sem.aksan, letterSpacing: 1.2)),
            const Spacer(),
            if (ders.startsWith('d'))
              InkWell(
                onTap: () => Navigator.push(c,
                    MaterialPageRoute(builder: (_) => DersEkran(ders))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.school_sharp, size: 14, color: sem.aksan),
                  const SizedBox(width: 5),
                  Text('dersi', style: Theme.of(c).textTheme.bodySmall
                      ?.copyWith(color: sem.aksan)),
                ]),
              ),
          ]),
          const SizedBox(height: 8),
          Text('${g['baslik']}', style: Theme.of(c).textTheme.titleMedium),
          const SizedBox(height: 10),
          Text('${g['anlatim']}',
              style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.6)),

          if ('${g['soru'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(height: 1, color: Renk.cizgi),
            const SizedBox(height: 14),
            Text('${g['soru']}',
                style: Theme.of(c).textTheme.bodyLarge?.copyWith(height: 1.5)),
            const SizedBox(height: 12),
          ],

          if (tur == 'secim')
            // Kendi seçenek satırımız: RadioListTile hem kullanımdan
            // kalktı hem de yuvarlak işaretiyle "sıfır yuvarlaklık"
            // kuralına aykırıydı.
            ...List.generate(((g['secenekler'] ?? []) as List).length, (i) {
              final sec = '${(g['secenekler'] as List)[i]}';
              final secili = _secim == i;
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: InkWell(
                  onTap: _dogruMu ? null : () => setState(() => _secim = i),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 16, height: 16,
                        margin: const EdgeInsets.only(top: 3),
                        decoration: BoxDecoration(
                          color: secili ? sem.aksan : Colors.transparent,
                          border: Border.all(
                              color: secili ? sem.aksan : Renk.cizgiParlak,
                              width: 1.6),
                        ),
                      ),
                      const SizedBox(width: 11),
                      Expanded(
                        child: Text(sec,
                            style: Theme.of(c).textTheme.bodyMedium
                                ?.copyWith(height: 1.45)),
                      ),
                    ],
                  ),
                ),
              );
            })
          else if (tur == 'sayi')
            TextField(
              controller: _cevap,
              enabled: !_dogruMu,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                  labelText: 'Cevabın',
                  suffixText: '${g['birim'] ?? ''}'),
            ),

          if (_geriBildirim != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color: (_dogruMu ? sem.arti : sem.uyari).withValues(alpha: 0.08),
                borderRadius: kose,
                border: Border.all(
                    color: (_dogruMu ? sem.arti : sem.uyari)
                        .withValues(alpha: 0.35)),
              ),
              child: Text(_geriBildirim!,
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.6)),
            ),
          ],

          const SizedBox(height: 14),
          if (tur == 'islem')
            SizedBox(width: double.infinity,
                child: FilledButton(
                    onPressed: widget.alimIste,
                    child: const Text('ALIM YAP')))
          else if (tur == 'ilerlet')
            SizedBox(width: double.infinity,
                child: FilledButton(
                    onPressed: widget.ilerletIste,
                    child: const Text('GÜNLERİ İLERLET')))
          else if (!_dogruMu)
            SizedBox(width: double.infinity,
                child: FilledButton(
                    onPressed: _kontrol, child: const Text('KONTROL ET'))),

          if (_dogruMu || tur == 'islem' || tur == 'ilerlet') ...[
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: widget.bitir,
                child: const Text('SONRAKİ GÖREV'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ── kum havuzunda alım ─────────────────────────────────────────────────────

/// Sanal alım ekranı.
///
/// Gerçek alım ekranından (alim.dart) FARKI: orası "Midas'ta aldım,
/// kaydediyorum" der; burası öğretir. Adet önerisini gösteriyor ama
/// ZORLAMIYOR — kullanıcı kendi sayısını girebilmeli, yoksa hesabı
/// öğrenmez, sadece kabul eder.
class KumAlimEkran extends StatefulWidget {
  const KumAlimEkran({super.key});
  @override
  State<KumAlimEkran> createState() => _KumAlimDurum();
}

class _KumAlimDurum extends State<KumAlimEkran> {
  final _sembol = TextEditingController();
  final _adet = TextEditingController();
  final _stop = TextEditingController();
  final _hedef = TextEditingController();

  Map<String, dynamic>? _bar;
  Map<String, dynamic>? _oneri;
  bool _mesgul = false;
  String? _hata;

  @override
  void dispose() {
    for (final x in [_sembol, _adet, _stop, _hedef]) {
      x.dispose();
    }
    super.dispose();
  }

  double? get _fiyat => (_bar?['kapanis'] as num?)?.toDouble();
  double? get _atr => (_bar?['atr'] as num?)?.toDouble();

  Future<void> _fiyatGetir() async {
    final sem = _sembol.text.trim().toUpperCase();
    if (sem.isEmpty) return;
    setState(() { _mesgul = true; _hata = null; _oneri = null; });
    try {
      final r = await depo.api.alistirmaGun(sem,
          tarih: kum.gecmisModu ? kum.tarih : null);
      if (!mounted) return;
      setState(() {
        _bar = r;
        // Stop önerisi 2 ATR: sistemin kendi kuralı. Kullanıcı
        // değiştirebilir ama başlangıç noktası doğru olsun.
        final a = (r['atr'] as num?)?.toDouble() ?? 0;
        final f = (r['kapanis'] as num?)?.toDouble() ?? 0;
        if (a > 0 && f > 0) {
          _stop.text = (f - 2 * a).toStringAsFixed(2);
          _hedef.text = (f + 3.5 * a).toStringAsFixed(2);
        }
      });
      await _adetOner();
    } on ApiHata catch (e) {
      if (mounted) setState(() => _hata = e.oneri ?? e.mesaj);
    } catch (e) {
      if (mounted) setState(() => _hata = '$e');
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  Future<void> _adetOner() async {
    final f = _fiyat;
    final s = double.tryParse(_stop.text.trim().replaceAll(',', '.'));
    if (f == null || s == null) return;
    try {
      final r = await depo.api.alistirmaAdet(kum.bakiye, f, s);
      if (mounted) {
        setState(() => _oneri = r);
        if (_adet.text.trim().isEmpty) {
          _adet.text = '${(r['adet'] as num?)?.toInt() ?? 0}';
        }
      }
    } catch (_) {}
  }

  Future<void> _kaydet() async {
    final f = _fiyat;
    if (f == null) {
      setState(() => _hata = 'Önce fiyatı getir.');
      return;
    }
    final adet = int.tryParse(_adet.text.trim()) ?? 0;
    final stop = double.tryParse(_stop.text.trim().replaceAll(',', '.')) ?? 0;
    final hedef = double.tryParse(_hedef.text.trim().replaceAll(',', '.')) ?? 0;

    final hata = await kum.al(KumPozisyon(
      sembol: _sembol.text.trim().toUpperCase(),
      adet: adet, giris: f, stop: stop, hedef: hedef,
      tarih: kum.tarih,
    ));
    if (!mounted) return;
    if (hata != null) {
      setState(() => _hata = hata);
      return;
    }
    Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final tavan = _bar?['tavan_mi'] == true;
    return Scaffold(
      appBar: AppBar(title: const Text('Sanal alım')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
        children: [
          Row(children: [
            Expanded(
              child: TextField(
                controller: _sembol,
                textCapitalization: TextCapitalization.characters,
                decoration: const InputDecoration(labelText: 'Hisse (örn. THYAO)'),
                onSubmitted: (_) => _fiyatGetir(),
              ),
            ),
            const SizedBox(width: 9),
            OutlinedButton(
              onPressed: _mesgul ? null : _fiyatGetir,
              child: const Text('GETİR'),
            ),
          ]),

          if (_bar != null) ...[
            const SizedBox(height: 14),
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Satir('Tarih', '${_bar!['tarih']}'),
                  Satir('Kapanış', '${tl(_fiyat)} ₺'),
                  Satir('ATR (günlük tipik hareket)', '${tl(_atr)} ₺'),
                ],
              ),
            ),
            if (tavan) ...[
              const SizedBox(height: 10),
              Not(
                  'Bu hisse tavana yakın açmış. Gerçekte tavanda satıcı '
                  'yoktur — emir girsen de gerçekleşmez.',
                  ikon: Icons.block_sharp, renk: sem.eksi),
            ],
          ],

          const SizedBox(height: 14),
          TextField(
            controller: _stop,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Stop', helperText: 'Önerilen: giriş − 2 ATR'),
            onChanged: (_) => _adetOner(),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _hedef,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Hedef', helperText: 'Önerilen: giriş + 3,5 ATR'),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _adet,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Adet'),
          ),

          if (_oneri != null) ...[
            const SizedBox(height: 12),
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SİSTEMİN HESABI',
                      style: Theme.of(c).textTheme.labelSmall
                          ?.copyWith(color: sem.aksan, letterSpacing: 1.2)),
                  const SizedBox(height: 8),
                  Satir('Risk bütçesi (%1,5)',
                      '${tl(_oneri!['risk_butcesi'])} ₺'),
                  Satir('Hisse başına risk',
                      '${tl(_oneri!['hisse_basi_risk'])} ₺'),
                  Satir('Önerilen adet', '${_oneri!['adet']}'),
                  Satir('Sınırlayan', '${_oneri!['baglayici']}'),
                ],
              ),
            ),
          ],

          if (_hata != null) ...[
            const SizedBox(height: 12),
            Not(_hata!, ikon: Icons.error_outline_sharp, renk: sem.eksi),
          ],

          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _mesgul ? null : _kaydet,
              child: const Text('SANAL ALIM YAP'),
            ),
          ),
        ],
      ),
    );
  }
}
