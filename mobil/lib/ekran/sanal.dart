import 'package:flutter/material.dart';

import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../servis/sanal.dart';
import '../servis/semboller.dart';
import '../parca/grafik.dart';
import '../parca/ipucu.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Sanal İşlem — sanal parayla, gerçek fiyatlarla.
///
/// Alıştırma bölümünün yerine geçiyor. Orası bir test kâğıdıydı
/// ("3 × 92,20 kaç eder"); burası bir simülatör: tarih seçiyorsun,
/// hisse alıyorsun, günleri ilerletiyorsun, portföyün değişiyor.
///
/// Eğitim ayrı bölüm DEĞİL: alanların yanında ipucu balonu olarak
/// çıkıyor, bir kez okunuyor, `?` ile geri getirilebiliyor.
class SanalEkran extends StatefulWidget {
  const SanalEkran({super.key});
  @override
  State<SanalEkran> createState() => _SanalDurum();
}

class _SanalDurum extends State<SanalEkran> {
  bool _mesgul = false;

  @override
  void initState() {
    super.initState();
    semboller.tazele();
    if (sanal.basladi) sanal.degerle();
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
        title: const Text('Sanal İşlem'),
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline_sharp),
            tooltip: 'İpuçlarını geri getir',
            onPressed: () => _calistir(() async {
              await ipucu.hepsiniGeriGetir();
              if (mounted) _uyar('İpuçları geri geldi.');
            }),
          ),
          if (sanal.basladi)
            IconButton(
              icon: const Icon(Icons.restart_alt_sharp),
              tooltip: 'Yeniden başla',
              onPressed: _mesgul ? null : _sifirlaSor,
            ),
        ],
      ),
      body: ListenableBuilder(
        listenable: sanal,
        builder: (_, __) => sanal.basladi
            ? _ana(c)
            : _Kurulum(baslat: (tarih, sermaye) =>
                _calistir(() => sanal.basla(tarih, sermaye))),
      ),
    );
  }

  // ── ana ekran ────────────────────────────────────────────────────────────

  Widget _ana(BuildContext c) {
    final sem = Sem(c);
    return RefreshIndicator(
      onRefresh: () => _calistir(sanal.degerle),
      child: ListView(
        padding: const EdgeInsets.only(top: 12, bottom: 32),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _ozet(c, sem),
          ),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _zamanDugmeleri(c),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: const IpucuBalonu('ilerlet'),
          ),

          const Baslik('Açık pozisyonlar'),
          if (sanal.pozisyonlar.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Kutu(
                child: Text('Henüz pozisyon yok. Aşağıdan bir hisse al ya '
                    'da sistemin o günkü sinyallerinden birini uygula.',
                    style: Theme.of(c).textTheme.bodyMedium
                        ?.copyWith(color: Renk.metinSolgun, height: 1.5)),
              ),
            )
          else
            ...sanal.pozisyonlar.map((p) => Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                  child: _pozisyonKarti(c, sem, p),
                )),

          Padding(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 0),
            child: SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _mesgul ? null : () => _alimSayfasi(),
                icon: const Icon(Icons.add_sharp, size: 18),
                label: const Text('KENDİM SEÇEYİM'),
              ),
            ),
          ),

          _SinyalBolumu(
            tarih: sanal.tarih,
            sermaye: sanal.baslangicSermaye,
            uygula: (s) => _alimSayfasi(oneri: s),
          ),

          if (sanal.kapali.isNotEmpty) ...[
            const Baslik('Kapanan işlemler'),
            ...sanal.kapali.reversed.map((i) => Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
                  child: _kapaliKarti(c, sem, i),
                )),
          ],
        ],
      ),
    );
  }

  Widget _ozet(BuildContext c, Sem sem) {
    final getiri = sanal.toplamGetiriYuzde;
    final d = sanal.sonDeger;
    final gunSayisi = sanal.ozkaynak.length - 1;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(sanal.baslangicTarih,
                style: Theme.of(c).textTheme.bodySmall),
            Icon(Icons.arrow_right_alt_sharp,
                size: 16, color: Renk.metinSolgun),
            Text(sanal.tarih,
                style: Theme.of(c).textTheme.bodyMedium
                    ?.copyWith(color: sem.aksan, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text(gunSayisi > 0 ? '$gunSayisi. gün' : 'başlangıç',
                style: Theme.of(c).textTheme.bodySmall),
          ]),
          const SizedBox(height: 10),
          Row(crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic, children: [
            Text('${tl(sanal.ozkaynakSimdi)} ₺',
                style: Theme.of(c).textTheme.headlineSmall),
            const Spacer(),
            Text(yzd(getiri, basamak: 1),
                style: TextStyle(
                    color: sem.yon(getiri), fontWeight: FontWeight.w700,
                    fontSize: 16,
                    fontFeatures: const [FontFeature.tabularFigures()])),
          ]),
          const SizedBox(height: 4),
          Text('nakit ${tl(sanal.nakit)} · '
              'pozisyonda ${tl((d?['piyasa'] as num?) ?? sanal.maliyetToplam)}',
              style: Theme.of(c).textTheme.bodySmall),
          if (sanal.ozkaynak.length >= 3) ...[
            const SizedBox(height: 14),
            FiyatGrafik(sanal.ozkaynak, yukseklik: 150),
          ],
        ],
      ),
    );
  }

  // Genişlikler etiket uzunluğuna göre: eşit paylaştırıldığında
  // "+1 HAFTA" iki satıra kırılıyordu.
  Widget _zamanDugmeleri(BuildContext c) => Row(children: [
        Expanded(
          flex: 4,
          child: OutlinedButton(
            onPressed: _mesgul ? null : () => _ilerlet(1),
            child: const Text('+1 GÜN'),
          ),
        ),
        const SizedBox(width: 7),
        Expanded(
          flex: 5,
          child: OutlinedButton(
            onPressed: _mesgul ? null : () => _ilerlet(5),
            child: const Text('+1 HAFTA'),
          ),
        ),
        const SizedBox(width: 7),
        Expanded(
          flex: 8,
          child: FilledButton(
            onPressed: _mesgul || sanal.pozisyonlar.isEmpty
                ? null
                : () => _ilerlet(0),
            child: const Text('KAPANANA KADAR'),
          ),
        ),
      ]);

  Widget _pozisyonKarti(BuildContext c, Sem sem, SanalPozisyon p) {
    final satir = ((sanal.sonDeger?['satirlar'] as List?) ?? [])
        .cast<Map<String, dynamic>>()
        .where((x) => x['sembol'] == p.sembol)
        .firstOrNull;
    final fiyat = (satir?['fiyat'] as num?)?.toDouble() ?? p.giris;
    final kar = (satir?['kar'] as num?)?.toDouble() ?? 0;
    final karY = (satir?['kar_yuzde'] as num?)?.toDouble() ?? 0;
    final stopU = (satir?['stop_uzaklik'] as num?)?.toDouble();
    final ad = semboller.hisseler
        .where((s) => s.kod == p.sembol).firstOrNull?.ad ?? '';

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(p.sembol, style: Theme.of(c).textTheme.titleMedium),
            if (ad.isNotEmpty) ...[
              const SizedBox(width: 8),
              Expanded(
                child: Text(ad,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(c).textTheme.bodySmall),
              ),
            ] else
              const Spacer(),
            Text('${tl(fiyat)} ₺',
                style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()])),
          ]),
          const SizedBox(height: 3),
          Row(children: [
            Text('${p.adet} adet · giriş ${tl(p.giris)}',
                style: Theme.of(c).textTheme.bodySmall),
            const Spacer(),
            Text('${kar >= 0 ? '+' : ''}${tl(kar)} ₺  ${yzd(karY, basamak: 1)}',
                style: TextStyle(
                    color: sem.yon(kar), fontWeight: FontWeight.w700,
                    fontSize: 13)),
          ]),
          const SizedBox(height: 9),
          Row(children: [
            Expanded(
              child: Text('stop ${tl(p.stop)}',
                  style: TextStyle(color: sem.eksi, fontSize: 12)),
            ),
            Expanded(
              child: Text('hedef ${tl(p.hedef)}',
                  textAlign: TextAlign.end,
                  style: TextStyle(color: sem.arti, fontSize: 12)),
            ),
          ]),
          if (stopU != null && stopU <= 2.0) ...[
            const SizedBox(height: 7),
            Row(children: [
              Icon(Icons.warning_amber_sharp, size: 14, color: sem.uyari),
              const SizedBox(width: 6),
              Text('stop\'a %${stopU.toStringAsFixed(1)} kaldı',
                  style: TextStyle(color: sem.uyari, fontSize: 12)),
            ]),
          ],
          const SizedBox(height: 11),
          Row(children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _mesgul ? null : () => _satSor(p),
                child: const Text('SAT'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                onPressed: _mesgul ? null : () => _stopSor(p, fiyat),
                child: const Text('STOP ÇEK'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton(
                onPressed: _mesgul
                    ? null
                    : () => _alimSayfasi(sembol: p.sembol),
                child: const Text('EKLE'),
              ),
            ),
          ]),
        ],
      ),
    );
  }

  Widget _kapaliKarti(BuildContext c, Sem sem, SanalIslem i) => Kutu(
        child: Row(children: [
          Rozet(i.sebep.toUpperCase(),
              renk: i.kar >= 0 ? sem.arti : sem.eksi),
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
              Text(yzd(i.karYuzde, basamak: 1),
                  style: Theme.of(c).textTheme.bodySmall
                      ?.copyWith(color: sem.yon(i.kar))),
            ],
          ),
        ]),
      );

  // ── eylemler ─────────────────────────────────────────────────────────────

  Future<void> _ilerlet(int adim) => _calistir(() async {
        final kapanan = await sanal.ilerlet(adim: adim);
        if (!mounted) return;
        if (kapanan.isEmpty) {
          _uyar('${sanal.tarih} — pozisyonlarda değişiklik yok');
        } else {
          _uyar(kapanan
              .map((k) => '${k.sembol} ${k.sebep} '
                  '(${k.kar >= 0 ? '+' : ''}${tl(k.kar)} ₺)')
              .join(' · '));
        }
      });

  Future<void> _alimSayfasi({String? sembol,
      Map<String, dynamic>? oneri}) async {
    final ok = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
            builder: (_) => SanalAlimEkran(sembol: sembol, oneri: oneri)));
    if (ok == true && mounted) setState(() {});
  }

  Future<void> _satSor(SanalPozisyon p) async {
    final adet = await showDialog<int>(
      context: context,
      builder: (d) => _AdetDialog(
          baslik: '${p.sembol} sat', azami: p.adet,
          eylem: 'SAT'),
    );
    if (adet == null) return;
    await _calistir(() async {
      final h = await sanal.sat(p.sembol, adet: adet >= p.adet ? 0 : adet);
      if (h != null && mounted) _uyar(h);
    });
  }

  Future<void> _stopSor(SanalPozisyon p, double fiyat) async {
    final yeni = await showDialog<double>(
      context: context,
      builder: (d) => _StopDialog(pozisyon: p, fiyat: fiyat),
    );
    if (yeni == null) return;
    await _calistir(() async {
      final h = await sanal.stopCek(p.sembol, yeni);
      if (h != null && mounted) _uyar(h);
    });
  }

  Future<void> _sifirlaSor() async {
    final onay = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('Yeniden başla'),
        content: const Text(
            'Simülasyon sıfırlanacak: tarih, bakiye, pozisyonlar, '
            'kapanan işlemler ve portföy geçmişi silinecek.\n\n'
            'Gerçek portföyün ve karar defterin etkilenmez.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(d, true),
              child: const Text('Sıfırla')),
        ],
      ),
    );
    if (onay == true) await _calistir(sanal.sifirla);
  }
}

