import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../servis/oyun.dart';
import '../tema.dart';

/// Emir onay animasyonu — "iletildi → gerçekleşti" akışı.
///
/// NEDEN ANİMASYON: emir vermek oyunun en önemli anı ve şu ana kadar
/// sessizce oluyordu (ekran kapanıyordu, o kadar). Onay olmadan
/// kullanıcı emrin gidip gitmediğinden emin olamıyor ve iki kez basıyor.
///
/// İki aşamalı: önce "İLETİLDİ", sonra gerçekleşme türüne göre
/// "GERÇEKLEŞTİ" ya da "EMİR DEFTERİNDE". İkisi arasındaki fark limit
/// emrinin ne olduğunu tek bakışta anlatıyor.
enum EmirSonucu { gerceklesti, beklemede }

Future<void> emirAnimasyonu(
  BuildContext c, {
  required EmirSonucu sonuc,
  required String sembol,
  required int adet,
  required double fiyat,
}) async {
  // Dokunsal geri bildirim: ekrana bakmadan da emrin gittiği anlaşılıyor.
  unawaited(HapticFeedback.mediumImpact());
  await showGeneralDialog(
    context: c,
    barrierDismissible: false,
    barrierColor: Colors.black.withValues(alpha: 0.72),
    transitionDuration: const Duration(milliseconds: 160),
    pageBuilder: (_, __, ___) => _EmirOnay(
        sonuc: sonuc, sembol: sembol, adet: adet, fiyat: fiyat),
  );
}

class _EmirOnay extends StatefulWidget {
  final EmirSonucu sonuc;
  final String sembol;
  final int adet;
  final double fiyat;
  const _EmirOnay({
    required this.sonuc, required this.sembol, required this.adet,
    required this.fiyat,
  });

  @override
  State<_EmirOnay> createState() => _EmirOnayDurum();
}

