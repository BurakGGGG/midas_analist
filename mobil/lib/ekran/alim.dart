import 'package:flutter/material.dart';
import '../servis/depo.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';
import 'tez_yaz.dart';

/// Alım kaydı — ama önce davranışsal kapı.
///
/// Kritik uyarı varsa kayıt tek dokunuşla yapılmaz; kullanıcı ek bir adım
/// atmak zorunda kalır. Bu sürtünme bilerek var: kritik uyarıya rağmen alım
/// yapmak bir KARAR olmalı, refleks değil.
class AlimEkran extends StatefulWidget {
  final String sembol;
  final double baslangicFiyat;
  final Map<String, dynamic>? onerilenPozisyon;
  const AlimEkran(this.sembol,
      {super.key, this.baslangicFiyat = 0, this.onerilenPozisyon});

  @override
  State<AlimEkran> createState() => _AlimDurum();
}

class _AlimDurum extends State<AlimEkran> {
  late final TextEditingController _adet, _fiyat, _stop, _hedef;
  Map<String, dynamic>? _kontrol;
  bool _kontrolEdiliyor = false;
  bool _onayVerdi = false;
  String _strateji = 'kirilim';

  @override
  void initState() {
    super.initState();
    final p = widget.onerilenPozisyon;
    _adet = TextEditingController(
        text: '${((p?['adet'] as num?) ?? 1).toInt().clamp(1, 99999)}');
    _fiyat = TextEditingController(
        text: widget.baslangicFiyat > 0
            ? widget.baslangicFiyat.toStringAsFixed(2)
            : '');
    _stop = TextEditingController(
        text: (p?['stop'] as num?)?.toStringAsFixed(2) ?? '');
    _hedef = TextEditingController(
        text: (p?['hedef'] as num?)?.toStringAsFixed(2) ?? '');
    _kontrolEt();
  }

  @override
  void dispose() {
    for (final k in [_adet, _fiyat, _stop, _hedef]) {
      k.dispose();
    }
    super.dispose();
  }

  double _d(TextEditingController k) =>
      double.tryParse(k.text.replaceAll(',', '.')) ?? 0;
  int _i(TextEditingController k) => int.tryParse(k.text.trim()) ?? 0;

  Future<void> _kontrolEt() async {
    final adet = _i(_adet), fiyat = _d(_fiyat);
    if (adet < 1 || fiyat <= 0) return;
    setState(() { _kontrolEdiliyor = true; _onayVerdi = false; });
    try {
      final r = await depo.api.alimKontrol(
        sembol: widget.sembol, adet: adet, fiyat: fiyat,
        sermaye: depo.ayarlar.sermaye,
        tezVarMi: depo.tezVarMi(widget.sembol),
        acik: depo.pozisyonlar,
        gecmis: depo.gecmisGetiriler(),
      );
      if (mounted) setState(() { _kontrol = r; _kontrolEdiliyor = false; });
    } catch (_) {
      if (mounted) setState(() => _kontrolEdiliyor = false);
    }
  }

