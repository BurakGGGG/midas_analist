import 'dart:convert';

import 'package:home_widget/home_widget.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:workmanager/workmanager.dart';

import 'api.dart';
import 'depo.dart';
import 'modeller.dart';
import '../tema.dart' show tl;

/// Ana ekran widget'larını besleyen katman.
///
/// AKIŞ: burada sunucudan tek istekle (/widget) veri çekiliyor, metne
/// çevrilip HomeWidget'a yazılıyor, sonra native sağlayıcılar (Kotlin
/// tarafı) okuyup çiziyor.
///
/// NEDEN METNE ÇEVİRİP YAZIYORUZ: biçimlendirme (binlik ayracı, ₺
/// işareti, işaret) Dart tarafında zaten var. Native tarafa ham sayı
/// gönderip orada yeniden biçimlendirmek, aynı kuralın iki dilde
/// kopyalanması olurdu ve biri sessizce kayardı.
///
/// TAZELEME ÜÇ YOLDAN:
///   1. Uygulama açılınca / öne gelince
///   2. WorkManager ile seans içinde 15 dakikada bir
///   3. Push geldiğinde (sunucu 09:45, 19:00 ve stop olaylarında yolluyor)
///
/// İkincisi kullanıcının tercihi, ama Android arka plan işlerini pil için
/// öldürüyor ve bazı markalarda hiç çalışmıyor. Üçüncüsü onun sigortası:
/// FCM zaten kurulu, ek maliyeti yok ve tam da önemli anlarda tetikleniyor.
class WidgetVeri {
  static const _isAdi = 'midas-widget-tazele';

  /// Native tarafın okuduğu anahtarlar. Kotlin ile birebir aynı olmalı;
  /// biri değişirse widget sessizce boş çizer.
  static const _saglayicilar = ['EmirlerWidget', 'PortfoyWidget', 'RejimWidget'];

  static Future<void> baslat() async {
    await HomeWidget.setAppGroupId('com.burak.midas_analist');
    await tazele();
    await _periyodikKur();
  }

  static Future<void> _periyodikKur() async {
    try {
      await Workmanager().initialize(arkaPlanGirisi);
      await Workmanager().registerPeriodicTask(
        _isAdi, _isAdi,
        // 15 dakika Android'in izin verdiği en kısa periyot. Daha kısası
        // kabul edilmiyor, uzunu da kullanıcının istediği tazelik değil.
        frequency: const Duration(minutes: 15),
        existingWorkPolicy: ExistingPeriodicWorkPolicy.keep,
        constraints: Constraints(networkType: NetworkType.connected),
      );
    } catch (_) {
      // Arka plan işi kurulamazsa widget yine çalışır — sadece daha
      // seyrek tazelenir. Uygulamanın açılışını bölmeye değmez.
    }
  }

  /// Sunucudan çekip widget'lara yazar. Hiçbir şey fırlatmaz.
  static Future<bool> tazele({Api? istemci, List<Pozisyon>? pozisyonlar,
      double? sermaye}) async {
    try {
      final api = istemci ?? depo.api;
      final poz = pozisyonlar ?? depo.pozisyonlar;
      final r = await api.widgetVeri(poz, sermaye ?? depo.ayarlar.sermaye);
      await yaz(r);
      return true;
    } catch (_) {
      // Ağ yoksa eski değerler ekranda kalır. Widget'ı boşaltmak, bayat
      // veri göstermekten kötü: kullanıcı "bozuldu" sanır.
      return false;
    }
  }

