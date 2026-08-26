"""Öğretici şemalar — veri grafiği DEĞİL, ders kitabı çizimi.

Fark önemli. `egitmen_gorsel.py` canlı veriyi çizer: "bu hissenin gerçek
RSI'si şu". Buradaki şemalar ise kavramı çizer: "destek nedir" sorusunun
cevabı, gerçek bir hissenin gürültüsü içinde kaybolur — temiz bir zikzak
üzerinde iki etiketle anlaşılır.

İkisi birbirini tamamlar: önce şema kavramı öğretir, sonra canlı grafik
onu gerçek piyasada gösterir.

ŞEMA SÖZLEŞMESİ — çizim istemcide yapılır, burada yalnızca tarif üretilir:

    en, boy      : koordinat uzayı (y YUKARI artar, ressam çevirir)
    cizgiler     : [{nokta: [[x,y],...], renk, kalin, kesik}]
    mumlar       : [{x, a(çılış), y(üksek), d(üşük), k(apanış), genislik}]
    seviyeler    : [{y, x1, x2, ad, renk}]        yatay etiketli çizgi
    etiketler    : [{x, y, ad, hiza}]             serbest metin
    oklar        : [{x1,y1,x2,y2, renk}]

Renk adları temadan çözülür: aksan / arti / eksi / uyari / solgun.
"""
from __future__ import annotations


def _sema(**kw) -> dict:
    taban = {"tur": "sema", "en": 100.0, "boy": 60.0,
             "cizgiler": [], "mumlar": [], "seviyeler": [],
             "etiketler": [], "oklar": []}
    taban.update(kw)
    return taban


# ── kavram şemaları ────────────────────────────────────────────────────────

def destek_direnc() -> dict:
    """Zikzak + etiketli seviyeler. Kitaplardaki klasik ilk çizim."""
    # Zikzak x=76'da biter, seviyeler x=79'da: etiketler sağda hizalı bir
    # sütun oluşturur ve çizginin üstüne binmez. Etiket okunmuyorsa şema
    # işini yapmıyor demektir.
    yol = [[0, 6], [10, 30], [20, 14], [32, 44], [42, 26], [54, 56], [64, 34],
           [76, 48]]
    return _sema(
        baslik="Destek ve direnç",
        aciklama=("Fiyat yükselirken durduğu yerler DİRENÇ, düşerken "
                  "tutunduğu yerler DESTEK'tir. İkisi de kesin bir nokta "
                  "değil, bir bölgedir."),
        cizgiler=[{"nokta": yol, "renk": "aksan", "kalin": 2.4}],
        seviyeler=[
            {"y": 30, "x1": 4, "x2": 79, "ad": "Direnç 1", "renk": "eksi"},
            {"y": 44, "x1": 26, "x2": 79, "ad": "Direnç 2", "renk": "eksi"},
            {"y": 56, "x1": 48, "x2": 79, "ad": "Direnç 3", "renk": "eksi"},
            {"y": 14, "x1": 14, "x2": 79, "ad": "Destek 1", "renk": "arti"},
            {"y": 26, "x1": 36, "x2": 79, "ad": "Destek 2", "renk": "arti"},
        ],
        sonuc=("Dikkat: her tepe bir öncekinden yüksek, her dip bir "
               "öncekinden yüksek. Bu, yükselen trendin tanımıdır."),
    )


