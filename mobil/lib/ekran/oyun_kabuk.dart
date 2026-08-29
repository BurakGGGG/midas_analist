
import 'package:flutter/material.dart';

import '../parca/kart.dart';
import '../servis/oyun.dart';
import '../tema.dart';
import 'kabuk.dart' show sekme, Sekme;
import '../parca/oyun_animasyon.dart';
import '../parca/ipucu.dart';
import 'oyun_acilis.dart';
import 'oyun_tanitim.dart';
import 'oyun_ekranlar.dart';

/// Sanal İşlem'in KENDİ kabuğu.
///
/// Midas'ın alt çubuğunu tamamen değiştiriyor: kullanıcı bu bölüme
/// girdiğinde başka bir uygulamaya geçmiş gibi hissetmeli. Kendi
/// sekmeleri (Portföy · Borsa · Analist · Haberler), kendi paleti
/// (kehribar) ve kendi üst şeridi var.
///
/// Zaman şeridi ÜST TARAFTA ve her sekmede duruyor: "gün ilerlet" oyunun
/// tek zorunlu eylemi; sekmeye gömülseydi kullanıcı onu aramak zorunda
/// kalırdı.
class OyunKabuk extends StatefulWidget {
  const OyunKabuk({super.key});
  @override
  State<OyunKabuk> createState() => _OyunKabukDurum();
}

class _OyunKabukDurum extends State<OyunKabuk> {
  int _sekme = 0;

  /// Açılış dizisi bitene kadar true. Kayıtlı oyun varsa piyasa
  /// yeniden üretilirken, yeni oyunda zorluk seçildikten sonra çalışıyor.
  bool _aciliyor = false;

  /// `?` ile elle açılan tanıtım.
  bool _tanitim = false;

  @override
  void initState() {
    super.initState();
    if (oyun.basladi && !oyun.piyasaHazir) {
      _aciliyor = true;
    }
  }

  Future<void> _yeniOyun(String zorluk) async {
    setState(() => _aciliyor = true);
    await oyun.basla(zorluk);
    if (mounted && oyun.hata != null) setState(() => _aciliyor = false);
  }

  void _cik() => sekme.value = Sekme.bugun;

  @override
  Widget build(BuildContext c) {
    // Tema burada sarmalanıyor: içerideki her widget kehribar paleti
    // görüyor, dışarısı yeşil kalıyor.
    return Theme(
      data: temaOyun,
      child: ListenableBuilder(
        listenable: oyun,
        builder: (_, __) => Scaffold(
          backgroundColor: OyunRenk.zemin,
          body: SafeArea(child: _govde(c)),
          bottomNavigationBar: oyun.basladi && oyun.piyasaHazir
              ? _altCubuk(c)
              : null,
        ),
      ),
    );
  }

