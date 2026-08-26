import 'package:flutter/material.dart';
import '../tema.dart';
import '../servis/modeller.dart';

/// Bölüm başlığı — ekranlar arası tutarlı hiyerarşi.
/// Terminal bölüm ayracı gibi: solda dolu blok, sağda çizgi.
class Baslik extends StatelessWidget {
  final String metin;
  final String? alt;
  final Widget? sag;
  const Baslik(this.metin, {super.key, this.alt, this.sag});

  @override
  Widget build(BuildContext c) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 22, 16, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(width: 8, height: 14, color: Renk.aksan),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    metin.toUpperCase(),
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                          color: Renk.aksan,
                          letterSpacing: 1.4,
                          fontSize: 11.5,
                        ),
                  ),
                ),
                if (sag != null) sag!,
              ],
            ),
            if (alt != null)
              Padding(
                padding: const EdgeInsets.only(left: 16, top: 4),
                child: Text(alt!,
                    style: Theme.of(c)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: Renk.metinSolgun)),
              ),
          ],
        ),
      );
}

/// Etiket–değer satırı. Sayılar sağa hizalı: göz tek sütunu tarar.
class Satir extends StatelessWidget {
  final String etiket;
  final String deger;
  final Color? renk;
  final String? not;
  final bool kalin;
  const Satir(this.etiket, this.deger,
      {super.key, this.renk, this.not, this.kalin = false});

  @override
  Widget build(BuildContext c) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(etiket, style: Theme.of(c).textTheme.bodyMedium),
                  if (not != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2, right: 8),
                      child: Text(not!,
                          style: Theme.of(c).textTheme.bodySmall?.copyWith(
                              color: Renk.metinSolgun, height: 1.35)),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Text(deger,
                style: Theme.of(c).textTheme.bodyMedium?.copyWith(
                      fontWeight: kalin ? FontWeight.w700 : FontWeight.w400,
                      color: renk,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    )),
          ],
        ),
      );
}

class Kutu extends StatelessWidget {
  final Widget child;
  final EdgeInsets? ic;
  final VoidCallback? tikla;
  const Kutu({super.key, required this.child, this.ic, this.tikla});

  @override
  Widget build(BuildContext c) {
    final k = Card(
      child: Padding(padding: ic ?? const EdgeInsets.all(16), child: child),
    );
    if (tikla == null) return k;
    return InkWell(borderRadius: kose, onTap: tikla, child: k);
  }
}

class Rozet extends StatelessWidget {
  final String metin;
  final Color? renk;
  final bool dolu;
  const Rozet(this.metin, {super.key, this.renk, this.dolu = false});

  @override
  Widget build(BuildContext c) {
    final r = renk ?? Renk.aksan;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: dolu ? r : Colors.transparent,
        borderRadius: kose,
        border: Border.all(color: r),
      ),
      child: Text(metin.toUpperCase(),
          style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
              color: dolu ? Renk.zemin : r)),
    );
  }
}

/// 0-100 skoru blok göstergeyle verir.
/// Halka değil: piksel ızgarasında daire yamuk görünür ve dolgu oranı
/// gözle okunmaz. On blok, her biri %10 — sayılabilir bir ölçek.
class SkorHalka extends StatelessWidget {
  final num? skor;
  final double boyut;
  final String? alt;
  const SkorHalka(this.skor, {super.key, this.boyut = 62, this.alt});

  @override
  Widget build(BuildContext c) {
    final renk = Sem(c).skor(skor);
    final dolu = ((skor ?? 0) / 10).clamp(0, 10).round();
    final blokEn = boyut / 10;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(skor == null ? '—' : skor!.toStringAsFixed(0),
            style: TextStyle(
                fontSize: boyut * 0.36,
                fontWeight: FontWeight.w700,
                color: renk,
                height: 1.1,
                fontFeatures: const [FontFeature.tabularFigures()])),
        const SizedBox(height: 5),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(
            10,
            (i) => Container(
              width: blokEn - 1.5,
              height: 7,
              margin: const EdgeInsets.only(right: 1.5),
              color: i < dolu ? renk : Renk.panelUst,
            ),
          ),
        ),
        if (alt != null) ...[
          const SizedBox(height: 4),
          Text(alt!.toUpperCase(),
              style: const TextStyle(
                  fontSize: 9,
                  letterSpacing: 0.8,
                  fontWeight: FontWeight.w700,
                  color: Renk.metinSonuk)),
        ],
      ],
    );
  }
}

