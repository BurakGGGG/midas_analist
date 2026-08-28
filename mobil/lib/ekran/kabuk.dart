import 'package:flutter/material.dart';
import 'package:home_widget/home_widget.dart';

import '../servis/push.dart';
import 'makro.dart';
import 'gun_ozeti.dart';
import 'bugun.dart';
import 'tarama.dart';
import 'portfoy.dart';
import 'tezler.dart';
import 'daha.dart';

/// Alt sekmeler. Sıra günlük akışı izler: bugün ne var → ara → neyim var
/// → neden aldım. `index` NavigationBar'ın beklediği sırayla aynı.
enum Sekme { bugun, tarama, portfoy, tezler, daha }

/// Seçili sekme — tek doğruluk kaynağı.
///
/// NEDEN GLOBAL: Bugün ekranındaki kartlar "Portföy'e git", "Tarama'ya git"
/// diyebilmeli. Geri çağrıyı widget ağacından aşağı taşımak, aradaki her
/// widget'ın const olmaktan çıkmasını ve derinlerdeki bir ekranın sekme
/// değiştirememesini getirirdi.
final sekme = ValueNotifier<Sekme>(Sekme.bugun);

/// Başka bir ekrandan sekme değiştirmek için. Üstte açık sayfa varsa
/// önce kapanır — yoksa kullanıcı sekmeyi değiştirir ama ekranda hâlâ
/// eski sayfayı görür.
void sekmeyeGit(BuildContext c, Sekme s) {
  Navigator.of(c).popUntil((r) => r.isFirst);
  sekme.value = s;
}

/// Bildirimden ya da widget'tan gelen "şu ekranı aç" isteğini karşılar.
///
/// TEK KAPI: push bildirimi `data.ekran` gönderiyor, widget ise
/// `midas://<ekran>` URI'si. İkisi de aynı adlara çözülüyor; ayrı ayrı
/// çözseydik biri eklenip diğeri unutulurdu.
void _ekranaGit(BuildContext c, String ad) {
  switch (ad) {
    case 'tarama':
      sekmeyeGit(c, Sekme.tarama);
    case 'portfoy':
      sekmeyeGit(c, Sekme.portfoy);
    case 'tezler':
      sekmeyeGit(c, Sekme.tezler);
    case 'makro':
      Navigator.push(c, MaterialPageRoute(builder: (_) => const MakroEkran()));
    case 'gun_ozeti':
      Navigator.push(c,
          MaterialPageRoute(builder: (_) => const GunOzetiEkran()));
    default:
      sekmeyeGit(c, Sekme.bugun);
  }
}


class Kabuk extends StatefulWidget {
  const Kabuk({super.key});
  @override
  State<Kabuk> createState() => _KabukDurum();
}

class _KabukDurum extends State<Kabuk> {
  static const _ekranlar = [BugunEkran(), TaramaEkran(), PortfoyEkran(),
                            TezlerEkran(), DahaEkran()];

  @override
  void initState() {
    super.initState();
    sekme.addListener(_degisti);
    push.acilacakEkran.addListener(_bildirimden);
    _widgetDinle();
  }

  /// Bildirime dokunulup uygulama açıldığında.
  void _bildirimden() {
    final v = push.acilacakEkran.value;
    if (v == null || !mounted) return;
    push.acilacakEkran.value = null;
    _ekranaGit(context, '${v['ekran'] ?? ''}');
  }

  /// Ana ekran widget'ına dokunulduğunda. URI biçimi: `midas://<ekran>`
  Future<void> _widgetDinle() async {
    HomeWidget.widgetClicked.listen((uri) {
      if (uri != null && mounted) _ekranaGit(context, uri.host);
    });
    try {
      final ilk = await HomeWidget.initiallyLaunchedFromHomeWidget();
      if (ilk != null && mounted) _ekranaGit(context, ilk.host);
    } catch (_) {}
  }

  @override
  void dispose() {
    sekme.removeListener(_degisti);
    push.acilacakEkran.removeListener(_bildirimden);
    super.dispose();
  }

  void _degisti() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext c) => Scaffold(
        body: IndexedStack(index: sekme.value.index, children: _ekranlar),
        bottomNavigationBar: NavigationBar(
          selectedIndex: sekme.value.index,
          onDestinationSelected: (v) => sekme.value = Sekme.values[v],
          destinations: const [
            NavigationDestination(
                icon: Icon(Icons.today_sharp),
                selectedIcon: Icon(Icons.today_sharp), label: 'Bugün'),
            NavigationDestination(
                icon: Icon(Icons.radar_sharp),
                selectedIcon: Icon(Icons.radar_sharp), label: 'Tarama'),
            NavigationDestination(
                icon: Icon(Icons.account_balance_wallet_sharp),
                selectedIcon: Icon(Icons.account_balance_wallet_sharp), label: 'Portföy'),
            NavigationDestination(
                icon: Icon(Icons.description_sharp),
                selectedIcon: Icon(Icons.description_sharp), label: 'Tezler'),
            NavigationDestination(
                icon: Icon(Icons.grid_view_sharp),
                selectedIcon: Icon(Icons.grid_view_sharp), label: 'Daha'),
          ],
        ),
      );
}