  Widget _govde(BuildContext c) {
    // TANITIM İLK: borsayı bilmeyen biri zorluk ekranında "8 hisse ·
    // 50.000 ₺" satırını okuyup ne yapacağını bilemiyordu. Dört adım,
    // bir kez çıkıyor, `?` ile geri geliyor.
    if (_tanitim || ipucu.gorunur('tanitim')) {
      return OyunTanitim(bitti: () {
        if (mounted) setState(() => _tanitim = false);
      });
    }
    if (_aciliyor) {
      return OyunAcilis(
        // Gerçek iş: kayıtlı oyunun piyasası üretiliyor. Yeni oyunda
        // `_yeniOyun` zaten başlattı, burada yalnızca bitmesini bekliyoruz.
        is_: () async {
          if (oyun.basladi && !oyun.piyasaHazir) await oyun.piyasayiGetir();
          while (oyun.yukleniyor) {
            await Future.delayed(const Duration(milliseconds: 60));
          }
        },
        bitti: () {
          if (mounted) setState(() => _aciliyor = false);
        },
      );
    }
    if (!oyun.basladi) {
      return OyunBaslangic(
          cikis: _cik, baslat: _yeniOyun,
          tanitim: () => setState(() => _tanitim = true));
    }
    if (oyun.hata != null && !oyun.piyasaHazir) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: HataGorunum(oyun.hata!, tekrar: () => oyun.piyasayiGetir()),
      );
    }
    if (!oyun.piyasaHazir) {
      return const Yukleniyor(mesaj: 'Piyasa hazırlanıyor');
    }
    return Column(
      children: [
        _ustSerit(c),
        Expanded(
          child: IndexedStack(
            index: _sekme,
            children: const [
              OyunPortfoy(), OyunBorsa(), OyunEmirler(), OyunAnalist(),
              OyunHaberler(),
            ],
          ),
        ),
      ],
    );
  }

  // ── üst şerit: gün, değer, zaman düğmeleri ───────────────────────────────

  Widget _ustSerit(BuildContext c) {
    final getiri = oyun.getiriYuzde;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 8, 10),
      decoration: const BoxDecoration(
        color: OyunRenk.panel,
        border: Border(bottom: BorderSide(color: OyunRenk.cizgi)),
      ),
      child: Column(
        children: [
          Row(children: [
            // "OYUN" rozeti KALICI: ekranda gerçek BIST kodları var ama
            // fiyatlar üretilmiş. Ekran görüntüsü gerçek kotasyon
            // sanılmamalı.
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              color: OyunRenk.aksan,
              child: const Text('OYUN',
                  style: TextStyle(
                      color: OyunRenk.zemin, fontSize: 9.5,
                      fontWeight: FontWeight.w700, letterSpacing: 1.2)),
            ),
            const SizedBox(width: 8),
            Text('${oyun.zorluk.toUpperCase()} · '
                '${oyun.gunSayisi - oyun.gun - 1} GÜN KALDI',
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 11,
                    letterSpacing: 0.8)),
            const Spacer(),
            IconButton(
              icon: const Icon(Icons.close_sharp, size: 20),
              tooltip: 'Midas\'a dön',
              color: OyunRenk.metinSolgun,
              onPressed: _cik,
              visualDensity: VisualDensity.compact,
            ),
          ]),
          const SizedBox(height: 2),
          Row(crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic, children: [
            Text('${tl(oyun.toplamDeger)} ₺',
                style: const TextStyle(
                    color: OyunRenk.metin, fontSize: 24,
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()])),
            const SizedBox(width: 10),
            Text(yzd(getiri, basamak: 1),
                style: TextStyle(
                    color: Sem(c).yon(getiri), fontSize: 15,
                    fontWeight: FontWeight.w700)),
            const Spacer(),
            Text('nakit ${tl(oyun.nakit)}',
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 11)),
          ]),
          const SizedBox(height: 9),
          if (oyun.bitti) _bitisSeridi(c) else _zamanDugmeleri(c),
        ],
      ),
    );
  }

  Widget _zamanDugmeleri(BuildContext c) => Row(children: [
        Expanded(flex: 4, child: _dugme(c, '+1 GÜN', () => _ilerlet(1))),
        const SizedBox(width: 6),
        Expanded(flex: 5, child: _dugme(c, '+1 HAFTA', () => _ilerlet(5))),
        const SizedBox(width: 6),
        Expanded(
          flex: 8,
          child: _dugme(c, 'KAPANANA KADAR',
              oyun.pozisyonlar.isEmpty ? null : () => _ilerlet(0),
              dolu: true),
        ),
      ]);

  Widget _dugme(BuildContext c, String etiket, VoidCallback? bas,
      {bool dolu = false}) {
    final kapali = bas == null;
    return SizedBox(
      height: 36,
      child: dolu
          ? FilledButton(
              onPressed: bas,
              style: FilledButton.styleFrom(
                  backgroundColor: OyunRenk.aksan,
                  foregroundColor: OyunRenk.zemin,
                  disabledBackgroundColor: OyunRenk.panelUst,
                  disabledForegroundColor: OyunRenk.metinSonuk,
                  padding: EdgeInsets.zero,
                  shape: const RoundedRectangleBorder(borderRadius: kose)),
              child: Text(etiket, style: const TextStyle(fontSize: 11.5)))
          : OutlinedButton(
              onPressed: bas,
              style: OutlinedButton.styleFrom(
                  foregroundColor:
                      kapali ? OyunRenk.metinSonuk : OyunRenk.metin,
                  side: const BorderSide(color: OyunRenk.cizgiParlak),
                  padding: EdgeInsets.zero,
                  shape: const RoundedRectangleBorder(borderRadius: kose)),
              child: Text(etiket, style: const TextStyle(fontSize: 11.5))),
    );
  }

  Widget _bitisSeridi(BuildContext c) {
    final k = oyun.toplamDeger - oyun.baslangicSermaye;
    return Row(children: [
      Icon(k >= 0 ? Icons.emoji_events_sharp : Icons.flag_sharp,
          size: 17, color: k >= 0 ? Sem(c).arti : OyunRenk.metinSolgun),
      const SizedBox(width: 8),
      Expanded(
        child: Text(
            k >= 0
                ? 'Oyun bitti · ${tl(k)} ₺ kazandın'
                : 'Oyun bitti · ${tl(k.abs())} ₺ kaybettin',
            style: TextStyle(
                color: k >= 0 ? Sem(c).arti : Sem(c).eksi, fontSize: 12.5,
                fontWeight: FontWeight.w700)),
      ),
      SizedBox(
        height: 32,
        child: FilledButton(
          onPressed: () => oyun.birak(),
          style: FilledButton.styleFrom(
              backgroundColor: OyunRenk.aksan,
              foregroundColor: OyunRenk.zemin,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              shape: const RoundedRectangleBorder(borderRadius: kose)),
          child: const Text('YENİ OYUN', style: TextStyle(fontSize: 11)),
        ),
      ),
    ]);
  }

  Future<void> _ilerlet(int adim) async {
    final ozet = oyun.ilerlet(adim: adim);
    if (!mounted) return;
    await gunOzetiGoster(context, ozet);
    if (mounted && oyun.bitti) await oyunSonuGoster(context);
  }

  // ── alt çubuk ────────────────────────────────────────────────────────────

  Widget _altCubuk(BuildContext c) {
    final okunmamis = oyun.okunmamisHaber;
    return NavigationBar(
      selectedIndex: _sekme,
      onDestinationSelected: (v) {
        setState(() => _sekme = v);
        if (v == 4) oyun.haberleriOkudum();
      },
      destinations: [
        const NavigationDestination(
            icon: Icon(Icons.account_balance_wallet_sharp), label: 'Portföy'),
        const NavigationDestination(
            icon: Icon(Icons.show_chart_sharp), label: 'Borsa'),
        NavigationDestination(
            icon: Badge(
              isLabelVisible: oyun.emirler.isNotEmpty,
              backgroundColor: OyunRenk.aksan,
              textColor: OyunRenk.zemin,
              label: Text('${oyun.emirler.length}'),
              child: const Icon(Icons.pending_actions_sharp),
            ),
            label: 'Emirler'),
        NavigationDestination(
            icon: Badge(
              isLabelVisible: oyun.bugunSinyaller.isNotEmpty,
              backgroundColor: OyunRenk.aksan,
              textColor: OyunRenk.zemin,
              label: Text('${oyun.bugunSinyaller.length}'),
              child: const Icon(Icons.insights_sharp),
            ),
            label: 'Analist'),
        NavigationDestination(
            icon: Badge(
              isLabelVisible: okunmamis > 0,
              backgroundColor: OyunRenk.aksan,
              textColor: OyunRenk.zemin,
              label: Text('$okunmamis'),
              child: const Icon(Icons.article_sharp),
            ),
            label: 'Haberler'),
      ],
    );
  }
}

