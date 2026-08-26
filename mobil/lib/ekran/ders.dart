import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/egitmen.dart';
import '../parca/ders_gorsel.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Ders okuma ekranı.
///
/// Bölümler bilinçli sırada: önce ana anlatım, sonra örnek, sonra BIST özeli,
/// en sonda TUZAK. Tuzak sona konur çünkü konuyu anlamadan "yaygın hata"yı
/// okumak, hatayı akılda kalıcı hale getirir.
class DersEkran extends StatefulWidget {
  final String kod;
  const DersEkran(this.kod, {super.key});
  @override
  State<DersEkran> createState() => _DersDurum();
}

class _DersDurum extends State<DersEkran> {
  Ders? _d;
  EgitmenModul? _m;
  bool _isaretli = false;
  bool _yukleniyor = true;
  Map<String, dynamic>? _gorsel;

  @override
  void initState() {
    super.initState();
    _baslat();
  }

  /// Ders bankası önbellekte yoksa ÖNCE onu çeker.
  ///
  /// Neden gerekli: bu ekrana artık yalnızca müfredattan gelinmiyor —
  /// "Günün dersi" kartı doğrudan buraya atlıyor. Banka yalnızca müfredat
  /// ekranı açıldığında indiriliyordu; temiz kurulumda karta basan
  /// kullanıcı "Ders bulunamadı" görüyordu.
  Future<void> _baslat() async {
    if (!egitmen.mufredatVar) {
      try {
        await egitmen.mufredatKaydet(await depo.api.egitmenMufredat());
      } catch (_) {
        // sunucuya ulaşılamadı: aşağıda "ders bulunamadı" gösterilir
      }
    }
    if (!mounted) return;
    final d = egitmen.ders(widget.kod);
    setState(() {
      _d = d;
      _m = egitmen.dersModulu(widget.kod);
      _isaretli = egitmen.dersKayit[widget.kod]?.isaretli ?? false;
      _yukleniyor = false;
    });
    // Ekranı açmak okundu saymak için yeterli — kullanıcı geri dönebilir.
    if (d != null) egitmen.dersOkundu(widget.kod);
    _gorseliGetir();
  }

  /// Görsel AYRI çekilir ve gecikmeli gelir: bazıları (korelasyon) tarama
  /// gerektiriyor. Ders metni onları beklemez — okumaya hemen başlanır,
  /// grafik hazır olunca yerine oturur. Hata olursa sessizce yok sayılır;
  /// sunucuya ulaşılamadığı için ders okunamaz hâle gelmesin.
  Future<void> _gorseliGetir() async {
    try {
      final g = await depo.api.dersGorseli(widget.kod);
      if (!mounted || g['yok'] == true) return;
      setState(() => _gorsel = g);
    } catch (_) {
      // sessiz: grafik olmadan da ders tamdır
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    if (_yukleniyor) {
      return Scaffold(
        appBar: AppBar(title: const Text('Ders')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (_d == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Ders')),
        body: const Bos(Icons.menu_book_sharp, 'Ders bulunamadı'),
      );
    }
    final d = _d!;
    return Scaffold(
      appBar: AppBar(
        title: Text(_m?.ad ?? 'Ders'),
        actions: [
          IconButton(
            icon: Icon(_isaretli ? Icons.bookmark_sharp : Icons.bookmark_border_sharp),
            tooltip: 'Buna dönmem lazım',
            color: _isaretli ? sem.uyari : null,
            onPressed: () async {
              await egitmen.dersIsaretle(d.kod, !_isaretli);
              if (mounted) setState(() => _isaretli = !_isaretli);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 40),
        children: [
          Row(children: [
            Rozet(d.kod, renk: sem.aksan),
            const SizedBox(width: 8),
            Text('~${d.sure} dk okuma',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
          ]),
          const SizedBox(height: 12),
          Text(d.baslik,
              style: Theme.of(c).textTheme.headlineSmall?.copyWith(height: 1.25)),
          const SizedBox(height: 10),
          Text(d.ozet,
              style: Theme.of(c).textTheme.titleMedium?.copyWith(
                  color: sem.aksan, height: 1.45, fontWeight: FontWeight.w500)),
          const SizedBox(height: 20),
          const Divider(),
          const SizedBox(height: 18),
          _metin(c, d.icerik),
          // Grafik anlatımdan SONRA: bağlamı kurmadan grafiğe bakan,
          // grafikte ne göreceğini bilmiyor.
          if (_gorsel != null) ...[
            const SizedBox(height: 22),
            DersGorsel(_gorsel!),
          ],
          if (d.ornek.isNotEmpty) ...[
            const SizedBox(height: 24),
            _bolum(c, 'ÖRNEK', d.ornek, Icons.calculate_sharp,
                Theme.of(c).colorScheme.onSurfaceVariant),
          ],
          if (d.bist.isNotEmpty) ...[
            const SizedBox(height: 18),
            _bolum(c, 'BIST / MİDAS ÖZELİ', d.bist, Icons.flag_sharp, sem.arti),
          ],
          if (d.tuzak.isNotEmpty) ...[
            const SizedBox(height: 18),
            _bolum(c, 'TUZAK', d.tuzak, Icons.dangerous_sharp, sem.eksi),
          ],
          const SizedBox(height: 26),
          if (d.sorular.isNotEmpty)
            Not(
              'Bu dersin ${d.sorular.length} pekiştirme sorusu var. '
              'Günlük oturumda karşına gelecekler.',
              ikon: Icons.quiz_sharp, renk: sem.aksan,
            ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
            child: const Text('Okudum'),
          ),
        ],
      ),
    );
  }

  Widget _metin(BuildContext c, String metin) => Text(
        metin,
        style: Theme.of(c).textTheme.bodyLarge?.copyWith(
            height: 1.72, fontSize: 16.5),
      );

  Widget _bolum(BuildContext c, String baslik, String metin, IconData ikon,
          Color renk) =>
      Container(
        padding: const EdgeInsets.fromLTRB(16, 15, 16, 17),
        decoration: BoxDecoration(
          color: renk.withValues(alpha: 0.07),
          borderRadius: kose,
          border: Border.all(color: renk.withValues(alpha: 0.28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(ikon, size: 17, color: renk),
              const SizedBox(width: 8),
              Text(baslik,
                  style: Theme.of(c).textTheme.labelSmall?.copyWith(
                      color: renk, letterSpacing: 1.2)),
            ]),
            const SizedBox(height: 12),
            Text(metin,
                style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.68)),
          ],
        ),
      );
}
