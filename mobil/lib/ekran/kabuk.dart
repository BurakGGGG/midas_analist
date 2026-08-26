import 'package:flutter/material.dart';
import 'bugun.dart';
import 'tarama.dart';
import 'portfoy.dart';
import 'tezler.dart';
import 'daha.dart';

class Kabuk extends StatefulWidget {
  const Kabuk({super.key});
  @override
  State<Kabuk> createState() => _KabukDurum();
}

class _KabukDurum extends State<Kabuk> {
  int _i = 0;

  // Sekme sırası günlük akışı izler: bugün ne var → ara → neyim var → neden aldım
  static const _ekranlar = [BugunEkran(), TaramaEkran(), PortfoyEkran(),
                            TezlerEkran(), DahaEkran()];

  @override
  Widget build(BuildContext c) => Scaffold(
        body: IndexedStack(index: _i, children: _ekranlar),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _i,
          onDestinationSelected: (v) => setState(() => _i = v),
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
