import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/egitmen.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'ders.dart';

/// Günlük eğitmen oturumu: önce DERS, sonra pekiştirme soruları.
///
/// Sıra bilinçli. Bu bir sınav değil, bir müfredat: önce öğrenirsin, sonra
/// pekiştirirsin. Soru bankasından sadece OKUDUĞUN derslerin soruları gelir.
class OgretEkran extends StatefulWidget {
  const OgretEkran({super.key});
  @override
  State<OgretEkran> createState() => _OgretDurum();
}

class _OgretDurum extends State<OgretEkran> {
  List<EgitmenSoru> _sorular = [];
  List<Ders> _gunlukDers = [];
  int _i = 0;
  bool _cevapAcik = false;
  bool _yukleniyor = true;
  bool _derslerBitti = false;
  Object? _hata;
  String _ilke = '';
  final List<int> _puanlar = [];
  int _baslangicSeviye = 1;

  @override
  void initState() {
    super.initState();
    _hazirla();
  }

  Future<void> _hazirla() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      // Müfredat ve banka yoksa indir — bir kez, sonra offline çalışır
      if (!egitmen.mufredatVar) {
        await egitmen.mufredatKaydet(await depo.api.egitmenMufredat());
      }
      if (!egitmen.bankaVar) {
        await egitmen.bankaKaydet(await depo.api.egitmenSorular());
      }
      _baslangicSeviye = egitmen.durum().seviye;
      _gunlukDers = egitmen.gunlukDers(adet: 1);
      final banka = egitmen.gunlukSecim(adet: 3);

