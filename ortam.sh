#!/usr/bin/env bash
# .env'i ortama yükler. Kaynak olarak çağrılır: . ./ortam.sh
#
# Neden ayrı dosya: aynı yükleme mantığı gunluk.sh, sunucu.sh ve systemd
# biriminde lazım. Üç yerde kopyalanırsa biri sessizce geride kalır.
_ORTAM_KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$_ORTAM_KOK/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$_ORTAM_KOK/.env"
  set +a
fi
