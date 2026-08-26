import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../parca/kart.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../tema.dart';

/// Sermaye defteri.
///
/// Tek işi var ama önemli: yatırdığın parayı kazandığın paradan ayırmak.
/// "Portföyüm 1.400 TL" cümlesi tek başına performans değildir.
class SermayeEkran extends StatelessWidget {
  const SermayeEkran({super.key});

  @override
  Widget build(BuildContext c) => ListenableBuilder(
        listenable: depo,
        builder: (_, __) {
          final h = depo.hareketler.reversed.toList();
          final net = depo.netYatirilan;
          final kar = depo.gerceklesenKar;
          final oran = depo.gerceklesenGetiriYuzde;
          final sem = Sem(c);

          return Scaffold(
            appBar: AppBar(
              title: const Text('SERMAYE'),
              actions: [
                IconButton(
                  tooltip: 'Toplamı elle ayarla',
                  icon: const Icon(Icons.tune_sharp, size: 20),
                  onPressed: () => _toplamAyarla(c),
                ),
              ],
            ),
            body: ListView(
              padding: const EdgeInsets.only(bottom: 120),
              children: [
                _Ozet(net: net, kar: kar, oran: oran),
                const Baslik('Dağılım',
                    alt: 'Nakit + açık pozisyonların maliyeti = toplam sermaye'),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Kutu(
                    child: Column(
                      children: [
                        Satir('Nakit', '${tl(depo.nakit)} ₺'),
                        const Divider(height: 14),
                        Satir('Açık pozisyonlar (maliyet)',
                            '${tl(depo.toplamMaliyet)} ₺',
                            not: depo.pozisyonlar.isEmpty
                                ? 'açık pozisyon yok'
                                : '${depo.pozisyonlar.length} pozisyon'),
                        const Divider(height: 14),
                        Satir('Toplam sermaye',
                            '${tl(depo.ayarlar.sermaye)} ₺',
                            kalin: true, renk: sem.aksan),
                      ],
                    ),
                  ),
                ),
                Baslik('Hareketler', alt: '${h.length} kayıt'),
                if (h.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16),
                    child: Kutu(
                      child: Text('Henüz kayıt yok. Aşağıdan para ekle.'),
                    ),
                  )
                else
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Kutu(
                      ic: EdgeInsets.zero,
                      child: Column(
                        children: [
                          for (var i = 0; i < h.length; i++) ...[
                            if (i > 0) const Divider(height: 1),
                            _HareketSatir(
                              h[i],
                              sil: () => _sil(c, depo.hareketler.length - 1 - i),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16),
                  child: Not(
                    'Kâr ve zarar kayıtları pozisyon kapattığında otomatik '
                    'yazılır. Elle eklemen gereken tek şey para giriş/çıkışı.',
                    ikon: Icons.info_outline_sharp,
                  ),
                ),
              ],
            ),
            floatingActionButton: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _paraGir(c, yatirma: false),
                  icon: const Icon(Icons.remove_sharp, size: 17),
                  label: const Text('ÇEK'),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: () => _paraGir(c, yatirma: true),
                  icon: const Icon(Icons.add_sharp, size: 17),
                  label: const Text('PARA EKLE'),
                ),
              ],
            ),
          );
        },
      );

  Future<void> _sil(BuildContext c, int sira) async {
    final onay = await showDialog<bool>(
      context: c,
      builder: (d) => AlertDialog(
        title: const Text('KAYDI SİL'),
        content: const Text(
            'Bu kayıt silinince toplam sermaye de o kadar değişir. '
            'Emin misin?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d, false),
              child: const Text('VAZGEÇ')),
          FilledButton(
              onPressed: () => Navigator.pop(d, true),
              child: const Text('SİL')),
        ],
      ),
    );
    if (onay == true) await depo.paraSil(sira);
  }

  Future<void> _paraGir(BuildContext c, {required bool yatirma}) async {
    final tutar = TextEditingController();
    final not = TextEditingController();
    final sonuc = await showDialog<double>(
      context: c,
      builder: (d) => AlertDialog(
        title: Text(yatirma ? 'PARA EKLE' : 'PARA ÇEK'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: tutar,
              autofocus: true,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))
              ],
              decoration: const InputDecoration(
                  labelText: 'Tutar', suffixText: '₺'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: not,
              decoration: const InputDecoration(
                  labelText: 'Not (isteğe bağlı)',
                  hintText: 'ör. maaştan ayırdım'),
            ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d),
              child: const Text('VAZGEÇ')),
          FilledButton(
            onPressed: () {
              final v =
                  double.tryParse(tutar.text.trim().replaceAll(',', '.'));
              if (v != null && v > 0) Navigator.pop(d, v);
            },
            child: const Text('KAYDET'),
          ),
        ],
      ),
    );
    if (sonuc == null) return;
    await depo.paraEkle(ParaHareketi(
      tarih: DateTime.now().toIso8601String().substring(0, 10),
      tutar: yatirma ? sonuc : -sonuc,
      tur: yatirma ? HareketTur.yatirma : HareketTur.cekme,
      not: not.text.trim(),
    ));
  }

  Future<void> _toplamAyarla(BuildContext c) async {
    final alan =
        TextEditingController(text: depo.ayarlar.sermaye.toStringAsFixed(0));
    var sebep = HareketTur.yatirma;

    final sonuc = await showDialog<double>(
      context: c,
      builder: (d) => StatefulBuilder(
        builder: (d2, yenile) => AlertDialog(
          title: const Text('TOPLAMI HİZALA'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Midas\'taki gerçek toplamınla uyuşmuyorsa buradan hizala.',
                  style: TextStyle(fontSize: 12, color: Renk.metinSolgun),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: alan,
                  autofocus: true,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[0-9.,]'))
                  ],
                  decoration: const InputDecoration(
                      labelText: 'Toplam sermaye', suffixText: '₺'),
                ),
                const SizedBox(height: 16),
                const Text('FARK NEDEN OLUŞTU?',
                    style: TextStyle(
                        fontSize: 10,
                        letterSpacing: 1.2,
                        fontWeight: FontWeight.w700,
                        color: Renk.aksan)),
                const SizedBox(height: 8),
                // Bu soru şart: aynı fark, sebebine göre "yatırdığın para"yı
                // ya da "kazandığın para"yı değiştirir. Karıştırılırsa getiri
                // yüzdesi anlamsızlaşır.
                for (final s in const [
                  (HareketTur.yatirma, 'Para yatırdım / çektim',
                      'Uygulamaya girmediğim para hareketi oldu'),
                  (HareketTur.kar, 'İşlem yaptım',
                      'Uygulama dışında alıp sattım, kâr/zarar oluştu'),
                  (HareketTur.duzeltme, 'Bilmiyorum',
                      'Küçük fark; getiri hesabına katılmasın'),
                ])
                  InkWell(
                    onTap: () => yenile(() => sebep = s.$1),
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.all(9),
                      decoration: BoxDecoration(
                        borderRadius: kose,
                        color: sebep == s.$1 ? Renk.panelUst : null,
                        border: Border.all(
                            color: sebep == s.$1 ? Renk.aksan : Renk.cizgi),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(sebep == s.$1 ? '[x]' : '[ ]',
                              style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: sebep == s.$1
                                      ? Renk.aksan
                                      : Renk.metinSonuk)),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(s.$2,
                                    style: const TextStyle(
                                        fontSize: 12.5,
                                        fontWeight: FontWeight.w700)),
                                const SizedBox(height: 2),
                                Text(s.$3,
                                    style: const TextStyle(
                                        fontSize: 11,
                                        height: 1.3,
                                        color: Renk.metinSonuk)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(d2), child: const Text('VAZGEÇ')),
            FilledButton(
              onPressed: () {
                final v =
                    double.tryParse(alan.text.trim().replaceAll(',', '.'));
                if (v != null && v >= 0) Navigator.pop(d2, v);
              },
              child: const Text('HİZALA'),
            ),
          ],
        ),
      ),
    );
    if (sonuc != null) await depo.sermayeyiAyarla(sonuc, sebep: sebep);
  }
}

