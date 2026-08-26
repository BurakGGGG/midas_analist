/// Görsel kimlik: TEK KOYU TEMA, piksel/terminal estetiği.
///
/// Üç kural, hepsi bilinçli:
///   1. Yuvarlaklık YOK. Her köşe 90°; yarıçap yalnızca [kose] üzerinden.
///   2. Gölge/elevation YOK. Derinlik gölgeyle değil, 1px kenarlıkla anlatılır.
///   3. Tek font: sabit genişlikli. Sayı sütunları kendiliğinden hizalanır —
///      borsa ekranında okuma hızı buna bağlı.
///
/// Açık tema kasten yoktur: iki tema demek her rengi iki kez doğrulamak
/// demekti ve yarısı hiç kullanılmıyordu.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Sıfır yarıçap. Tek yerden geçsin ki "şurada bir tanecik" kalmasın.
const kose = BorderRadius.zero;

class Renk {
  // ── zemin katmanları (koyudan açığa)
  static const zemin = Color(0xFF0A0C0A); // uygulama arkaplanı
  static const panel = Color(0xFF12160F); // kart/panel
  static const panelUst = Color(0xFF1A1F16); // seçili/vurgulu panel
  static const cizgi = Color(0xFF2C3626); // kenarlık
  static const cizgiParlak = Color(0xFF44543A); // vurgulu kenarlık

  // ── metin
  static const metin = Color(0xFFD8E0CE); // ana metin (hafif fosfor tonu)
  static const metinSolgun = Color(0xFF8A9680); // ikincil
  static const metinSonuk = Color(0xFF5A6552); // üçüncül / devre dışı

  // ── aksan: yeşil fosfor. Piyasa yeşiliyle KARIŞMASIN diye
  //    aksan sarı-yeşile, artı rengi mavi-yeşile çekildi.
  static const aksan = Color(0xFFA3E635);
  static const aksanKoyu = Color(0xFF3F5314);

  // ── semantik (piyasa) — aksandan ayrı tutulur
  static const arti = Color(0xFF3DD68C);
  static const eksi = Color(0xFFFF5C5C);
  static const uyari = Color(0xFFFFB020);
  static const notr = Color(0xFF7A8770);
}

/// Tema-duyarlı semantik renkler.
/// Tek tema kaldığı için artık parlaklık sorgulamıyor, ama çağrı yerlerini
/// bozmamak ve ileride gerekirse tek noktadan dönebilmek için duruyor.
class Sem {
  final BuildContext c;
  const Sem(this.c);

  Color get arti => Renk.arti;
  Color get eksi => Renk.eksi;
  Color get uyari => Renk.uyari;
  Color get aksan => Renk.aksan;

  /// Değişime göre renk: sıfır nötr kalır, yanlış sinyal vermesin.
  Color yon(num? v) {
    if (v == null || v == 0) return Renk.notr;
    return v > 0 ? Renk.arti : Renk.eksi;
  }

  Color skor(num? s) {
    if (s == null) return Renk.notr;
    if (s >= 70) return Renk.arti;
    if (s >= 55) return Renk.uyari;
    if (s >= 40) return Renk.metinSolgun;
    return Renk.eksi;
  }
}

const _yaziTipi = 'Piksel';

/// Köşeli kenarlık — kart, kutu, giriş alanı hepsi bunu kullanır.
OutlineInputBorder _kenar([Color renk = Renk.cizgi, double kalinlik = 1]) =>
    OutlineInputBorder(
      borderRadius: kose,
      borderSide: BorderSide(color: renk, width: kalinlik),
    );