// ── kurulum: tarih ve sermaye ──────────────────────────────────────────────

class _Kurulum extends StatefulWidget {
  final void Function(String tarih, double sermaye) baslat;
  const _Kurulum({required this.baslat});

  @override
  State<_Kurulum> createState() => _KurulumDurum();
}

class _KurulumDurum extends State<_Kurulum> {
  final _sermaye = TextEditingController(text: '10000');
  DateTime? _tarih;
  DateTime? _enErken, _enGec;
  bool _yukleniyor = true;

  @override
  void initState() {
    super.initState();
    _araligiGetir();
  }

  @override
  void dispose() {
    _sermaye.dispose();
    super.dispose();
  }

  Future<void> _araligiGetir() async {
    try {
      final r = await depo.api.sanalAralik();
      if (!mounted) return;
      setState(() {
        _enErken = DateTime.tryParse('${r['en_erken']}');
        _enGec = DateTime.tryParse('${r['en_gec']}');
        // Varsayılan: bir yıl önce — ama aralığın dışına taşmasın.
        final biryil = DateTime.now().subtract(const Duration(days: 365));
        _tarih = _kis(biryil);
        _yukleniyor = false;
      });
    } catch (_) {
      if (mounted) setState(() => _yukleniyor = false);
    }
  }

  DateTime _kis(DateTime d) {
    if (_enErken != null && d.isBefore(_enErken!)) return _enErken!;
    if (_enGec != null && d.isAfter(_enGec!)) return _enGec!;
    return d;
  }

