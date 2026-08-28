#!/usr/bin/env bash
# Midas Analist günlük işi. BIST 18:00'de kapanır, kapanış seansı 18:10'a kadar sürer;
# bu betik 19:00'da çalışır (resmî kapanış yayına girsin diye).
set -uo pipefail
cd "$(dirname "$0")"

# Anahtarlar .env'den gelir. Zamanlayıcı senin terminal oturumunu görmez;
# burada yüklenmezse AI katmanı her gece sessizce atlanır.
. ./ortam.sh

KAYIT="veri/gunluk.log"
mkdir -p veri

{
  echo "════════════════════════════════════════════════════════"
  echo "  $(date '+%Y-%m-%d %H:%M:%S')  günlük iş başlıyor"
  echo "════════════════════════════════════════════════════════"
  .venv/bin/python -m cekirdek.gunluk_calistir 2>&1
  echo "  bitiş: $(date '+%H:%M:%S')  çıkış kodu: $?"
  echo
} >> "$KAYIT" 2>&1

# Kayıt dosyası şişmesin — son 5000 satırı tut
if [ "$(wc -l < "$KAYIT")" -gt 5000 ]; then
  tail -n 5000 "$KAYIT" > "$KAYIT.tmp" && mv "$KAYIT.tmp" "$KAYIT"
fi
