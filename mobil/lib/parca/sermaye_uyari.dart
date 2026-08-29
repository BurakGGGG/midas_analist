import 'package:flutter/material.dart';

import '../parca/kart.dart';
import '../servis/depo.dart';
import '../tema.dart';

/// Bedelsiz / sermaye artırımı uyarısı.
///
/// NEDEN AYRI BİR PARÇA: aynı uyarı hem portföyde hem hisse ekranında
/// gösteriliyor. İki yere kopyalansaydı biri güncellenip öteki
/// unutulurdu.
///
/// NEDEN ÖNEMLİ: bedelsizden sonra fiyat MEKANİK olarak düşer. Hisse
/// ucuzlamaz, adet artar, toplam para aynı kalır. Bunu bilmeyen
/// kullanıcı aracı kurum ekranında −%50 görüp panik satar — hiçbir şey
/// olmadığı bir günde hayatının en pahalı kararını verir.
class SermayeUyarisi extends StatefulWidget {
  /// Boş liste = sunucunun izlediği hisseler.
  final List<String> semboller;

  const SermayeUyarisi({super.key, this.semboller = const []});

  @override
  State<SermayeUyarisi> createState() => _SermayeUyarisiDurum();
}

class _SermayeUyarisiDurum extends State<SermayeUyarisi> {
  List<dynamic> _islemler = const [];

  @override
  void initState() {
    super.initState();
    _getir();
  }

  @override
  void didUpdateWidget(SermayeUyarisi eski) {
    super.didUpdateWidget(eski);
    if (eski.semboller.join(',') != widget.semboller.join(',')) _getir();
  }

  Future<void> _getir() async {
    try {
      final r = await depo.api.sermayeIslemleri(semboller: widget.semboller);
      if (mounted) setState(() => _islemler = (r['islemler'] ?? []) as List);
    } catch (_) {
      // Sessiz: uyarı gelmemesi ekranı bozmamalı.
    }
  }

  @override
  Widget build(BuildContext c) {
    if (_islemler.isEmpty) return const SizedBox.shrink();
    final sem = Sem(c);
    return Column(
      children: _islemler.take(3).map((x) {
        final m = Map<String, dynamic>.from(x as Map);
        final boler = m['fiyat_bolunur'] == true;
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Not(
            '${m['aciklama']}',
            // Bölünme uyarısı UYARI rengiyle: kullanıcı ekranda büyük
            // bir düşüş görmeden ÖNCE dikkatini çekmeli. Diğer sermaye
            // işlemleri bilgi niteliğinde.
            baslik: boler
                ? '${m['sembol']} · FİYAT MEKANİK OLARAK DÜŞECEK'
                : '${m['sembol']} · ${m['konu']}',
            ikon: boler ? Icons.call_split_sharp : Icons.info_outline_sharp,
            renk: boler ? sem.uyari : Renk.metinSolgun,
          ),
        );
      }).toList(),
    );
  }
}
