import 'dart:async';

import 'package:flutter/material.dart';

import '../tema.dart';

/// Terminal açılış dizisi.
///
/// SAHTE BEKLEME DEĞİL: piyasa gerçekten üretiliyor (sunucuda 0,8-1,6 sn)
/// ve satırlar o sırada akıyor. Animasyon bittiğinde iş de bitmiş oluyor;
/// biri diğerini beklemiyor.
///
/// NEDEN VAR: "Sanal" sekmesine basınca başka bir uygulamaya geçtiğin
/// hissi, o geçişin kendisinden doğuyor. Ekranın anında değişmesi
/// sekme değiştirmek gibi hissettiriyordu; açılış dizisi bir eşik koyuyor.
class OyunAcilis extends StatefulWidget {
  /// Arka planda süren gerçek iş. Bitince animasyon da tamamlanıyor.
  final Future<void> Function() is_;
  final VoidCallback bitti;

  const OyunAcilis({super.key, required this.is_, required this.bitti});

  @override
  State<OyunAcilis> createState() => _OyunAcilisDurum();
}

class _OyunAcilisDurum extends State<OyunAcilis>
    with SingleTickerProviderStateMixin {
  static const _satirlar = [
    'terminal başlatılıyor',
    'piyasa üretiliyor',
    'hisse senetleri yükleniyor',
    'analist bağlanıyor',
    'haber akışı açılıyor',
    'emir defteri hazırlanıyor',
  ];

  int _adim = 0;
  bool _isBitti = false;
  Timer? _sayac;
  late final AnimationController _yanip;

  @override
  void initState() {
    super.initState();
    _yanip = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 700))
      ..repeat(reverse: true);

    // Satırlar akıyor; gerçek iş paralel sürüyor.
    _sayac = Timer.periodic(const Duration(milliseconds: 260), (t) {
      if (!mounted) return;
      if (_adim < _satirlar.length) {
        setState(() => _adim++);
      } else if (_isBitti) {
        t.cancel();
        // Son satır bir an dursun: hemen kaybolan "HAZIR" okunmuyor.
        Future.delayed(const Duration(milliseconds: 340), () {
          if (mounted) widget.bitti();
        });
      }
    });

    widget.is_().whenComplete(() {
      if (mounted) setState(() => _isBitti = true);
    });
  }

  @override
  void dispose() {
    _sayac?.cancel();
    _yanip.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) {
    final hepsi = _adim >= _satirlar.length;
    return Container(
      color: OyunRenk.zemin,
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('MİDAS',
                style: TextStyle(
                    color: OyunRenk.metinSonuk, fontSize: 12,
                    letterSpacing: 5)),
            const SizedBox(height: 4),
            const Text('SANAL BORSA',
                style: TextStyle(
                    color: OyunRenk.aksan, fontSize: 26,
                    fontWeight: FontWeight.w700, letterSpacing: 3.5)),
            const SizedBox(height: 3),
            Container(height: 2, width: 210, color: OyunRenk.aksan),
            const SizedBox(height: 26),

            ...List.generate(_satirlar.length, (i) {
              final gorunur = i < _adim;
              final tamam = i < _adim - 1 || (i == _adim - 1 && _isBitti) ||
                  (hepsi && _isBitti);
              return AnimatedOpacity(
                opacity: gorunur ? 1 : 0,
                duration: const Duration(milliseconds: 180),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(children: [
                    SizedBox(
                      width: 18,
                      child: Text(tamam ? '✓' : '▸',
                          style: TextStyle(
                              color: tamam
                                  ? OyunRenk.aksan
                                  : OyunRenk.metinSonuk,
                              fontSize: 13)),
                    ),
                    Text(_satirlar[i],
                        style: TextStyle(
                            color: tamam
                                ? OyunRenk.metin
                                : OyunRenk.metinSolgun,
                            fontSize: 13)),
                    if (!tamam && gorunur) ...[
                      const SizedBox(width: 6),
                      const _Nokta(),
                    ],
                  ]),
                ),
              );
            }),

            const SizedBox(height: 22),
            // İlerleme: gerçek işin durumunu yansıtıyor, süre saymıyor.
            SizedBox(
              width: 210,
              child: Row(
                children: List.generate(_satirlar.length, (i) {
                  final dolu = i < _adim && (_isBitti || i < _adim - 1);
                  return Expanded(
                    child: Container(
                      height: 5,
                      margin: EdgeInsets.only(
                          right: i == _satirlar.length - 1 ? 0 : 3),
                      color: dolu ? OyunRenk.aksan : OyunRenk.cizgi,
                    ),
                  );
                }),
              ),
            ),
            const SizedBox(height: 20),
            FadeTransition(
              opacity: _yanip,
              child: Text(
                  hepsi && _isBitti ? 'HAZIR' : 'BEKLE',
                  style: TextStyle(
                      color: hepsi && _isBitti
                          ? OyunRenk.aksan
                          : OyunRenk.metinSonuk,
                      fontSize: 12, letterSpacing: 3,
                      fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}

/// Yanıp sönen üç nokta — "çalışıyor" işareti.
class _Nokta extends StatefulWidget {
  const _Nokta();
  @override
  State<_Nokta> createState() => _NoktaDurum();
}

class _NoktaDurum extends State<_Nokta> {
  int _n = 0;
  Timer? _t;

  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(milliseconds: 300), (_) {
      if (mounted) setState(() => _n = (_n + 1) % 4);
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) => SizedBox(
        width: 22,
        child: Text('.' * _n,
            style: const TextStyle(
                color: OyunRenk.aksan, fontSize: 13, letterSpacing: 1.5)),
      );
}
