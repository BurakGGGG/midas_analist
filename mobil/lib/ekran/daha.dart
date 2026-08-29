import 'package:flutter/material.dart';
import '../parca/kart.dart';
import '../servis/egitmen.dart';
import '../tema.dart';
import 'makro.dart';
import 'sektor.dart';
import 'risk_ekran.dart';
import 'ogren.dart';
import 'ayarlar.dart';
import 'ilerleme.dart';
import 'gun_ozeti.dart';
import 'defter.dart';
import 'tezler.dart';
import 'karne.dart';
import 'sermaye.dart';
import 'sozluk.dart';
import 'hesap.dart';
import 'kilit.dart';

class DahaEkran extends StatelessWidget {
  const DahaEkran({super.key});

  @override
  Widget build(BuildContext c) {
    final sem = Sem(c);
    final ogeler = [
      (Icons.account_balance_wallet_sharp, 'Sermaye',
          'Para yatır/çek · yatırdığın para ile kazandığın ayrı',
          const SermayeEkran()),
      (Icons.event_note_sharp, 'Gün özeti',
          'Dün → bugün, hareket edenler, haberler · 18:10 otomatik',
          const GunOzetiEkran()),
      (Icons.fact_check_sharp, 'Sistemin sicili',
          'Sinyaller gerçekte ne yaptı — backtest değil, canlı',
          const KarneEkran()),
      // Sicilin hemen ALTINDA: ikisi kardeş ölçüm. Biri sistemin ne
      // yaptığını, diğeri senin ne yaptığını söylüyor.
      (Icons.menu_book_sharp, 'Karar defterin',
          'Senin kararların — sistemi takip mi ettin, kendi fikrin mi',
          const DefterEkran()),
      // Karar defterinin YANINDA: tez "neden aldım"ın yazılı hâli ve
      // defterle birlikte okunuyor. Alt sekmeden buraya indi — günde bir
      // kez bakılıyor ve alım anında zaten kendiliğinden açılıyor.
      (Icons.description_sharp, 'Tezlerin',
          'Neden aldım · alım anında yazılır, çıkışta okunur',
          const TezlerEkran()),
      // Sayılar müfredattan okunuyor: sabit yazıldığında iki kez eskidi
      // (65 → 72 → 76) ve ikisini de ancak gözle bakınca fark ettik.
      (Icons.school_sharp, 'Eğitmen',
          '${egitmen.moduller.length} modül, ${egitmen.tumDersler.length} ders'
          ' · günlük ders + pekiştirme',
          const IlerlemeEkran()),
      // Eğitmenin hemen ALTINDA: ikisi aynı soruya iki farklı sürede
      // cevap veriyor. Sözlük 30 saniye, ders 6-9 dakika.
      (Icons.abc_sharp, 'Sözlük',
          'Ekranlardaki terimler ne demek — GG60, ATR, Sharpe, karantina',
          const SozlukEkran()),
      (Icons.public_sharp, 'Makro', 'Kur, faiz, emtia, enflasyon ve piyasa rejimi',
          const MakroEkran()),
      (Icons.donut_large_sharp, 'Sektörler', 'Hangi sektör rüzgârı arkasına almış',
          const SektorEkran()),
      (Icons.calculate_sharp, 'Risk matematiği',
          'Beklenen değer, Monte Carlo, çeşitlendirmenin sınırı',
          const RiskEkran()),
      (Icons.school_sharp, 'Öğren',
          '10 konu — özellikle göstergelerin yanıldığı yerler',
          const OgrenEkran()),
      // Ayarların hemen ÜSTÜNDE: ikisi de kurulumla ilgili ve yeni
      // telefonda sırayla yapılıyor — önce sunucu, sonra hesap.
      (Icons.cloud_sharp, 'Hesap ve yedek',
          'Portföy, tez ve ilerleme buluta yedeklensin',
          const HesapEkran()),
      (Icons.lock_sharp, 'Güvenlik',
          'Uygulama açılışında 6 haneli PIN sor',
          const GuvenlikEkran()),
      (Icons.settings_sharp, 'Ayarlar', 'Sunucu adresi, risk kuralları',
          const AyarlarEkran()),
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Daha')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        children: [
          ...ogeler.map((o) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Kutu(
                  tikla: () => Navigator.push(
                      c, MaterialPageRoute(builder: (_) => o.$4)),
                  child: Row(
                    children: [
                      Container(
                        width: 38, height: 38,
                        decoration: BoxDecoration(
                          color: Renk.panelUst,
                          borderRadius: kose,
                          border: Border.all(color: Renk.cizgi),
                        ),
                        child: Icon(o.$1, color: sem.aksan, size: 19),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(o.$2, style: Theme.of(c).textTheme.titleMedium),
                            const SizedBox(height: 2),
                            Text(o.$3,
                                style: Theme.of(c).textTheme.bodySmall?.copyWith(
                                    color: Theme.of(c)
                                        .colorScheme.onSurfaceVariant,
                                    height: 1.35)),
                          ],
                        ),
                      ),
                      const Text('›',
                          style: TextStyle(
                              fontSize: 20, color: Renk.metinSonuk)),
                    ],
                  ),
                ),
              )),
          const SizedBox(height: 12),
          Not(
            'Bu bir yatırım tavsiyesi değildir. Geçmiş getiri gelecek getiriyi '
            'göstermez. Stop garantili değildir: hisse stop seviyesinin altında '
            'açılabilir. BIST\'te günlük tavan/taban ±%20.',
            ikon: Icons.gavel_sharp,
          ),
        ],
      ),
    );
  }
}
