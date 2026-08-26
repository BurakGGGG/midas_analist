#!/usr/bin/env bash
# Sabah emir hatırlatıcısı. Sürekli işlem 10:00'da başlar; bu betik
# 09:45'te çalışır ki mesajı görüp emri açılışa yetiştirebilesin.
#
# Yeni analiz YAPMAZ — dün akşamki kaydı okur. Bu yüzden saniyeler sürer.
set -uo pipefail
cd "$(dirname "$0")"

. ./ortam.sh

KAYIT="veri/gunluk.log"
mkdir -p veri

{
  echo "──────────────────────────────────────────────────────────"
  echo "  $(date '+%Y-%m-%d %H:%M:%S')  sabah hatırlatıcı"
  .venv/bin/python -m cekirdek.sabah_calistir 2>&1
} >> "$KAYIT" 2>&1
