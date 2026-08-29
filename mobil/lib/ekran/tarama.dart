import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'hisse.dart';

class TaramaEkran extends StatefulWidget {
  const TaramaEkran({super.key});
  @override
  State<TaramaEkran> createState() => _TaramaDurum();
}

class _TaramaDurum extends State<TaramaEkran> {
  Map<String, dynamic>? _veri;
  Object? _hata;
  bool _yukleniyor = true;
  bool _sadeceSinyal = true;
  bool _sadeceAlinabilir = false;

  @override
  void initState() {
    super.initState();
    _getir();
  }

  Future<void> _getir() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final a = depo.ayarlar;
      final r = await depo.api.tarama(
        sermaye: a.sermaye, sadeceSinyal: _sadeceSinyal,
        riskYuzde: a.riskYuzde, azamiPozisyon: a.azamiPozisyon, adet: 60,
      );
      if (!mounted) return;
      setState(() { _veri = r; _yukleniyor = false; });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    var adaylar = (_veri?['adaylar'] as List?) ?? [];
    if (_sadeceAlinabilir) {
      adaylar = adaylar.where((a) {
        final p = a['pozisyon'];
        return p != null && ((p['adet'] as num?) ?? 0) >= 1;
      }).toList();
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tarama'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh_sharp), onPressed: _getir),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(50),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('Sinyal verenler'),
                  selected: _sadeceSinyal,
                  onSelected: (v) {
                    setState(() => _sadeceSinyal = v);
                    _getir();
                  },
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: Text('${tl(depo.ayarlar.sermaye, basamak: 0)} ₺ ile alınabilir'),
                  selected: _sadeceAlinabilir,
                  onSelected: (v) => setState(() => _sadeceAlinabilir = v),
                ),
              ],
            ),
          ),
        ),
      ),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: '100 hisse taranıyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _getir)
              : adaylar.isEmpty
                  ? Bos(Icons.filter_alt_off_sharp,
                      _sadeceSinyal
                          ? 'Bugün sinyal veren hisse yok'
                          : 'Filtreyi geçen hisse yok',
                      alt: _sadeceSinyal
                          ? 'Bu bir sorun değil. Sinyal yoksa işlem yapılmaz —\nnakitte beklemek de bir pozisyondur.'
                          : null,
                      eylem: _sadeceSinyal
                          ? TextButton(
                              onPressed: () {
                                setState(() => _sadeceSinyal = false);
                                _getir();
                              },
                              child: const Text('Tüm hisseleri göster'))
                          : null)
                  : RefreshIndicator(
                      onRefresh: _getir,
                      child: ListView(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                        children: [
                          _ozet(c, sem),
                          const SizedBox(height: 14),
                          // Karantina notu listenin ÜSTÜNDE, yoğunlaşma
                          // notu ALTINDA. İkisi farklı soruya cevap veriyor:
                          // karantina "bu sinyallere güvenilir mi" diyor ve
                          // okumadan ÖNCE bilinmeli; yoğunlaşma ise "bu
                          // sinyaller birbirinden bağımsız mı" diyor ve
                          // ancak listeyi gördükten SONRA anlam kazanıyor.
                          //
                          // Ayrıca ikisi üst üste duruyordu: iki tam
                          // genişlik uyarı kutusu, tek bir hisse görünmeden
                          // önce ekranın yarısını yiyordu.
                          ..._karantinaNotu(c, sem),
                          ...adaylar.map((a) => Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: _adayKart(c, sem, a as Map<String, dynamic>),
                              )),
                          const SizedBox(height: 4),
                          ..._yogunlasmaNotu(c, sem),
                          const SizedBox(height: 10),
                          Not(
                            'Skor bir kesinlik değil, SIRALAMA aracıdır. '
                            '80 puanlık hisse de zarar ettirebilir.',
                            ikon: Icons.info_outline_sharp,
                          ),
                        ],
                      ),
                    ),
    );
  }

  /// Sicili beklenenin altında kalan stratejileri ve gerekçesini gösterir.
  ///
  /// Neden görünür: kullanıcı "önerilen 0" yazısını görüp sebebini
  /// bilmezse sisteme değil kendine güvenmeyi bırakır. Karantina bir
  /// yargıdır; yargının gerekçesi de gösterilmeli.
  /// KARANTİNA ve KAPATMA ayrı şeyler; ikisi de `onerilir: false` ama
  /// aynı cümleyle anlatmak iki yanlış birden söylüyordu.
  ///
  ///   karantina — geçici, veriye bağlı, sinyal ÜRETİLMEYE devam eder
  ///   kapalı    — kalıcı karar, sinyal hiç üretilmez
  List<Widget> _karantinaNotu(BuildContext c, Sem sem) {
    final d = (_veri?['strateji_durumlari'] as Map?) ?? {};
    final karantina = d.entries
        .where((e) => (e.value as Map)['onerilir'] == false &&
            (e.value as Map)['sinif'] != 'kapalı')
        .toList();
    final kapatilan = d.entries
        .where((e) => (e.value as Map)['sinif'] == 'kapalı')
        .toList();

    return [
      if (karantina.isNotEmpty) ...[
        Not(
          'Karantinada: ${karantina.map((e) => e.key).join(', ')}. Bu '
          'stratejilerin sinyalleri gösterilir ama ÖNERİLMEZ — canlı '
          'sicilleri beklenen aralığın altında.'
          '\n\n${(karantina.first.value as Map)['gerekce'] ?? ''}',
          baslik: 'SİCİLİ ZAYIF STRATEJİLER',
          ikon: Icons.gpp_maybe_outlined,
          renk: sem.uyari,
        ),
        const SizedBox(height: 14),
      ],
      if (kapatilan.isNotEmpty) ...[
        Not(
          '${kapatilan.map((e) => e.key).join(', ')} artık sinyal '
          'üretmiyor. Ölçümde para kaybettiği için kapatıldı; geçmiş '
          'sicili kayıt olarak duruyor.',
          baslik: 'KAPATILAN STRATEJİ',
          ikon: Icons.do_not_disturb_on_outlined,
          renk: Renk.metinSolgun,
        ),
        const SizedBox(height: 14),
      ],
    ];
  }

  /// Aynı gün çıkan sinyaller gerçekten farklı bahisler mi?
  ///
  /// Neden görünür: "3 sinyal" yazısı üç ayrı fırsat gibi okunur. Oysa
  /// bu sistemin bütün sinyalleri uzun yönlü ve aynı anda açık — çoğu
  /// zaman tek bir bahsin üç parçası. Sayıyı görmeden bu anlaşılmıyor.
  List<Widget> _yogunlasmaNotu(BuildContext c, Sem sem) {
    final y = (_veri?['yogunlasma'] as Map?) ?? {};
    if (y['yeterli_mi'] != true) return const [];
    final bagimsiz = (y['bagimsiz_bahis'] as num?)?.toDouble() ?? 0;
    final adet = (y['adet'] as num?)?.toInt() ?? 0;
    final zayif = (adet > 1 && bagimsiz < adet * 0.6) ||
        y['sektor_uyarisi'] == true;
    final cift = (y['en_yakin_cift'] as List?)?.join(' ↔ ');
    final ek = StringBuffer();
    if (cift != null) {
      ek.write('\n\nEn yakın çift: $cift '
          '(korelasyon ${y['en_yuksek_korelasyon']}).');
    }
    return [
      Not(
        '${y['yorum']}$ek',
        baslik: 'KAÇ BAĞIMSIZ BAHİS',
        ikon: zayif ? Icons.link_sharp : Icons.hub_outlined,
        renk: zayif ? sem.uyari : null,
      ),
      const SizedBox(height: 14),
    ];
  }

  Widget _ozet(BuildContext c, Sem sem) {
    final v = _veri!;
    return Kutu(
      ic: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      child: Row(
        children: [
          _sayi(c, '${v['toplam']}', 'filtreyi geçti'),
          _ayrac(c),
          _sayi(c, '${v['sinyalli']}', 'sinyal veriyor', renk: sem.aksan),
          _ayrac(c),
          // 'alınabilir' parayla alınabilir demek; 'önerilen' ise sicili
          // beklenenin altında kalan stratejiler ayıklandıktan sonrası.
          // İkincisi olmadan kullanıcı karantinayı hiç görmez.
          _sayi(c, '${v['onerilen'] ?? v['alinabilir']}', 'önerilen',
              renk: (v['onerilen'] ?? 1) == 0 ? sem.uyari : sem.arti),
        ],
      ),
    );
  }

  Widget _ayrac(BuildContext c) =>
      Container(width: 1, height: 30, color: Theme.of(c).dividerColor);

  Widget _sayi(BuildContext c, String s, String etiket, {Color? renk}) => Expanded(
        child: Column(
          children: [
            Text(s,
                style: TextStyle(
                    fontSize: 21, fontWeight: FontWeight.w800, color: renk)),
            Text(etiket,
                textAlign: TextAlign.center,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    fontSize: 11,
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
          ],
        ),
      );

  Widget _adayKart(BuildContext c, Sem sem, Map<String, dynamic> a) {
    final poz = a['pozisyon'] as Map<String, dynamic>?;
    final adet = ((poz?['adet'] as num?) ?? 0).toInt();
    final alinabilir = adet >= 1;
    final sinyaller = (a['sinyaller'] as List?) ?? [];
    final vade = (a['vade'] as String?) ?? '';
    // Sinyal yoksa "ne kadar uzakta" bilgisi. Sinyal VARSA gösterilmez:
    // zaten sinyal var, yakınlık artık haber değil.
    final yakinlik = a['yakinlik'] as Map<String, dynamic>?;
    final yakin = sinyaller.isEmpty && (yakinlik?['yakin'] as bool? ?? false);

    return Kutu(
      tikla: () => Navigator.push(c,
          MaterialPageRoute(builder: (_) => HisseEkran(a['sembol'] as String))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SkorHalka((a['skor'] as num?), boyut: 46),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text('${a['sembol']}',
                            style: Theme.of(c).textTheme.titleMedium),
                        const SizedBox(width: 8),
                        if ((a['sma200_ustu'] as bool?) == true)
                          Icon(Icons.arrow_upward_sharp, size: 13, color: sem.arti)
                        else if ((a['sma200_ustu'] as bool?) == false)
                          Icon(Icons.arrow_downward_sharp, size: 13, color: sem.eksi),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Text('${tl(a['fiyat'] as num?)} ₺',
                            style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontFeatures: [FontFeature.tabularFigures()])),
                        const SizedBox(width: 8),
                        Text(yzd(a['gunluk_degisim'] as num?, basamak: 1),
                            style: TextStyle(
                                color: sem.yon(a['gunluk_degisim'] as num?),
                                fontWeight: FontWeight.w700, fontSize: 13)),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Wrap(
                    spacing: 5,
                    children: sinyaller.map((s) {
                      // Karantinadaki strateji GİZLENMEZ — sicili zayıf diye
                      // saklamak, kullanıcıyı bilgisiz bırakır. Gösterilir
                      // ama uyarı rengiyle ve üstü çizili.
                      final karantina =
                          ((a['sinyaller_karantina'] as List?) ?? []).contains(s);
                      return Rozet(karantina ? '$s ⚠' : '$s',
                          renk: karantina ? sem.uyari : sem.aksan);
                    }).toList(),
                  ),
                  const SizedBox(height: 6),
                  Text('RSI ${tl(a['rsi'] as num?, basamak: 0)}',
                      style: Theme.of(c).textTheme.bodySmall?.copyWith(
                          color: Theme.of(c).colorScheme.onSurfaceVariant)),
                ],
              ),
            ],
          ),
          // Tipik tutma süresi — "aldım, ne kadar tutacağım" sorusunun
          // cevabı ALIM ANINDA verilmeli. Sonradan sorulduğunda cevap
          // artık duygusal oluyor.
          if (vade.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Icon(Icons.schedule_sharp,
                    size: 13, color: Theme.of(c).colorScheme.onSurfaceVariant),
                const SizedBox(width: 6),
                Text('tipik tutma: $vade',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant)),
              ],
            ),
          ],
          if (yakin) ...[
            const SizedBox(height: 10),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.radar_sharp, size: 14, color: sem.uyari),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'sinyale yakın · ${yakinlik!['strateji']} '
                        '${yakinlik['karsilanan']}/${yakinlik['toplam']}',
                        style: TextStyle(
                            color: sem.uyari,
                            fontWeight: FontWeight.w700,
                            fontSize: 12),
                      ),
                      const SizedBox(height: 2),
                      Text('${yakinlik['mesaj']}',
                          style: Theme.of(c).textTheme.bodySmall?.copyWith(
                              height: 1.4,
                              color: Theme.of(c).colorScheme.onSurfaceVariant)),
                    ],
                  ),
                ),
              ],
            ),
          ],
          if (poz != null) ...[
            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 10),
            if (alinabilir)
              Row(
                children: [
                  _kucuk(c, 'Adet', '$adet'),
                  _kucuk(c, 'Tutar', '${tl(poz['maliyet'] as num?)} ₺'),
                  _kucuk(c, 'Stop', '${tl(poz['stop'] as num?)} ₺', renk: sem.eksi),
                  _kucuk(c, 'Hedef', '${tl(poz['hedef'] as num?)} ₺', renk: sem.arti),
                ],
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.block_sharp, size: 15, color: sem.uyari),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('${poz['uyari']}',
                        style: Theme.of(c).textTheme.bodySmall?.copyWith(
                            color: sem.uyari, height: 1.4)),
                  ),
                ],
              ),
          ],
        ],
      ),
    );
  }

  Widget _kucuk(BuildContext c, String e, String d, {Color? renk}) => Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(e,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                    fontSize: 11,
                    color: Theme.of(c).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 1),
            Text(d,
                style: TextStyle(
                    fontWeight: FontWeight.w700, fontSize: 13, color: renk,
                    fontFeatures: const [FontFeature.tabularFigures()])),
          ],
        ),
      );
}
