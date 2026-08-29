import 'package:flutter/material.dart';

import '../parca/ipucu.dart';
import '../tema.dart';

/// Oyuna ilk girişte açılan dört adımlık tanıtım.
///
/// NEDEN VAR: oyun şu ana kadar borsayı bilen birine göre yazılmıştı.
/// "Stop", "hedef", "limit emri" bilmeyene hiçbir şey ifade etmiyor ve
/// bilmeyen kişi ilk ekranda kayboluyor.
///
/// DÖRT ADIM, HER BİRİ TEK FİKİR: daha fazlası okunmuyor, daha azı
/// eksik bırakıyor. Tanıtım bir kez çıkıyor, `?` ile geri geliyor.
class OyunTanitim extends StatefulWidget {
  final VoidCallback bitti;
  const OyunTanitim({super.key, required this.bitti});

  @override
  State<OyunTanitim> createState() => _OyunTanitimDurum();
}

class _Adim {
  final IconData ikon;
  final String baslik, metin;
  final Widget? gorsel;
  const _Adim(this.ikon, this.baslik, this.metin, {this.gorsel});
}

class _OyunTanitimDurum extends State<OyunTanitim> {
  final _sayfa = PageController();
  int _adim = 0;

  late final List<_Adim> _adimlar = [
    const _Adim(
      Icons.casino_sharp,
      'Bu bir oyun',
      'Sanal borsa. Gerçek para yok, kaybedecek bir şeyin yok.\n\n'
      'Hisse kodları gerçek ama fiyatları biz uyduruyoruz — burada olan '
      'hiçbir şey gerçek borsada olmadı. Her yeni oyun bir öncekinden '
      'farklı.',
    ),
    _Adim(
      Icons.trending_up_sharp,
      'Nasıl kazanılır',
      'Bir şirketin küçük bir parçasını (hisse) satın alırsın. Fiyatı '
      'çıkarsa kâr, düşerse zarar edersin.\n\n'
      'Ucuza al, pahalıya sat. Aradaki fark senin.',
      gorsel: const _AlSatGorsel(),
    ),
    _Adim(
      Icons.shield_sharp,
      'Alırken iki fiyat belirlersin',
      'STOP: "buraya düşerse çık, daha fazla kaybetmeyeyim."\n'
      'HEDEF: "buraya çıkarsa sat, kârı cebe koyayım."\n\n'
      'İkisini alım anında koyarsın; sonra sistem senin yerine izler. '
      'Fiyat hangisine önce değerse pozisyon orada kapanır.',
      gorsel: const _StopHedefGorsel(),
    ),
    const _Adim(
      Icons.fast_forward_sharp,
      'Zamanı sen ilerletirsin',
      '"+1 gün" düğmesine bastıkça piyasa ilerler. Gerçek borsada bir ay '
      'süren şey burada bir dakikada biter.\n\n'
      'Yolda analistin önerileri ve haberler gelir. Analist her zaman '
      'haklı değil, haberler bazen yanıltır — kime ne kadar '
      'güveneceğini burada öğrenirsin.',
    ),
  ];

  @override
  void dispose() {
    _sayfa.dispose();
    super.dispose();
  }

  void _ileri() {
    if (_adim < _adimlar.length - 1) {
      _sayfa.nextPage(
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOut);
    } else {
      _kapat();
    }
  }

  Future<void> _kapat() async {
    await ipucu.okundu('tanitim');
    if (mounted) widget.bitti();
  }

