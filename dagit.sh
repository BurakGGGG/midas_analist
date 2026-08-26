#!/usr/bin/env bash
# Backend'i bulut sunucusuna dağıtır (Oracle Cloud Always Free / Ubuntu).
#
#   ./dagit.sh --ilk      ilk kurulum: .env + geçmiş veri + sunucu kurulumu
#   ./dagit.sh            günlük kullanım: kodu gönder, API'yi yeniden başlat
#
# Sunucu adresi .env içindeki MIDAS_SUNUCU'dan okunur, yoksa ortamdan:
#   MIDAS_SUNUCU=ubuntu@140.238.x.x ./dagit.sh --ilk
#
# Cloud Run dağıtımı artık bulut/cloudrun_dagit.sh içinde. Bu proje kalıcı
# disk istiyor (veri/ambar.db her gün büyür), Cloud Run'da kalıcı disk yok.
set -euo pipefail
cd "$(dirname "$0")"

ILK=0
[ "${1:-}" = "--ilk" ] && ILK=1

# ─────────────────────────────────────────────── sunucu adresi
[ -f .env ] && { set -a; . ./.env; set +a; }
SUNUCU="${MIDAS_SUNUCU:-}"
if [ -z "$SUNUCU" ]; then
  echo "MIDAS_SUNUCU tanımlı değil." >&2
  echo "  .env içine ekle:  MIDAS_SUNUCU=ubuntu@SUNUCU_IP" >&2
  exit 1
fi
UZAK_KOK="midas"

# ─────────────────────────────────────────────── API anahtarı
# Bulutta ZORUNLU: anahtarsız açılan API'nin bütün uçları herkese açık olur.
if ! grep -qE '^MIDAS_API_ANAHTARI=.+' .env 2>/dev/null; then
  if [ "$ILK" != "1" ]; then
    echo "MIDAS_API_ANAHTARI boş. Önce: ./dagit.sh --ilk" >&2; exit 1
  fi
  YENI="$(head -c 48 /dev/urandom | base64 | tr -d '/+=' | head -c 40)"
  # Satır varsa doldur, yoksa ekle.
  if grep -q '^MIDAS_API_ANAHTARI=' .env; then
    sed -i "s|^MIDAS_API_ANAHTARI=.*|MIDAS_API_ANAHTARI=$YENI|" .env
  else
    printf '\nMIDAS_API_ANAHTARI=%s\n' "$YENI" >> .env
  fi
  chmod 600 .env
  echo "→ API anahtarı üretildi ve .env'e yazıldı"
fi
ANAHTAR="$(sed -n 's/^MIDAS_API_ANAHTARI=//p' .env | head -1)"

# ─────────────────────────────────────────────── kod
# --delete var ama dışlananlar silinmez (rsync varsayılanı): sunucudaki
# veri/ ve .venv/ olduğu yerde kalır.
echo "→ kod gönderiliyor: $SUNUCU:~/$UZAK_KOK"
ssh "$SUNUCU" "mkdir -p ~/$UZAK_KOK"
rsync -az --delete \
  --exclude '.venv/' \
  --exclude 'mobil/' \
  --exclude 'veri/' \
  --exclude 'cikti/' \
  --exclude '__pycache__/' \
  --exclude '**/__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.git/' \
  --exclude '.env' \
  ./ "$SUNUCU:$UZAK_KOK/"

if [ "$ILK" = "1" ]; then
  # .env ayrı ve dar izinle gider (Claude anahtarı ve API anahtarı içinde).
  echo "→ .env gönderiliyor"
  rsync -az --chmod=F600 .env "$SUNUCU:$UZAK_KOK/.env"

  # Geçmişi taşı. ambar.db öğrenme katmanının hafızası: fiyat geçmişi,
  # sinyaller ve sonuçları burada. Taşımazsan canlı sicil sıfırdan başlar.
  # *.pkl önbelleği de gider — yoksa sunucu ilk açılışta 100 hisseyi
  # yeniden indirir (dakikalar sürer).
  if [ -f veri/ambar.db ]; then
    echo "→ geçmiş veri gönderiliyor ($(du -sh veri | cut -f1))"
    ssh "$SUNUCU" "mkdir -p ~/$UZAK_KOK/veri/temel"
    rsync -az veri/ "$SUNUCU:$UZAK_KOK/veri/"
  fi

  echo "→ sunucu kurulumu çalışıyor (ilk seferde birkaç dakika)"
  ssh -t "$SUNUCU" "bash ~/$UZAK_KOK/bulut/sunucu_kur.sh"
else
  echo "→ API yeniden başlatılıyor"
  ssh "$SUNUCU" "sudo systemctl restart midas-api"
fi

# ─────────────────────────────────────────────── doğrulama
IP="${SUNUCU##*@}"
ALAN="${IP//./-}.sslip.io"
echo "→ sağlık kontrolü (önbellek ısınırken 'hazir' false olabilir)"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 10 "https://$ALAN/saglik" 2>/dev/null; then
    echo; break
  fi
  [ "$i" = "10" ] && echo "  yanıt yok — aşağıdaki notlara bak"
  sleep 6
done

echo ""
echo "────────────────────────────────────────────────────────"
echo "  Sunucu : https://$ALAN"
if [ "$ILK" = "1" ]; then
  echo "  Anahtar: $ANAHTAR"
  echo ""
  echo "  Telefonda Ayarlar > Sunucu'ya adresi, API anahtarı alanına"
  echo "  yukarıdaki anahtarı gir."
  echo ""
  echo "  Yanıt gelmiyorsa: Oracle konsolu > VCN > Security List'te"
  echo "  80 ve 443 portlarına gelen kural ekli mi?"
fi
echo "  Kayıt  : ssh $SUNUCU 'tail -f ~/$UZAK_KOK/veri/gunluk.log'"
echo "────────────────────────────────────────────────────────"