  Future<void> _kaydet() async {
    final adet = _i(_adet), fiyat = _d(_fiyat);
    if (adet < 1 || fiyat <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Adet ve fiyat girilmeli')));
      return;
    }
    // Kayıt artık SUNUCUDAKİ deftere gidiyor. Ağ hatasında sessiz
    // kalırsak kullanıcı kaydettiğini sanır ama hiçbir yerde yoktur —
    // bir alım kaydının kaybolması, hiç kaydedilmemesinden kötüdür.
    try {
      await depo.pozisyonEkle(Pozisyon(
        sembol: widget.sembol.toUpperCase(), adet: adet, giris: fiyat,
        stop: _d(_stop), hedef: _d(_hedef),
        tarih: DateTime.now().toIso8601String().substring(0, 10),
        strateji: _strateji,
      ));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Kaydedilemedi — sunucuya ulaşılamadı.\n'
            'Bağlantını kontrol edip tekrar dene.'),
        duration: const Duration(seconds: 5),
      ));
      return;
    }
    if (!mounted) return;
    final tezYaz = !depo.tezVarMi(widget.sembol);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text('${widget.sembol.toUpperCase()} kaydedildi. '
          'Emri Midas\'ta gerçekten girdiğinden emin ol.'),
      duration: const Duration(seconds: 4),
    ));
    Navigator.pop(context);
    if (tezYaz) {
      Navigator.push(context,
          MaterialPageRoute(builder: (_) => TezYazEkran(widget.sembol, fiyat: fiyat)));
    }
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final uyarilar = (_kontrol?['uyarilar'] as List?) ?? [];
    final kritik = ((_kontrol?['kritik'] as num?) ?? 0).toInt();
    final kapali = kritik > 0 && !_onayVerdi;

    return Scaffold(
      appBar: AppBar(title: Text('${widget.sembol.toUpperCase()} alım kaydı')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 30),
        children: [
          Kutu(
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(child: _alan(_adet, 'Adet', null, tam: true)),
                    const SizedBox(width: 12),
                    Expanded(child: _alan(_fiyat, 'Alış fiyatı', '₺')),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(child: _alan(_stop, 'Stop', '₺', renk: sem.eksi)),
                    const SizedBox(width: 12),
                    Expanded(child: _alan(_hedef, 'Hedef', '₺', renk: sem.arti)),
                  ],
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(
                  initialValue: _strateji,
                  decoration: const InputDecoration(
                      labelText: 'Strateji', border: OutlineInputBorder()),
                  items: const [
                    DropdownMenuItem(value: 'kirilim', child: Text('kirilim — 20g zirve kırılımı')),
                    DropdownMenuItem(value: 'trend', child: Text('trend — geri çekilme alımı')),
                    DropdownMenuItem(value: 'tepki', child: Text('tepki — aşırı satım')),
                  ],
                  onChanged: (v) => setState(() => _strateji = v ?? 'kirilim'),
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Toplam ${tl(_i(_adet) * _d(_fiyat))} ₺ · '
                    'sermayenin %${tl(_i(_adet) * _d(_fiyat) / depo.ayarlar.sermaye * 100, basamak: 0)}\'i',
                    style: Theme.of(c).textTheme.bodySmall?.copyWith(
                        color: Theme.of(c).colorScheme.onSurfaceVariant),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: _kontrolEdiliyor ? null : _kontrolEt,
              icon: const Icon(Icons.refresh_sharp, size: 17),
              label: const Text('Kontrolü yenile'),
            ),
          ),
          if (_kontrolEdiliyor)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 26),
              child: Yukleniyor(mesaj: 'Davranışsal tarama yapılıyor...'),
            )
          else if (uyarilar.isEmpty && _kontrol != null)
            Not('Davranışsal uyarı yok. Kurallarına uygun görünüyor.',
                ikon: Icons.check_circle_outline_sharp, renk: sem.arti)
          else
            ...uyarilar.map((u) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _uyariKart(c, sem, u as Map<String, dynamic>),
                )),
          const SizedBox(height: 16),
          if (kapali) ...[
            Not(
              '$kritik kritik uyarı var. Yukarıdaki soruları cevapladıysan ve '
              'yine de devam etmek istiyorsan aşağıdaki kutuyu işaretle.\n\n'
              'Bu ek adım bilerek var: kritik uyarıya rağmen alım yapmak bir '
              'karar olmalı, refleks değil.',
              ikon: Icons.gpp_maybe_sharp, renk: sem.eksi,
              baslik: 'Kayıt kilitli',
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              value: _onayVerdi,
              onChanged: (v) => setState(() => _onayVerdi = v ?? false),
              title: const Text('Uyarıları okudum, sorumluluğu alıyorum'),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
            ),
          ],
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: kapali ? null : _kaydet,
            icon: const Icon(Icons.check_sharp),
            label: const Text('Alımı kaydet'),
            style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(50)),
          ),
          const SizedBox(height: 12),
          Not(
            'Bu kayıt Midas\'ta emir GİRMEZ. Emri sen giriyorsun; burası '
            'takip ve disiplin için.',
            ikon: Icons.info_outline_sharp,
          ),
        ],
      ),
    );
  }

  Widget _alan(TextEditingController k, String etiket, String? sonek,
          {Color? renk, bool tam = false}) =>
      TextField(
        controller: k,
        keyboardType: tam
            ? TextInputType.number
            : const TextInputType.numberWithOptions(decimal: true),
        onChanged: (_) => setState(() {}),
        onEditingComplete: _kontrolEt,
        decoration: InputDecoration(
          labelText: etiket, suffixText: sonek,
          border: const OutlineInputBorder(),
          labelStyle: renk == null ? null : TextStyle(color: renk),
        ),
      );

  Widget _uyariKart(BuildContext c, Sem sem, Map<String, dynamic> u) {
    final seviye = '${u['seviye']}';
    final renk = seviye == 'dur'
        ? sem.eksi
        : seviye == 'dikkat'
            ? sem.uyari
            : Theme.of(c).colorScheme.onSurfaceVariant;
    final etiket = {'dur': 'DUR', 'dikkat': 'DİKKAT', 'bilgi': 'BİLGİ'}[seviye] ?? seviye;

    return Kutu(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Rozet(etiket, renk: renk, dolu: seviye == 'dur'),
              const SizedBox(width: 10),
              Expanded(
                child: Text('${u['baslik']}',
                    style: Theme.of(c).textTheme.titleMedium?.copyWith(fontSize: 15)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('${u['aciklama']}',
              style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),
          if ('${u['soru']}'.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(11),
              decoration: BoxDecoration(
                color: renk.withValues(alpha: 0.09),
                borderRadius: kose,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.psychology_sharp, size: 16, color: renk),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('${u['soru']}',
                        style: TextStyle(
                            fontStyle: FontStyle.italic, fontSize: 13,
                            height: 1.45, color: renk)),
                  ),
                ],
              ),
            ),
          ],
          // Uyarı ne yapılacağını söylüyor; yapmayı da sunmalı.
          // "Tezini yaz" deyip kullanıcıyı arayışa bırakmak yarım iş —
          // hele ki tez yazma ekranı iki dokunuş uzaktayken.
          if ('${u['kod']}' == 'tez_yok') ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                // Dönüşte kontrol yenileniyor: tez yazıldıysa "tez yok"
                // uyarısı kalkmalı, yoksa kullanıcı yazdığı halde uyarıyı
                // görmeye devam eder ve kilidi elle açmak zorunda kalır.
                onPressed: () => Navigator.push<void>(
                    c,
                    MaterialPageRoute(
                        builder: (_) => TezYazEkran(widget.sembol,
                            fiyat: _d(_fiyat)))).then((_) => _kontrolEt()),
                icon: const Icon(Icons.edit_note_sharp, size: 18),
                label: const Text('TEZİNİ YAZ'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
