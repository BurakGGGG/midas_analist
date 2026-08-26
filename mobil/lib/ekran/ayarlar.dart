import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../servis/api.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'sermaye.dart';

class AyarlarEkran extends StatefulWidget {
  const AyarlarEkran({super.key});
  @override
  State<AyarlarEkran> createState() => _AyarlarDurum();
}

class _AyarlarDurum extends State<AyarlarEkran> {
  late TextEditingController _sunucu, _anahtar, _risk, _pozisyon;
  String? _baglanti;
  bool _deneniyor = false;

  @override
  void initState() {
    super.initState();
    final a = depo.ayarlar;
    _sunucu = TextEditingController(text: a.sunucu);
    _anahtar = TextEditingController(text: a.apiAnahtar);
    _risk = TextEditingController(text: a.riskYuzde.toString());
    _pozisyon = TextEditingController(text: a.azamiPozisyon.toStringAsFixed(0));
  }

  @override
  void dispose() {
    for (final k in [_sunucu, _anahtar, _risk, _pozisyon]) {
      k.dispose();
    }
    super.dispose();
  }

  Future<void> _dene() async {
    setState(() { _deneniyor = true; _baglanti = null; });
    try {
      final r = await Api(_sunucu.text.trim(),
              anahtar: _anahtar.text.trim())
          .saglik();
      final ob = r['onbellek'] as Map?;
      setState(() => _baglanti = 'Bağlantı kuruldu · '
          '${ob?['hisse_sayisi'] ?? '?'} hisse önbellekte · '
          '${(ob?['hazir'] == true) ? 'hazır' : 'hazırlanıyor'}');
    } catch (e) {
      setState(() => _baglanti = e is ApiHata ? '${e.mesaj}\n${e.oneri ?? ''}' : '$e');
    } finally {
      if (mounted) setState(() => _deneniyor = false);
    }
  }

  Future<void> _kaydet() async {
    await depo.ayarKaydet(depo.ayarlar.kopya(
      sunucu: _sunucu.text.trim(),
      apiAnahtar: _anahtar.text.trim(),
      riskYuzde: double.tryParse(_risk.text.replaceAll(',', '.')),
      azamiPozisyon: double.tryParse(_pozisyon.text.replaceAll(',', '.')),
    ));
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Ayarlar kaydedildi')));
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Ayarlar')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
        children: [
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('SUNUCU',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.1)),
                const SizedBox(height: 10),
                TextField(
                  controller: _sunucu,
                  keyboardType: TextInputType.url,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: 'http://192.168.1.20:8000',
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  children: [
                    ActionChip(
                      label: const Text('Android emülatör'),
                      onPressed: () =>
                          setState(() => _sunucu.text = 'http://10.0.2.2:8000'),
                    ),
                    ActionChip(
                      label: const Text('Aynı cihaz'),
                      onPressed: () =>
                          setState(() => _sunucu.text = 'http://127.0.0.1:8000'),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _anahtar,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'API anahtarı (bulut için)',
                    helperText: 'Yerel ağda boş bırak. Cloud Run\'a dağıttıysan '
                        'dagit.sh\'ın verdiği anahtarı gir.',
                    helperMaxLines: 2,
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton.tonalIcon(
                  onPressed: _deneniyor ? null : _dene,
                  icon: _deneniyor
                      ? const SizedBox(
                          width: 15, height: 15,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.wifi_tethering_sharp, size: 18),
                  label: const Text('Bağlantıyı dene'),
                ),
                if (_baglanti != null) ...[
                  const SizedBox(height: 10),
                  Not(_baglanti!,
                      ikon: _baglanti!.startsWith('Bağlantı kuruldu')
                          ? Icons.check_circle_outline_sharp
                          : Icons.error_outline_sharp,
                      renk: _baglanti!.startsWith('Bağlantı kuruldu')
                          ? sem.arti : sem.eksi),
                ],
                const SizedBox(height: 12),
                Not(
                  'Gerçek telefondan bağlanıyorsan PC\'nin yerel IP adresini yaz '
                  '(PC\'de: hostname -I). Telefon ve PC aynı Wi-Fi\'da olmalı.',
                  ikon: Icons.lightbulb_outline_sharp,
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Kutu(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('RİSK KURALLARI',
                    style: Theme.of(c).textTheme.labelSmall?.copyWith(
                        color: sem.aksan, letterSpacing: 1.4)),
                const SizedBox(height: 12),
                // Sermaye BURADA düzenlenmez. Defterden türüyor; iki yerden
                // yazılırsa "yatırdığın para" ile toplam arasındaki bağ kopar.
                InkWell(
                  onTap: () => Navigator.push(c,
                      MaterialPageRoute(builder: (_) => const SermayeEkran())),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      borderRadius: kose,
                      border: Border.all(color: Renk.cizgi),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Toplam sermaye',
                                  style: TextStyle(
                                      fontSize: 12,
                                      color: Renk.metinSolgun)),
                              const SizedBox(height: 3),
                              Text('${tl(depo.ayarlar.sermaye)} ₺',
                                  style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.w700)),
                            ],
                          ),
                        ),
                        const Text('SERMAYE EKRANI  ›',
                            style: TextStyle(
                                fontSize: 10,
                                letterSpacing: 0.8,
                                fontWeight: FontWeight.w700,
                                color: Renk.aksan)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _risk,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                      labelText: 'İşlem başına risk', suffixText: '%',
                      helperText: '1000 ₺\'de %1,5 = 15 ₺. %2 üstü küçük hesapta hızlı erimedir.',
                      helperMaxLines: 2,
                      border: OutlineInputBorder(), isDense: true),
                ),
                const SizedBox(height: 18),
                TextField(
                  controller: _pozisyon,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                      labelText: 'Tek hissede azami pay', suffixText: '%',
                      helperText: 'BIST\'te kesirli hisse yok — bu tavan pahalı hisseleri eler.',
                      helperMaxLines: 2,
                      border: OutlineInputBorder(), isDense: true),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: _kaydet,
            icon: const Icon(Icons.save_sharp),
            label: const Text('Kaydet'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
          ),
        ],
      ),
    );
  }
}