  String _iso(DateTime d) => '${d.year}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  String _gosterim(DateTime d) => '${d.day.toString().padLeft(2, '0')}.'
      '${d.month.toString().padLeft(2, '0')}.${d.year}';

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    if (_yukleniyor) return const Yukleniyor(mesaj: 'Takvim hazırlanıyor');

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
      children: [
        Not(
          'Sanal parayla, gerçek fiyatlarla işlem yapacaksın. Gerçek '
          'portföyüne, karar defterine ve siciline hiç dokunmaz.',
          ikon: Icons.science_sharp, renk: sem.aksan,
        ),
        const SizedBox(height: 20),

        Text('BAŞLANGIÇ TARİHİ',
            style: Theme.of(c).textTheme.labelSmall
                ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
        const SizedBox(height: 8),
        InkWell(
          onTap: _tarihSec,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
            decoration: BoxDecoration(
              border: Border.all(color: Renk.cizgiParlak),
              borderRadius: kose,
            ),
            child: Row(children: [
              Text(_tarih == null ? 'seç' : _gosterim(_tarih!),
                  style: Theme.of(c).textTheme.titleMedium),
              const Spacer(),
              Icon(Icons.calendar_today_sharp, size: 18, color: sem.aksan),
            ]),
          ),
        ),
        if (_enErken != null && _enGec != null) ...[
          const SizedBox(height: 6),
          Text('seçilebilir: ${_gosterim(_enErken!)} — ${_gosterim(_enGec!)}',
              style: Theme.of(c).textTheme.bodySmall),
        ],
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _hazir(c, '1 YIL ÖNCE', 365),
          _hazir(c, '6 AY ÖNCE', 182),
          _hazir(c, '3 AY ÖNCE', 91),
        ]),

        const SizedBox(height: 22),
        Text('SERMAYE',
            style: Theme.of(c).textTheme.labelSmall
                ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
        const SizedBox(height: 8),
        TextField(
          controller: _sermaye,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(suffixText: '₺'),
        ),
        const SizedBox(height: 6),
        Text('Gerçek sermayenle denemek istersen onu yaz — küçük '
            'sermayede tek hissenin portföyün ne kadarını kapladığını '
            'ancak böyle görürsün.',
            style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),

        const SizedBox(height: 26),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _tarih == null ? null : () {
              final s = double.tryParse(
                  _sermaye.text.trim().replaceAll('.', '').replaceAll(',', '.'));
              if (s == null || s < 100) {
                ScaffoldMessenger.of(c).showSnackBar(const SnackBar(
                    content: Text('Sermaye en az 100 ₺ olmalı.')));
                return;
              }
              widget.baslat(_iso(_tarih!), s);
            },
            child: const Text('BAŞLA'),
          ),
        ),
      ],
    );
  }

  Widget _hazir(BuildContext c, String etiket, int gun) => OutlinedButton(
        onPressed: () => setState(() =>
            _tarih = _kis(DateTime.now().subtract(Duration(days: gun)))),
        child: Text(etiket),
      );

  Future<void> _tarihSec() async {
    final ilk = _enErken ?? DateTime(2023);
    final son = _enGec ?? DateTime.now();
    final s = await showDatePicker(
      context: context,
      initialDate: _tarih ?? son,
      firstDate: ilk,
      lastDate: son,
      helpText: 'Simülasyon başlangıcı',
      cancelText: 'Vazgeç',
      confirmText: 'Seç',
    );
    if (s != null) setState(() => _tarih = _kis(s));
  }
}

