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
///   1. Başlangıç  — iki soru: yardım ister misin, hangi zamanda
///   2. Rehberli görevler — sırayla, her biri bir dersi uygulatıyor
///   3. Serbest mod — görevler bitince (ya da baştan seçilince) sanal defter
///
/// GÖREV KARTI EN ÜSTTE: sıradaki adım her zaman ilk görülen şey olmalı.
/// Önceki halinde bakiye özeti üstteydi ve görev ekranın altında kalıyordu;
/// telefonda görevi görmek için kaydırmak gerekiyordu.
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

  /// Sıradaki görev. Serbest modda hep null — görev akışı kapalı.
  Map<String, dynamic>? get _siradaki {
    if (!kum.rehberli) return null;
    for (final g in _gorevler) {
      final m = Map<String, dynamic>.from(g as Map);
      if (!kum.bitenGorevler.contains('${m['kod']}')) return m;
    }
    return null;
  }

  bool get _hepsiBitti =>
      _gorevler.isNotEmpty && kum.bitenGorevler.length >= _gorevler.length;

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
                ? _Baslangic(
                    baslat: (mod, tarih, rehber) =>
                        _calistir(() => kum.basla(mod, tarih, rehber)))
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
        if (kum.rehberli) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _IlerlemeSeridi(
                biten: kum.bitenGorevler.length,
                toplam: _gorevler.isEmpty ? 8 : _gorevler.length,
                puan: kum.puan,
                // Görevler bitince rozetler kutlama kartında ZATEN var
                // (kazanılmayanlarla birlikte). İki yerde göstermek
                // ekranı uzatıyor ve ikisinden hangisinin tam liste
                // olduğunu belirsizleştiriyordu.
                rozetler: _hepsiBitti ? const [] : kum.rozetler),
          ),
          const SizedBox(height: 4),
        ],

        if (g != null) ...[
          const Baslik('Sıradaki görev'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _GorevKarti(
              // ANAHTAR ŞART. Bu olmadan Flutter görev değişince aynı
              // State nesnesini yeniden kullanıyordu: bir önceki görevin
              // "doğru bildin" durumu kalıyor, cevap kutusu kapalı
              // geliyor ve yeşil kutuda ÖNCEKİ görevin açıklaması
              // duruyordu. Tek satırlık eksik, üç ayrı belirti.
              key: ValueKey('${g['kod']}'),
              gorev: g,
              sira: kum.bitenGorevler.length + 1,
              toplam: _gorevler.length,
              denemeKaydet: () => kum.denemeEkle('${g['kod']}'),
              // Uygulamalı görevlerde "yaptım" iddiası değil, KANIT
              // aranıyor: alım görevinde açık ya da kapanmış bir pozisyon,
              // ilerletme görevinde kapanmış bir işlem. Kanıtsız
              // geçilebilseydi rozet hiçbir şey ifade etmezdi.
              isKaniti: '${g['tur']}' == 'islem'
                  ? kum.pozisyonlar.isNotEmpty || kum.kapali.isNotEmpty
                  : '${g['tur']}' == 'ilerlet'
                      ? kum.kapali.isNotEmpty
                      : true,
              bitir: () => _calistir(() =>
                  kum.gorevBitir('${g['kod']}', toplamGorev: _gorevler.length)),
              alimIste: _alimSayfasi,
              ilerletIste: _ilerlet,
            ),
          ),
        ] else if (kum.rehberli && _hepsiBitti) ...[
          const Baslik('Sonuç', alt: 'rehberli mod tamamlandı'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _Kutlama(
                puan: kum.puan,
                azami: (_gorevler.isEmpty ? 8 : _gorevler.length) * 10,
                rozetler: kum.rozetler),
          ),
        ] else if (!kum.rehberli) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            child: Kutu(
              child: Row(children: [
                Icon(Icons.explore_off_sharp, size: 18, color: Renk.metinSolgun),
                const SizedBox(width: 11),
                Expanded(
                  child: Text('Kendi başına moddasın. Takılırsan rehberi '
                      'açabilirsin — ilerlemen kaybolmaz.',
                      style: Theme.of(c).textTheme.bodySmall),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: _mesgul
                      ? null
                      : () => _calistir(() => kum.rehberDegistir('rehberli')),
                  child: const Text('AÇ'),
                ),
              ]),
            ),
          ),
        ],

        const Baslik('Sanal hesabın'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: _ozet(c, sem),
        ),

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
        await kum.islemRozetleri(
            toplamGorev: _gorevler.isEmpty ? 8 : _gorevler.length);
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
    if (ok == true && mounted) {
      await kum.islemRozetleri(
          toplamGorev: _gorevler.isEmpty ? 8 : _gorevler.length);
      if (mounted) setState(() {});
    }
  }

  Future<void> _sifirlaSor() async {
    final onay = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('Alıştırmayı sıfırla'),
        content: const Text(
            'Sanal bakiye, pozisyonlar, kapanan işlemler, puanın, '
            'rozetlerin ve görev ilerlemen silinecek.\n\n'
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

// ── rozetler ───────────────────────────────────────────────────────────────

/// Rozet tanımları tek yerde: ad, ikon ve KAZANMA SEBEBİ.
///
/// `ilk_stop` bilerek burada: stop yemek bir başarısızlık değil, sistemin
/// çalıştığının kanıtı. Ödüllendirilmezse kullanıcı stopu "kaybettiğim
/// yer" diye öğrenir ve bir dahakine koymaz.
const rozetTanim = <String, (IconData, String, String)>{
  'ilk_adim': (Icons.flag_sharp, 'İlk adım', 'İlk görevi bitirdin'),
  'yarim_yol': (Icons.timeline_sharp, 'Yarı yol', 'Görevlerin yarısı bitti'),
  'mezun': (Icons.school_sharp, 'Mezun', 'Bütün görevleri bitirdin'),
  'kusursuz': (Icons.auto_awesome_sharp, 'Kusursuz',
      'Her görevi ilk denemede bildin'),
  'ilk_islem': (Icons.candlestick_chart_sharp, 'İlk işlem',
      'İlk sanal işlemini kapattın'),
  'ilk_kar': (Icons.trending_up_sharp, 'İlk kâr', 'Kârla kapanan bir işlem'),
  'ilk_stop': (Icons.shield_sharp, 'Stop çalıştı',
      'Bir stop seni korudu — bu da öğrenmek'),
};

class _RozetPulu extends StatelessWidget {
  final String kod;
  final bool kazanildi;
  const _RozetPulu(this.kod, {this.kazanildi = true});

  @override
  Widget build(BuildContext c) {
    final t = rozetTanim[kod];
    if (t == null) return const SizedBox.shrink();
    final renk = kazanildi ? Sem(c).aksan : Renk.cizgiParlak;
    return Tooltip(
      message: t.$3,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          border: Border.all(color: renk, width: 1.2),
          color: kazanildi ? renk.withValues(alpha: 0.10) : Colors.transparent,
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(t.$1, size: 13, color: renk),
          const SizedBox(width: 6),
          Text(t.$2,
              style: TextStyle(
                  fontSize: 11, color: renk, fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }
}

// ── ilerleme şeridi ────────────────────────────────────────────────────────

class _IlerlemeSeridi extends StatelessWidget {
  final int biten, toplam, puan;
  final List<String> rozetler;
  const _IlerlemeSeridi({
    required this.biten, required this.toplam,
    required this.puan, required this.rozetler,
  });

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('İLERLEME',
                style: Theme.of(c).textTheme.labelSmall
                    ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
            const Spacer(),
            Text('$puan',
                style: Theme.of(c).textTheme.titleMedium
                    ?.copyWith(color: sem.aksan)),
            Text(' / ${toplam * 10} puan',
                style: Theme.of(c).textTheme.bodySmall),
          ]),
          const SizedBox(height: 10),
          // Kutucuklu çubuk: sürekli bir çizgi yerine görev sayısı kadar
          // kutu. "Kaç tane kaldı" sayılabilir olsun — yüzde soyut,
          // "8'de 3" somut.
          Row(
            children: List.generate(toplam, (i) {
              return Expanded(
                child: Container(
                  height: 8,
                  margin: EdgeInsets.only(right: i == toplam - 1 ? 0 : 3),
                  color: i < biten ? sem.aksan : Renk.cizgi,
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          Text('$biten / $toplam görev',
              style: Theme.of(c).textTheme.bodySmall),
          if (rozetler.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6, runSpacing: 6,
              children: rozetler.map((r) => _RozetPulu(r)).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

// ── kutlama ────────────────────────────────────────────────────────────────

class _Kutlama extends StatelessWidget {
  final int puan, azami;
  final List<String> rozetler;
  const _Kutlama({
    required this.puan, required this.azami, required this.rozetler,
  });

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    // Puana göre değişen tek cümle. Sabit bir "tebrikler" hiçbir şey
    // söylemiyor; kaç denemede bitirdiğini yansıtan cümle söylüyor.
    final yorum = azami > 0 && puan >= azami
        ? 'Hepsini ilk denemede bildin. Bu nadir.'
        : puan >= azami * 0.75
            ? 'Sağlam. Birkaç yerde ikinci denemeye kaldın, o da normal.'
            : 'Bitirdin. Zorlandığın yerleri sıfırlayıp tekrar edebilirsin.';

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.emoji_events_sharp, size: 22, color: sem.aksan),
            const SizedBox(width: 10),
            Text('Görevler bitti',
                style: Theme.of(c).textTheme.titleMedium
                    ?.copyWith(color: sem.aksan)),
          ]),
          const SizedBox(height: 10),
          Text('$puan / $azami puan',
              style: Theme.of(c).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(yorum,
              style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.55)),
          const SizedBox(height: 14),
          Text('ROZETLER',
              style: Theme.of(c).textTheme.labelSmall
                  ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
          const SizedBox(height: 9),
          // Kazanılmayanlar da SOLGUN gösteriliyor: neyin kaldığını
          // görmeden peşine düşülmez.
          Wrap(
            spacing: 6, runSpacing: 6,
            children: rozetTanim.keys
                .map((k) => _RozetPulu(k, kazanildi: rozetler.contains(k)))
                .toList(),
          ),
          const SizedBox(height: 14),
          Text('Artık serbestsin: sanal para, gerçek fiyat, gerçek kurallar. '
              'Aşağıdan istediğin gibi dene.',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.55)),
        ],
      ),
    );
  }
}

// ── başlangıç: iki soru ────────────────────────────────────────────────────

/// İki ayrı soru, iki ayrı adım.
///
/// Tek ekranda dört kutucuk (rehberli-geçmiş, rehberli-canlı, serbest-geçmiş,
/// serbest-canlı) gösterilebilirdi ama o dört seçenek arasında karar
/// verilemez. İki soruyu ayırmak, her birini tek başına cevaplanabilir
/// hale getiriyor.
class _Baslangic extends StatefulWidget {
  final void Function(String mod, String tarih, String rehber) baslat;
  const _Baslangic({required this.baslat});

  @override
  State<_Baslangic> createState() => _BaslangicDurum();
}

class _BaslangicDurum extends State<_Baslangic> {
  String? _rehber;

  String _iso(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final adim = _rehber == null ? 1 : 2;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
      children: [
        Not(
          'Sanal 10.000 ₺ ile işlem yapacaksın. Gerçek portföyüne, karar '
          'defterine ve siciline hiç dokunmaz — istediğin zaman sıfırlarsın.',
          ikon: Icons.science_sharp, renk: sem.aksan,
        ),
        const SizedBox(height: 18),

        Row(children: [
          Text('ADIM $adim / 2',
              style: Theme.of(c).textTheme.labelSmall
                  ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
          const Spacer(),
          if (adim == 2)
            TextButton(
              onPressed: () => setState(() => _rehber = null),
              child: const Text('GERİ'),
            ),
        ]),
        const SizedBox(height: 10),

        if (adim == 1) ...[
          Text('Yardım ister misin?',
              style: Theme.of(c).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text('İstediğin zaman değiştirebilirsin.',
              style: Theme.of(c).textTheme.bodySmall),
          const SizedBox(height: 14),
          _secenek(c, sem,
              ikon: Icons.handshake_sharp,
              baslik: 'Elimden tut',
              vurgu: true,
              rozet: 'ÖNERİLEN',
              metin: '8 kısa görev, sırayla. Her biri tek bir şey öğretiyor: '
                  'tutar, stop, hedef, adet, sonra gerçek bir sanal alım.\n\n'
                  'Puan toplarsın, rozet kazanırsın. Yanlış cevap bir şey '
                  'kaybettirmez — sadece ipucu getirir.',
              sec: () => setState(() => _rehber = 'rehberli')),
          const SizedBox(height: 10),
          _secenek(c, sem,
              ikon: Icons.explore_sharp,
              baslik: 'Kendi başıma',
              metin: 'Görevleri atla, doğrudan sanal işleme başla. '
                  'Hisseyi sen seçersin, stopu sen koyarsın.\n\n'
                  'Takılırsan rehberi sonradan açabilirsin.',
              sec: () => setState(() => _rehber = 'serbest')),
        ] else ...[
          Text('Hangi zamanda?', style: Theme.of(c).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text('Sonucu ne kadar hızlı göreceğini bu belirliyor.',
              style: Theme.of(c).textTheme.bodySmall),
          const SizedBox(height: 14),
          _secenek(c, sem,
              ikon: Icons.fast_forward_sharp,
              baslik: 'Geçmiş',
              vurgu: true,
              rozet: 'HIZLI',
              metin: '4 ay öncesine gidersin, alım yaparsın, "sonraki gün" '
                  'düğmesiyle ilerlersin. 20 günlük sonucu 20 saniyede '
                  'görürsün.\n\nÖğrenmek için en hızlı yol.',
              sec: () => widget.baslat('gecmis',
                  _iso(DateTime.now().subtract(const Duration(days: 120))),
                  _rehber!)),
          const SizedBox(height: 10),
          _secenek(c, sem,
              ikon: Icons.today_sharp,
              baslik: 'Canlı',
              metin: 'Bugünün gerçek fiyatlarından alırsın, sonucu gerçek '
                  'günlerde görürsün.\n\nDaha gerçekçi ama yavaş: bir stopun '
                  'çalıştığını görmen haftalar alabilir.',
              sec: () =>
                  widget.baslat('canli', _iso(DateTime.now()), _rehber!)),
        ],
      ],
    );
  }

  Widget _secenek(BuildContext c, Sem sem,
      {required IconData ikon,
      required String baslik,
      required String metin,
      required VoidCallback sec,
      bool vurgu = false,
      String? rozet}) {
    return Kutu(
      tikla: sec,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(ikon, size: 19, color: vurgu ? sem.aksan : null),
            const SizedBox(width: 10),
            Text(baslik,
                style: Theme.of(c).textTheme.titleMedium
                    ?.copyWith(color: vurgu ? sem.aksan : null)),
            const Spacer(),
            if (rozet != null) Rozet(rozet, renk: sem.aksan),
          ]),
          const SizedBox(height: 8),
          Text(metin,
              style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.55)),
        ],
      ),
    );
  }
}

// ── görev kartı ────────────────────────────────────────────────────────────

class _GorevKarti extends StatefulWidget {
  final Map<String, dynamic> gorev;
  final int sira, toplam;
  final Future<int> Function() denemeKaydet;
  final bool isKaniti;
  final VoidCallback bitir;
  final VoidCallback alimIste;
  final VoidCallback ilerletIste;

  const _GorevKarti({
    super.key,
    required this.gorev, required this.sira, required this.toplam,
    required this.denemeKaydet, required this.isKaniti,
    required this.bitir, required this.alimIste, required this.ilerletIste,
  });

  @override
  State<_GorevKarti> createState() => _GorevKartiDurum();
}

class _GorevKartiDurum extends State<_GorevKarti> {
  final _cevap = TextEditingController();
  int? _secim;
  bool _dogruMu = false;
  bool _ipucuAcik = false;
  bool _anlatimAcik = true;
  int _deneme = 0;
  String? _geriBildirim;

  @override
  void dispose() {
    _cevap.dispose();
    super.dispose();
  }

  Future<void> _kontrol() async {
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

    final n = await widget.denemeKaydet();
    if (!mounted) return;
    setState(() {
      _deneme = n;
      _dogruMu = dogru;
      _geriBildirim = dogru
          ? '${g['aciklama']}'
          : 'Henüz değil. ${g['ipucu'] ?? ''}'.trim();
      // Doğru cevapta anlatımı topla: ekranda yer açılsın, açıklama ve
      // sonraki adım aynı anda görünsün.
      if (dogru) _anlatimAcik = false;
      if (!dogru) _ipucuAcik = true;
    });
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final g = widget.gorev;
    final tur = '${g['tur']}';
    final ders = '${g['ders'] ?? ''}';
    final amac = '${g['amac'] ?? ''}';
    final ipucu = '${g['ipucu'] ?? ''}';
    final soru = '${g['soru'] ?? ''}';
    final cevaplanabilir = tur == 'secim' || tur == 'sayi';

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── üst şerit
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              color: sem.aksan.withValues(alpha: 0.14),
              child: Text('GÖREV ${widget.sira}/${widget.toplam}',
                  style: Theme.of(c).textTheme.labelSmall
                      ?.copyWith(color: sem.aksan, letterSpacing: 1.2)),
            ),
            const SizedBox(width: 8),
            if (_dogruMu)
              Rozet('+${KumHavuzu.puanHesapla(_deneme)} PUAN', renk: sem.arti),
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
          const SizedBox(height: 10),
          Text('${g['baslik']}', style: Theme.of(c).textTheme.titleMedium),

          // "Bitirince ne bileceksin" — görev tanımında hep vardı ama
          // ekranda hiç gösterilmiyordu. Bir göreve başlamadan önce
          // sorulacak ilk soru bu.
          if (amac.isNotEmpty) ...[
            const SizedBox(height: 5),
            Text('Bitirince: $amac',
                style: Theme.of(c).textTheme.bodySmall
                    ?.copyWith(color: sem.aksan, height: 1.4)),
          ],

          // ── anlatım (katlanabilir)
          // Anlatım uzun; açık kaldığında soru telefon ekranının altına
          // düşüyordu ve kullanıcı soruyu görmek için kaydırmak zorundaydı.
          const SizedBox(height: 12),
          InkWell(
            onTap: () => setState(() => _anlatimAcik = !_anlatimAcik),
            child: Row(children: [
              Icon(_anlatimAcik
                      ? Icons.keyboard_arrow_down_sharp
                      : Icons.keyboard_arrow_right_sharp,
                  size: 17, color: Renk.metinSolgun),
              const SizedBox(width: 4),
              Text('ÖNCE ŞUNU BİL',
                  style: Theme.of(c).textTheme.labelSmall
                      ?.copyWith(letterSpacing: 1.2)),
            ]),
          ),
          if (_anlatimAcik) ...[
            const SizedBox(height: 8),
            Text('${g['anlatim']}',
                style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.6)),
          ],

          // ── soru
          if (soru.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(
                color: Renk.panelUst,
                border: Border(
                    left: BorderSide(color: sem.aksan, width: 3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SORU',
                      style: Theme.of(c).textTheme.labelSmall
                          ?.copyWith(color: sem.aksan, letterSpacing: 1.3)),
                  const SizedBox(height: 7),
                  Text(soru,
                      style: Theme.of(c).textTheme.bodyLarge
                          ?.copyWith(height: 1.5)),
                ],
              ),
            ),
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
              autofocus: false,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _dogruMu ? null : _kontrol(),
              decoration: InputDecoration(
                  labelText: 'Cevabın',
                  hintText: '0,00',
                  suffixText: '${g['birim'] ?? ''}'),
            ),

          // ── ipucu (istenince)
          // Önceden ipucu YALNIZCA yanlış cevaptan sonra görünüyordu.
          // Tıkanan biri o yüzden rastgele bir sayı yazıp "yanlış" almak
          // zorunda kalıyordu. Artık isteyen önce bakabiliyor.
          if (cevaplanabilir && ipucu.isNotEmpty && !_dogruMu) ...[
            const SizedBox(height: 6),
            if (!_ipucuAcik)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => setState(() => _ipucuAcik = true),
                  icon: const Icon(Icons.lightbulb_outline_sharp, size: 16),
                  label: const Text('İPUCU'),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(children: [
                  Icon(Icons.lightbulb_sharp, size: 15, color: sem.uyari),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(ipucu,
                        style: Theme.of(c).textTheme.bodySmall
                            ?.copyWith(color: sem.uyari)),
                  ),
                ]),
              ),
          ],

          // ── geri bildirim
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(_dogruMu
                            ? Icons.check_circle_sharp
                            : Icons.refresh_sharp,
                        size: 16, color: _dogruMu ? sem.arti : sem.uyari),
                    const SizedBox(width: 7),
                    Text(
                        _dogruMu
                            ? (_deneme <= 1
                                ? 'DOĞRU — ilk denemede'
                                : 'DOĞRU — $_deneme. denemede')
                            : 'BİR DAHA DENE',
                        style: TextStyle(
                            color: _dogruMu ? sem.arti : sem.uyari,
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                            letterSpacing: 0.8)),
                  ]),
                  const SizedBox(height: 9),
                  Text(_geriBildirim!,
                      style: Theme.of(c).textTheme.bodySmall
                          ?.copyWith(height: 1.6)),
                ],
              ),
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
              child: FilledButton.icon(
                onPressed: widget.isKaniti ? widget.bitir : null,
                icon: const Icon(Icons.arrow_forward_sharp, size: 18),
                label: Text(!widget.isKaniti
                    ? (tur == 'islem'
                        ? 'ÖNCE BİR ALIM YAP'
                        : 'ÖNCE POZİSYON KAPANSIN')
                    : widget.sira >= widget.toplam
                        ? 'GÖREVLERİ BİTİR'
                        : 'SONRAKİ GÖREV'),
              ),
            ),
            // Kapı YUMUŞAK: kanıt istiyoruz ama kimseyi kilitlemiyoruz.
            // Geçmiş modda bir stopun hiç çalışmaması mümkün; sert kapı
            // olsaydı kullanıcı kalan görevleri hiç göremezdi.
            if (!widget.isKaniti) ...[
              const SizedBox(height: 4),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                    onPressed: widget.bitir,
                    child: const Text('YİNE DE ATLA')),
              ),
            ],
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
