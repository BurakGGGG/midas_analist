import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.burak.midas_analist"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.burak.midas_analist"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // Yayın imzası. key.properties VARSA onunla, yoksa debug anahtarıyla.
    //
    // NEDEN ÖNEMLİ: debug anahtarı ~/.android/debug.keystore'da durur,
    // yedeklenmez ve makineye özeldir. Bir gün yenilenirse (yeni bilgisayar,
    // sistem kurulumu, klasörün silinmesi) imza değişir; Android o andan
    // sonra "üstüne kur"maya izin vermez ve tek yol kaldırıp yeniden
    // kurmaktır — yani UYGULAMA VERİSİNİN TAMAMI SİLİNİR, geri dönüşü yok.
    //
    // Kendi anahtarını üretmek için:  mobil/anahtar_uret.sh
    // Ürettikten sonra hem .jks dosyasını hem key.properties'i YEDEKLE.
    // Kaybedersen aynı sonuç: bir daha asla üstüne kurulum yapamazsın.
    val anahtarDosyasi = rootProject.file("key.properties")
    val anahtar = Properties().apply {
        if (anahtarDosyasi.exists()) anahtarDosyasi.inputStream().use { load(it) }
    }

    signingConfigs {
        if (anahtarDosyasi.exists()) {
            create("yayin") {
                storeFile = file(anahtar.getProperty("storeFile"))
                storePassword = anahtar.getProperty("storePassword")
                keyAlias = anahtar.getProperty("keyAlias")
                keyPassword = anahtar.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (anahtarDosyasi.exists()) {
                signingConfigs.getByName("yayin")
            } else {
                // Geçici: `flutter run --release` çalışsın diye. Yukarıdaki
                // nota bak — kalıcı çözüm değil.
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