// ── o gün sistemin sinyalleri ──────────────────────────────────────────────

class _SinyalBolumu extends StatefulWidget {
  final String tarih;
  final double sermaye;
  final void Function(Map<String, dynamic>) uygula;
  const _SinyalBolumu({
    required this.tarih, required this.sermaye, required this.uygula,
  });

  @override
  State<_SinyalBolumu> createState() => _SinyalBolumuDurum();
}

class _SinyalBolumuDurum extends State<_SinyalBolumu> {
  List<dynamic>? _sinyaller;
  String _yuklenenTarih = '';
  bool _mesgul = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _getir();
  }

  @override
  void didUpdateWidget(_SinyalBolumu eski) {
    super.didUpdateWidget(eski);
    if (eski.tarih != widget.tarih) _getir();
  }

  Future<void> _getir() async {
    if (_mesgul || _yuklenenTarih == widget.tarih) return;
    setState(() => _mesgul = true);
    try {
      final r = await depo.api
          .sanalSinyaller(widget.tarih, sermaye: widget.sermaye);
      if (!mounted) return;
      setState(() {
        _sinyaller = (r['sinyaller'] ?? []) as List;
        _yuklenenTarih = widget.tarih;
      });
    } catch (_) {
      // Sinyal gelmemesi ekranı bozmamalı — kullanıcı kendi hissesini
      // seçmeye devam edebilir.
      if (mounted) setState(() => _sinyaller = const []);
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final s = _sinyaller;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Baslik('Sistem ne diyordu', alt: widget.tarih),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: const IpucuBalonu('sinyal'),
        ),
        if (_mesgul && s == null)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Yukleniyor(mesaj: 'O günün sinyalleri hesaplanıyor'),
          )
        else if (s == null || s.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Kutu(
              child: Text('O gün sistem sinyal üretmemiş. '
                  'Nakitte beklemek de bir pozisyondur.',
                  style: Theme.of(c).textTheme.bodyMedium
                      ?.copyWith(color: Renk.metinSolgun)),
            ),
          )
        else
          ...s.take(5).map((x) {
            final m = Map<String, dynamic>.from(x as Map);
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 9),
              child: _sinyalKarti(c, sem, m),
            );
          }),
      ],
    );
  }

  Widget _sinyalKarti(BuildContext c, Sem sem, Map<String, dynamic> m) {
    final alinabilir = m['alinabilir'] == true &&
        ((m['adet'] as num?) ?? 0) >= 1;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            SkorHalka(m['skor'] as num?, boyut: 38),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text('${m['sembol']}',
                        style: Theme.of(c).textTheme.titleMedium),
                    const SizedBox(width: 8),
                    Rozet('${m['strateji']}', renk: sem.aksan),
                  ]),
                  if ('${m['vade'] ?? ''}'.isNotEmpty)
                    Text('tipik tutma: ${m['vade']}',
                        style: Theme.of(c).textTheme.bodySmall),
                ],
              ),
            ),
            Text('${tl(m['fiyat'] as num?)} ₺',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: Text('stop ${tl(m['stop'] as num?)}',
                style: TextStyle(color: sem.eksi, fontSize: 12))),
            Expanded(child: Text('hedef ${tl(m['hedef'] as num?)}',
                textAlign: TextAlign.center,
                style: TextStyle(color: sem.arti, fontSize: 12))),
            Expanded(child: Text('${m['adet']} adet',
                textAlign: TextAlign.end,
                style: const TextStyle(fontSize: 12))),
          ]),
          const SizedBox(height: 11),
          SizedBox(
            width: double.infinity,
            child: alinabilir
                ? FilledButton(
                    onPressed: () => widget.uygula(m),
                    child: const Text('BU EMRİ UYGULA'))
                : OutlinedButton(
                    onPressed: () => widget.uygula(m),
                    child: Text('${m['uyari'] ?? 'yine de bak'}',
                        maxLines: 1, overflow: TextOverflow.ellipsis)),
          ),
        ],
      ),
    );
  }
}

