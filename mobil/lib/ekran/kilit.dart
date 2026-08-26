import 'dart:async';

import 'package:flutter/material.dart';

import '../servis/hesap.dart';
import '../servis/kilit.dart';
import '../parca/kart.dart';
import '../tema.dart';

/// PIN girişi — uygulamanın önünde duran kilit ekranı.
///
/// Kendi tuş takımını çiziyor, sistem klavyesini kullanmıyor. Sebep: sayı
/// klavyesi cihazdan cihaza değişiyor, bazılarında öneri çubuğu ve pano
/// yapıştırma çıkıyor. Altı hane için kendi tuşlarımız hem daha hızlı hem
/// tema kurallarına (sıfır yuvarlaklık) uyuyor.
class KilitEkran extends StatefulWidget {
  /// Kilidi açtıktan sonra ne olacak. Null ise ekran kendini kapatır.
  final VoidCallback? acilinca;
  const KilitEkran({super.key, this.acilinca});

  @override
  State<KilitEkran> createState() => _KilitDurum();
}

class _KilitDurum extends State<KilitEkran> {
  String _pin = '';
  bool _mesgul = false;
  String? _hata;
  Timer? _sayac;

  @override
  void initState() {
    super.initState();
    // Bekleme süresi geri sayarken ekran her saniye tazelensin.
    _sayac = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted && kilit.bekleme > 0) setState(() {});
    });
  }

  @override
  void dispose() {
    _sayac?.cancel();
    super.dispose();
  }

  Future<void> _bas(String d) async {
    if (_mesgul || kilit.bekleme > 0) return;
    if (_pin.length >= Kilit.basamak) return;
    setState(() { _pin += d; _hata = null; });
    if (_pin.length == Kilit.basamak) await _dene();
  }

  void _sil() {
    if (_mesgul || _pin.isEmpty) return;
    setState(() => _pin = _pin.substring(0, _pin.length - 1));
  }

  Future<void> _dene() async {
    setState(() => _mesgul = true);
    final ok = await kilit.dogrula(_pin);
    if (!mounted) return;
    if (ok) {
      if (widget.acilinca != null) {
        widget.acilinca!();
      } else {
        Navigator.pop(context, true);
      }
      return;
    }
    setState(() {
      _mesgul = false;
      _pin = '';
      _hata = kilit.bekleme > 0
          ? null
          : 'Yanlış PIN. ${_kalanHak()} deneme sonra bekleme başlar.';
    });
  }

  String _kalanHak() {
    final k = 5 - kilit.deneme;
    return k > 0 ? '$k' : '0';
  }

  Future<void> _unuttum() async {
    if (!hesap.girisli) {
      showDialog(
        context: context,
        builder: (c) => AlertDialog(
          backgroundColor: Renk.panel,
          shape: const RoundedRectangleBorder(borderRadius: kose),
          title: const Text('Hesap yok'),
          content: const Text(
              'PIN sıfırlamanın tek yolu bulut hesabının parolası. Bu '
              'telefonda giriş yapılmış bir hesap yok.\n\n'
              'Bu durumda uygulamayı kaldırıp yeniden kurmak gerekir ve '
              'telefondaki veri gider.'),
          actions: [TextButton(
              onPressed: () => Navigator.pop(c), child: const Text('Tamam'))],
        ),
      );
      return;
    }
    final parola = await _parolaSor();
    if (parola == null || parola.isEmpty) return;
    setState(() => _mesgul = true);
    final ok = await kilit.hesapParolasiylaSifirla(parola);
    if (!mounted) return;
    setState(() { _mesgul = false; _pin = ''; });
    if (ok) {
      if (widget.acilinca != null) {
        widget.acilinca!();
      } else if (mounted) {
        Navigator.pop(context, true);
      }
    } else {
      setState(() => _hata = 'Hesap parolası doğrulanamadı.');
    }
  }

  Future<String?> _parolaSor() {
    final d = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('Hesap parolan'),
        content: TextField(
          controller: d, obscureText: true, autofocus: true,
          decoration: InputDecoration(labelText: hesap.eposta ?? ''),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(c, d.text),
              child: const Text('Doğrula')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final bekle = kilit.bekleme;
    return Scaffold(
      backgroundColor: Renk.zemin,
      // Tuş takımı ALTTA, kimlik ve noktalar üstteki boşlukta ortalı.
      // Önce hepsi dikey ortadaydı: ekranın altı boş kalıyor, tuşlar
      // başparmağın ulaşamayacağı yükseklikte duruyordu.
      body: SafeArea(
        child: Column(
          children: [
            // Center ŞART: Expanded içindeki kaydırma görünümü tüm boyu
            // kaplar ve içeriği yukarı yapıştırır — mainAxisAlignment
            // orada işe yaramaz, çünkü Column zaten içeriği kadar.
            // Center, kaydırma görünümünü içeriği kadar küçültüp ortalar.
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 32, vertical: 20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                Icon(Icons.lock_outline_sharp, size: 34, color: sem.aksan),
                const SizedBox(height: 14),
                Text('Midas Analist',
                    style: Theme.of(c).textTheme.titleMedium),
                const SizedBox(height: 6),
                Text(bekle > 0 ? 'Çok fazla hatalı deneme' : 'PIN gir',
                    style: Theme.of(c).textTheme.bodySmall
                        ?.copyWith(color: Renk.metinSolgun)),
                const SizedBox(height: 26),

                _Noktalar(dolu: _pin.length, hata: _hata != null),

                const SizedBox(height: 18),
                SizedBox(
                  height: 34,
                  child: bekle > 0
                      ? Text('${_sure(bekle)} sonra tekrar dene',
                          style: Theme.of(c).textTheme.bodyMedium
                              ?.copyWith(color: sem.uyari))
                      : (_hata == null
                          ? const SizedBox.shrink()
                          : Text(_hata!,
                              textAlign: TextAlign.center,
                              style: Theme.of(c).textTheme.bodySmall
                                  ?.copyWith(color: sem.eksi))),
                ),
                    ],
                  ),
                ),
              ),
            ),
            _TusTakimi(
              etkin: !_mesgul && bekle == 0,
              bas: _bas,
              sil: _sil,
            ),
            const SizedBox(height: 4),
            TextButton(
              onPressed: _mesgul ? null : _unuttum,
              // Kaçış yolu, ana eylem değil: aksan yeşili tuş takımıyla
              // yarışıyordu.
              style: TextButton.styleFrom(foregroundColor: Renk.metinSolgun),
              child: const Text('PIN\'i unuttum'),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  static String _sure(int sn) {
    if (sn < 60) return '$sn saniye';
    final d = (sn / 60).ceil();
    return '$d dakika';
  }
}

/// PIN kurma / değiştirme. İki adım: gir, doğrula.
class KilitKurEkran extends StatefulWidget {
  final bool degistir;
  const KilitKurEkran({super.key, this.degistir = false});
  @override
  State<KilitKurEkran> createState() => _KurDurum();
}

class _KurDurum extends State<KilitKurEkran> {
  String _ilk = '';
  String _pin = '';
  String? _hata;
  bool _mesgul = false;

  bool get _dogrulamaAdimi => _ilk.isNotEmpty;

  Future<void> _bas(String d) async {
    if (_mesgul || _pin.length >= Kilit.basamak) return;
    setState(() { _pin += d; _hata = null; });
    if (_pin.length < Kilit.basamak) return;

    if (!_dogrulamaAdimi) {
      setState(() { _ilk = _pin; _pin = ''; });
      return;
    }
    if (_pin != _ilk) {
      setState(() { _hata = 'İki giriş aynı değil.'; _ilk = ''; _pin = ''; });
      return;
    }
    setState(() => _mesgul = true);
    await kilit.kur(_pin);
    if (mounted) Navigator.pop(context, true);
  }

  void _sil() {
    if (_pin.isEmpty) return;
    setState(() => _pin = _pin.substring(0, _pin.length - 1));
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(
          title: Text(widget.degistir ? 'PIN değiştir' : 'PIN belirle')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _dogrulamaAdimi
                    ? 'Aynı PIN\'i bir daha gir'
                    : '${Kilit.basamak} haneli bir PIN seç',
                style: Theme.of(c).textTheme.bodyLarge,
              ),
              const SizedBox(height: 24),
              _Noktalar(dolu: _pin.length, hata: _hata != null),
              SizedBox(
                height: 40,
                child: Center(
                  child: _hata == null
                      ? const SizedBox.shrink()
                      : Text(_hata!,
                          style: Theme.of(c).textTheme.bodySmall
                              ?.copyWith(color: sem.eksi)),
                ),
              ),
              _TusTakimi(etkin: !_mesgul, bas: _bas, sil: _sil),
              const SizedBox(height: 20),
              Text(
                'PIN telefonda kalır, buluta gitmez. Unutursan bulut '
                'hesabının parolasıyla sıfırlayabilirsin.',
                textAlign: TextAlign.center,
                style: Theme.of(c).textTheme.bodySmall
                    ?.copyWith(color: Renk.metinSolgun, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Daha > Güvenlik: kilidi kur, değiştir, kaldır.
class GuvenlikEkran extends StatefulWidget {
  const GuvenlikEkran({super.key});
  @override
  State<GuvenlikEkran> createState() => _GuvenlikDurum();
}

class _GuvenlikDurum extends State<GuvenlikEkran> {
  Future<void> _kaldir() async {
    // Önce PIN doğrulanır; sonra niyet onayı. İkisi ayrı sorular:
    // biri "sen misin", diğeri "gerçekten istiyor musun".
    final ok = await Navigator.push<bool>(context,
        MaterialPageRoute(builder: (_) => const KilitEkran()));
    if (ok != true || !mounted) return;

    final onay = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: Renk.panel,
        shape: const RoundedRectangleBorder(borderRadius: kose),
        title: const Text('PIN kaldırılsın mı?'),
        content: const Text('Uygulama bundan sonra doğrudan açılır.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false),
              child: const Text('Vazgeç')),
          TextButton(onPressed: () => Navigator.pop(d, true),
              child: const Text('Kaldır')),
        ],
      ),
    );
    if (onay != true) return;
    // KilitEkran doğrulamayı zaten yaptı; PIN'i ikinci kez sormuyoruz.
    await kilit.zorlaKaldir();
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Scaffold(
      appBar: AppBar(title: const Text('Güvenlik')),
      body: ListenableBuilder(
        listenable: kilit,
        builder: (_, __) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
          children: [
            Not(
              kilit.kuruldu
                  ? 'Uygulama açılışta ve ${Kilit.arkaPlanDakika} dakikadan '
                      'uzun arka planda kaldıktan sonra PIN soruyor.'
                  : 'PIN, telefonun açıkken el değiştirdiği anı korur. '
                      'Cihazın verisini çıkarabilen birine karşı koruma '
                      'değildir — oradaki koruma Android\'in kendi '
                      'şifrelemesidir.',
              ikon: kilit.kuruldu ? Icons.lock_sharp : Icons.lock_open_sharp,
              renk: kilit.kuruldu ? sem.arti : sem.aksan,
            ),
            const SizedBox(height: 14),
            if (!kilit.kuruldu)
              Kutu(
                tikla: () async {
                  final ok = await Navigator.push<bool>(context,
                      MaterialPageRoute(builder: (_) => const KilitKurEkran()));
                  if (ok == true && mounted) setState(() {});
                },
                child: Row(children: [
                  Icon(Icons.pin_sharp, size: 18, color: sem.aksan),
                  const SizedBox(width: 12),
                  Text('PIN belirle',
                      style: Theme.of(c).textTheme.bodyLarge
                          ?.copyWith(color: sem.aksan)),
                ]),
              )
            else ...[
              Kutu(
                tikla: () async {
                  final ok = await Navigator.push<bool>(context,
                      MaterialPageRoute(builder: (_) => const KilitEkran()));
                  if (ok != true || !mounted) return;
                  await Navigator.push<bool>(context, MaterialPageRoute(
                      builder: (_) => const KilitKurEkran(degistir: true)));
                  if (mounted) setState(() {});
                },
                child: Row(children: [
                  const Icon(Icons.password_sharp, size: 18),
                  const SizedBox(width: 12),
                  Text('PIN değiştir',
                      style: Theme.of(c).textTheme.bodyLarge),
                ]),
              ),
              const SizedBox(height: 9),
              Kutu(
                tikla: _kaldir,
                child: Row(children: [
                  Icon(Icons.lock_open_sharp, size: 18, color: sem.eksi),
                  const SizedBox(width: 12),
                  Text('PIN\'i kaldır',
                      style: Theme.of(c).textTheme.bodyLarge
                          ?.copyWith(color: sem.eksi)),
                ]),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Noktalar extends StatelessWidget {
  final int dolu;
  final bool hata;
  const _Noktalar({required this.dolu, this.hata = false});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(Kilit.basamak, (i) {
        final iciDolu = i < dolu;
        return Container(
          // 16'dan 20'ye: bu ekranın TEK geri bildirimi bu kareler, kaç
          // hane girdiğini başka hiçbir şey söylemiyor. Boş halin
          // kenarlığı da Renk.cizgi'den cizgiParlak'a alındı — zeminden
          // ayırt edilemiyordu.
          width: 20, height: 20,
          margin: const EdgeInsets.symmetric(horizontal: 7),
          decoration: BoxDecoration(
            // Sıfır yuvarlaklık: nokta değil kare. Tema kuralı.
            color: iciDolu ? (hata ? sem.eksi : sem.aksan) : Colors.transparent,
            border: Border.all(
                color: hata
                    ? sem.eksi
                    : (iciDolu ? sem.aksan : Renk.cizgiParlak),
                width: 1.8),
          ),
        );
      }),
    );
  }
}

class _TusTakimi extends StatelessWidget {
  final bool etkin;
  final Future<void> Function(String) bas;
  final VoidCallback sil;
  const _TusTakimi({required this.etkin, required this.bas, required this.sil});

  @override
  Widget build(BuildContext c) {
    Widget tus(String d, {IconData? ikon, VoidCallback? ozel}) => SizedBox(
          width: 74, height: 60,
          child: Kutu(
            tikla: !etkin ? null : (ozel ?? () => bas(d)),
            child: Center(
              child: ikon != null
                  ? Icon(ikon, size: 20,
                      color: etkin ? Renk.metin : Renk.metinSonuk)
                  : Text(d,
                      style: Theme.of(c).textTheme.titleMedium?.copyWith(
                          color: etkin ? Renk.metin : Renk.metinSonuk)),
            ),
          ),
        );

    Widget satir(List<Widget> c2) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (final w in c2)
              Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: w),
          ]),
        );

    return Column(children: [
      satir([tus('1'), tus('2'), tus('3')]),
      satir([tus('4'), tus('5'), tus('6')]),
      satir([tus('7'), tus('8'), tus('9')]),
      satir([
        const SizedBox(width: 74, height: 60),
        tus('0'),
        tus('', ikon: Icons.backspace_outlined, ozel: sil),
      ]),
    ]);
  }
}
