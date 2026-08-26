import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../parca/grafik.dart';
import '../tema.dart';
import 'alim.dart';
import 'sirket_oku.dart';

class HisseEkran extends StatefulWidget {
  final String sembol;
  const HisseEkran(this.sembol, {super.key});
  @override
  State<HisseEkran> createState() => _HisseDurum();
}

class _HisseDurum extends State<HisseEkran> with SingleTickerProviderStateMixin {
  late final TabController _tab;
  Map<String, dynamic>? _teknik, _yapi, _sirket;
  Object? _hata;
  bool _yukleniyor = true;
  bool _yapiYukleniyor = false, _sirketYukleniyor = false;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 3, vsync: this);
    _tab.addListener(_sekmeDegisti);
    _teknikGetir();
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  /// Sekmeler TEMBEL yüklenir: şirket verisi ilk çekimde yavaş, kullanıcı
  /// o sekmeye girmediyse beklemesin.
  void _sekmeDegisti() {
    if (_tab.indexIsChanging) return;
    if (_tab.index == 1 && _yapi == null && !_yapiYukleniyor) _yapiGetir();
    if (_tab.index == 2 && _sirket == null && !_sirketYukleniyor) _sirketGetir();
  }

  Future<void> _teknikGetir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final r = await depo.api
          .hisse(widget.sembol, sermaye: depo.ayarlar.sermaye);
      if (!mounted) return;
      setState(() { _teknik = r; _yukleniyor = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  Future<void> _yapiGetir() async {
    setState(() => _yapiYukleniyor = true);
    try {
      final r = await depo.api.yapi(widget.sembol);
      if (mounted) setState(() { _yapi = r; _yapiYukleniyor = false; });
    } catch (_) {
      if (mounted) setState(() => _yapiYukleniyor = false);
    }
  }

  Future<void> _sirketGetir() async {
    setState(() => _sirketYukleniyor = true);
    try {
      final r = await depo.api.sirket(widget.sembol);
      if (mounted) setState(() { _sirket = r; _sirketYukleniyor = false; });
    } catch (e) {
      if (mounted) setState(() { _sirketYukleniyor = false; _sirket = {'hata': '$e'}; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final skor = _teknik?['skor'] as Map<String, dynamic>?;
    final poz = depo.pozisyon(widget.sembol);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text(widget.sembol.toUpperCase()),
            if (skor != null) ...[
              const SizedBox(width: 12),
              Text('${tl(skor['fiyat'] as num?)} ₺',
                  style: TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w600,
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
              const SizedBox(width: 7),
              Text(yzd(skor['gunluk_degisim'] as num?, basamak: 1),
                  style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w700,
                      color: sem.yon(skor['gunluk_degisim'] as num?))),
            ],
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.school_sharp),
            tooltip: 'Şirketi oku egzersizi',
            onPressed: () => Navigator.push(c,
                MaterialPageRoute(builder: (_) => SirketOkuEkran(widget.sembol))),
          ),
        ],
        bottom: TabBar(
          controller: _tab,
          tabs: const [
            Tab(text: 'Teknik'), Tab(text: 'Yapı'), Tab(text: 'Şirket'),
          ],
        ),
      ),
      floatingActionButton: _yukleniyor || _hata != null
          ? null
          : poz != null
              ? FloatingActionButton.extended(
                  onPressed: () => _satDialog(c, poz),
                  backgroundColor: sem.eksi,
                  foregroundColor: Renk.zemin,
                  icon: const Icon(Icons.remove_circle_outline_sharp),
                  label: const Text('Pozisyonu kapat'))
              : FloatingActionButton.extended(
                  onPressed: () => Navigator.push(
                      c,
                      MaterialPageRoute(
                          builder: (_) => AlimEkran(
                                widget.sembol,
                                baslangicFiyat:
                                    (skor?['fiyat'] as num?)?.toDouble() ?? 0,
                                onerilenPozisyon:
                                    _teknik?['pozisyon'] as Map<String, dynamic>?,
                              ))).then((_) => setState(() {})),
                  icon: const Icon(Icons.add_shopping_cart_sharp),
                  label: const Text('Alım kaydet')),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Analiz ediliyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _teknikGetir)
              : TabBarView(
                  controller: _tab,
                  children: [_teknikSekme(c, sem), _yapiSekme(c, sem), _sirketSekme(c, sem)],
                ),
    );
  }

  // ───────────────────────────────────────────── TEKNİK

  Widget _teknikSekme(BuildContext c, Sem sem) {
    final skor = _teknik!['skor'] as Map<String, dynamic>;
    final filtre = _teknik!['filtre'] as Map<String, dynamic>;
    final sev = _teknik!['seviyeler'] as Map<String, dynamic>;
    final poz = _teknik!['pozisyon'] as Map<String, dynamic>?;
    final g = _teknik!['grafik'] as Map<String, dynamic>?;
    final fiyat = (skor['fiyat'] as num?)?.toDouble() ?? 0;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
      children: [
        if (g != null)
          Kutu(
            ic: const EdgeInsets.fromLTRB(8, 14, 8, 6),
            child: Column(
              children: [
                FiyatGrafik(g['kapanis'], ema20: g['ema20'], sma200: g['sma200']),
                const SizedBox(height: 6),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    children: [
                      _lejant(c, sem.arti, 'Fiyat'),
                      const SizedBox(width: 14),
                      _lejant(c, sem.aksan.withValues(alpha: 0.6), 'EMA20'),
                      const SizedBox(width: 14),
                      _lejant(c,
                          Theme.of(c).colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
                          'SMA200'),
                    ],
                  ),
                ),
                if (g['rsi'] != null) ...[
                  const SizedBox(height: 12),
                  const Divider(),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Padding(
                      padding: const EdgeInsets.only(left: 8, bottom: 4),
                      child: Text('RSI(14)',
                          style: Theme.of(c).textTheme.labelSmall?.copyWith(
                              color: Theme.of(c).colorScheme.onSurfaceVariant)),
                    ),
                  ),
                  RsiGrafik(g['rsi']),
                ],
              ],
            ),
          ),
        const SizedBox(height: 14),
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  SkorHalka(skor['skor'] as num?, boyut: 66, alt: '/100'),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _cubuk(c, 'Trend', (skor['trend'] as num?)?.toDouble() ?? 0, 30),
                        _cubuk(c, 'Momentum', (skor['momentum'] as num?)?.toDouble() ?? 0, 25),
                        _cubuk(c, 'Zamanlama', (skor['zamanlama'] as num?)?.toDouble() ?? 0, 25),
                        _cubuk(c, 'Kalite', (skor['kalite'] as num?)?.toDouble() ?? 0, 20),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 7, runSpacing: 7,
                children: [
                  ...((skor['sinyaller'] as List?) ?? [])
                      .map((s) => Rozet('$s sinyali', renk: sem.aksan, dolu: true)),
                  Rozet(
                      (filtre['gecti'] as bool? ?? false)
                          ? 'filtre ✓'
                          : '${filtre['sebep']}',
                      renk: (filtre['gecti'] as bool? ?? false) ? sem.arti : sem.eksi),
                ],
              ),
              if ((skor['zamanlama'] as num? ?? 25) < 8) ...[
                const SizedBox(height: 12),
                Not(
                  'Zamanlama puanı düşük — trend iyi olsa bile şu an giriş için '
                  'pahalı bir nokta. RSI ${tl(skor['rsi'] as num?, basamak: 0)}.',
                  ikon: Icons.schedule_sharp, renk: sem.uyari,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('SEVİYELER',
                  style: Theme.of(c).textTheme.labelSmall?.copyWith(
                      color: sem.aksan, letterSpacing: 1.1)),
              const SizedBox(height: 6),
              ...[
                ('EMA20', sev['EMA20']), ('EMA50', sev['EMA50']),
                ('SMA200', sev['SMA200']), ('Bollinger alt', sev['BB_alt']),
                ('Bollinger üst', sev['BB_ust']), ('20g zirve', sev['DON_ust']),
                ('52h zirve', sev['52h_zirve']), ('52h dip', sev['52h_dip']),
              ].where((e) => e.$2 != null).map((e) {
                final v = (e.$2 as num).toDouble();
                final fark = fiyat > 0 ? (fiyat / v - 1) * 100 : 0.0;
                return Satir(e.$1, '${tl(v)} ₺',
                    not: 'fiyat ${yzd(fark, basamak: 1)} '
                        '${fark > 0 ? 'üstünde' : 'altında'}',
                    renk: sem.yon(fark));
              }),
            ],
          ),
        ),
        if (poz != null) ...[
          const SizedBox(height: 14),
          _pozisyonPlani(c, sem, poz),
        ],
      ],
    );
  }

  Widget _lejant(BuildContext c, Color renk, String metin) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 12, height: 2.5,
              decoration: BoxDecoration(
                  color: renk, borderRadius: kose)),
          const SizedBox(width: 5),
          Text(metin,
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  fontSize: 11,
                  color: Theme.of(c).colorScheme.onSurfaceVariant)),
        ],
      );

  Widget _cubuk(BuildContext c, String ad, double v, double azami) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                    child: Text(ad,
                        style: Theme.of(c).textTheme.bodySmall)),
                Text('${v.toStringAsFixed(0)}/${azami.toStringAsFixed(0)}',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 3),
            ClipRRect(
              borderRadius: kose,
              child: LinearProgressIndicator(
                value: (v / azami).clamp(0, 1), minHeight: 5,
                backgroundColor: Theme.of(c).dividerColor,
                valueColor: AlwaysStoppedAnimation(Sem(c).skor(v / azami * 100)),
              ),
            ),
          ],
        ),
      );

  Widget _pozisyonPlani(BuildContext c, Sem sem, Map<String, dynamic> p) {
    final adet = ((p['adet'] as num?) ?? 0).toInt();
    final a = depo.ayarlar;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('POZİSYON PLANI · ${tl(a.sermaye, basamak: 0)} ₺ SERMAYE',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 10),
          if (adet >= 1) ...[
            Satir('Alınacak adet', '$adet', kalin: true),
            Satir('Toplam tutar', '${tl(p['maliyet'] as num?)} ₺',
                not: 'sermayenin %${tl(p['sermaye_payi'] as num?, basamak: 0)}\'i'),
            Satir('Stop', '${tl(p['stop'] as num?)} ₺',
                renk: sem.eksi,
                not: 'buraya düşerse ${tl(p['risk_tl'] as num?)} ₺ kayıp'),
            Satir('Hedef', '${tl(p['hedef'] as num?)} ₺', renk: sem.arti),
            if ('${p['uyari']}'.isNotEmpty) ...[
              const SizedBox(height: 10),
              Not('${p['uyari']}', ikon: Icons.warning_amber_sharp, renk: sem.uyari),
            ],
          ] else
            Not('${p['uyari']}', ikon: Icons.block_sharp, renk: sem.eksi,
                baslik: 'Bu sermayeyle alınamıyor'),
        ],
      ),
    );
  }

  // ───────────────────────────────────────────── YAPI

  Widget _yapiSekme(BuildContext c, Sem sem) {
    if (_yapiYukleniyor) return const Yukleniyor(mesaj: 'Yapı analiz ediliyor...');
    if (_yapi == null) {
      return Bos(Icons.insights_sharp, 'Yapı verisi yok',
          eylem: TextButton(onPressed: _yapiGetir, child: const Text('Yükle')));
    }
    final y = _yapi!['yapi'] as Map<String, dynamic>?;
    final cz = _yapi!['cok_zamanli'] as Map<String, dynamic>?;
    final fb = _yapi!['fibonacci'] as Map<String, dynamic>?;
    final sk = _yapi!['sahte_kirilim'] as Map<String, dynamic>?;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
      children: [
        if (y != null)
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('TREND YAPISI',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 10),
                Rozet('${y['yapi']}',
                    renk: '${y['yapi']}' == 'YÜKSELEN'
                        ? sem.arti
                        : '${y['yapi']}' == 'DÜŞEN'
                            ? sem.eksi
                            : sem.uyari,
                    dolu: true),
                const SizedBox(height: 10),
                Text('${y['aciklama']}'),
                if ((y['tepeler'] as List?)?.isNotEmpty ?? false) ...[
                  const SizedBox(height: 10),
                  Satir('Son tepeler',
                      (y['tepeler'] as List).map((x) => tl(x as num)).join('  ›  ')),
                  Satir('Son dipler',
                      (y['dipler'] as List).map((x) => tl(x as num)).join('  ›  ')),
                ],
                const SizedBox(height: 10),
                Not('Trendin gerçek tanımı budur — hareketli ortalama değil.',
                    ikon: Icons.school_sharp),
              ],
            ),
          ),
        const SizedBox(height: 14),
        if (cz != null && cz['dilimler'] != null)
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ÇOKLU ZAMAN DİLİMİ',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 10),
                ...(cz['dilimler'] as List).map((d) {
                  final yon = '${d['yon']}';
                  return Satir('${d['dilim']}', yon,
                      renk: yon == 'yukarı'
                          ? sem.arti
                          : yon == 'aşağı'
                              ? sem.eksi
                              : null,
                      not: 'fiyat ${tl(d['fiyat'] as num?)} · '
                          'uzun ort ${tl(d['uzun_ort'] as num?)}');
                }),
                const SizedBox(height: 8),
                Rozet('${cz['uyum']}',
                    renk: '${cz['uyum']}'.contains('yukarı')
                        ? sem.arti
                        : '${cz['uyum']}'.contains('ÇELİŞKİ') ||
                                '${cz['uyum']}'.contains('aşağı')
                            ? sem.eksi
                            : sem.uyari,
                    dolu: true),
                const SizedBox(height: 8),
                Text('${cz['aciklama']}'),
                const SizedBox(height: 10),
                Not('${cz['kural']}', ikon: Icons.school_sharp),
              ],
            ),
          ),
        const SizedBox(height: 14),
        if (fb != null && fb['seviyeler'] != null)
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('FIBONACCI · ${fb['yon']} hareketi',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 4),
                Text('${tl(fb['dip'] as num?)} → ${tl(fb['tepe'] as num?)} ₺',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant)),
                const SizedBox(height: 8),
                ...(fb['seviyeler'] as Map).entries.map((e) {
                  final enYakin =
                      (fb['en_yakin'] as Map?)?['seviye'] == e.key;
                  return Satir(e.key, '${tl(e.value as num)} ₺',
                      kalin: enYakin,
                      renk: enYakin ? sem.aksan : null,
                      not: enYakin ? 'fiyat buraya en yakın' : null);
                }),
                const SizedBox(height: 10),
                Not('${fb['not']}', ikon: Icons.warning_amber_sharp,
                    renk: sem.uyari),
              ],
            ),
          ),
        const SizedBox(height: 14),
        if (sk != null)
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('KIRILIM GÜVENİLİRLİĞİ',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 10),
                if (sk['hata'] != null)
                  Text('${sk['hata']}',
                      style: Theme.of(c).textTheme.bodySmall)
                else ...[
                  Row(
                    children: [
                      SkorHalka(sk['tutma_orani_yuzde'] as num?, boyut: 54, alt: '%'),
                      const SizedBox(width: 14),
                      Expanded(child: Text('${sk['yorum']}')),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Satir('Kırılım sayısı', '${sk['kirilim_sayisi']}'),
                  Satir('Tutan', '${sk['tutan']}', renk: sem.arti),
                  Satir('Sahte çıkan',
                      '${tl(sk['sahte_orani_yuzde'] as num?, basamak: 0)}%',
                      renk: sem.eksi),
                ],
              ],
            ),
          ),
      ],
    );
  }

  // ───────────────────────────────────────────── ŞİRKET

  Widget _sirketSekme(BuildContext c, Sem sem) {
    if (_sirketYukleniyor) {
      return const Yukleniyor(
          mesaj: 'Finansal tablolar ve sektör emsalleri çekiliyor...\n'
              'İlk seferde 1-2 dakika sürebilir.');
    }
    if (_sirket == null) {
      return Bos(Icons.business_sharp, 'Şirket verisi yüklenmedi',
          eylem: TextButton(onPressed: _sirketGetir, child: const Text('Yükle')));
    }
    if (_sirket!['hata'] != null) {
      return Bos(Icons.error_outline_sharp, 'Finansal veri alınamadı',
          alt: 'Bu hisse için yfinance finansal tablo döndürmüyor olabilir.',
          eylem: TextButton(onPressed: _sirketGetir, child: const Text('Tekrar dene')));
    }
    final s = _sirket!;
    final kalite = s['kalite'] as Map<String, dynamic>?;
    final bayrak = (s['bayraklar'] as List?) ?? [];
    final oranlar = (s['oranlar'] as Map?) ?? {};
    final carpanlar = (s['carpanlar'] as Map?) ?? {};
    final dcf = s['ters_dcf'] as Map<String, dynamic>?;
    final hukum = s['hukum'] as Map<String, dynamic>?;
    final rehber = s['sektor_rehberi'] as Map<String, dynamic>?;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
      children: [
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${s['ad']}', style: Theme.of(c).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text('${s['sektor']} · ${s['sanayi']}',
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      color: Theme.of(c).colorScheme.onSurfaceVariant)),
              const SizedBox(height: 12),
              Row(
                children: [
                  SkorHalka(kalite?['skor'] as num?, boyut: 62, alt: 'kalite'),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Piyasa değeri ${buyukTl(s['piyasa_degeri'] as num?)} ₺',
                            style: const TextStyle(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 4),
                        if (kalite?['banka_modu'] == true)
                          const Rozet('banka modu'),
                      ],
                    ),
                  ),
                ],
              ),
              if (s['kur_uyusmazligi'] == true) ...[
                const SizedBox(height: 12),
                Not(
                  'Finansallar ${s['tablo_para']} cinsinden açıklanıyor, hisse '
                  '${s['fiyat_para']} işlem görüyor. Çarpanlar kur ${tl(s['kur'] as num?)} '
                  'ile düzeltildi — yfinance\'in ham oranları bu hissede yanlıştır.',
                  ikon: Icons.currency_exchange_sharp, renk: sem.uyari,
                  baslik: 'Kur uyuşmazlığı',
                ),
              ],
            ],
          ),
        ),
        if (bayrak.isNotEmpty) ...[
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('KIRMIZI BAYRAKLAR',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.eksi, letterSpacing: 1.1)),
                const SizedBox(height: 8),
                ...bayrak.map((b) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.priority_high_sharp, size: 15, color: sem.eksi),
                          const SizedBox(width: 8),
                          Expanded(child: Text('$b',
                              style: Theme.of(c).textTheme.bodySmall
                                  ?.copyWith(height: 1.45))),
                        ],
                      ),
                    )),
              ],
            ),
          ),
        ],
        const SizedBox(height: 14),
        _oranGrup(c, sem, 'Kârlılık', oranlar,
            ['brut_marj', 'faaliyet_marj', 'favok_marj', 'net_marj']),
        _oranGrup(c, sem, 'Sermaye getirisi', oranlar, ['roe', 'roa', 'roic']),
        _oranGrup(c, sem, 'Borçluluk', oranlar,
            ['borc_ozsermaye', 'net_borc_favok', 'faiz_karsilama']),
        _oranGrup(c, sem, 'Nakit ve büyüme', oranlar,
            ['fcf_marj', 'kar_kalitesi', 'hasilat_buyume', 'hasilat_cagr3']),
        const SizedBox(height: 14),
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('DEĞERLEME',
                  style: Theme.of(c).textTheme.labelSmall?.copyWith(
                      color: sem.aksan, letterSpacing: 1.1)),
              const SizedBox(height: 8),
              ...carpanlar.entries.where((e) => e.value['gecerli'] == true).map((e) {
                final v = e.value as Map;
                final so = v['sektor_ort'] as num?;
                final d = v['deger'] as num?;
                String? not;
                Color? renk;
                if (d != null && so != null && so != 0) {
                  final fark = (d / so - 1) * 100;
                  final dusukUcuz = v['dusuk_ucuz'] as bool? ?? true;
                  final ucuz = dusukUcuz ? fark < 0 : fark > 0;
                  not = 'sektör ${tl(so)} · %${tl(fark.abs(), basamak: 0)} '
                      '${ucuz ? 'ucuz' : 'pahalı'}';
                  renk = ucuz ? sem.arti : sem.eksi;
                }
                return Satir('${v['ad']}', d == null ? '—' : tl(d),
                    not: not, renk: renk);
              }),
              if (hukum != null && hukum['hukum'] != null) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text('Hüküm: ',
                        style: Theme.of(c).textTheme.bodyMedium),
                    Rozet('${hukum['hukum']}',
                        renk: '${hukum['hukum']}'.toLowerCase().contains('ucuz')
                            ? sem.arti
                            : '${hukum['hukum']}'.toLowerCase().contains('pahalı')
                                ? sem.eksi
                                : sem.uyari,
                        dolu: true),
                  ],
                ),
                if (hukum['uyari'] != null) ...[
                  const SizedBox(height: 10),
                  Not('${hukum['uyari']}', ikon: Icons.warning_amber_sharp,
                      renk: sem.uyari),
                ],
              ],
            ],
          ),
        ),
        if (dcf != null && dcf['yorum'] != null) ...[
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('TERS DCF',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 8),
                Text('${dcf['yorum']}',
                    style: Theme.of(c).textTheme.bodyMedium),
                const SizedBox(height: 8),
                Text('${dcf['kiyas']}',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant)),
                const SizedBox(height: 10),
                Not('Soru şu: bu büyüme sence makul mü? Değilse fiyat pahalıdır.',
                    ikon: Icons.help_outline_sharp),
              ],
            ),
          ),
        ],
        if (rehber != null) ...[
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('SEKTÖR REHBERİ · ${rehber['ad']}',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 8),
                Text('${rehber['rehber']}',
                    style: Theme.of(c).textTheme.bodyMedium?.copyWith(height: 1.5)),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _oranGrup(BuildContext c, Sem sem, String baslik, Map oranlar,
      List<String> anahtarlar) {
    final gecerli = anahtarlar
        .where((a) => oranlar[a] != null && oranlar[a]['gecerli'] == true)
        .toList();
    if (gecerli.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Kutu(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(baslik.toUpperCase(),
                style: Theme.of(c).textTheme.labelSmall?.copyWith(
                    color: sem.aksan, letterSpacing: 1.1)),
            const SizedBox(height: 6),
            ...gecerli.map((a) {
              final o = oranlar[a] as Map;
              final d = o['deger'] as num?;
              final durum = '${o['durum']}';
              return Satir('${o['ad']}',
                  d == null ? '—' : '${tl(d)}${o['birim']}',
                  renk: durum == 'iyi'
                      ? sem.arti
                      : durum == 'kotu'
                          ? sem.eksi
                          : null,
                  not: o['yorum'] as String?);
            }),
          ],
        ),
      ),
    );
  }

  Future<void> _satDialog(BuildContext c, Pozisyon p) async {
    final fiyatK = TextEditingController(
        text: ((_teknik?['skor'] as Map?)?['fiyat'] as num?)
                ?.toStringAsFixed(2) ??
            '');
    final dersK = TextEditingController();
    final onay = await showDialog<bool>(
      context: c,
      builder: (d) => AlertDialog(
        title: Text('${p.sembol} pozisyonunu kapat'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: fiyatK,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                    labelText: 'Satış fiyatı', suffixText: '₺'),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: dersK,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Ne öğrendin?',
                  hintText: 'Kapanış notu olmayan işlem, tekrarlanacak hatadır.',
                  alignLabelWithHint: true,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false),
              child: const Text('Vazgeç')),
          FilledButton(onPressed: () => Navigator.pop(d, true),
              child: const Text('Kapat')),
        ],
      ),
    );
    if (onay == true) {
      final f = double.tryParse(fiyatK.text.replaceAll(',', '.')) ?? p.giris;
      // Kapatma da deftere yazılıyor; sessiz başarısızlık pozisyonun
      // açık kalmasına ve stop uyarılarının sürmesine yol açar.
      try {
        await depo.pozisyonKapat(p.sembol, f, ders: dersK.text.trim());
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Kapatılamadı — sunucuya ulaşılamadı.'),
          duration: Duration(seconds: 4),
        ));
        return;
      }
      if (mounted) setState(() {});
    }
  }
}