class _Ozet extends StatelessWidget {
  final double net, kar;
  final double? oran;
  const _Ozet({required this.net, required this.kar, this.oran});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: Kutu(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('TOPLAM SERMAYE',
                style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.4,
                    fontWeight: FontWeight.w700,
                    color: Renk.metinSonuk)),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text(tl(depo.ayarlar.sermaye),
                    style: const TextStyle(
                        fontSize: 34,
                        fontWeight: FontWeight.w700,
                        height: 1.1,
                        color: Renk.metin,
                        fontFeatures: [FontFeature.tabularFigures()])),
                const SizedBox(width: 5),
                const Text('₺',
                    style: TextStyle(fontSize: 17, color: Renk.metinSolgun)),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(height: 1),
            const SizedBox(height: 12),
            Satir('Yatırdığın para', '${tl(net)} ₺',
                not: 'kâr/zarar hariç, senin cebinden çıkan'),
            Satir('Gerçekleşen kâr/zarar', '${tl(kar)} ₺',
                renk: sem.yon(kar), not: 'kapanmış pozisyonlardan'),
            if (oran != null)
              Satir('Gerçekleşen getiri', yzd(oran),
                  renk: sem.yon(oran), kalin: true),
            const SizedBox(height: 10),
            const Not(
              'Açık pozisyonların kâğıt üstündeki kârı buraya dahil değil — '
              'o daha gerçekleşmedi. Portföy sekmesi onu ayrıca gösterir.',
              ikon: Icons.warning_amber_sharp,
              renk: Renk.uyari,
            ),
            // Düzeltmeler ne yatırılan paraya ne kâra sayılır; birikirse
            // getiri yüzdesi sessizce anlamını yitirir.
            if (depo.duzeltmeToplami.abs() > 0.005) ...[
              const SizedBox(height: 8),
              Not(
                'Defterde ${tl(depo.duzeltmeToplami)} ₺ tutarında '
                '"bilmiyorum" düzeltmesi var. Bu tutar ne yatırdığın paraya '
                'ne kârına sayılıyor, yani yukarıdaki getiri yüzdesi o kadar '
                'eksik anlatıyor.',
                ikon: Icons.help_outline_sharp,
                renk: Renk.metinSolgun,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HareketSatir extends StatelessWidget {
  final ParaHareketi h;
  final VoidCallback sil;
  const _HareketSatir(this.h, {required this.sil});

  @override
  Widget build(BuildContext c) {
    final artik = h.tutar >= 0;
    final renk = switch (h.tur) {
      HareketTur.yatirma => Renk.aksan,
      HareketTur.cekme => Renk.metinSolgun,
      HareketTur.kar => Renk.arti,
      HareketTur.zarar => Renk.eksi,
      HareketTur.duzeltme => Renk.uyari,
    };
    // Kâr/zarar kayıtları otomatik yazılır; elle silinirse pozisyon
    // geçmişiyle defter çelişir. Sadece para giriş/çıkışı silinebilir.
    final silinebilir = h.sermayeGirisi || h.tur == HareketTur.duzeltme;

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 11, 6, 11),
      child: Row(
        children: [
          Container(width: 3, height: 30, color: renk),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(h.etiket,
                    style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        color: renk)),
                const SizedBox(height: 2),
                Text(
                  h.not.isEmpty ? h.tarih : '${h.tarih} · ${h.not}',
                  style: const TextStyle(
                      fontSize: 11, color: Renk.metinSonuk, height: 1.3),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text('${artik ? '+' : ''}${tl(h.tutar)}',
              style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: renk,
                  fontFeatures: const [FontFeature.tabularFigures()])),
          if (silinebilir)
            IconButton(
              icon: const Icon(Icons.close_sharp, size: 15),
              visualDensity: VisualDensity.compact,
              onPressed: sil,
            )
          else
            const SizedBox(width: 40),
        ],
      ),
    );
  }
}
