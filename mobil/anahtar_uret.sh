#!/usr/bin/env bash
# Yayın imza anahtarı üretir.
#
# NEDEN: debug anahtarıyla imzalanan uygulama, o anahtar bir gün yenilenirse
# bir daha "üstüne kurulamaz" — tek yol kaldırıp yeniden kurmaktır ve o da
# uygulama verisinin tamamını siler. Kendi anahtarın sende kaldığı sürece bu
# olmaz.
#
# DİKKAT: bu betiği çalıştırdıktan sonraki ilk kurulum, imza değiştiği için
# MEVCUT UYGULAMANIN KALDIRILMASINI ister ve telefondaki veri silinir.
# Önce Daha > Hesap ve yedek'ten buluta yedek al.
set -euo pipefail
cd "$(dirname "$0")"

JKS="${JKS:-$HOME/midas-yayin.jks}"
ALIAS="midas"

if [ -f "$JKS" ]; then
  echo "Zaten var: $JKS"
  echo "Üzerine yazmak veriyi kurtarılamaz hale getirir; elle sil ve tekrar çalıştır."
  exit 1
fi

PAROLA="$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 28)"

keytool -genkeypair -v \
  -keystore "$JKS" -alias "$ALIAS" \
  -keyalg RSA -keysize 4096 -validity 10000 \
  -storepass "$PAROLA" -keypass "$PAROLA" \
  -dname "CN=Midas Analist, O=Kisisel, C=TR"

cat > android/key.properties <<PROP
storeFile=$JKS
storePassword=$PAROLA
keyAlias=$ALIAS
keyPassword=$PAROLA
PROP
chmod 600 android/key.properties

echo
echo "────────────────────────────────────────────────────────"
echo "  Anahtar : $JKS"
echo "  Ayar    : $(pwd)/android/key.properties"
echo
echo "  İKİSİNİ DE YEDEKLE. Kaybedersen bir daha üstüne kurulum"
echo "  yapamazsın; her güncelleme veriyi silmek zorunda kalır."
echo "  İkisi de .gitignore'da — repoya girmezler."
echo "────────────────────────────────────────────────────────"