  /// Sunucu yanıtını widget metinlerine çevirip yazar.
  static Future<void> yaz(Map<String, dynamic> r) async {
    final e = Map<String, dynamic>.from((r['emirler'] ?? {}) as Map);
    final p = Map<String, dynamic>.from((r['portfoy'] ?? {}) as Map);
    final j = Map<String, dynamic>.from((r['rejim'] ?? {}) as Map);
    final saat = _saat(r['zaman']);

    // ── emirler
    final liste = (e['liste'] ?? []) as List;
    final sayi = (e['sayi'] as num?)?.toInt() ?? 0;
    await HomeWidget.saveWidgetData<int>('emir_sayi', sayi);
    await HomeWidget.saveWidgetData<String>(
        'emir_govde',
        liste.isEmpty
            ? ''
            : liste.map((x) {
                final m = Map<String, dynamic>.from(x as Map);
                return '${m['sembol']}  ${m['adet']} adet\n'
                    '  stop ${tl(m['stop'])}  hedef ${tl(m['hedef'])}';
              }).join('\n'));
    await HomeWidget.saveWidgetData<String>('emir_alt',
        sayi > 0 ? '${e['tarih']} kapanışına göre · $saat' : saat);

    // ── portföy
    final adet = (p['adet'] as num?)?.toInt() ?? 0;
    if (adet == 0) {
      await HomeWidget.saveWidgetData<String>('poz_deger', '');
    } else {
      final kar = (p['kar'] as num?)?.toDouble() ?? 0;
      final yuzde = (p['kar_yuzde'] as num?)?.toDouble() ?? 0;
      final yakin = p['en_yakin_stop'];
      await HomeWidget.saveWidgetData<String>(
          'poz_deger', '${tl(p['deger'])} ₺');
      await HomeWidget.saveWidgetData<String>('poz_kar',
          '${kar >= 0 ? '+' : ''}${tl(kar)} ₺  '
          '${yuzde >= 0 ? '+' : ''}${yuzde.toStringAsFixed(2)}%');
      await HomeWidget.saveWidgetData<bool>('poz_artida', kar >= 0);
      await HomeWidget.saveWidgetData<String>(
          'poz_alt',
          '$adet pozisyon'
          '${yakin == null ? '' : ' · ${yakin['sembol']} stopa '
              '%${(yakin['mesafe_yuzde'] as num).toStringAsFixed(1)}'}');
      await HomeWidget.saveWidgetData<String>('poz_zaman', '$saat itibarıyla');
    }

    // ── rejim
    final xu = (j['xu100_degisim'] as num?)?.toDouble();
    await HomeWidget.saveWidgetData<String>('rejim_xu',
        xu == null ? '—' : 'XU100 ${xu >= 0 ? '+' : ''}'
            '${xu.toStringAsFixed(2)}%');
    await HomeWidget.saveWidgetData<bool>('rejim_artida', (xu ?? 0) >= 0);
    await HomeWidget.saveWidgetData<String>(
        'rejim_ad', '${j['ad'] ?? ''}'.toUpperCase());
    final reel = (j['reel_1y'] as num?)?.toDouble();
    await HomeWidget.saveWidgetData<String>('rejim_reel',
        reel == null ? '' : 'reel ${reel.toStringAsFixed(1)}%');

    for (final s in _saglayicilar) {
      await HomeWidget.updateWidget(name: s, androidName: s);
    }
  }

  /// Ayarları DİSKTEN okuyup tazeler.
  ///
  /// İki ayrı izolattan çağrılıyor: WorkManager arka plan işi ve FCM
  /// arka plan mesajı. İkisinde de uygulama kapalı olabilir, yani
  /// bellekteki `depo` yok. Aynı kod iki yerde kopyalanmasın diye burada.
  static Future<void> disktenTazele() async {
    final p = await SharedPreferences.getInstance();
    final ayarJson = p.getString('ayarlar_v1');
    if (ayarJson == null) return;
    final a = Ayarlar.fromJson(
        Map<String, dynamic>.from(jsonDecode(ayarJson) as Map));

    final pozJson = p.getString('pozisyonlar_v1');
    final pozlar = pozJson == null
        ? <Pozisyon>[]
        : (jsonDecode(pozJson) as List)
            .map((e) => Pozisyon.fromJson(Map<String, dynamic>.from(e)))
            .toList();

    await tazele(
        istemci: Api(a.sunucu, anahtar: a.apiAnahtar),
        pozisyonlar: pozlar, sermaye: a.sermaye);
  }

  static String _saat(dynamic iso) {
    final t = DateTime.tryParse('$iso')?.toLocal();
    if (t == null) return '';
    String i(int n) => n.toString().padLeft(2, '0');
    return '${i(t.hour)}:${i(t.minute)}';
  }
}

/// WorkManager arka plan girişi.
///
/// AYRI İZOLAT: uygulama kapalıyken çalışıyor, `depo` ve `hesap` gibi
/// bellekteki nesneler burada YOK. Ayarları diskten kendisi okuyup
/// istemciyi kendisi kuruyor — bu yüzden `tazele` dışarıdan istemci
/// kabul ediyor.
@pragma('vm:entry-point')
void arkaPlanGirisi() {
  Workmanager().executeTask((_, __) async {
    try {
      // Seans dışında tazelemeye gerek yok: fiyat değişmiyor, boşuna
      // istek ve boşuna pil.
      final s = DateTime.now();
      final seansta = s.weekday < 6 && s.hour >= 9 && s.hour < 19;
      if (!seansta) return true;

      await WidgetVeri.disktenTazele();
    } catch (_) {
      // Arka plan işinin çökmesi Android'de iş kaydını "başarısız"
      // yapar ve sistem bir süre sonra işi tamamen bırakır.
    }
    return true;
  });
}
