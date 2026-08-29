import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'servis/depo.dart';
import 'servis/egitmen.dart';
import 'servis/hesap.dart';
import 'servis/kilit.dart';
import 'servis/push.dart';
import 'servis/sanal.dart';
import 'servis/semboller.dart';
import 'parca/ipucu.dart';
import 'servis/widget_veri.dart';
import 'ekran/kabuk.dart';
import 'ekran/kilit.dart';
import 'tema.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(sistemUst);
  await depo.yukle();
  await egitmen.yukle();
  await hesap.yukle();
  // Kurulu bir PIN varsa uygulama KİLİTLİ açılır.
  await kilit.yukle();
  await sanal.yukle();
  await semboller.yukle();
  await ipucu.yukle();
  // Firebase yoksa sessizce kapalı kalır; uygulama push'suz çalışır.
  // await edilmiyor: izin diyaloğu ve ağ turu açılışı geciktirmemeli.
  unawaited(push.baslat());
  // Ana ekran widget'ları: açılışta bir kez tazele, sonra 15 dakikalık
  // arka plan işini kur. await edilmiyor — ağ turu açılışı geciktirmemeli.
  unawaited(WidgetVeri.baslat());
  // Depo her değiştiğinde geciktirmeli bulut yedeği. Girişli değilse
  // dinleyici hiçbir şey yapmaz — ağ isteği de yok.
  hesap.otomatikBasla();
  runApp(const Uygulama());
}

class Uygulama extends StatefulWidget {
  const Uygulama({super.key});
  @override
  State<Uygulama> createState() => _UygulamaDurum();
}

class _UygulamaDurum extends State<Uygulama> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// Kilidi yalnızca soğuk açılışta uygulamak işe yaramaz: uygulama
  /// günlerce bellekte kalır ve kilit bir daha hiç görünmez. Arka plana
  /// düşüş zamanı işaretlenir, dönüşte süre dolmuşsa yeniden kilitlenir.
  @override
  void didChangeAppLifecycleState(AppLifecycleState durum) {
    if (durum == AppLifecycleState.paused ||
        durum == AppLifecycleState.hidden) {
      kilit.arkaPlanaGitti();
    } else if (durum == AppLifecycleState.resumed) {
      kilit.oneCikti();
    }
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Listenable.merge([depo, kilit]),
        builder: (_, __) => MaterialApp(
          title: 'Midas Analist',
          debugShowCheckedModeBanner: false,
          // Tek tema. Cihaz açık moddaysa bile uygulama koyu kalır —
          // açık tema kasten yok (bkz. tema.dart).
          theme: temaKoyu,
          darkTheme: temaKoyu,
          themeMode: ThemeMode.dark,
          // Kilit ekranı Kabuk'un YERİNE geçiyor, üstüne değil: üstüne
          // konsaydı arkadaki ekran bir kare boyunca görünürdü.
          // acilinca boş: dogrula() zaten kilitli'yi düşürüyor ve bu
          // ListenableBuilder yeniden çiziyor.
          home: kilit.kilitli
              ? KilitEkran(acilinca: () {})
              : const Kabuk(),
        ),
      );
}