// ── diyaloglar ─────────────────────────────────────────────────────────────

class _AdetDialog extends StatefulWidget {
  final String baslik, eylem;
  final int azami;
  const _AdetDialog({
    required this.baslik, required this.azami, required this.eylem,
  });

  @override
  State<_AdetDialog> createState() => _AdetDialogDurum();
}

class _AdetDialogDurum extends State<_AdetDialog> {
  late double _adet = widget.azami.toDouble();

  @override
  Widget build(BuildContext c) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: Text(widget.baslik),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${_adet.round()} / ${widget.azami} adet',
                style: Theme.of(c).textTheme.titleMedium),
            if (widget.azami > 1)
              Slider(
                value: _adet, min: 1, max: widget.azami.toDouble(),
                divisions: widget.azami - 1,
                onChanged: (v) => setState(() => _adet = v),
              ),
            const SizedBox(height: 4),
            Text(_adet.round() >= widget.azami
                    ? 'Pozisyonun tamamı kapanacak.'
                    : 'Kalan ${widget.azami - _adet.round()} adet açık kalacak.',
                style: Theme.of(c).textTheme.bodySmall),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(c, _adet.round()),
              child: Text(widget.eylem)),
        ],
      );
}

class _StopDialog extends StatefulWidget {
  final SanalPozisyon pozisyon;
  final double fiyat;
  const _StopDialog({required this.pozisyon, required this.fiyat});

  @override
  State<_StopDialog> createState() => _StopDialogDurum();
}

class _StopDialogDurum extends State<_StopDialog> {
  late final _alan = TextEditingController(
      text: _ondalik(widget.pozisyon.stop));

