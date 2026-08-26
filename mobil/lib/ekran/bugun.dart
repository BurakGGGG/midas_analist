import 'package:flutter/material.dart';
import 'ders.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'hisse.dart';
import 'ayarlar.dart';
import 'sermaye.dart';

/// Günün özeti. Sıralama bilinçli: önce ELDEKİ pozisyonlar (aksiyon gerektirir),
/// sonra piyasa rejimi, en son yeni fırsatlar. Yeni alım en son bakılacak şeydir.
class BugunEkran extends StatefulWidget {
  const BugunEkran({super.key});
  @override
  State<BugunEkran> createState() => _BugunDurum();
}

class _BugunDurum extends State<BugunEkran> {
  Map<String, dynamic>? _portfoy, _makro, _ders;
  int? _sinyalSayisi;
  Object? _hata;
  bool _yukleniyor = true;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final api = depo.api;
      final a = depo.ayarlar;
      final sonuclar = await Future.wait([
        depo.pozisyonlar.isEmpty
            ? Future.value(<String, dynamic>{})
            : api.portfoyKontrol(depo.pozisyonlar, a.sermaye),
        api.makro(),
        api.tarama(sermaye: a.sermaye, sadeceSinyal: true, adet: 5),
        // Ders akışın İÇİNDE: ayrı sekmeye gitmek gerekirse açılmıyor
        // (ölçüldü: 65 dersten 1'i okunmuş).
        api.gununDersi(portfoyAdet: depo.pozisyonlar.length)
            .catchError((_) => <String, dynamic>{}),
      ]);
      if (!mounted) return;
      setState(() {
        _portfoy = sonuclar[0];
        _makro = sonuclar[1];
        _sinyalSayisi = (sonuclar[2]['sinyalli'] as num?)?.toInt();
        _ders = (sonuclar[3]['ders'] as Map?)?.cast<String, dynamic>();
        _yukleniyor = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bugün'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_sharp),
            onPressed: () => Navigator.push(c,
                MaterialPageRoute(builder: (_) => const AyarlarEkran())),
          ),
        ],
      ),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Piyasa verisi alınıyor...\nİlk açılışta uzun sürebilir.')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : RefreshIndicator(
                  onRefresh: _getir,
                  child: ListView(
                    padding: const EdgeInsets.only(bottom: 26),
                    children: [
                      _portfoyOzet(c, sem),
                      _aksiyonlar(c, sem),
                      _rejim(c, sem),
                      _firsat(c, sem),
                      _gununDersi(c, sem),
                      _hatirlatma(c),
                    ],
                  ),
                ),
    );
  }

  Widget _portfoyOzet(BuildContext c, Sem sem) {
    final o = _portfoy?['ozet'] as Map<String, dynamic>?;
    final a = depo.ayarlar;
    final deger = (o?['deger'] as num?)?.toDouble() ?? 0;
    final kar = (o?['kar'] as num?)?.toDouble() ?? 0;
    final karY = (o?['kar_yuzde'] as num?)?.toDouble() ?? 0;
    final nakit = (o?['nakit'] as num?)?.toDouble() ?? a.sermaye;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Kutu(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('PORTFÖY',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.4)),
                const Spacer(),
                // Sermaye tek dokunuş uzakta olmalı: kullanıcı hesabına
                // sürekli para ekliyor, bunu ayarlar içinde aramamalı.
                InkWell(
                  onTap: () => Navigator.push(c,
                      MaterialPageRoute(builder: (_) => const SermayeEkran())),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      border: Border.all(color: Renk.cizgi),
                      borderRadius: kose,
                    ),
                    child: const Text('SERMAYE +/−',
                        style: TextStyle(
                            fontSize: 10,
                            letterSpacing: 0.8,
                            fontWeight: FontWeight.w700,
                            color: Renk.metinSolgun)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('${tl(deger + nakit)} ₺',
                    style: Theme.of(c).textTheme.displaySmall?.copyWith(
                        fontFeatures: const [FontFeature.tabularFigures()])),
                const SizedBox(width: 10),
                if (depo.pozisyonlar.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 5),
                    child: Text('${tl(kar)} ₺ (${yzd(karY)})',
                        style: TextStyle(
                            color: sem.yon(kar),
                            fontWeight: FontWeight.w700,
                            fontSize: 14)),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 6),
            Row(
              children: [
                _mini(c, 'Piyasada', '${tl(deger)} ₺'),
                _mini(c, 'Nakit', '${tl(nakit)} ₺'),
                _mini(c, 'Pozisyon', '${depo.pozisyonlar.length}'),
              ],
            ),
            // Yatırdığın para ile toplam arasındaki fark: asıl performans.
            // Üstteki büyük rakam para eklediğinde de büyür, bu büyümez.
            if (depo.netYatirilan > 0) ...[
              const SizedBox(height: 10),
              const Divider(height: 1),
              const SizedBox(height: 8),
              Builder(builder: (_) {
                final yatirilan = depo.netYatirilan;
                final toplam = deger + nakit;
                final fark = toplam - yatirilan;
                return Row(
                  children: [
                    Expanded(
                      child: Text('Yatırdığın ${tl(yatirilan)} ₺ üzerine',
                          style: const TextStyle(
                              fontSize: 11.5, color: Renk.metinSolgun)),
                    ),
                    Text('${fark >= 0 ? '+' : ''}${tl(fark)} ₺  '
                        '(${yzd(fark / yatirilan * 100)})',
                        style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                            color: sem.yon(fark))),
                  ],
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Widget _mini(BuildContext c, String etiket, String deger) => Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(etiket,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 2),
            Text(deger,
                style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()])),
          ],
        ),
      );

  Widget _aksiyonlar(BuildContext c, Sem sem) {
    final liste = (_portfoy?['pozisyonlar'] as List?) ?? [];
    final satilacak = liste.where((p) => p['aksiyon'] == 'SAT').toList();
    if (satilacak.isEmpty) {
      if (depo.pozisyonlar.isEmpty) return const SizedBox.shrink();
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
        child: Not('Açık pozisyonlarda çıkış sinyali yok. Bugün bir şey yapmana gerek yok.',
            ikon: Icons.check_circle_outline_sharp, renk: sem.arti),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Baslik('Bugün aksiyon gerekiyor',
            alt: '${satilacak.length} pozisyonda çıkış sinyali var'),
        ...satilacak.map((p) => Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: Kutu(
                tikla: () => Navigator.push(
                    c,
                    MaterialPageRoute(
                        builder: (_) => HisseEkran(p['sembol'] as String))),
                child: Row(
                  children: [
                    const Rozet('SAT', renk: Color(0xFF993229), dolu: true),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${p['sembol']}',
                              style: Theme.of(c).textTheme.titleMedium),
                          const SizedBox(height: 2),
                          Text('${p['aciklama']}',
                              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
                        ],
                      ),
                    ),
                    Text(yzd((p['kar_yuzde'] as num?)?.toDouble()),
                        style: TextStyle(
                            color: sem.yon((p['kar_yuzde'] as num?)),
                            fontWeight: FontWeight.w700)),
                  ],
                ),
              ),
            )),
      ],
    );
  }

  Widget _rejim(BuildContext c, Sem sem) {
    final r = _makro?['rejim'] as Map<String, dynamic>?;
    final enf = _makro?['enflasyon'] as Map<String, dynamic>?;
    final reel = (_makro?['bist_reel_getiri_1y'] as num?)?.toDouble();
    if (r == null) return const SizedBox.shrink();
    final ad = '${r['rejim']}';
    final renk = ad.contains('AÇIK')
        ? sem.arti
        : ad.contains('SAVUNMA')
            ? sem.eksi
            : sem.uyari;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Baslik('Piyasa rejimi'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Rozet(ad, renk: renk, dolu: true),
                    const Spacer(),
                    if (enf != null)
                      Text('Enflasyon ${yzd(enf['yillik'] as num?, isaret: false)}',
                          style: Theme.of(c).textTheme.bodySmall?.copyWith(
                              color: Theme.of(c).colorScheme.onSurfaceVariant)),
                  ],
                ),
                const SizedBox(height: 10),
                Text('${r['aciklama']}',
                    style: Theme.of(c).textTheme.bodyMedium),
                if ((r['notlar'] as List?)?.isNotEmpty ?? false) ...[
                  const SizedBox(height: 10),
                  ...(r['notlar'] as List).map((n) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('· ',
                                style: TextStyle(color: sem.aksan)),
                            Expanded(
                                child: Text('$n',
                                    style: Theme.of(c).textTheme.bodySmall)),
                          ],
                        ),
                      )),
                ],
                if (reel != null) ...[
                  const SizedBox(height: 12),
                  Not(
                    'BIST 100\'ün son 1 yıl REEL getirisi ${yzd(reel)}. '
                    'Nominal getiri enflasyondan arındırılmadan bir şey ifade etmez.',
                    ikon: Icons.trending_down_sharp,
                    renk: reel < 0 ? sem.eksi : sem.arti,
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _firsat(BuildContext c, Sem sem) {
    if (_sinyalSayisi == null) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Baslik('Yeni fırsatlar'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Kutu(
            child: _sinyalSayisi == 0
                ? Row(
                    children: [
                      Icon(Icons.nights_stay_sharp,
                          color: Theme.of(c).colorScheme.onSurfaceVariant),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                            'Bugün hiçbir hisse giriş sinyali vermiyor. '
                            'Sinyal yoksa işlem yapılmaz — nakitte beklemek de bir pozisyondur.'),
                      ),
                    ],
                  )
                : Row(
                    children: [
                      // Burada SkorHalka KULLANILMAZ: o halka uygulamanın her
                      // yerinde 0-100 kalite skoru demek. Sinyal sayısını oraya
                      // koymak, 6 sinyali "100 puan" gibi gösterirdi.
                      Container(
                        width: 42, height: 42,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: Renk.panelUst,
                          borderRadius: kose,
                          border: Border.all(color: sem.aksan),
                        ),
                        child: Text('$_sinyalSayisi',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.w700,
                                color: sem.aksan)),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Text(
                            '$_sinyalSayisi hisse bugün giriş sinyali veriyor. '
                            'Tarama sekmesinden bak.'),
                      ),
                      const Icon(Icons.chevron_right_sharp),
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  /// Günün dersi — müfredat sırası değil, BUGÜNÜN durumu belirler.
  ///
  /// Neden burada: eğitmen ayrı bir sekmede dururken açılmıyordu (65
  /// dersten 1'i okunmuştu). Sebep içerik değil akış — kimse "eğitim"
  /// için ayrı zaman ayırmıyor. Ders, o günün olayının açıklaması olarak
  /// günlük akışın içinde durursa ayrı bir iş olmaktan çıkıyor.
  Widget _gununDersi(BuildContext c, Sem sem) {
    final d = _ders;
    if (d == null) return const SizedBox.shrink();
    final tekrar = d['tekrar'] == true;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Baslik('Günün dersi'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Kutu(
            child: InkWell(
              onTap: () => Navigator.push(c, MaterialPageRoute(
                  builder: (_) => DersEkran('${d['kod']}'))),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.school_sharp, size: 18, color: sem.aksan),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text('${d['baslik']}',
                            style: Theme.of(c).textTheme.titleMedium),
                      ),
                      if (tekrar) Rozet('TEKRAR', renk: sem.uyari),
                      const SizedBox(width: 6),
                      const Icon(Icons.chevron_right_sharp, size: 18),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // "Neden bu ders" olmadan kart rastgele bir öneri gibi
                  // görünür ve tıklanmaz.
                  Text('${d['neden']}',
                      style: Theme.of(c).textTheme.bodySmall?.copyWith(
                          color: Theme.of(c).colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 6),
                  Text('${d['sure']} dakika',
                      style: Theme.of(c).textTheme.bodySmall
                          ?.copyWith(color: sem.aksan)),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _hatirlatma(BuildContext c) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
        child: Not(
          'Emirleri Midas uygulamasında sen giriyorsun. Midas\'ın API\'si yok — '
          'bu uygulama neyi neden alacağını söyler, emri senin yerine veremez.',
          ikon: Icons.info_outline_sharp,
        ),
      );
}