def mum_anatomisi() -> dict:
    """Tek bir mumun parçaları — gövde, fitil, açılış, kapanış."""
    return _sema(
        en=100.0, boy=60.0,
        baslik="Bir mum neyi anlatır",
        aciklama=("Her mum bir zaman diliminin DÖRT fiyatını taşır: açılış, "
                  "en yüksek, en düşük, kapanış. Gövde açılış ile kapanış "
                  "arasıdır; fitil o aralığın dışına taşan uçları gösterir."),
        mumlar=[
            # yükselen mum (kapanış > açılış)
            {"x": 30, "a": 20, "y": 52, "d": 12, "k": 40, "genislik": 11},
            # düşen mum (kapanış < açılış)
            {"x": 70, "a": 44, "y": 52, "d": 10, "k": 22, "genislik": 11},
        ],
        etiketler=[
            {"x": 30, "y": 57, "ad": "en yüksek", "hiza": "orta"},
            {"x": 30, "y": 6, "ad": "en düşük", "hiza": "orta"},
            {"x": 44, "y": 40, "ad": "kapanış", "hiza": "sol"},
            {"x": 44, "y": 20, "ad": "açılış", "hiza": "sol"},
            {"x": 30, "y": 30, "ad": "gövde", "hiza": "orta"},
            {"x": 16, "y": 47, "ad": "fitil", "hiza": "sag"},
            {"x": 30, "y": 0, "ad": "YÜKSELEN", "hiza": "orta"},
            {"x": 70, "y": 0, "ad": "DÜŞEN", "hiza": "orta"},
            {"x": 84, "y": 44, "ad": "açılış", "hiza": "sol"},
            {"x": 84, "y": 22, "ad": "kapanış", "hiza": "sol"},
        ],
        sonuc=("Gövde ne kadar uzunsa o dönemde taraflardan biri o kadar "
               "baskındı. Uzun fitil ise reddedilmiş bir fiyat demektir: "
               "oraya gidildi ama tutunulamadı."),
    )


def trend_cizgisi() -> dict:
    """Yükselen trend + dipleri birleştiren çizgi."""
    yol = [[0, 6], [10, 22], [18, 14], [30, 34], [40, 24], [54, 46], [64, 36],
           [78, 56], [88, 46]]
    return _sema(
        baslik="Trend çizgisi nasıl çizilir",
        aciklama=("Yükselen trendde çizgi DİPLERİ birleştirir, tepeleri "
                  "değil. En az iki dip gerekir; üçüncü dokunuş çizgiyi "
                  "doğrular."),
        cizgiler=[
            {"nokta": yol, "renk": "aksan", "kalin": 2.4},
            {"nokta": [[8, 18], [92, 54]], "renk": "arti", "kalin": 1.8,
             "kesik": True},
        ],
        etiketler=[
            {"x": 18, "y": 9, "ad": "dip 1", "hiza": "orta"},
            {"x": 40, "y": 19, "ad": "dip 2", "hiza": "orta"},
            {"x": 64, "y": 31, "ad": "dip 3", "hiza": "orta"},
            {"x": 88, "y": 58, "ad": "trend çizgisi", "hiza": "sag"},
        ],
        sonuc=("Çizgi kırılınca trend bitmiş SAYILMAZ — önce kırılımın "
               "kalıcı olup olmadığına bakılır. Tek mumluk delme, en sık "
               "yanıltan şeydir."),
    )


def mum_formasyonlari() -> dict:
    """Üç klasik: çekiç, doji, yutan boğa."""
    return _sema(
        en=120.0, boy=60.0,
        baslik="Üç temel mum formasyonu",
        aciklama=("Formasyon tek başına sinyal değildir — nerede oluştuğu "
                  "her şeyi değiştirir. Aynı çekiç, düşüşün dibinde başka, "
                  "yükselişin tepesinde başka anlama gelir."),
        mumlar=[
            # Çekiç: küçük gövde üstte, uzun alt fitil
            {"x": 20, "a": 40, "y": 46, "d": 10, "k": 44, "genislik": 10},
            # Doji: açılış ≈ kapanış
            {"x": 60, "a": 30, "y": 50, "d": 12, "k": 30.6, "genislik": 10},
            # Yutan boğa: küçük düşen mum + onu kapsayan yükselen mum
            {"x": 94, "a": 36, "y": 40, "d": 30, "k": 31, "genislik": 8},
            {"x": 108, "a": 28, "y": 50, "d": 24, "k": 46, "genislik": 10},
        ],
        etiketler=[
            {"x": 20, "y": 2, "ad": "ÇEKİÇ", "hiza": "orta"},
            {"x": 60, "y": 2, "ad": "DOJİ", "hiza": "orta"},
            {"x": 101, "y": 2, "ad": "YUTAN BOĞA", "hiza": "orta"},
            # Etiketler KISA: uzun metin komşusuyla çakışıyor ve ikisi de
            # okunmaz oluyor. Ayrıntı zaten alttaki sonuç kutusunda.
            {"x": 20, "y": 54, "ad": "kısa gövde", "hiza": "orta"},
            {"x": 20, "y": 20, "ad": "uzun alt fitil", "hiza": "orta"},
            {"x": 60, "y": 54, "ad": "gövde yok", "hiza": "orta"},
            {"x": 101, "y": 54, "ad": "kapsıyor", "hiza": "orta"},
        ],
        sonuc=("Çekiç: satıldı ama geri alındı. Doji: taraflar berabere, "
               "kararsızlık. Yutan boğa: yön değişimi denemesi. Üçü de "
               "TEYİT ister — sonraki mum ne yaptı?"),
    )