  @override
  void dispose() {
    _alan.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) {
    final basabas = widget.pozisyon.giris;
    return AlertDialog(
      backgroundColor: Renk.panel,
      shape: const RoundedRectangleBorder(borderRadius: kose),
      title: Text('${widget.pozisyon.sembol} stop'),
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
          Text('Şu an ${tl(widget.fiyat)} ₺ · giriş ${tl(basabas)} ₺',
              style: Theme.of(c).textTheme.bodySmall),
          const SizedBox(height: 6),
          Text('Stop yalnızca YUKARI çekilebilir. Aşağı çekmek kaybı '
              'büyütür ve bir kere yapan bir daha yapar.',
              style: Theme.of(c).textTheme.bodySmall
                  ?.copyWith(color: Sem(c).uyari, height: 1.5)),
          if (basabas > widget.pozisyon.stop) ...[
            const SizedBox(height: 10),
            OutlinedButton(
              onPressed: () => _alan.text = _ondalik(basabas),
              child: const Text('BAŞABAŞA ÇEK'),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c),
            child: const Text('Vazgeç')),
        TextButton(
          onPressed: () {
            final v = double.tryParse(
                _alan.text.trim().replaceAll(',', '.'));
            Navigator.pop(c, v);
          },
          child: const Text('ÇEK'),
        ),
      ],
    );
  }
}

// ── sanal alım ─────────────────────────────────────────────────────────────

/// Sanal alım ekranı.
///
/// Gerçek alım ekranından (alim.dart) FARKI: orası "Midas'ta aldım,
/// kaydediyorum" der ve karar defterine yazar; burası öğretir ve
/// hiçbir kalıcı kayda dokunmaz.
///
/// HİSSE ARAMASI: kullanıcı "thy" yazınca THYAO çıkıyor. Eskiden
/// sembolü harfi harfine bilmek gerekiyordu ve yanlış yazınca "veri
/// yok" deyip neyi yanlış yazdığını söylemiyorduk.
/// Alım ekranındaki ipucu sırası — yukarıdan aşağı, alanların sırasıyla.
/// Aynı anda hepsi açılınca ekran metin duvarına dönüyordu.
const _alimAkisi = ['kayma', 'stop', 'hedef', 'adet', 'tavan'];

class SanalAlimEkran extends StatefulWidget {
  /// Doğrudan bir hisseyle açmak için (pozisyona ekleme).
  final String? sembol;

  /// Sistemin o günkü sinyali — alanlar önceden dolu gelir.
  final Map<String, dynamic>? oneri;

  const SanalAlimEkran({super.key, this.sembol, this.oneri});

  @override
  State<SanalAlimEkran> createState() => _SanalAlimDurum();
}

/// Virgüllü ondalık — uygulamanın geri kalanı da öyle gösteriyor.
/// Ayrıştırıcılar iki biçimi de kabul ediyor.
String _ondalik(double v, [int basamak = 2]) =>
    v.toStringAsFixed(basamak).replaceAll('.', ',');

class _SanalAlimDurum extends State<SanalAlimEkran> {
  final _arama = TextEditingController();
  final _adet = TextEditingController();
  final _stop = TextEditingController();
  final _hedef = TextEditingController();
  final _odak = FocusNode();

  Sembol? _secili;
  Map<String, dynamic>? _bar;
  Map<String, dynamic>? _hesap;
  bool _mesgul = false;
  String? _hata;

  @override
  void initState() {
    super.initState();
    final o = widget.oneri;
    final kod = widget.sembol ?? (o == null ? null : '${o['sembol']}');
    if (kod != null) {
      _secili = semboller.hisseler
          .where((s) => s.kod == kod)
          .firstOrNull ??
          Sembol(kod: kod, ad: '', izleniyor: false, terimler: [kod]);
      _arama.text = kod;
      if (o != null) {
        _stop.text = (o['stop'] as num?)?.toStringAsFixed(2) ?? '';
        _hedef.text = (o['hedef'] as num?)?.toStringAsFixed(2) ?? '';
        _adet.text = '${(o['adet'] as num?)?.toInt() ?? ''}';
      }
      _fiyatGetir();
    }
  }

  @override
  void dispose() {
    for (final x in [_arama, _adet, _stop, _hedef]) {
      x.dispose();
    }
    _odak.dispose();
    super.dispose();
  }

  double? get _fiyat => (_bar?['kapanis'] as num?)?.toDouble();
  double? get _atr => (_bar?['atr'] as num?)?.toDouble();

