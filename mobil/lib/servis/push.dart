import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'depo.dart';
import 'hesap.dart';

/// Push bildirimi (Firebase Cloud Messaging).
///
/// TELEGRAM'IN YERİNE, ONUN YANINA: sunucu her iki kanala da gönderiyor.
/// Telegram anahtarları .env'den silindiği gün o kanal susar; burada bir
/// bayrak ya da kod değişikliği gerekmez.
///
/// FIREBASE YOKKEN SESSİZCE KAPALI. `google-services.json` Firebase
/// konsolundan indirilir ve repoya girmez; olmayan bir makinede
/// `Firebase.initializeApp()` istisna atar. O istisnayı yutup `hazir`
/// alanını false bırakmak, uygulamanın push olmadan çalışmasını sağlıyor.
/// Aynı yaklaşım sunucudaki push.py'de de var: bildirim, işin kendisi
/// değil üstüne eklenen katman.
///
/// JETON KALICI DEĞİL: uygulama yeniden kurulunca, veri temizlenince ya
/// da kendiliğinden yenilenebilir. Bu yüzden her açılışta VE her
/// yenilemede sunucuya gönderiliyor. Tek seferlik kayıt yapsaydık jeton
/// yenilendiği gün bildirimler sessizce kesilirdi.
class Push extends ChangeNotifier {
  bool hazir = false;
  bool izinVar = false;
  String? jeton;
  String? hata;

  StreamSubscription<String>? _yenileme;

  /// Bildirime dokunulduğunda hangi ekrana gidilecek. Kabuk dinliyor.
  final ValueNotifier<Map<String, dynamic>?> acilacakEkran =
      ValueNotifier(null);

  Future<void> baslat() async {
    try {
      await Firebase.initializeApp();
      hazir = true;
    } catch (e) {
      // google-services.json yok ya da bozuk. Uygulama push'suz çalışır.
      hazir = false;
      hata = 'Firebase kurulu değil';
      notifyListeners();
      return;
    }

    try {
      final m = FirebaseMessaging.instance;

      final ayar = await m.requestPermission(alert: true, badge: true, sound: true);
      izinVar = ayar.authorizationStatus == AuthorizationStatus.authorized ||
          ayar.authorizationStatus == AuthorizationStatus.provisional;

      jeton = await m.getToken();
      await _sunucuyaBildir();

      // Jeton yenilenince sunucudaki kayıt eskir; anında tazele.
      _yenileme = m.onTokenRefresh.listen((y) async {
        jeton = y;
        await _sunucuyaBildir();
      });

      // Uygulama AÇIKKEN gelen bildirim sistem tepsisine düşmez; burada
      // yakalanmazsa kullanıcı hiçbir şey görmez.
      FirebaseMessaging.onMessage.listen((m) {
        acilacakEkran.value = null;   // ön planda: yalnızca tazele
        notifyListeners();
      });

      // Bildirime dokunulup uygulama açıldığında.
      FirebaseMessaging.onMessageOpenedApp.listen((m) {
        acilacakEkran.value = Map<String, dynamic>.from(m.data);
      });
      final ilk = await m.getInitialMessage();
      if (ilk != null) {
        acilacakEkran.value = Map<String, dynamic>.from(ilk.data);
      }
    } catch (e) {
      hata = '$e';
    }
    notifyListeners();
  }

  /// Jetonu sunucuya yazar. Hesap yoksa beklenir: jeton kullanıcıya
  /// bağlı saklanıyor, oturumsuz kaydedilemez.
  Future<void> _sunucuyaBildir() async {
    final j = jeton;
    if (j == null || j.isEmpty || !hesap.girisli) return;
    try {
      await depo.api.cihazKaydet(hesap.jeton!, j, defaultTargetPlatform.name);
    } catch (_) {
      // Sunucuya ulaşılamıyorsa sessiz geç: bir sonraki açılışta yeniden
      // denenecek. Kullanıcının işini bölmeye değmez.
    }
  }

  /// Giriş yapıldıktan sonra çağrılır — jeton o ana kadar sahipsizdi.
  Future<void> hesapAcildi() => _sunucuyaBildir();

  /// Çıkışta çağrılır: bu telefona artık bildirim gitmesin.
  Future<void> hesapKapandi(String oturumJetonu) async {
    final j = jeton;
    if (j == null || j.isEmpty) return;
    try {
      await depo.api.cihazSil(oturumJetonu, j);
    } catch (_) {}
  }

  @override
  void dispose() {
    _yenileme?.cancel();
    super.dispose();
  }
}

final push = Push();
