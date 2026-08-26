import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'hisse.dart';

class PortfoyEkran extends StatefulWidget {
  const PortfoyEkran({super.key});
  @override
  State<PortfoyEkran> createState() => _PortfoyDurum();
}

class _PortfoyDurum extends State<PortfoyEkran> {
  Map<String, dynamic>? _veri, _risk;
  Object? _hata;
  bool _yukleniyor = false;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    // Önce defterden tazele: pozisyonların tek kaynağı sunucu, telefon
    // yalnızca kopya tutuyor. Bot'tan /aldim ile girilen bir pozisyon
    // burada da görünmeli.
    await depo.pozisyonlariSenkronla();
    if (!mounted) return;
    if (depo.pozisyonlar.isEmpty) {
      setState(() { _veri = null; _risk = null; _yukleniyor = false; });
      return;
    }
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final api = depo.api;
      final r = await api.portfoyKontrol(depo.pozisyonlar, depo.ayarlar.sermaye);
      Map<String, dynamic>? risk;
      if (depo.pozisyonlar.length >= 2) {
        try {
          risk = await api.riskPortfoy(depo.pozisyonlar);
        } catch (_) {}
      }
      if (!mounted) return;
      setState(() { _veri = r; _risk = risk; _yukleniyor = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return ListenableBuilder(
      listenable: depo,
      builder: (_, __) => Scaffold(
        appBar: AppBar(
          title: const Text('Portföy'),
          actions: [
            IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
          ],
        ),
        body: depo.pozisyonlar.isEmpty
            ? Bos(Icons.account_balance_wallet_sharp, 'Açık pozisyon yok',
                alt: 'Midas\'ta bir alım yaptığında Tarama\'dan hisseyi aç ve\n'
                    '"Alım kaydet" ile buraya ekle.')
            : _yukleniyor
                ? const Yukleniyor(mesaj: 'Pozisyonlar değerlendiriliyor...')
                : _hata != null
                    ? HataGorunum(_hata!, tekrar: _getir)
                    : RefreshIndicator(
                        onRefresh: _getir,
                        child: ListView(
                          padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
                          children: [
                            _ozet(c, sem),
                            const SizedBox(height: 14),
                            ...((_veri?['pozisyonlar'] as List?) ?? []).map((p) =>
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 10),
                                  child: _kart(c, sem, p as Map<String, dynamic>),
                                )),
                            if (_risk != null && _risk!['hata'] == null) ...[
                              const SizedBox(height: 6),
                              _riskKart(c, sem),
                            ],
                          ],
                        ),
                      ),
      ),
    );
  }

  Widget _ozet(BuildContext c, Sem sem) {
    final o = _veri?['ozet'] as Map<String, dynamic>?;
    if (o == null) return const SizedBox.shrink();
    final kar = (o['kar'] as num?)?.toDouble() ?? 0;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Güncel değer',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(
                            color: Theme.of(c).colorScheme.onSurfaceVariant)),
                    Text('${tl(o['deger'] as num?)} ₺',
                        style: Theme.of(c).textTheme.headlineSmall),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('${tl(kar)} ₺',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.w800,
                          color: sem.yon(kar))),
                  Text(yzd(o['kar_yuzde'] as num?),
                      style: TextStyle(
                          fontWeight: FontWeight.w700, color: sem.yon(kar))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text('Maliyet ${tl(o['maliyet'] as num?)} ₺',
                    style: Theme.of(c).textTheme.bodySmall),
              ),
              Expanded(
                child: Text('Nakit ${tl(o['nakit'] as num?)} ₺',
                    style: Theme.of(c).textTheme.bodySmall),
              ),
              Text('%${tl(o['piyasa_yuzde'] as num?, basamak: 0)} piyasada',
                  style: Theme.of(c).textTheme.bodySmall),
            ],
          ),
        ],
      ),
    );
  }

  Widget _kart(BuildContext c, Sem sem, Map<String, dynamic> p) {
    if (p['hata'] != null) {
      return Kutu(child: Text('${p['sembol']}: ${p['hata']}'));
    }
    final sat = p['aksiyon'] == 'SAT';
    final karY = (p['kar_yuzde'] as num?)?.toDouble() ?? 0;
    final poz = depo.pozisyon('${p['sembol']}');

    return Kutu(
      tikla: () => Navigator.push(c,
              MaterialPageRoute(builder: (_) => HisseEkran('${p['sembol']}')))
          .then((_) => _getir()),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Rozet(sat ? 'SAT' : 'TUT',
                  renk: sat ? sem.eksi : sem.arti, dolu: sat),
              const SizedBox(width: 10),
              Expanded(
                child: Text('${p['sembol']}',
                    style: Theme.of(c).textTheme.titleMedium),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('${tl(p['fiyat'] as num?)} ₺',
                      style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontFeatures: [FontFeature.tabularFigures()])),
                  Text(yzd(p['gunluk_degisim'] as num?, basamak: 1),
                      style: TextStyle(
                          fontSize: 12,
                          color: sem.yon(p['gunluk_degisim'] as num?))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _mini(c, '${p['adet']} adet', 'giriş ${tl(p['giris'] as num?)}'),
              _mini(c, '${tl(p['kar'] as num?)} ₺', 'kâr/zarar',
                  renk: sem.yon(karY)),
              _mini(c, yzd(karY), 'getiri', renk: sem.yon(karY)),
              _mini(c, '${p['gun']} gün', 'tutuluyor'),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: (sat ? sem.eksi : Theme.of(c).colorScheme.onSurfaceVariant)
                  .withValues(alpha: 0.08),
              borderRadius: kose,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${p['aciklama']}',
                    style: Theme.of(c).textTheme.bodySmall),
                if ('${p['oneri']}'.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Icon(Icons.trending_up_sharp, size: 15, color: sem.uyari),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text('${p['oneri']}',
                            style: TextStyle(fontSize: 12.5, color: sem.uyari)),
                      ),
                      if (poz != null)
                        TextButton(
                          onPressed: () => _stopCek(poz, '${p['oneri']}'),
                          style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 8),
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                          child: const Text('Uygula', style: TextStyle(fontSize: 12.5)),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text('Stop ${tl(p['stop'] as num?)} ₺',
                    style: TextStyle(fontSize: 12.5, color: sem.eksi)),
              ),
              Expanded(
                child: Text('Hedef ${tl(p['hedef'] as num?)} ₺',
                    style: TextStyle(fontSize: 12.5, color: sem.arti)),
              ),
              if (!depo.tezVarMi('${p['sembol']}'))
                Rozet('tez yok', renk: sem.uyari),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _stopCek(Pozisyon p, String oneri) async {
    // "stop'u 36.38 → 38.10 yukarı çek" içinden ikinci sayıyı al
    final sayilar = RegExp(r'(\d+[.,]?\d*)').allMatches(oneri).toList();
    if (sayilar.length < 2) return;
    final yeni = double.tryParse(sayilar[1].group(1)!.replaceAll(',', '.'));
    if (yeni == null) return;
    await depo.pozisyonGuncelle(p.stopIle(yeni));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('${p.sembol} stop → ${tl(yeni)} ₺. '
            'Midas\'ta da güncellemeyi unutma.')));
    _getir();
  }

  Widget _mini(BuildContext c, String ust, String alt, {Color? renk}) => Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(ust,
                style: TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 13, color: renk,
                    fontFeatures: const [FontFeature.tabularFigures()])),
            Text(alt,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    fontSize: 11,
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
          ],
        ),
      );

  Widget _riskKart(BuildContext c, Sem sem) {
    final r = _risk!;
    final kor = (r['ortalama_korelasyon'] as num?)?.toDouble();
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('PORTFÖY RİSKİ',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 8),
          Satir('Yıllık oynaklık',
              '%${tl(r['portfoy_oynaklik_yuzde'] as num?, basamak: 1)}'),
          Satir('Ortalama korelasyon', tl(kor),
              renk: (kor ?? 0) > 0.7 ? sem.eksi : null),
          Satir('Etkin hisse sayısı',
              '${tl(r['etkin_hisse_sayisi'] as num?, basamak: 1)} '
              '(nominal ${r['nominal_hisse_sayisi']})'),
          Satir('Çeşitlendirme kazancı',
              '%${tl(r['cesitlendirme_kazanci_yuzde'] as num?, basamak: 1)}'),
          if ('${r['uyari']}'.isNotEmpty) ...[
            const SizedBox(height: 10),
            Not('${r['uyari']}', ikon: Icons.warning_amber_sharp, renk: sem.eksi),
          ],
        ],
      ),
    );
  }
}