ThemeData _tema() {
  const renkler = ColorScheme.dark(
    primary: Renk.aksan,
    onPrimary: Renk.zemin,
    primaryContainer: Renk.aksanKoyu,
    onPrimaryContainer: Renk.aksan,
    secondary: Renk.aksan,
    onSecondary: Renk.zemin,
    surface: Renk.panel,
    onSurface: Renk.metin,
    onSurfaceVariant: Renk.metinSolgun,
    surfaceContainerHighest: Renk.panelUst,
    outline: Renk.cizgi,
    outlineVariant: Renk.cizgi,
    error: Renk.eksi,
    onError: Renk.zemin,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: renkler,
    scaffoldBackgroundColor: Renk.zemin,
    canvasColor: Renk.zemin,
    fontFamily: _yaziTipi,
    splashFactory: NoSplash.splashFactory, // dalga efekti piksel değil
    highlightColor: Renk.panelUst,

    // Sabit genişlikli fontta harf aralığı zaten geniş; başlıklarda
    // sıkıştırmak yerine BÜYÜK HARF + aralık ile terminal hissi veriliyor.
    textTheme: const TextTheme(
      displaySmall: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0),
      headlineSmall: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0),
      titleLarge: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.2),
      titleMedium: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.2),
      bodyMedium: TextStyle(height: 1.5, letterSpacing: 0),
      bodySmall: TextStyle(height: 1.45, color: Renk.metinSolgun),
      labelSmall: TextStyle(letterSpacing: 1.2, fontWeight: FontWeight.w700),
      labelLarge: TextStyle(letterSpacing: 0.8, fontWeight: FontWeight.w700),
    ),

    cardTheme: const CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: Renk.panel,
      shadowColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: kose,
        side: BorderSide(color: Renk.cizgi),
      ),
    ),

    appBarTheme: const AppBarTheme(
      backgroundColor: Renk.zemin,
      foregroundColor: Renk.metin,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 17,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.5,
        color: Renk.metin,
      ),
    ),

    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Renk.panel,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      indicatorColor: Renk.aksanKoyu,
      indicatorShape: const RoundedRectangleBorder(borderRadius: kose),
      height: 60,
      labelTextStyle: WidgetStatePropertyAll(
        const TextStyle(
          fontFamily: _yaziTipi,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
        ),
      ),
      iconTheme: WidgetStateProperty.resolveWith(
        (d) => IconThemeData(
          size: 20,
          color: d.contains(WidgetState.selected)
              ? Renk.aksan
              : Renk.metinSonuk,
        ),
      ),
    ),

    dividerTheme: const DividerThemeData(
      color: Renk.cizgi,
      thickness: 1,
      space: 1,
    ),

    chipTheme: const ChipThemeData(
      backgroundColor: Renk.panelUst,
      side: BorderSide(color: Renk.cizgi),
      shape: RoundedRectangleBorder(borderRadius: kose),
      labelStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 11,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.4,
        color: Renk.metin,
      ),
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Renk.zemin,
      border: _kenar(),
      enabledBorder: _kenar(),
      focusedBorder: _kenar(Renk.aksan, 2),
      errorBorder: _kenar(Renk.eksi),
      focusedErrorBorder: _kenar(Renk.eksi, 2),
      labelStyle: const TextStyle(color: Renk.metinSolgun),
      hintStyle: const TextStyle(color: Renk.metinSonuk),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
    ),

    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: const RoundedRectangleBorder(borderRadius: kose),
        backgroundColor: Renk.aksan,
        foregroundColor: Renk.zemin,
        disabledBackgroundColor: Renk.panelUst,
        disabledForegroundColor: Renk.metinSonuk,
        textStyle: const TextStyle(
          fontFamily: _yaziTipi,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.8,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      ),
    ),

    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        shape: const RoundedRectangleBorder(borderRadius: kose),
        foregroundColor: Renk.metin,
        side: const BorderSide(color: Renk.cizgi),
        textStyle: const TextStyle(
          fontFamily: _yaziTipi,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.8,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      ),
    ),

    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        shape: const RoundedRectangleBorder(borderRadius: kose),
        foregroundColor: Renk.aksan,
        textStyle: const TextStyle(
          fontFamily: _yaziTipi,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
        ),
      ),
    ),

    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        shape: const RoundedRectangleBorder(borderRadius: kose),
        foregroundColor: Renk.metinSolgun,
      ),
    ),

    dialogTheme: const DialogThemeData(
      backgroundColor: Renk.panel,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: kose,
        side: BorderSide(color: Renk.cizgiParlak),
      ),
      titleTextStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 16,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.5,
        color: Renk.metin,
      ),
      contentTextStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 13,
        height: 1.5,
        color: Renk.metin,
      ),
    ),

    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Renk.panel,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: kose,
        side: BorderSide(color: Renk.cizgiParlak),
      ),
    ),

    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Renk.panelUst,
      contentTextStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 13,
        color: Renk.metin,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: kose,
        side: BorderSide(color: Renk.cizgiParlak),
      ),
    ),

    tabBarTheme: const TabBarThemeData(
      labelColor: Renk.aksan,
      unselectedLabelColor: Renk.metinSonuk,
      indicatorColor: Renk.aksan,
      indicatorSize: TabBarIndicatorSize.tab,
      dividerColor: Renk.cizgi,
      labelStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 12,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.8,
      ),
      unselectedLabelStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 12,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.8,
      ),
    ),

    // FAB varsayılanı daire/stadyum — piksel dilde en göze batan yuvarlaklık.
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: Renk.aksan,
      foregroundColor: Renk.zemin,
      elevation: 0,
      focusElevation: 0,
      hoverElevation: 0,
      highlightElevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: kose,
        side: BorderSide(color: Renk.cizgiParlak),
      ),
      extendedTextStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.8,
        fontSize: 13,
      ),
    ),

    listTileTheme: const ListTileThemeData(
      shape: RoundedRectangleBorder(borderRadius: kose),
      iconColor: Renk.metinSolgun,
      textColor: Renk.metin,
    ),

    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
        (d) => d.contains(WidgetState.selected) ? Renk.aksan : Renk.metinSonuk,
      ),
      trackColor: WidgetStateProperty.resolveWith(
        (d) => d.contains(WidgetState.selected)
            ? Renk.aksanKoyu
            : Renk.panelUst,
      ),
      trackOutlineColor: const WidgetStatePropertyAll(Renk.cizgi),
    ),

    sliderTheme: const SliderThemeData(
      activeTrackColor: Renk.aksan,
      inactiveTrackColor: Renk.panelUst,
      thumbColor: Renk.aksan,
      trackHeight: 3,
      overlayShape: RoundSliderOverlayShape(overlayRadius: 0),
    ),

    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: Renk.aksan,
      linearTrackColor: Renk.panelUst,
      linearMinHeight: 4,
    ),

    tooltipTheme: const TooltipThemeData(
      decoration: BoxDecoration(
        color: Renk.panelUst,
        borderRadius: kose,
        border: Border.fromBorderSide(BorderSide(color: Renk.cizgiParlak)),
      ),
      textStyle: TextStyle(
        fontFamily: _yaziTipi,
        fontSize: 11,
        color: Renk.metin,
      ),
    ),
  );
}