  @override
  Widget build(BuildContext c) {
    final son = _adim == _adimlar.length - 1;
    return Container(
      color: OyunRenk.zemin,
      child: SafeArea(
        child: Column(
          children: [
            // ── üst: adım göstergesi ve atla
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 12, 4),
              child: Row(children: [
                ...List.generate(_adimlar.length, (i) => Container(
                      width: i == _adim ? 22 : 8,
                      height: 4,
                      margin: const EdgeInsets.only(right: 5),
                      color: i <= _adim ? OyunRenk.aksan : OyunRenk.cizgi,
                    )),
                const Spacer(),
                TextButton(
                  onPressed: _kapat,
                  style: TextButton.styleFrom(
                      foregroundColor: OyunRenk.metinSonuk),
                  child: const Text('ATLA'),
                ),
              ]),
            ),

            Expanded(
              child: PageView.builder(
                controller: _sayfa,
                onPageChanged: (i) => setState(() => _adim = i),
                itemCount: _adimlar.length,
                itemBuilder: (_, i) => _sayfaGovde(c, _adimlar[i], i),
              ),
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 22),
              child: SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton(
                  onPressed: _ileri,
                  style: FilledButton.styleFrom(
                      backgroundColor: OyunRenk.aksan,
                      foregroundColor: OyunRenk.zemin,
                      shape:
                          const RoundedRectangleBorder(borderRadius: kose)),
                  child: Text(son ? 'BAŞLAYALIM' : 'DEVAM'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sayfaGovde(BuildContext c, _Adim a, int i) => SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(11),
              decoration: BoxDecoration(
                border: Border.all(color: OyunRenk.aksan, width: 1.5),
              ),
              child: Icon(a.ikon, size: 26, color: OyunRenk.aksan),
            ),
            const SizedBox(height: 18),
            Text('${i + 1} / ${_adimlar.length}',
                style: const TextStyle(
                    color: OyunRenk.metinSonuk, fontSize: 11,
                    letterSpacing: 1.4)),
            const SizedBox(height: 6),
            Text(a.baslik,
                style: const TextStyle(
                    color: OyunRenk.metin, fontSize: 23,
                    fontWeight: FontWeight.w700, height: 1.25)),
            const SizedBox(height: 16),
            Text(a.metin,
                style: const TextStyle(
                    color: OyunRenk.metinSolgun, fontSize: 14.5,
                    height: 1.65)),
            if (a.gorsel != null) ...[
              const SizedBox(height: 22),
              a.gorsel!,
            ],
          ],
        ),
      );
}

// ── küçük anlatım görselleri ───────────────────────────────────────────────
//
// Metin tek başına soyut kalıyor: "ucuza al pahalıya sat" cümlesini
// okuyan biri sayıyı görene kadar kavramıyor.

class _AlSatGorsel extends StatelessWidget {
  const _AlSatGorsel();

  @override
  Widget build(BuildContext c) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: OyunRenk.panel,
          border: Border.all(color: OyunRenk.cizgi),
        ),
        child: Column(children: [
          _satir(c, 'Aldın', '10 adet × 100 ₺', '1.000 ₺',
              OyunRenk.metinSolgun),
          const SizedBox(height: 10),
          _satir(c, 'Fiyat çıktı', '10 adet × 120 ₺', '1.200 ₺',
              OyunRenk.metin),
          const SizedBox(height: 12),
          Container(height: 1, color: OyunRenk.cizgi),
          const SizedBox(height: 12),
          _satir(c, 'Kârın', '', '+200 ₺', Renk.arti),
        ]),
      );

  Widget _satir(BuildContext c, String sol, String orta, String sag,
          Color renk) =>
      Row(children: [
        SizedBox(
          width: 92,
          child: Text(sol,
              style: TextStyle(color: renk, fontSize: 12.5)),
        ),
        Expanded(
          child: Text(orta,
              style: const TextStyle(
                  color: OyunRenk.metinSonuk, fontSize: 12)),
        ),
        Text(sag,
            style: TextStyle(
                color: renk, fontSize: 13.5, fontWeight: FontWeight.w700)),
      ]);
}

class _StopHedefGorsel extends StatelessWidget {
  const _StopHedefGorsel();

  @override
  Widget build(BuildContext c) => Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        decoration: BoxDecoration(
          color: OyunRenk.panel,
          border: Border.all(color: OyunRenk.cizgi),
        ),
        child: Column(children: [
          _seviye(c, 'HEDEF', '120 ₺', 'buraya çıkarsa sat', Renk.arti),
          const SizedBox(height: 9),
          _seviye(c, 'ALDIN', '100 ₺', '', OyunRenk.aksan),
          const SizedBox(height: 9),
          _seviye(c, 'STOP', '92 ₺', 'buraya düşerse çık', Renk.eksi),
        ]),
      );

  Widget _seviye(BuildContext c, String etiket, String fiyat, String not,
          Color renk) =>
      Row(children: [
        Container(width: 4, height: 26, color: renk),
        const SizedBox(width: 11),
        SizedBox(
          width: 58,
          child: Text(etiket,
              style: TextStyle(
                  color: renk, fontSize: 11, fontWeight: FontWeight.w700,
                  letterSpacing: 0.8)),
        ),
        SizedBox(
          width: 56,
          child: Text(fiyat,
              style: const TextStyle(
                  color: OyunRenk.metin, fontSize: 13,
                  fontWeight: FontWeight.w700)),
        ),
        Expanded(
          child: Text(not,
              style: const TextStyle(
                  color: OyunRenk.metinSonuk, fontSize: 11.5)),
        ),
      ]);
}
