import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../tema.dart';

/// İpucu balonu — alanın yanında bir kez çıkar, okununca kaybolur.
///
/// NEDEN AYRI EĞİTİM BÖLÜMÜ YOK: "stop nedir" sorusunun cevabı, stop
/// kutusuna bakarken lazım. Ayrı bir ders bölümüne konsa oraya
/// gidilmiyor; gidilse bile okunanla yapılan arasındaki mesafe kapanmıyor.
///
/// BİR KEZ: "anladım" denince kalıcı olarak kapanıyor ve bulut yedeğine
/// giriyor. Her açılışta tekrar çıkan bir balon açıklama değil, engel.
/// Sağ üstteki `?` ile hepsi geri getirilebiliyor.
class IpucuDeposu extends ChangeNotifier {
  static const anahtar = 'ipucu_v1';

  Set<String> okunan = {};

  Future<void> yukle() async {
    final p = await SharedPreferences.getInstance();
    okunan = (p.getStringList(anahtar) ?? const []).toSet();
    notifyListeners();
  }

  bool gorunur(String kod) => !okunan.contains(kod);

  /// Verilen sıradaki İLK okunmamış ipucu.
  ///
  /// Balonlar aynı anda çıkmasın diye: alım ekranında dört balon birden
  /// açıldığında ekran bir metin duvarına dönüyor ve hiçbiri okunmuyor.
  /// Biri "anladım" alınca sonraki beliriyor.
  String? siradaki(List<String> kodlar) {
    for (final k in kodlar) {
      if (gorunur(k)) return k;
    }
    return null;
  }

  Future<void> okundu(String kod) async {
    if (okunan.contains(kod)) return;
    okunan = {...okunan, kod};
    final p = await SharedPreferences.getInstance();
    await p.setStringList(anahtar, okunan.toList());
    notifyListeners();
  }

  Future<void> hepsiniGeriGetir() async {
    okunan = {};
    final p = await SharedPreferences.getInstance();
    await p.remove(anahtar);
    notifyListeners();
  }
}

final ipucu = IpucuDeposu();

/// İpucu metinleri tek yerde.
///
/// Hepsi bir MEKANİZMA anlatıyor, tanım vermiyor: "stop nedir" değil
/// "stopu nereye koyarsın ve neden". Tanım ezberletir, mekanizma karar
/// aldırır.
const ipucuMetni = <String, (String, String)>{
  'stop': (
    'Stop',
    '"Buraya gelirse yanıldım" dediğin fiyat. Alımdan ÖNCE konur — '
        'sonra konamaz, çünkü fiyat düşerken her seviye "biraz daha '
        'bekleyeyim" gibi görünür.\n\n'
        'Nereye? Hissenin normal günlük dalgalanmasının DIŞINA. Bunu '
        'ölçen sayı ATR. Sistem girişin 2 ATR altını öneriyor; daha '
        'yakın koyarsan hissenin normal nefes alışı seni dışarı atar.',
  ),
  'hedef': (
    'Hedef',
    'Kârı realize etmeyi planladığın fiyat. Asıl mesele hedefin '
        'kendisi değil, stop ile arasındaki ORAN:\n\n'
        '   ödül/risk = (hedef − giriş) ÷ (giriş − stop)\n\n'
        'Bu oran 2,5 ise işlemlerin %29\'u tutsa başabaşı geçersin. '
        '1\'in altındaysa kazandığında kaybettiğinden az kazanıyorsun.',
  ),
  'adet': (
    'Adet',
    'Adedi cüzdanın değil STOP MESAFESİ belirler.\n\n'
        '   risk bütçesi = sermaye × %1,5\n'
        '   adet = risk bütçesi ÷ (giriş − stop)\n\n'
        'Stop yakınsa daha çok adet alırsın, uzaksa daha az — risk '
        'aynı kalır. 1.844 ₺ harcayıp 150 ₺ riske girmek mümkün; '
        'ikisini karıştırmak en pahalı hatalardan biri.',
  ),
  'kayma': (
    'Kayma',
    'Emrin tam kapanış fiyatından gerçekleşmez. Alışta biraz yukarı, '
        'satışta biraz aşağı kayar — piyasada karşı tarafta bekleyen '
        'fiyat farklıdır.\n\n'
        'Simülatör %0,15 kayma uyguluyor; backtest\'in kullandığı '
        'sayının aynısı. Uygulamasaydık simülasyon gerçekte '
        'olabileceğinden daha kârlı görünürdü.',
  ),
  'tavan': (
    'Tavan',
    'BIST\'te bir hisse günde en fazla ~%20 hareket edebilir. Tavana '
        'vurmuş hissede SATICI YOKTUR — emir girersin, gerçekleşmez.\n\n'
        'Simülatör bu emirleri reddediyor. Kabul etseydi gerçekte '
        'giremeyeceğin işlemlerden kâr sayardı ve sonucu olduğundan '
        'iyi gösterirdi.',
  ),
  'ilerlet': (
    'Günleri ilerletmek',
    'Her ilerlettiğin günde sırayla şuna bakılıyor: hisse stopun '
        'altında mı açtı, gün içinde stopa değdi mi, hedefe değdi mi.\n\n'
        'Aynı gün ikisi de görüldüyse STOP sayılıyor — günlük veriyle '
        'hangisinin önce olduğunu bilemeyiz ve iyimser varsaymak '
        'sonuçları sistematik olarak güzelleştirirdi.',
  ),
  'sinyal': (
    'O gün sistem ne diyordu',
    'Bunlar, seçtiğin tarihte sistemin gerçekten ürettiği sinyaller. '
        'Sonrasını bilmeden hesaplandı: veri o güne kadar kesiliyor.\n\n'
        'Sisteme güvenip güvenmeyeceğini gerçek parayla değil burada '
        'öğren. Uygulamak zorunda değilsin — kendi hisseni de seçebilirsin.',
  ),
};

/// Alanın altında çıkan balon.
class IpucuBalonu extends StatelessWidget {
  final String kod;

  /// Aynı ekrandaki ipuçlarının SIRASI. Verilirse balon yalnızca
  /// sıradaki ilk okunmamış ipucu kendisiyse görünür.
  final List<String>? akis;

  const IpucuBalonu(this.kod, {super.key, this.akis});

  @override
  Widget build(BuildContext c) {
    return ListenableBuilder(
      listenable: ipucu,
      builder: (_, __) {
        if (!ipucu.gorunur(kod)) return const SizedBox.shrink();
        if (akis != null && ipucu.siradaki(akis!) != kod) {
          return const SizedBox.shrink();
        }
        final m = ipucuMetni[kod];
        if (m == null) return const SizedBox.shrink();
        final sem = Sem(c);
        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(top: 8),
          padding: const EdgeInsets.fromLTRB(13, 12, 13, 8),
          decoration: BoxDecoration(
            color: sem.uyari.withValues(alpha: 0.07),
            border: Border(left: BorderSide(color: sem.uyari, width: 3)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.lightbulb_sharp, size: 15, color: sem.uyari),
                const SizedBox(width: 8),
                Text(m.$1,
                    style: TextStyle(
                        color: sem.uyari, fontWeight: FontWeight.w700,
                        fontSize: 13)),
              ]),
              const SizedBox(height: 8),
              Text(m.$2,
                  style: Theme.of(c).textTheme.bodySmall?.copyWith(
                      height: 1.6, color: Theme.of(c).colorScheme.onSurface)),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => ipucu.okundu(kod),
                  child: const Text('ANLADIM'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