def bosluk() -> dict:
    """Gap: iki mum arasında hiç işlem görmemiş fiyat aralığı."""
    return _sema(
        en=110.0, boy=60.0,
        baslik="Boşluk (gap) nedir",
        aciklama=("Bir mumun en düşüğü, bir öncekinin en yükseğinin "
                  "üstündeyse arada BOŞLUK kalır: o fiyatlardan hiç işlem "
                  "geçmemiştir."),
        mumlar=[
            {"x": 18, "a": 14, "y": 24, "d": 10, "k": 22, "genislik": 9},
            {"x": 34, "a": 20, "y": 26, "d": 16, "k": 24, "genislik": 9},
            {"x": 58, "a": 38, "y": 48, "d": 36, "k": 46, "genislik": 9},
            {"x": 74, "a": 46, "y": 54, "d": 42, "k": 52, "genislik": 9},
            {"x": 90, "a": 52, "y": 56, "d": 44, "k": 46, "genislik": 9},
        ],
        seviyeler=[
            {"y": 26, "x1": 28, "x2": 66, "ad": "önceki en yüksek",
             "renk": "solgun"},
            {"y": 36, "x1": 28, "x2": 66, "ad": "sonraki en düşük",
             "renk": "solgun"},
        ],
        etiketler=[{"x": 46, "y": 31, "ad": "BOŞLUK", "hiza": "orta"}],
        sonuc=("Boşluklar genelde kapanır — fiyat geri gelip o aralığı "
               "doldurur. Ama 'genelde' her zaman demek değildir; boşluk "
               "kapanmasına bahis girmek pahalı bir alışkanlıktır."),
    )


def zaman_dilimi() -> dict:
    """Aynı hareket, iki farklı zaman diliminde."""
    gunluk = [[0, 30], [8, 22], [16, 34], [24, 18], [32, 40], [40, 26],
              [48, 44], [56, 30], [64, 48], [72, 36], [80, 52], [88, 44]]
    haftalik = [[0, 30], [22, 26], [44, 38], [66, 42], [88, 48]]
    return _sema(
        baslik="Aynı hisse, iki zaman dilimi",
        aciklama=("Üstteki çizgi günlük, alttaki aynı dönemin haftalık "
                  "hâli. Aynı fiyat hareketi, hangi pencereden baktığına "
                  "göre 'dalgalı' ya da 'istikrarlı yükseliyor' görünür."),
        cizgiler=[
            {"nokta": gunluk, "renk": "solgun", "kalin": 1.4},
            {"nokta": haftalik, "renk": "aksan", "kalin": 2.6},
        ],
        etiketler=[
            {"x": 88, "y": 40, "ad": "günlük", "hiza": "sag"},
            {"x": 88, "y": 52, "ad": "haftalık", "hiza": "sag"},
        ],
        sonuc=("Kısa zaman dilimi daha çok sinyal üretir ama sinyallerin "
               "çoğu gürültüdür. Bu sistem GÜNLÜK mumla çalışır: gün içi "
               "gürültüyü bilerek görmez."),
    )


