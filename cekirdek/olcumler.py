"""Ders metinlerinde "sistem ölçtü" diye aktarılan rakamların TEK KAYNAĞI.

NEDEN VAR: müfredat birçok yerde ölçülmüş rakam aktarıyor — "kirilim %48
kazanma, +%117,7 getiri", "BIST 1 yıl reel getiri −%4,2" gibi. Bunlar
metnin içine gömülü sabitlerdi ve ölçüm yenilendiğinde güncellenmeleri
kimsenin hatırlamasına kalıyordu.

Bir eğitim sisteminde "sistem ölçtü" diye aktarılan rakamın sessizce
bayatlaması, o sistemin öğrettiği her şeye gölge düşürür. Kendi dersi
(d1202) backtest dürüstlüğünü anlatırken kendi rakamı yanlış olamaz.

NASIL KORUNUYOR: `testler/test_olcum_tutarlilik.py` buradaki her rakamın
ilgili ders metninde GEÇTİĞİNİ doğrular. Ölçüm yenilenip bu dosya
güncellenirse, ders metni de güncellenene kadar test düşer.

YENİDEN ÖLÇME: veri katmanına dokunulduğunda ya da evren değiştiğinde
`analist.py backtest` çalıştırılıp buradaki rakamlar ve OLCUM_TARIHI
güncellenmeli.
"""
from __future__ import annotations

OLCUM_TARIHI = "2026-08-26"

# Portföy backtesti: 99 hisse, 3,29 yıl, 15bp kayma, aynı anda en fazla
# 4 pozisyon, nakit kısıtlı. Sinyal seviyesindeki `ogrenme.BACKTEST_REFERANS`
# ile KARIŞTIRILMAMALI — o canlı sicille kıyas için, bu strateji tanıtımı için.
# SHARPE RİSKSİZ GETİRİYE GÖRE (%40). 2026-08-26'da düzeltildi: backtest
# risksiz getiriyi çıkarmıyordu ve kirilim için 1,93 gibi mükemmel bir skor
# üretiyordu — oysa strateji yıllık %26,7 kazanırken mevduat %40 veriyordu.
# `istatistik.performans` bunu baştan doğru yapıyordu; iki yerde iki farklı
# sayı vardı ve dersler yanlış olanı aktarıyordu.
PORTFOY_BACKTEST = {
    "trend":   {"islem": 236, "kazanma": 48.3, "ort_kazanc": 12.1,
                "ort_kayip": 7.6, "getiri": 82.1, "yillik": 20.0,
                "azami_dusus": 16.1, "sharpe": -0.91, "usd_getiri": -25.6},
    "tepki":   {"islem": 328, "kazanma": 52.7, "ort_kazanc": 4.0,
                "ort_kayip": 5.5, "getiri": -22.0, "yillik": -7.3,
                "azami_dusus": 28.2, "sharpe": -4.29, "usd_getiri": -68.2},
    "kirilim": {"islem": 189, "kazanma": 48.1, "ort_kazanc": 15.5,
                "ort_kayip": 7.9, "getiri": 117.7, "yillik": 26.7,
                "azami_dusus": 11.3, "sharpe": -0.71, "usd_getiri": -11.1},
}
ENDEKS = {"getiri": 221.1, "sharpe": -0.03, "azami_dusus": 22.9,
          "usd_getiri": 31.1, "yillik": 42.6}
BACKTEST_YIL = 3.29
RISKSIZ_YILLIK = 40.0

# Piyasa bağlamı — derslerde "nominal yanılsaması" anlatılırken kullanılıyor.
PIYASA = {
    "xu100_tl_3y": 221,        # % — aynı dönem, TL bazında
    "xu100_usd_3y": 31,        # % — dolar bazında; aradaki fark kurdur
    "usdtry_ilk": 19.63,
    "usdtry_son": 48.08,
    "bist_reel_1y": -4.2,      # % — nominal getiri eksi enflasyon
}

# Canlı sicil: sistemin gerçekte ürettiği sinyallerin sonucu.
CANLI_SICIL = {
    "ay": 4.1,
    "sinyal": 767,
    "kazanma_20g": 35.5,
    "ortalama_20g": -0.98,
}
