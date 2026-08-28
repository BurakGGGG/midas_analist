package com.burak.midas_analist

import android.appwidget.AppWidgetManager
import android.content.Context
import android.content.SharedPreferences
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetProvider
import es.antonborri.home_widget.HomeWidgetLaunchIntent

/**
 * Ana ekran widget'ları.
 *
 * VERİ AKIŞI: Flutter tarafı (servis/widget_veri.dart) değerleri
 * HomeWidget.saveWidgetData ile yazıyor, buradaki sağlayıcılar okuyup
 * çiziyor. Widget'ın kendi ağ çağrısı YOK — arka plan işi Flutter
 * tarafında çalışıp veriyi tazeliyor.
 *
 * NEDEN BÖYLE: widget sürecinde ağ çağrısı yapmak, API anahtarını ve
 * sunucu adresini native tarafa taşımayı gerektirirdi. İkisi de
 * Flutter'daki ayarlarda yaşıyor ve orada kalmalı.
 *
 * DOKUNMA: her widget kendi ekranını açıyor. Push bildirimlerindeki
 * "ekran" verisiyle aynı mekanizma.
 */

private fun oku(p: SharedPreferences, k: String, v: String = "") =
    p.getString(k, v) ?: v

class EmirlerWidget : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context, manager: AppWidgetManager,
        ids: IntArray, veri: SharedPreferences
    ) {
        ids.forEach { id ->
            val g = RemoteViews(context.packageName, R.layout.widget_emirler)
            val sayi = veri.getInt("emir_sayi", -1)

            when {
                sayi < 0 -> {
                    g.setTextViewText(R.id.emirler_sayi, "")
                    g.setTextViewText(R.id.emirler_govde,
                        "Uygulamayı bir kez aç,\nveri buraya gelsin.")
                    g.setTextViewText(R.id.emirler_alt, "")
                }
                sayi == 0 -> {
                    g.setTextViewText(R.id.emirler_sayi, "yok")
                    g.setTextViewText(R.id.emirler_govde,
                        "Bugün önerilen emir yok.\nNakitte beklemek de bir pozisyondur.")
                    g.setTextViewText(R.id.emirler_alt,
                        oku(veri, "emir_alt"))
                }
                else -> {
                    g.setTextViewText(R.id.emirler_sayi, "$sayi emir")
                    g.setTextViewText(R.id.emirler_govde, oku(veri, "emir_govde"))
                    g.setTextViewText(R.id.emirler_alt, oku(veri, "emir_alt"))
                }
            }

            g.setOnClickPendingIntent(
                R.id.emirler_kok,
                HomeWidgetLaunchIntent.getActivity(
                    context, MainActivity::class.java,
                    android.net.Uri.parse("midas://tarama")))
            manager.updateAppWidget(id, g)
        }
    }
}

class PortfoyWidget : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context, manager: AppWidgetManager,
        ids: IntArray, veri: SharedPreferences
    ) {
        ids.forEach { id ->
            val g = RemoteViews(context.packageName, R.layout.widget_portfoy)
            val deger = oku(veri, "poz_deger")

            if (deger.isEmpty()) {
                g.setTextViewText(R.id.portfoy_deger, "—")
                g.setTextViewText(R.id.portfoy_kar, "")
                g.setTextViewText(R.id.portfoy_alt,
                    "Açık pozisyon yok.")
                g.setTextViewText(R.id.portfoy_zaman, "")
            } else {
                g.setTextViewText(R.id.portfoy_deger, deger)
                g.setTextViewText(R.id.portfoy_kar, oku(veri, "poz_kar"))
                // Kâr yeşil, zarar kırmızı — uygulamadaki semantik renkler.
                g.setTextColor(R.id.portfoy_kar,
                    if (veri.getBoolean("poz_artida", true))
                        0xFF3DD68C.toInt() else 0xFFFF5C5C.toInt())
                g.setTextViewText(R.id.portfoy_alt, oku(veri, "poz_alt"))
                g.setTextViewText(R.id.portfoy_zaman, oku(veri, "poz_zaman"))
            }

            g.setOnClickPendingIntent(
                R.id.portfoy_kok,
                HomeWidgetLaunchIntent.getActivity(
                    context, MainActivity::class.java,
                    android.net.Uri.parse("midas://portfoy")))
            manager.updateAppWidget(id, g)
        }
    }
}

class RejimWidget : HomeWidgetProvider() {
    override fun onUpdate(
        context: Context, manager: AppWidgetManager,
        ids: IntArray, veri: SharedPreferences
    ) {
        ids.forEach { id ->
            val g = RemoteViews(context.packageName, R.layout.widget_rejim)
            g.setTextViewText(R.id.rejim_xu, oku(veri, "rejim_xu", "—"))
            g.setTextViewText(R.id.rejim_ad, oku(veri, "rejim_ad"))
            g.setTextViewText(R.id.rejim_reel, oku(veri, "rejim_reel"))
            // XU100 değişimi negatifse kırmızı.
            g.setTextColor(R.id.rejim_xu,
                if (veri.getBoolean("rejim_artida", true))
                    0xFF3DD68C.toInt() else 0xFFFF5C5C.toInt())

            g.setOnClickPendingIntent(
                R.id.rejim_kok,
                HomeWidgetLaunchIntent.getActivity(
                    context, MainActivity::class.java,
                    android.net.Uri.parse("midas://makro")))
            manager.updateAppWidget(id, g)
        }
    }
}
