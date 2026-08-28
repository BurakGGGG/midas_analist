"""BIST işlem evreni: hangi hisselere bakacağız, hangilerini elemeli."""
from __future__ import annotations

# Midas'ın yayınladığı güncel BIST 100 bileşenleri (Ağustos 2026).
# Endeks 3 ayda bir revize edilir; `analist.py evren-guncelle` ile yenilenir.
BIST100 = [
    "AEFES","AKBNK","AKSA","AKSEN","ALARK","ALTNY","ANSGR","ARCLK","ASELS","ASTOR",
    "BALSU","BERA","BIMAS","BRSAN","BRYAT","BSOKE","BTCIM","CANTE","CCOLA","CIMSA",
    "CVKMD","CWENE","DAPGM","DOAS","DOHOL","DSTKF","ECILC","EFOR","EKGYO","ENERY",
    "ENJSA","ENKAI","EREGL","ESEN","EUPWR","EUREN","FENER","FROTO","GARAN","GENIL",
    "GESAN","GLRMK","GRSEL","GRTHO","GSRAY","GUBRF","HALKB","HEKTS","IEYHO","ISCTR",
    "ISMEN","IZENR","KCHOL","KLRHO","KRDMD","KTLEV","KUYAS","MAGEN","MAVI","MGROS",
    "MIATK","MPARK","OBAMS","ODAS","ODINE","OTKAR","OYAKC","PAHOL","PASEU","PATEK",
    "PETKM","PGSUS","PSGYO","QUAGR","RALYH","REEDR","SAHOL","SARKY","SASA","SISE",
    "SKBNK","SOKM","TAVHL","TCELL","THYAO","TKFEN","TOASO","TRALT","TRENJ","TRMET",
    "TSKB","TTKOM","TUKAS","TUPRS","TURSG","ULKER","VAKBN","VESTL","YKBNK","ZOREN",
]

# BIST 30 - en likit çekirdek. Küçük sermaye için en güvenli oyun alanı:
# spread dar, derinlik yüksek, brüt takas riski düşük.
#
# KOZAL burada değil: şirket TRALT (Türk Altın İşletmeleri) olarak
# yeniden adlandırıldı. Eski kod her taramada 4 başarısız HTTP isteği
# ve çağrı başına ~3,6 saniye maliyet çıkarıyordu.
BIST30 = [
    "AKBNK","ALARK","ASELS","ASTOR","BIMAS","CIMSA","EKGYO","ENKAI","EREGL","FROTO",
    "GARAN","GUBRF","HALKB","ISCTR","KCHOL","TRALT","KRDMD","MGROS","OYAKC","PETKM",
    "PGSUS","SAHOL","SASA","SISE","TAVHL","TCELL","THYAO","TOASO","TUPRS","YKBNK",
]

ENDEKS = "XU100.IS"   # kıyas ölçütü (benchmark)
KUR = "TRY=X"         # USD/TRY

def yf_kodu(sembol: str) -> str:
    """'THYAO' -> 'THYAO.IS'.

    BIST dışı semboller (döviz 'TRY=X', endeks '^GSPC', ABD hissesi 'AAPL')
    olduğu gibi bırakılır - onlara .IS eklemek 404 verir.
    """
    s = sembol.strip().upper()
    if s.endswith(".IS") or "=" in s or s.startswith("^") or "-" in s:
        return s
    return f"{s}.IS"

def sade_kod(sembol: str) -> str:
    """'THYAO.IS' -> 'THYAO'. Döviz/endeks kodları bozulmadan geçer."""
    return sembol.strip().upper().removesuffix(".IS")

def evren_getir(ad: str = "bist100") -> list[str]:
    ad = ad.lower()
    if ad in ("bist30", "xu030", "30"):
        return list(BIST30)
    if ad in ("bist100", "xu100", "100"):
        return list(BIST100)
    if ad == "hepsi":
        return sorted(set(BIST100) | set(BIST30))
    # virgüllü özel liste: "THYAO,GARAN,ASELS"
    return [sade_kod(x) for x in ad.split(",") if x.strip()]
