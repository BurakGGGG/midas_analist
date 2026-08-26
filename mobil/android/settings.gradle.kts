pluginManagement {
    val flutterSdkPath =
        run {
            val properties = java.util.Properties()
            file("local.properties").inputStream().use { properties.load(it) }
            val flutterSdkPath = properties.getProperty("flutter.sdk")
            require(flutterSdkPath != null) { "flutter.sdk not set in local.properties" }
            flutterSdkPath
        }

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "9.0.1" apply false
    id("org.jetbrains.kotlin.android") version "2.3.20" apply false
    // Firebase (push bildirimi). `apply false`: eklenti burada yalnızca
    // BİLDİRİLİYOR, uygulanmıyor. Uygulama kararı app/build.gradle.kts'te
    // ve google-services.json dosyasının varlığına bağlı — dosya yoksa
    // eklenti uygulanırsa derleme kırılır.
    id("com.google.gms.google-services") version "4.4.2" apply false
}

include(":app")