  Future<void> _fiyatGetir() async {
    final s = _secili;
    if (s == null) return;
    setState(() { _mesgul = true; _hata = null; });
    try {
      final r = await depo.api.alistirmaGun(s.kod, tarih: sanal.tarih);
      if (!mounted) return;
      setState(() {
        _bar = r;
        final a = (r['atr'] as num?)?.toDouble() ?? 0;
        final f = (r['kapanis'] as num?)?.toDouble() ?? 0;
        // Stop 2 ATR, hedef 3,5 ATR: sistemin kendi kuralı. Kullanıcı
        // değiştirebilir ama başlangıç noktası doğru olsun.
        if (a > 0 && f > 0 && _stop.text.trim().isEmpty) {
          _stop.text = _ondalik(f - 2 * a);
          _hedef.text = _ondalik(f + 3.5 * a);
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
    if (f == null || s == null || s >= f) return;
    try {
      final r = await depo.api.alistirmaAdet(sanal.nakit, f, s);
      if (!mounted) return;
      setState(() => _hesap = r);
      if (_adet.text.trim().isEmpty) {
        _adet.text = '${(r['adet'] as num?)?.toInt() ?? 0}';
      }
    } catch (_) {}
  }

  Future<void> _kaydet() async {
    final s = _secili;
    if (s == null || _fiyat == null) {
      setState(() => _hata = 'Önce bir hisse seç.');
      return;
    }
    final adet = int.tryParse(_adet.text.trim()) ?? 0;
    final stop = double.tryParse(_stop.text.trim().replaceAll(',', '.')) ?? 0;
    final hedef = double.tryParse(_hedef.text.trim().replaceAll(',', '.')) ?? 0;
    if (adet < 1) {
      setState(() => _hata = 'Adet en az 1 olmalı.');
      return;
    }
    if (stop <= 0 || stop >= _fiyat!) {
      setState(() => _hata = 'Stop giriş fiyatının altında olmalı.');
      return;
    }

    setState(() { _mesgul = true; _hata = null; });
    try {
      final h = await sanal.al(s.kod, adet, stop, hedef);
      if (!mounted) return;
      if (h != null) {
        setState(() => _hata = h);
        return;
      }
      Navigator.pop(context, true);
    } on ApiHata catch (e) {
      if (mounted) setState(() => _hata = e.oneri ?? e.mesaj);
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final tavan = _bar?['tavan_mi'] == true;
    final adet = int.tryParse(_adet.text.trim()) ?? 0;
    final stop = double.tryParse(_stop.text.trim().replaceAll(',', '.'));
    final hedef = double.tryParse(_hedef.text.trim().replaceAll(',', '.'));
    final f = _fiyat;

    return Scaffold(
      appBar: AppBar(title: Text('Sanal alım · ${sanal.tarih}')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
        children: [
          _AramaAlani(
            denetleyici: _arama,
            odak: _odak,
            secildi: (s) {
              setState(() {
                _secili = s;
                _bar = null;
                _hesap = null;
                _stop.clear();
                _hedef.clear();
                _adet.clear();
              });
              _fiyatGetir();
            },
          ),

          if (_secili != null && _bar != null) ...[
            const SizedBox(height: 16),
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${_secili!.kod}'
                      '${_secili!.ad.isNotEmpty ? ' · ${_secili!.ad}' : ''}',
                      style: Theme.of(c).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Satir('Tarih', '${_bar!['tarih']}'),
                  Satir('Kapanış', '${tl(f)} ₺'),
                  Satir('ATR (günlük tipik hareket)', '${tl(_atr)} ₺'),
                ],
              ),
            ),
            const IpucuBalonu('kayma', akis: _alimAkisi),
            if (tavan) ...[
              const SizedBox(height: 10),
              Not('Bu hisse tavana yakın açmış — emir gerçekleşmez.',
                  ikon: Icons.block_sharp, renk: sem.eksi),
              const IpucuBalonu('tavan', akis: _alimAkisi),
            ],
          ],

          const SizedBox(height: 16),
          TextField(
            controller: _stop,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Stop', helperText: 'Önerilen: giriş − 2 ATR'),
            onChanged: (_) { setState(() {}); _adetOner(); },
          ),
          const IpucuBalonu('stop', akis: _alimAkisi),

          const SizedBox(height: 12),
          TextField(
            controller: _hedef,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
                labelText: 'Hedef', helperText: 'Önerilen: giriş + 3,5 ATR'),
            onChanged: (_) => setState(() {}),
          ),
          if (f != null && stop != null && hedef != null &&
              stop < f && hedef > f) ...[
            const SizedBox(height: 6),
            Text('ödül/risk: '
                '${_ondalik((hedef - f) / (f - stop), 1)}',
                style: Theme.of(c).textTheme.bodySmall
                    ?.copyWith(color: sem.aksan)),
          ],
          const IpucuBalonu('hedef', akis: _alimAkisi),

          const SizedBox(height: 12),
          TextField(
            controller: _adet,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Adet'),
            onChanged: (_) => setState(() {}),
          ),
          if (f != null && adet > 0) ...[
            const SizedBox(height: 6),
            Text('tutar ${tl(adet * f)} ₺'
                '${stop != null && stop < f
                    ? '  ·  riskin ${tl(adet * (f - stop))} ₺' : ''}',
                style: Theme.of(c).textTheme.bodySmall),
          ],
          const IpucuBalonu('adet', akis: _alimAkisi),

          if (_hesap != null) ...[
            const SizedBox(height: 14),
            Kutu(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SİSTEMİN HESABI',
                      style: Theme.of(c).textTheme.labelSmall
                          ?.copyWith(color: sem.aksan, letterSpacing: 1.2)),
                  const SizedBox(height: 8),
                  Satir('Risk bütçesi (%1,5)',
                      '${tl(_hesap!['risk_butcesi'])} ₺'),
                  Satir('Hisse başına risk',
                      '${tl(_hesap!['hisse_basi_risk'])} ₺'),
                  Satir('Önerilen adet', '${_hesap!['adet']}'),
                  Satir('Sınırlayan', '${_hesap!['baglayici']}'),
                ],
              ),
            ),
          ],

          if (_hata != null) ...[
            const SizedBox(height: 12),
            Not(_hata!, ikon: Icons.error_outline_sharp, renk: sem.eksi),
          ],

          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _mesgul || _secili == null ? null : _kaydet,
              child: const Text('SANAL ALIM YAP'),
            ),
          ),
        ],
      ),
    );
  }
}