// ── başlangıç: zorluk seçimi ───────────────────────────────────────────────

class OyunBaslangic extends StatelessWidget {
  final VoidCallback cikis;
  final VoidCallback tanitim;
  final void Function(String zorluk) baslat;
  const OyunBaslangic({
    super.key, required this.cikis, required this.baslat,
    required this.tanitim,
  });

  // Açıklamalar borsa BİLMEYENE göre yazıldı: "testere ağzı piyasa,
  // yalancı kırılma, geniş makas" cümlesi doğruydu ama ilk kez oynayan
  // birine hiçbir şey söylemiyordu.
  static const _zorluklar = [
    ('kolay', 'Kolay',
     'Fiyatlar düzgün yükselir ya da düşer, yönü görmek kolay. '
     'Haberler doğru söyler. Bol paran var.',
     '8 hisse · 50.000 ₺ · 40 gün'),
    ('normal', 'Normal',
     'Fiyatlar zikzak çizer, yön her zaman belli olmaz. Haberlerin '
     'beşte biri yanıltır. Gerçeğe en yakın olan bu.',
     '14 hisse · 25.000 ₺ · 60 gün'),
    ('zor', 'Zor',
     'Fiyat yükseliyor görünüp aniden döner. Haberlerin neredeyse '
     'yarısı yanıltır, paran dar, takip edecek çok hisse var.',
     '22 hisse · 10.000 ₺ · 90 gün'),
  ];

  @override
  Widget build(BuildContext c) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 28),
      children: [
        Row(children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
            color: OyunRenk.aksan,
            child: const Text('SANAL İŞLEM',
                style: TextStyle(
                    color: OyunRenk.zemin, fontSize: 11,
                    fontWeight: FontWeight.w700, letterSpacing: 1.4)),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.help_outline_sharp, size: 19),
            tooltip: 'Nasıl oynanır',
            color: OyunRenk.metinSolgun,
            onPressed: tanitim,
          ),
          IconButton(
            icon: const Icon(Icons.close_sharp, size: 20),
            color: OyunRenk.metinSolgun,
            onPressed: cikis,
          ),
        ]),
        const SizedBox(height: 18),
        const Not(
          'Hisse kodları gerçek ama fiyatları biz uyduruyoruz — burada '
          'olan hiçbir şey gerçek borsada olmadı.\n\n'
          'Her yeni oyun bir öncekinden farklı olur.',
          ikon: Icons.casino_sharp, renk: OyunRenk.aksan,
        ),
        const SizedBox(height: 20),
        const Text('ZORLUK SEÇ',
            style: TextStyle(
                color: OyunRenk.aksan, fontSize: 11, letterSpacing: 1.4,
                fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        ..._zorluklar.map((z) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Kutu(
                tikla: () => baslat(z.$1),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text(z.$2,
                          style: Theme.of(c).textTheme.titleMedium
                              ?.copyWith(color: OyunRenk.aksan)),
                      const Spacer(),
                      Text(z.$4,
                          style: const TextStyle(
                              color: OyunRenk.metinSonuk, fontSize: 10.5)),
                    ]),
                    const SizedBox(height: 7),
                    Text(z.$3,
                        style: Theme.of(c).textTheme.bodyMedium
                            ?.copyWith(height: 1.5)),
                  ],
                ),
              ),
            )),
        if (oyun.hata != null) ...[
          const SizedBox(height: 12),
          Not('${oyun.hata}', ikon: Icons.error_outline_sharp,
              renk: Renk.eksi),
        ],
      ],
    );
  }
}