final temaKoyu = _tema();

const sistemUst = SystemUiOverlayStyle(
  statusBarColor: Colors.transparent,
  statusBarIconBrightness: Brightness.light,
  systemNavigationBarColor: Renk.panel,
  systemNavigationBarIconBrightness: Brightness.light,
);

/// Piksel çubuk: yüzdeyi blok karakterlerle çizer.
/// Neden widget değil de metin: sabit genişlikli fontta hizalanır ve
/// ekranın geri kalanıyla aynı ızgaraya oturur.
String blokCubuk(num? oran, {int genislik = 10}) {
  if (oran == null) return '·' * genislik;
  final d = (oran.clamp(0, 1) * genislik).round();
  return '█' * d + '░' * (genislik - d);
}

/// Sayıları Türkçe biçimde yazan yardımcılar.
/// Not: fiyatlar ve yüzdeler her yerde AYNI biçimde görünmeli — okuma hızı
/// buna bağlı. Bu yüzden tek yerden geçiyorlar.
String tl(num? v, {int basamak = 2}) {
  if (v == null) return '—';
  final s = v.abs().toStringAsFixed(basamak);
  final parca = s.split('.');
  final tam = parca[0]
      .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]}.');
  final son = parca.length > 1 ? '$tam,${parca[1]}' : tam;
  return '${v < 0 ? '-' : ''}$son';
}

String yzd(num? v, {int basamak = 2, bool isaret = true}) {
  if (v == null) return '—';
  final i = (isaret && v > 0) ? '+' : '';
  return '$i${tl(v, basamak: basamak)}%';
}

String buyukTl(num? v) {
  if (v == null) return '—';
  final a = v.abs();
  if (a >= 1e9) return '${tl(v / 1e9, basamak: 1)} mlr';
  if (a >= 1e6) return '${tl(v / 1e6, basamak: 1)} mn';
  if (a >= 1e3) return '${tl(v / 1e3, basamak: 0)} b';
  return tl(v, basamak: 0);
}