/// Hata görünümü — sorunu VE ne yapılacağını söyler.
class HataGorunum extends StatelessWidget {
  final Object hata;
  final VoidCallback? tekrar;
  const HataGorunum(this.hata, {super.key, this.tekrar});

  @override
  Widget build(BuildContext c) {
    final api = hata is ApiHata ? hata as ApiHata : null;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('[ ! ]',
                style: TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 2,
                    color: Renk.eksi)),
            const SizedBox(height: 14),
            Text(api?.mesaj ?? 'Bir şeyler ters gitti',
                textAlign: TextAlign.center,
                style: Theme.of(c).textTheme.titleMedium),
            if (api?.oneri != null) ...[
              const SizedBox(height: 10),
              Text(api!.oneri!,
                  textAlign: TextAlign.center,
                  style: Theme.of(c)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: Renk.metinSolgun, height: 1.5)),
            ],
            if (tekrar != null) ...[
              const SizedBox(height: 18),
              OutlinedButton(
                  onPressed: tekrar, child: const Text('TEKRAR DENE')),
            ],
          ],
        ),
      ),
    );
  }
}

class Bos extends StatelessWidget {
  final IconData ikon;
  final String baslik;
  final String? alt;
  final Widget? eylem;
  const Bos(this.ikon, this.baslik, {super.key, this.alt, this.eylem});

  @override
  Widget build(BuildContext c) => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(
                  border: Border.all(color: Renk.cizgi),
                  borderRadius: kose,
                ),
                child: Icon(ikon, size: 26, color: Renk.metinSonuk),
              ),
              const SizedBox(height: 14),
              Text(baslik,
                  textAlign: TextAlign.center,
                  style: Theme.of(c).textTheme.titleMedium),
              if (alt != null) ...[
                const SizedBox(height: 8),
                Text(alt!,
                    textAlign: TextAlign.center,
                    style: Theme.of(c)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: Renk.metinSolgun, height: 1.5)),
              ],
              if (eylem != null) ...[const SizedBox(height: 18), eylem!],
            ],
          ),
        ),
      );
}

/// Yükleniyor — dönen halka yerine kayan blok şeridi.
class Yukleniyor extends StatefulWidget {
  final String? mesaj;
  const Yukleniyor({super.key, this.mesaj});

  @override
  State<Yukleniyor> createState() => _YukleniyorDurum();
}

class _YukleniyorDurum extends State<Yukleniyor>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext c) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedBuilder(
              animation: _c,
              builder: (_, __) {
                const n = 12;
                final bas = (_c.value * n).floor();
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(n, (i) {
                    // Üç bloklu bir dalga soldan sağa kayar.
                    final d = (i - bas + n) % n;
                    final aktif = d < 3;
                    return Container(
                      width: 7,
                      height: 12,
                      margin: const EdgeInsets.only(right: 2),
                      color: aktif ? Renk.aksan : Renk.panelUst,
                    );
                  }),
                );
              },
            ),
            if (widget.mesaj != null) ...[
              const SizedBox(height: 16),
              Text(widget.mesaj!,
                  textAlign: TextAlign.center,
                  style: Theme.of(c)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: Renk.metinSolgun)),
            ],
          ],
        ),
      );
}

/// Uyarı/bilgi kutusu — davranışsal uyarılar ve tuzak notları için.
class Not extends StatelessWidget {
  final String metin;
  final IconData ikon;
  final Color? renk;
  final String? baslik;
  const Not(this.metin,
      {super.key, this.ikon = Icons.info_outline_sharp, this.renk, this.baslik});

  @override
  Widget build(BuildContext c) {
    final r = renk ?? Renk.metinSolgun;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
      decoration: BoxDecoration(
        color: Renk.panelUst,
        borderRadius: kose,
        border: Border(
          left: BorderSide(color: r, width: 4),
          top: const BorderSide(color: Renk.cizgi),
          right: const BorderSide(color: Renk.cizgi),
          bottom: const BorderSide(color: Renk.cizgi),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(ikon, size: 16, color: r),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (baslik != null) ...[
                  Text(baslik!.toUpperCase(),
                      style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 11,
                          letterSpacing: 0.8,
                          color: r)),
                  const SizedBox(height: 4),
                ],
                Text(metin,
                    style:
                        Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
