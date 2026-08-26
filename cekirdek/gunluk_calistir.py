"""`python -m cekirdek.gunluk_calistir` — günlük işi çalıştıran giriş noktası."""
from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")


def main() -> int:
    from pathlib import Path
    import yaml
    from . import gunluk

    kok = Path(__file__).resolve().parent.parent
    sermaye = 1000.0
    try:
        a = yaml.safe_load((kok / "ayarlar.yaml").read_text(encoding="utf-8")) or {}
        sermaye = float(a.get("sermaye", 1000))
    except Exception:
        pass

    r = gunluk.calistir(sermaye=sermaye, sessiz=False)
    if r["durum"] == "hata":
        print(f"HATA: {r.get('hata')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
