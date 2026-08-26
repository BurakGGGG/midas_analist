import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Tez yazma. Sekiz soru, en kritiği "hangi durumda yanıldığını kabul edeceksin".
/// Bu cevap ÖNCEDEN yazılmazsa sonradan hiç yazılmaz — her düşüş "geçici" görünür.
class TezYazEkran extends StatefulWidget {
  final String sembol;
  final double fiyat;
  const TezYazEkran(this.sembol, {super.key, this.fiyat = 0});
  @override
  State<TezYazEkran> createState() => _TezYazDurum();
}

class _TezYazDurum extends State<TezYazEkran> {
  List<Map<String, String>> _sorular = [];
  final Map<String, TextEditingController> _k = {};
  Map<String, dynamic>? _anlik;
  bool _yukleniyor = true, _kaydediyor = false;
  Object? _hata;

  @override
  void initState() {
    super.initState();
    _hazirla();
  }

  @override
  void dispose() {
    for (final k in _k.values) {
      k.dispose();
    }
    super.dispose();
  }

  Future<void> _hazirla() async {
    setState(() { _yukleniyor = true; _hata = null; });
    try {
      final api = depo.api;
      final sonuc = await Future.wait([
        api.tezSorulari(),
        api.tezAnlik(widget.sembol, sermaye: depo.ayarlar.sermaye),
      ]);
      final sorular = (sonuc[0] as List)
          .map((s) => {'anahtar': '${s['anahtar']}', 'soru': '${s['soru']}'})
          .toList();
      final mevcut = depo.acikTez(widget.sembol);
      if (!mounted) return;
      setState(() {
        _sorular = sorular;
        _anlik = sonuc[1] as Map<String, dynamic>;
        for (final s in sorular) {
          _k[s['anahtar']!] =
              TextEditingController(text: mevcut?.cevaplar[s['anahtar']!] ?? '');
        }
        depo.tezSorulari = sorular;
        _yukleniyor = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _hata = e; _yukleniyor = false; });
    }
  }

  Future<void> _kaydet() async {
    setState(() => _kaydediyor = true);
    final cevaplar = <String, String>{};
    _k.forEach((a, k) => cevaplar[a] = k.text.trim());
    final poz = depo.pozisyon(widget.sembol);
    await depo.tezEkle(Tez(
      sembol: widget.sembol.toUpperCase(),
      tarih: DateTime.now().toIso8601String().substring(0, 10),
      fiyat: widget.fiyat > 0
          ? widget.fiyat
          : ((_anlik?['teknik'] as Map?)?['fiyat'] as num?)?.toDouble() ?? 0,
      adet: poz?.adet ?? 0,
      cevaplar: cevaplar,
      anlik: _anlik ?? {},
    ));
    if (!mounted) return;
    final eksik = cevaplar.values.where((v) => v.isEmpty).length;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(eksik == 0
          ? 'Tez kaydedildi — tamamı dolu.'
          : 'Tez kaydedildi ($eksik soru boş kaldı).'),
    ));
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: Text('${widget.sembol.toUpperCase()} tezi')),
      body: _yukleniyor
          ? const Yukleniyor(mesaj: 'Alım anındaki durum kaydediliyor...')
          : _hata != null
              ? HataGorunum(_hata!, tekrar: _hazirla)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
                  children: [
                    Not(
                      'Bir hisseyi neden aldığını yazmadan alırsan, düştüğünde '
                      'neden tuttuğunu da bilemezsin. O boşluğu umut doldurur.',
                      ikon: Icons.edit_note_sharp, renk: sem.aksan,
                    ),
                    const SizedBox(height: 14),
                    if (_anlik != null) _anlikKart(c, sem),
                    const SizedBox(height: 14),
                    ..._sorular.map((s) {
                      final kritik = s['anahtar'] == 'yanilma_kosulu';
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: Kutu(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(s['soru']!,
                                        style: Theme.of(c)
                                            .textTheme
                                            .titleMedium
                                            ?.copyWith(fontSize: 14.5)),
                                  ),
                                  if (kritik) ...[
                                    const SizedBox(width: 8),
                                    Rozet('EN KRİTİK', renk: sem.eksi),
                                  ],
                                ],
                              ),
                              const SizedBox(height: 10),
                              TextField(
                                controller: _k[s['anahtar']!],
                                maxLines: null,
                                minLines: 2,
                                textCapitalization: TextCapitalization.sentences,
                                decoration: InputDecoration(
                                  border: const OutlineInputBorder(),
                                  hintText: kritik
                                      ? 'Somut ve ölçülebilir yaz: fiyat seviyesi ya da olay'
                                      : null,
                                  isDense: true,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),
                    FilledButton.icon(
                      onPressed: _kaydediyor ? null : _kaydet,
                      icon: const Icon(Icons.save_sharp),
                      label: const Text('Tezi kaydet'),
                      style: FilledButton.styleFrom(
                          minimumSize: const Size.fromHeight(50)),
                    ),
                  ],
                ),
    );
  }

  Widget _anlikKart(BuildContext c, Sem sem) {
    final t = _anlik!['teknik'] as Map<String, dynamic>?;
    final tm = _anlik!['temel'] as Map<String, dynamic>?;
    final mk = _anlik!['makro'] as Map<String, dynamic>?;
    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('BUGÜNÜN OBJEKTİF GÖRÜNTÜSÜ',
              style: Theme.of(c).textTheme.labelSmall?.copyWith(
                  color: sem.aksan, letterSpacing: 1.1)),
          const SizedBox(height: 4),
          Text('Tezle birlikte dondurulur. Altı ay sonra "aslında biliyordum" '
              'demek yerine o günkü gerçek rakamlara bakarsın.',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(
                  color: Theme.of(c).colorScheme.onSurfaceVariant, height: 1.4)),
          const SizedBox(height: 10),
          if (t != null) ...[
            Satir('Teknik skor', tl(t['skor'] as num?, basamak: 0)),
            Satir('RSI', tl(t['rsi'] as num?, basamak: 0)),
            Satir('200 gün ortalaması',
                (t['sma200_ustu'] as bool?) == true ? 'üstünde' : 'altında',
                renk: (t['sma200_ustu'] as bool?) == true ? sem.arti : sem.eksi),
          ],
          if (tm != null) ...[
            Satir('Kalite skoru', tl(tm['kalite_skoru'] as num?, basamak: 0)),
            if ((tm['kirmizi_bayrak'] as List?)?.isNotEmpty ?? false)
              Satir('Kırmızı bayrak',
                  '${(tm['kirmizi_bayrak'] as List).length} adet',
                  renk: sem.eksi),
          ],
          if (mk != null)
            Satir('Piyasa rejimi', '${mk['rejim']}'),
        ],
      ),
    );
  }
}
