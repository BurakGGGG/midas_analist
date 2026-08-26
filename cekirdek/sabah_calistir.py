"""`python -m cekirdek.sabah_calistir` — sabah emir hatırlatıcısı.

Ayrı bir giriş noktası: günlük iş 100 hisse indirip saatlerce sürebilen
bir hesap yapıyor, bu iş ise ambardan bir kayıt okuyup mesaj atıyor.
İkisini aynı sürece koymak, sabah 09:45'te bir tarama tetikleme riskini
getirirdi.
"""
from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")


def main() -> int:
    from . import sabah, bildirim, telegram

    plan = sabah.hazirla()
    if not plan.get("gonder"):
        # Sessiz kalmak normal bir sonuç, hata değil: çıkış kodu 0.
        print(f"hatırlatma yok — {plan.get('sebep', 'sebep belirtilmedi')}")
        return 0

    metin = bildirim.sabah_hatirlatici(plan)
    if not metin:
        print("hatırlatma yok — mesaj boş üretildi")
        return 0

    if not telegram.kurulu_mu():
        print("Telegram kurulu değil; mesaj gönderilmedi:\n")
        print(metin)
        return 0

    if telegram.gonder(metin):
        print(f"{len(plan['emirler'])} emir hatırlatıldı "
              f"({plan.get('tarih')} kapanışına göre)")
        return 0

    print("HATA: Telegram gönderimi başarısız", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
