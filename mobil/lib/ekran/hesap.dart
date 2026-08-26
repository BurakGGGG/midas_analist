import 'package:flutter/material.dart';

import '../servis/hesap.dart';
import '../servis/modeller.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// Hesap ve bulut yedeği ekranı.
///
/// İki hâli var ve bilerek tek ekranda: girişli değilsen giriş/kayıt formu,
/// girişliysen yedek durumu. Ayrı ekranlara bölmek, "yedeğim alınıyor mu"
/// sorusunu iki tık uzağa iterdi.
class HesapEkran extends StatefulWidget {
  const HesapEkran({super.key});
  @override
  State<HesapEkran> createState() => _HesapDurum();
}

class _HesapDurum extends State<HesapEkran> {
  final _eposta = TextEditingController();
  final _parola = TextEditingController();
  bool _kayitModu = false;
  bool _mesgul = false;
  String? _hata;
  String? _bilgi;

  @override
  void dispose() {
    _eposta.dispose();
    _parola.dispose();
    super.dispose();
  }

  Future<void> _calistir(Future<void> Function() is_, {String? basari}) async {
    setState(() { _mesgul = true; _hata = null; _bilgi = null; });
    try {
      await is_();
      if (mounted) setState(() => _bilgi = basari);
    } on ApiHata catch (e) {
      if (mounted) setState(() => _hata = e.oneri ?? e.mesaj);
    } catch (e) {
      if (mounted) setState(() => _hata = '$e');
    } finally {
      if (mounted) setState(() => _mesgul = false);
    }
  }

  Future<void> _girisYap() => _calistir(() async {
        final e = _eposta.text.trim();
        final p = _parola.text;
        if (_kayitModu) {
          await hesap.kayit(e, p);
          // Yeni hesabın ilk yedeği hemen alınsın: kullanıcı "kayıt oldum
          // ama bulutta bir şey yok" boşluğunu görmesin.
          await hesap.yedekle(zorla: true);
        } else {
          await hesap.giris(e, p);
        }
        _parola.clear();
      }, basari: _kayitModu ? 'Hesap açıldı ve ilk yedek alındı.' : null);

