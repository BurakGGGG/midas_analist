#!/usr/bin/env bash
# ESKİ / KULLANILMIYOR — Cloud Run'da kalıcı disk yok, veri/ambar.db her
# uyanışta sıfırlanır. Güncel yol: kökteki dagit.sh (bkz. README > Buluta taşıma).
# API'yi Google Cloud Run'a dağıtır.
#
# Ön koşullar:
#   1) gcloud CLI kurulu ve giriş yapılmış:  gcloud auth login
#   2) Bir proje seçili:                     gcloud config set project PROJE_ID
#   3) Cloud Run ve Cloud Build API'leri açık
set -euo pipefail
cd "$(dirname "$0")/.."   # betik bulut/ altında, kaynak kök dizin

BOLGE=${BOLGE:-europe-west1}          # Türkiye'ye en yakın düşük gecikmeli bölge
SERVIS=${SERVIS:-midas-analist-api}

# Anahtar yoksa üret — bulutta kimlik doğrulaması OLMADAN açma.
ANAHTAR=${MIDAS_API_ANAHTARI:-$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 40)}

# Claude anahtarı VARSA taşı. Yoksa taşıma — bulutta AI'sız da tam çalışır.
# Tavanı da birlikte gönder: tavansız bulut örneği, farkında olmadan
# harcayabileceğin tek yerdir.
AI_ENV=""
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  AI_ENV=",ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
  AI_ENV="$AI_ENV,MIDAS_AI_TAVAN_TL=${MIDAS_AI_TAVAN_TL:-100}"
  echo "  Claude anahtarı taşınıyor (aylık tavan ${MIDAS_AI_TAVAN_TL:-100} TL)"
else
  echo "  Claude anahtarı yok — bulutta AI katmanı kapalı olacak"
fi

echo "Dağıtılıyor: $SERVIS → $BOLGE"
gcloud run deploy "$SERVIS" \
  --source . \
  --region "$BOLGE" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "MIDAS_API_ANAHTARI=$ANAHTAR${AI_ENV}"

echo ""
echo "────────────────────────────────────────────────────────"
echo "  API ANAHTARIN (kaydet, bir daha gösterilmez):"
echo "  $ANAHTAR"
echo ""
echo "  Uygulamada Ayarlar > Sunucu alanına yukarıdaki URL'yi,"
echo "  API anahtarı alanına bu anahtarı gir."
echo "────────────────────────────────────────────────────────"
