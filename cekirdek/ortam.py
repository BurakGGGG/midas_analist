"""`.env` dosyasını ortama yükler — bağımlılıksız.

Neden var: anahtarı kendi terminalinde `export` etmek yetmiyor. Üç ayrı
giriş noktası var (CLI, uvicorn sunucusu, 18:10 systemd zamanlayıcısı) ve
zamanlayıcı senin oturumunu HİÇ görmez. Anahtar tek yerde tanımlanmazsa
gece çalışan iş AI katmanını sessizce atlar ve bunu kimse fark etmez.

Kural: ortamda ZATEN tanımlı bir değişken ezilmez. Böylece tek seferlik
denemeler (`MIDAS_AI_TAVAN_TL=0 python analist.py ...`) dosyayı geçersiz
kılabilir.

Bu modül içe aktarıldığı anda çalışır; `ai.py` env okumadan ÖNCE onu
içe aktarır.
"""
from __future__ import annotations

import os
from pathlib import Path

DOSYA = Path(__file__).resolve().parent.parent / ".env"


def yukle(yol: Path | None = None, ez: bool = False) -> int:
    """`.env` içindeki KEY=VALUE satırlarını ortama koyar.

    Döner: yüklenen değişken sayısı. Dosya yoksa 0 — hata değil.
    """
    yol = yol or DOSYA
    if not yol.is_file():
        return 0
    n = 0
    try:
        for ham in yol.read_text(encoding="utf-8").splitlines():
            satir = ham.strip()
            if not satir or satir.startswith("#") or "=" not in satir:
                continue
            # `export KEY=değer` biçimi de kabul edilsin
            if satir.startswith("export "):
                satir = satir[7:].lstrip()
            ad, _, deger = satir.partition("=")
            ad = ad.strip()
            deger = deger.strip()
            # Tırnakları soy — "sk-ant-..." ve 'sk-ant-...' aynı şey olmalı
            if len(deger) >= 2 and deger[0] == deger[-1] and deger[0] in "\"'":
                deger = deger[1:-1]
            if not ad or (not ez and ad in os.environ):
                continue
            if deger == "":
                continue          # boş değer "tanımsız" demektir, tanımlama
            os.environ[ad] = deger
            n += 1
    except OSError:
        return 0
    return n


def durum() -> dict:
    """Hangi anahtarlar tanımlı — DEĞERLERİ ASLA döndürmez."""
    return {
        "dosya": str(DOSYA),
        "dosya_var": DOSYA.is_file(),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "api_anahtari": bool(os.environ.get("MIDAS_API_ANAHTARI")),
        "ai_tavan": os.environ.get("MIDAS_AI_TAVAN_TL", "100"),
    }


# İçe aktarıldığı anda yükle.
YUKLENEN = yukle()