  Future<void> _geriYukle() async {
    final onay = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('Buluttan geri yükle'),
        content: const Text(
            'Telefondaki portföy, tezler, karar defteri, sermaye defteri ve '
            'eğitim ilerlemesi buluttaki kopyayla DEĞİŞTİRİLECEK.\n\n'
            'Bu geri alınamaz.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(c, true),
              child: const Text('Geri yükle')),
        ],
      ),
    );
    if (onay != true) return;
    await _calistir(() async {
      final r = await hesap.geriYukle();
      if (r['geri_yuklendi'] != true) throw ApiHata('${r['not']}');
    }, basari: 'Buluttaki yedek telefona yazıldı.');
  }

  Future<void> _yedekle() async {
    await _calistir(() async {
      final r = await hesap.yedekle();
      if (r['cakisma'] == true) {
        // Bulutta bizden YENİ bir yedek var: başka bir cihaz yazmış.
        // Sessizce ezmek, o cihazın verisini yok etmek olurdu.
        if (!mounted) return;
        final ez = await showDialog<bool>(
          context: context,
          builder: (c) => AlertDialog(
            backgroundColor: Renk.panel,
            shape: const RoundedRectangleBorder(borderRadius: kose),
            title: const Text('Bulutta daha yeni bir yedek var'),
            content: Text(
                'Başka bir cihaz senden sonra yedek almış '
                '(sürüm ${r['surum']}).\n\n'
                'Bu telefondakini yazarsan o cihazın verisi kaybolur.'),
            actions: [
              TextButton(onPressed: () => Navigator.pop(c, false),
                  child: const Text('Vazgeç')),
              TextButton(onPressed: () => Navigator.pop(c, true),
                  child: const Text('Yine de yaz')),
            ],
          ),
        );
        if (ez == true) await hesap.yedekle(zorla: true);
      }
    }, basari: 'Yedek alındı.');
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Hesap')),
      body: ListenableBuilder(
        listenable: hesap,
        builder: (_, __) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
          children: [
            if (_hata != null) ...[
              _Kutucuk(_hata!, renk: sem.eksi, ikon: Icons.error_outline_sharp),
              const SizedBox(height: 12),
            ],
            if (_bilgi != null) ...[
              _Kutucuk(_bilgi!, renk: sem.arti, ikon: Icons.check_sharp),
              const SizedBox(height: 12),
            ],
            if (hesap.girisli) ..._girisli(c, sem) else ..._girisSiz(c, sem),
          ],
        ),
      ),
    );
  }

  // ── girişli ───────────────────────────────────────────────────────────────

  List<Widget> _girisli(BuildContext c, Sem sem) => [
        Kutu(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('GİRİŞ YAPILDI',
                  style: Theme.of(c).textTheme.labelSmall
                      ?.copyWith(color: sem.arti, letterSpacing: 1.2)),
              const SizedBox(height: 8),
              Text(hesap.eposta ?? '',
                  style: Theme.of(c).textTheme.bodyLarge),
              const SizedBox(height: 12),
              Satir('Son yedek', _zaman(hesap.sonYedek)),
              Satir('Yedek sürümü', '${hesap.surum}'),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Not(
          'Değişiklikler otomatik yedekleniyor — alım kaydettiğinde ya da '
          'ders okuduğunda birkaç saniye sonra buluta gidiyor.',
          ikon: Icons.cloud_done_sharp, renk: sem.aksan,
        ),
        const SizedBox(height: 14),
        // Düğme hiyerarşisi temadan geliyor: dolu = birincil eylem,
        // çerçeveli = ikincil, düz = geri dönüşü olan/kaçış. Önceden üçü
        // de aynı kutu satırıydı ve hangisinin ana eylem olduğu
        // görünmüyordu.
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _mesgul ? null : _yedekle,
            icon: const Icon(Icons.cloud_upload_sharp, size: 18),
            label: const Text('ŞİMDİ YEDEKLE'),
          ),
        ),
        const SizedBox(height: 9),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _mesgul ? null : _geriYukle,
            icon: const Icon(Icons.cloud_download_sharp, size: 18),
            label: const Text('BULUTTAN GERİ YÜKLE'),
          ),
        ),
        const SizedBox(height: 4),
        Center(
          child: TextButton(
            onPressed: _mesgul ? null : () => _calistir(hesap.cikis),
            child: const Text('Çıkış yap'),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'Yedeklenenler: portföy, tezler, karar defteri, sermaye defteri, '
          'eğitim ilerlemesi ve ayarlar.\n\n'
          'Yedeklenmeyenler: müfredat, soru bankası ve sözlük — üçü de '
          'sunucudan yeniden inebiliyor.\n\n'
          'API anahtarı buluta GİTMEZ. Yeni telefonda sunucuya ulaşmak için '
          'onu zaten elle giriyorsun.',
          style: Theme.of(c).textTheme.bodySmall
              ?.copyWith(color: Renk.metinSolgun, height: 1.55),
        ),
      ];

  // ── girişsiz ──────────────────────────────────────────────────────────────

  List<Widget> _girisSiz(BuildContext c, Sem sem) => [
        Not(
          'Uygulamayı yeniden kurduğunda portföy, tezler ve eğitim ilerlemen '
          'telefonda kalmaz. Hesap açarsan sunucunda saklanır ve yeni '
          'telefonda geri gelir.',
          ikon: Icons.cloud_sharp, renk: sem.aksan,
        ),
        const SizedBox(height: 14),
        // Alanlar Kutu İÇİNDE değil: kutunun kendi kenarlığı ile alanın
        // kenarlığı iç içe iki çerçeve yapıyordu ve form gereğinden ağır
        // görünüyordu.
        TextField(
          controller: _eposta,
          keyboardType: TextInputType.emailAddress,
          autocorrect: false,
          style: Theme.of(c).textTheme.bodyMedium,
          decoration: const InputDecoration(labelText: 'E-posta'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _parola,
          obscureText: true,
          style: Theme.of(c).textTheme.bodyMedium,
          decoration: InputDecoration(
              labelText:
                  _kayitModu ? 'Parola (en az 8 karakter)' : 'Parola'),
          onSubmitted: (_) => _mesgul ? null : _girisYap(),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _mesgul ? null : _girisYap,
            child: Text(_kayitModu ? 'HESAP AÇ' : 'GİRİŞ YAP'),
          ),
        ),
        const SizedBox(height: 4),
        Center(
          child: TextButton(
            onPressed: _mesgul
                ? null
                : () => setState(() { _kayitModu = !_kayitModu; _hata = null; }),
            child: Text(_kayitModu
                ? 'Zaten hesabım var — giriş yap'
                : 'Hesabım yok — yeni hesap aç'),
          ),
        ),
      ];

  static String _zaman(String? iso) {
    if (iso == null || iso.isEmpty) return 'henüz yok';
    final t = DateTime.tryParse(iso)?.toLocal();
    if (t == null) return iso;
    String i(int n) => n.toString().padLeft(2, '0');
    return '${i(t.day)}.${i(t.month)}.${t.year}  ${i(t.hour)}:${i(t.minute)}';
  }
}

class _Kutucuk extends StatelessWidget {
  final String metin;
  final Color renk;
  final IconData ikon;
  const _Kutucuk(this.metin, {required this.renk, required this.ikon});

  @override
  Widget build(BuildContext c) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: renk.withValues(alpha: 0.08),
          borderRadius: kose,
          border: Border.all(color: renk.withValues(alpha: 0.35)),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ikon, size: 17, color: renk),
          const SizedBox(width: 10),
          Expanded(
            child: Text(metin,
                style: Theme.of(c).textTheme.bodySmall?.copyWith(height: 1.5)),
          ),
        ]),
      );
}