def retest() -> dict:
    """Kırılım, geri dönüş ve rol değişimi tek çizimde."""
    # Seviye y=34. Çizgi önce ona üç kez dokunup dönüyor (direnç), sonra
    # aşıyor, sonra geri gelip üstünde tutunuyor (retest), sonra devam.
    yol = [[0, 12], [10, 33], [20, 22], [32, 34], [42, 24], [52, 33],
           [60, 44], [68, 50], [78, 36], [86, 48], [98, 58]]
    return _sema(
        en=110.0, boy=60.0,
        baslik="Kırılım ve retest",
        aciklama=("Fiyat aynı seviyeden üç kez döndü, sonra aştı. Geri "
                  "dönüp o seviyeye dokunmasına RETEST denir: kırılan "
                  "direnç bu kez destek gibi davranır."),
        cizgiler=[{"nokta": yol, "renk": "aksan", "kalin": 2.4}],
        seviyeler=[
            # Aynı y, iki parça: solda direnç, sağda destek. Rol değişimi
            # tek bir çizgide anlatılamaz — renk değişimi anlatır.
            {"y": 34, "x1": 4, "x2": 58, "ad": "direnç", "renk": "eksi"},
            {"y": 34, "x1": 60, "x2": 106, "ad": "artık destek",
             "renk": "arti"},
        ],
        etiketler=[
            {"x": 60, "y": 56, "ad": "kırılım", "hiza": "orta"},
            {"x": 80, "y": 28, "ad": "retest", "hiza": "orta"},
        ],
        sonuc=("Retest daha iyi giriş fiyatı verir: stop kırılan seviyenin "
               "altında sabit kaldığı için hisse başına risk küçülür. "
               "Bedeli, retest hiç gelmezse işlemin hiç olmamasıdır."),
    )


def mum_sozlugu() -> dict:
    """Çekiç ve asılı adam: aynı dört sayı, zıt anlam."""
    # İki mum BİLEREK aynı ölçüde: gövde 2, alt fitil 12, üst fitil 1.
    # Şemanın tek iddiası bu — şekil tek başına hiçbir şey söylemiyor.
    dusus = [[6, 50], [14, 42], [22, 36], [30, 30]]
    yukselis = [[68, 14], [76, 22], [84, 28], [92, 34]]
    return _sema(
        en=120.0, boy=60.0,
        baslik="Aynı şekil, zıt anlam",
        aciklama=("Soldaki ve sağdaki mum birebir aynı: kısa gövde, uzun "
                  "alt fitil. Farkı yaratan tek şey solunda kalan grafik — "
                  "biri düşüşün dibinde, diğeri yükselişin tepesinde."),
        cizgiler=[
            {"nokta": dusus, "renk": "solgun", "kalin": 1.8},
            {"nokta": yukselis, "renk": "solgun", "kalin": 1.8},
        ],
        mumlar=[
            {"x": 38, "a": 26, "y": 29, "d": 14, "k": 28, "genislik": 9},
            {"x": 100, "a": 38, "y": 41, "d": 26, "k": 40, "genislik": 9},
        ],
        etiketler=[
            {"x": 38, "y": 4, "ad": "ÇEKİÇ", "hiza": "orta"},
            {"x": 100, "y": 4, "ad": "ASILI ADAM", "hiza": "orta"},
            {"x": 18, "y": 54, "ad": "düşüş trendi", "hiza": "orta"},
            {"x": 78, "y": 8, "ad": "yükseliş trendi", "hiza": "orta"},
        ],
        sonuc=("Sıralama şudur: önce trend, sonra konum, en son şekil. "
               "Şekille başlarsan gerisini kendine uydurursun — beynin "
               "gürültüde desen görmek üzere kuruludur."),
    )


