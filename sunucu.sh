#!/usr/bin/env bash
# Midas Analist API'yi yerel ağda başlatır ve telefonun kullanacağı adresi yazar.
set -euo pipefail
cd "$(dirname "$0")"

. ./ortam.sh

if [ ! -x .venv/bin/uvicorn ]; then
  echo "uvicorn bulunamadı. Önce: .venv/bin/pip install -r requirements.txt"; exit 1
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
PORT=${PORT:-8000}

echo "────────────────────────────────────────────────────────"
echo "  Midas Analist API"
echo ""
echo "  Bu bilgisayardan : http://127.0.0.1:$PORT"
echo "  Android emülatör : http://10.0.2.2:$PORT"
[ -n "${IP:-}" ] && echo "  Telefondan       : http://$IP:$PORT   <-- Ayarlar'a bunu gir"
echo ""
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "  AI katmanı       : açık (aylık tavan ${MIDAS_AI_TAVAN_TL:-100} TL)"
else
  echo "  AI katmanı       : kapalı (.env içine ANTHROPIC_API_KEY yaz)"
fi
echo ""
echo "  Telefon ve bilgisayar AYNI Wi-Fi'da olmalı."
echo "  İlk açılışta ~100 hisse indirilir; birkaç dakika sürebilir."
echo "  Durdurmak için Ctrl+C"
echo "────────────────────────────────────────────────────────"

exec .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