/// Otomatik tamamlamalı hisse arama.
///
/// Arama TELEFONDA çalışıyor: liste bir kez inip saklanıyor, tuş başına
/// ağ isteği yok. Sıralama sunucudakiyle aynı kurallar
/// (servis/semboller.dart).
class _AramaAlani extends StatefulWidget {
  final TextEditingController denetleyici;
  final FocusNode odak;
  final void Function(Sembol) secildi;
  const _AramaAlani({
    required this.denetleyici, required this.odak, required this.secildi,
  });

  @override
  State<_AramaAlani> createState() => _AramaAlaniDurum();
}

class _AramaAlaniDurum extends State<_AramaAlani> {
  List<Sembol> _sonuc = const [];
  bool _acik = false;

  void _ara(String q) {
    setState(() {
      _sonuc = semboller.ara(q, azami: 6);
      _acik = q.trim().isNotEmpty && _sonuc.isNotEmpty;
    });
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: widget.denetleyici,
          focusNode: widget.odak,
          textCapitalization: TextCapitalization.characters,
          decoration: InputDecoration(
            labelText: 'Hisse',
            hintText: 'thy · iş bankası · EREGL',
            prefixIcon: const Icon(Icons.search_sharp, size: 20),
            suffixIcon: widget.denetleyici.text.isEmpty
                ? null
                : IconButton(
                    icon: const Icon(Icons.close_sharp, size: 18),
                    onPressed: () {
                      widget.denetleyici.clear();
                      _ara('');
                    },
                  ),
          ),
          onChanged: _ara,
        ),
        if (_acik)
          Container(
            margin: const EdgeInsets.only(top: 4),
            decoration: BoxDecoration(
              color: Renk.panelUst,
              border: Border.all(color: Renk.cizgi),
            ),
            child: Column(
              children: _sonuc.map((s) => InkWell(
                    onTap: () {
                      widget.denetleyici.text = s.kod;
                      setState(() => _acik = false);
                      widget.odak.unfocus();
                      widget.secildi(s);
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 13, vertical: 11),
                      child: Row(children: [
                        SizedBox(
                          width: 62,
                          child: Text(s.kod,
                              style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  color: s.izleniyor ? sem.aksan : null)),
                        ),
                        Expanded(
                          child: Text(s.ad,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(c).textTheme.bodySmall),
                        ),
                        if (s.izleniyor)
                          Icon(Icons.visibility_sharp,
                              size: 13, color: sem.aksan),
                      ]),
                    ),
                  )).toList(),
            ),
          ),
      ],
    );
  }
}