      // Canlı sorular: bağlantı varsa ekle, yoksa sessizce atla
      var canli = <EgitmenSoru>[];
      try {
        final r = await depo.api.egitmenCanli(
            sermaye: depo.ayarlar.sermaye, azami: 2,
            pozisyonlar: depo.pozisyonlar);
        canli = ((r['sorular'] ?? []) as List)
            .map((e) => EgitmenSoru.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        _ilke = '${r['ilke'] ?? ''}';
      } catch (_) {}

      if (!mounted) return;
      setState(() {
        _sorular = [...canli, ...banka];
        _ilke = _ilke.isEmpty ? egitmen.ilkeGunun() : _ilke;
        _yukleniyor = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  Future<void> _degerlendir(int kalite) async {
    final s = _sorular[_i];
    if (!s.canli) {
      await egitmen.cevapla(s.kod, kalite);
      _puanlar.add(kalite);
    }
    if (_i + 1 >= _sorular.length) {
      if (mounted) setState(() => _i = _sorular.length);
    } else {
      if (mounted) setState(() { _i++; _cevapAcik = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Günlük oturum'),
        bottom: _sorular.isEmpty || _i >= _sorular.length
            ? null
            : PreferredSize(
                preferredSize: const Size.fromHeight(3),
                child: LinearProgressIndicator(
                  value: _i / _sorular.length, minHeight: 3,
                  backgroundColor: Theme.of(c).dividerColor,
                ),
              ),
      ),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Ders ve sorular hazırlanıyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _hazirla)
              : (!_derslerBitti && _gunlukDers.isNotEmpty)
                  ? _dersGorunum(c, sem)
                  : _sorular.isEmpty
                      ? _bitis(c, sem)
                      : _i >= _sorular.length
                          ? _bitis(c, sem)
                          : _soruGorunum(c, sem),
    );
  }

  /// Günün dersi — okumadan soruya geçilmez.
  Widget _dersGorunum(BuildContext c, Sem sem) {
    final d = _gunlukDers.first;
    final m = egitmen.dersModulu(d.kod);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 30),
      children: [
        Row(children: [
          Rozet('BUGÜNÜN DERSİ', renk: sem.aksan, dolu: true),
          const Spacer(),
          Text('~${d.sure} dk',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
        ]),
        const SizedBox(height: 18),
        Kutu(
          ic: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (m != null) ...[
                Text(m.ad.toUpperCase(),
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 8),
              ],
              Text(d.baslik,
                  style: Theme.of(c).textTheme.headlineSmall
                      ?.copyWith(height: 1.25)),
              const SizedBox(height: 12),
              Text(d.ozet,
                  style: Theme.of(c).textTheme.bodyLarge?.copyWith(
                      height: 1.5,
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
            ],
          ),
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: () => Navigator.push(c,
                  MaterialPageRoute(builder: (_) => DersEkran(d.kod)))
              .then((_) => setState(() => _derslerBitti = true)),
          icon: const Icon(Icons.menu_book_sharp),
          label: const Text('Dersi oku'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        ),
        const SizedBox(height: 10),
        TextButton(
          onPressed: () => setState(() => _derslerBitti = true),
          child: Text(_sorular.isEmpty
              ? 'Bugün atla'
              : 'Dersi atla, sorulara geç'),
        ),
        const SizedBox(height: 16),
        Not(
          'Soru bankasından sadece OKUDUĞUN derslerin soruları gelir. '
          'Ders atlarsan pekiştirme de eksik kalır.',
          ikon: Icons.school_sharp,
        ),
      ],
    );
  }

  Widget _soruGorunum(BuildContext c, Sem sem) {
    final s = _sorular[_i];
    final seviyeAd = {1: 'temel', 2: 'orta', 3: 'usta'}[s.seviye] ?? '';
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 30),
      children: [
        Row(
          children: [
            Text('${_i + 1} / ${_sorular.length}',
                style: Theme.of(c).textTheme.labelSmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
            const Spacer(),
            if (s.canli)
              Rozet('CANLI · bugünkü veri', renk: sem.arti, dolu: true)
            else ...[
              Rozet(seviyeAd),
              if (s.kategori != seviyeAd) ...[
                const SizedBox(width: 6),
                Rozet(s.kategori, renk: Theme.of(c).colorScheme.onSurfaceVariant),
              ],
            ],
          ],
        ),
        const SizedBox(height: 16),
        Kutu(
          ic: const EdgeInsets.all(20),
          child: Text(s.soru,
              style: Theme.of(c).textTheme.titleLarge?.copyWith(
                  fontSize: 19, height: 1.4)),
        ),
        const SizedBox(height: 18),
        if (!_cevapAcik) ...[
          Not(
            'Cevabı açmadan önce kendi cevabını kur. Aklından geçirmek yetmez — '
            'cümleyi tamamla. Bu adımı atlarsan öğrenmezsin, sadece okursun.',
            ikon: Icons.psychology_sharp, renk: sem.aksan,
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () => setState(() => _cevapAcik = true),
            icon: const Icon(Icons.visibility_sharp),
            label: const Text('Cevabı gör'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          ),
        ] else ...[
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('CEVAP',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.arti, letterSpacing: 1.1)),
                const SizedBox(height: 10),
                Text(s.cevap,
                    style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.6)),
              ],
            ),
          ),
          if (s.tuzak.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: sem.eksi.withValues(alpha: 0.08),
                borderRadius: kose,
                border: Border.all(color: sem.eksi.withValues(alpha: 0.3)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(Icons.dangerous_sharp, size: 17, color: sem.eksi),
                    const SizedBox(width: 7),
                    Text('YAYGIN HATA',
                        style: Theme.of(c).textTheme.labelSmall
                            ?.copyWith(color: sem.eksi, letterSpacing: 1.1)),
                  ]),
                  const SizedBox(height: 8),
                  Text(s.tuzak,
                      style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.55)),
                ],
              ),
            ),
          ],
          if (s.anahtar.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 6, runSpacing: 6,
              children: s.anahtar.map((a) => Rozet(a)).toList(),
            ),
          ],
          const SizedBox(height: 20),
          if (s.canli)
            FilledButton(
              onPressed: () => _degerlendir(3),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
              child: Text(_i + 1 >= _sorular.length ? 'Bitir' : 'Devam'),
            )
          else ...[
            Text('Kendini değerlendir',
                style: Theme.of(c).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Dürüst ol — bu değerlendirme sorunun ne zaman tekrar '
                'geleceğini belirler.',
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 12),
            Row(
              children: [
                _puanDugme(c, 'Bilmiyordum', 1, sem.eksi),
                const SizedBox(width: 8),
                _puanDugme(c, 'Kısmen', 3, sem.uyari),
                const SizedBox(width: 8),
                _puanDugme(c, 'Biliyordum', 5, sem.arti),
              ],
            ),
          ],
        ],
      ],
    );
  }

  Widget _puanDugme(BuildContext c, String metin, int kalite, Color renk) =>
      Expanded(
        child: OutlinedButton(
          onPressed: () => _degerlendir(kalite),
          style: OutlinedButton.styleFrom(
            foregroundColor: renk,
            side: BorderSide(color: renk.withValues(alpha: 0.6)),
            padding: const EdgeInsets.symmetric(vertical: 14),
          ),
          child: Text(metin,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
        ),
      );

  Widget _bitis(BuildContext c, Sem sem) {
    final d = egitmen.durum();
    final atladi = d.seviye > _baslangicSeviye;
    final ort = _puanlar.isEmpty
        ? 0.0
        : _puanlar.reduce((a, b) => a + b) / _puanlar.length;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 30, 16, 30),
      children: [
        Icon(atladi ? Icons.military_tech_sharp : Icons.check_circle_outline_sharp,
            size: 60, color: atladi ? sem.uyari : sem.arti),
        const SizedBox(height: 18),
        Text(atladi ? 'Seviye atladın: ${d.unvan}' : 'Oturum tamamlandı',
            textAlign: TextAlign.center,
            style: Theme.of(c).textTheme.headlineSmall),
        const SizedBox(height: 10),
        Text(
            '${d.dersOkunan}/${d.dersToplam} ders okundu'
            '${_puanlar.isNotEmpty ? " · ${_puanlar.length} soru · ortalama ${ort.toStringAsFixed(1)}/5" : ""}',
            textAlign: TextAlign.center,
            style: Theme.of(c).textTheme.bodyMedium?.copyWith(
                color: Theme.of(c).colorScheme.onSurfaceVariant)),
        const SizedBox(height: 6),
        Text('${d.dakikaKalan} dakika okuma kaldı',
            textAlign: TextAlign.center,
            style: Theme.of(c).textTheme.bodySmall?.copyWith(
                color: Theme.of(c).colorScheme.onSurfaceVariant)),
        const SizedBox(height: 26),
        Kutu(
          child: Column(
            children: [
              Text(_ilke,
                  textAlign: TextAlign.center,
                  style: Theme.of(c).textTheme.titleMedium?.copyWith(
                      fontStyle: FontStyle.italic, height: 1.5,
                      color: sem.aksan)),
            ],
          ),
        ),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => Navigator.pop(c),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          child: const Text('Bitir'),
        ),
      ],
    );
  }
}