class _EmirOnayDurum extends State<_EmirOnay>
    with SingleTickerProviderStateMixin {
  int _asama = 0;   // 0: iletildi · 1: sonuç
  Timer? _t1, _t2;
  late final AnimationController _ac = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 320))
    ..forward();

  @override
  void initState() {
    super.initState();
    _t1 = Timer(const Duration(milliseconds: 520), () {
      if (mounted) {
        setState(() => _asama = 1);
        unawaited(widget.sonuc == EmirSonucu.gerceklesti
            ? HapticFeedback.heavyImpact()
            : HapticFeedback.selectionClick());
      }
    });
    _t2 = Timer(const Duration(milliseconds: 1500), () {
      if (mounted) Navigator.of(context).maybePop();
    });
  }

  @override
  void dispose() {
    _t1?.cancel();
    _t2?.cancel();
    _ac.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) {
    final gercek = widget.sonuc == EmirSonucu.gerceklesti;
    final bitti = _asama == 1;
    final renk = !bitti
        ? OyunRenk.metinSolgun
        : (gercek ? Renk.arti : OyunRenk.aksan);

    return Center(
      child: ScaleTransition(
        scale: CurvedAnimation(parent: _ac, curve: Curves.easeOutBack),
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 36),
          padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
          decoration: BoxDecoration(
            color: OyunRenk.panel,
            border: Border.all(color: renk, width: 1.6),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 220),
                child: Icon(
                  !bitti
                      ? Icons.upload_sharp
                      : (gercek
                          ? Icons.check_circle_sharp
                          : Icons.schedule_sharp),
                  key: ValueKey(bitti),
                  size: 40, color: renk,
                ),
              ),
              const SizedBox(height: 14),
              Text(
                  !bitti
                      ? 'EMİR İLETİLİYOR'
                      : (gercek ? 'GERÇEKLEŞTİ' : 'EMİR DEFTERİNDE'),
                  style: TextStyle(
                      color: renk, fontSize: 13, letterSpacing: 2,
                      fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              Text('${widget.sembol}  ·  ${widget.adet} adet',
                  style: const TextStyle(
                      color: OyunRenk.metin, fontSize: 15,
                      fontWeight: FontWeight.w700)),
              const SizedBox(height: 3),
              Text('${tl(widget.fiyat)} ₺',
                  style: const TextStyle(
                      color: OyunRenk.metinSolgun, fontSize: 13)),
              if (bitti && !gercek) ...[
                const SizedBox(height: 10),
                const Text('Fiyat buraya gelirse dolar.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        color: OyunRenk.metinSonuk, fontSize: 11.5,
                        height: 1.4)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ── gün sonu özeti ─────────────────────────────────────────────────────────

/// Günleri ilerlettikten sonra çıkan özet.
///
/// Öncesinde tek satırlık bir SnackBar vardı ve bir haftada dört şey
/// olduğunda hepsi tek satıra sıkışıp okunmuyordu. Hiçbir şey olmadıysa
/// bu kart hiç çıkmıyor — boş bildirim gürültüdür.
Future<void> gunOzetiGoster(BuildContext c, GunOzeti o) async {
  if (o.sessiz) return;
  unawaited(o.kapananlar.any((k) => k.sebep == 'stop')
      ? HapticFeedback.heavyImpact()
      : HapticFeedback.lightImpact());
  await showModalBottomSheet<void>(
    context: c,
    backgroundColor: OyunRenk.panel,
    shape: const RoundedRectangleBorder(borderRadius: kose),
    builder: (_) => _GunOzetiSayfa(o),
  );
}

class _GunOzetiSayfa extends StatelessWidget {
  final GunOzeti o;
  const _GunOzetiSayfa(this.o);

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 26),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('GÜN ${o.gun + 1}',
                style: const TextStyle(
                    color: OyunRenk.aksan, fontSize: 11.5,
                    letterSpacing: 1.6, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text(
                '${o.fark >= 0 ? '+' : ''}${tl(o.fark)} ₺  '
                '${yzd(o.farkYuzde, basamak: 1)}',
                style: TextStyle(
                    color: sem.yon(o.fark), fontWeight: FontWeight.w700,
                    fontSize: 14)),
          ]),
          const SizedBox(height: 14),

          for (final k in o.kapananlar)
            _satir(
              c,
              ikon: k.sebep == 'hedef'
                  ? Icons.check_circle_sharp
                  : Icons.shield_sharp,
              renk: k.kar >= 0 ? sem.arti : sem.eksi,
              baslik: '${k.sembol} · ${k.sebep} çalıştı',
              alt: '${k.adet} adet · ${tl(k.giris)} → ${tl(k.cikis)} ₺',
              sag: '${k.kar >= 0 ? '+' : ''}${tl(k.kar)} ₺',
            ),
          for (final e in o.dolanlar)
            _satir(
              c,
              ikon: Icons.playlist_add_check_sharp,
              renk: OyunRenk.aksan,
              baslik: '${e.sembol} · emrin doldu',
              alt: '${e.adet} adet · ${tl(e.fiyat)} ₺',
              sag: '',
            ),
          for (final e in o.iptaller)
            _satir(
              c,
              ikon: Icons.timer_off_sharp,
              renk: OyunRenk.metinSonuk,
              baslik: '${e.sembol} · emrin süresi doldu',
              alt: 'fiyat ${tl(e.fiyat)} ₺ seviyesine hiç gelmedi',
              sag: '',
            ),
        ],
      ),
    );
  }

  Widget _satir(BuildContext c,
      {required IconData ikon, required Color renk, required String baslik,
      required String alt, required String sag}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ikon, size: 17, color: renk),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(baslik,
                  style: const TextStyle(
                      color: OyunRenk.metin, fontSize: 13.5,
                      fontWeight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text(alt,
                  style: const TextStyle(
                      color: OyunRenk.metinSonuk, fontSize: 11.5)),
            ],
          ),
        ),
        if (sag.isNotEmpty)
          Text(sag,
              style: TextStyle(
                  color: renk, fontWeight: FontWeight.w700, fontSize: 13)),
      ]),
    );
  }
}
