import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'servis/depo.dart';
import 'servis/egitmen.dart';
import 'ekran/kabuk.dart';
import 'tema.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(sistemUst);
  await depo.yukle();
  await egitmen.yukle();
  runApp(const Uygulama());
}

class Uygulama extends StatelessWidget {
  const Uygulama({super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: depo,
        builder: (_, __) => MaterialApp(
          title: 'Midas Analist',
          debugShowCheckedModeBanner: false,
          // Tek tema. Cihaz açık moddaysa bile uygulama koyu kalır —
          // açık tema kasten yok (bkz. tema.dart).
          theme: temaKoyu,
          darkTheme: temaKoyu,
          themeMode: ThemeMode.dark,
          home: const Kabuk(),
        ),
      );
}