def formasyon_sicili() -> dict:
    """Bulkowski'nin dönüş oranları, yazı tura çizgisiyle birlikte."""
    # Yatay çubuk: seviye çizgisinin uzunluğu oranı temsil ediyor.
    # x = 10 + oran * 0,8  →  %50 ekseni tam ortada (x=50) durur.
    def bar(oran: float) -> float:
        return 10.0 + oran * 0.8

    return _sema(
        en=100.0, boy=60.0,
        baslik="Formasyonlar gerçekte ne kadar tutuyor",
        aciklama=("Bulkowski'nin 103 mum formasyonunu taradığı ölçümünden "
                  "üç tanesi. Çubuk uzunluğu dönüş oranı; kesikli çizgi "
                  "yazı tura sınırı."),
        cizgiler=[
            {"nokta": [[50, 6], [50, 54]], "renk": "eksi", "kalin": 1.6,
             "kesik": True},
        ],
        seviyeler=[
            {"y": 46, "x1": 10, "x2": bar(60), "ad": "Çekiç %60",
             "renk": "aksan"},
            {"y": 34, "x1": 10, "x2": bar(63), "ad": "Yutan boğa %63",
             "renk": "aksan"},
            {"y": 22, "x1": 10, "x2": bar(79), "ad": "Yutan ayı %79",
             "renk": "arti"},
        ],
        etiketler=[
            {"x": 50, "y": 58, "ad": "yazı tura %50", "hiza": "orta"},
            # Şemanın asıl dersi bu etikette: en uzun çubuk en iyi
            # formasyon değil. Dönüş oldu demek, kazandın demek değil.
            {"x": 74, "y": 16, "ad": "ama hareketi kısa", "hiza": "orta"},
        ],
        sonuc=("Üçü de yazı turadan iyi. Ama yutan ayı — en yüksek dönüş "
               "oranı — dönüşten sonraki hareket sıralamasında 103 "
               "formasyon içinde 91'inci. İsabet oranı kazanç değildir."),
    )


def zaman_serisi() -> dict:
    """Gördüğün fiyat = trend + gürültü. Hangisi büyük?"""
    trend = [[0, 16], [25, 24], [50, 32], [75, 40], [100, 48]]
    fiyat = [[0, 14], [6, 22], [12, 16], [18, 26], [24, 20], [30, 30],
             [36, 24], [42, 34], [48, 28], [54, 38], [60, 32], [66, 42],
             [72, 36], [78, 46], [84, 40], [90, 50], [96, 44], [100, 52]]
    return _sema(
        en=100.0, boy=60.0,
        baslik="Trend ve gürültü",
        aciklama=("Kalın çizgi fiyatın gerçek yönü, ince çizgi ekranda "
                  "gördüğün fiyat. Aradaki mesafenin adı gürültü ve günlük "
                  "grafikte hareketin çoğunu o oluşturur."),
        cizgiler=[
            {"nokta": trend, "renk": "aksan", "kalin": 2.6},
            {"nokta": fiyat, "renk": "solgun", "kalin": 1.4},
        ],
        oklar=[{"x1": 78, "y1": 41, "x2": 78, "y2": 45, "renk": "uyari"}],
        etiketler=[
            {"x": 50, "y": 57, "ad": "gördüğün fiyat", "hiza": "orta"},
            {"x": 20, "y": 8, "ad": "trend", "hiza": "orta"},
            {"x": 74, "y": 52, "ad": "gürültü", "hiza": "orta"},
        ],
        sonuc=("Bir kural ancak gürültüden büyük bir sinyal yakalarsa "
               "değerlidir. Teknik analizin zor olmasının sebebi budur: "
               "ekrandaki hareketin çoğu bir şey anlatmıyor."),
    )


SEMALAR = {
    "destek_direnc": destek_direnc,
    "mum_anatomisi": mum_anatomisi,
    "trend_cizgisi": trend_cizgisi,
    "mum_formasyonlari": mum_formasyonlari,
    "bosluk": bosluk,
    "zaman_dilimi": zaman_dilimi,
    "retest": retest,
    "mum_sozlugu": mum_sozlugu,
    "formasyon_sicili": formasyon_sicili,
    "zaman_serisi": zaman_serisi,
}


def sema_getir(ad: str) -> dict:
    uretici = SEMALAR.get(ad)
    if not uretici:
        return {"yok": True}
    try:
        return uretici()
    except Exception as e:
        return {"yok": True, "hata": str(e)[:120]}
