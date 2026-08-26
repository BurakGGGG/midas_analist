#!/usr/bin/env bash
# Always Free ARM (A1) kapasitesini kovalar: yer açılana kadar sürekli dener.
#
# Oracle'da A1 kapasitesi gün içinde kısa aralıklarla açılıyor; elle denemekle
# yakalaması şansa kalıyor. Bu betik sürekli dener, kapasite hatalarını normal
# karşılar, geçici hataları yutar, yalnızca gerçek engellerde durur.
#
#   ./bulut/a1_kovala.sh                 2 OCPU / 12 GB
#   OCPU=1 RAM=6 ./bulut/a1_kovala.sh    daha küçük (yer bulması daha kolay)
#   ARALIK=30 ./bulut/a1_kovala.sh       30 saniyede bir dene
set -uo pipefail
cd "$(dirname "$0")/.."

OCI="${OCI:-$HOME/.oci-cli-venv/bin/oci}"
[ -x "$OCI" ] || OCI="$(command -v oci || true)"
if [ -z "$OCI" ] || [ ! -x "$OCI" ]; then
  echo "OCI CLI yok. Önce: ./bulut/oci_kur.sh" >&2; exit 1
fi

AD_ADI="${AD_ADI:-midas}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPU="${OCPU:-2}"
RAM="${RAM:-12}"
ARALIK="${ARALIK:-60}"
ANAHTAR_DOSYA="${ANAHTAR_DOSYA:-$HOME/.ssh/oracle_midas.pub}"
KAYIT="${KAYIT:-veri/a1_kovala.log}"

[ -f "$ANAHTAR_DOSYA" ] || { echo "SSH açık anahtarı yok: $ANAHTAR_DOSYA" >&2; exit 1; }
SSH_ANAHTAR="$(cat "$ANAHTAR_DOSYA")"

yaz() { printf '%s  %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$KAYIT"; }
mkdir -p "$(dirname "$KAYIT")"

KIRACI="$(awk -F= '/^tenancy=/{print $2; exit}' "$HOME/.oci/config" | tr -d ' \r')"
[ -n "$KIRACI" ] || { echo "~/.oci/config içinde tenancy yok. ./bulut/oci_kur.sh çalıştır." >&2; exit 1; }
BOLGE="$(awk -F= '/^region=/{print $2; exit}' "$HOME/.oci/config" | tr -d ' \r')"
BOLME="$KIRACI"   # kök bölme = tenancy

# Kimlik/ağ çağrıları da ara sıra geçici 401 dönüyor; ısrarla dene.
israrla() {
  local i cikti
  for i in 1 2 3 4 5 6; do
    cikti="$("$OCI" "$@" 2>&1)"
    if [ $? -eq 0 ] && ! printf '%s' "$cikti" | grep -q 'NotAuthenticated\|ServiceError'; then
      printf '%s' "$cikti"; return 0
    fi
    sleep 5
  done
  return 1
}

yaz "hazırlık: hesap bilgileri okunuyor"
ADLAR_HAM="$(israrla iam availability-domain list --compartment-id "$BOLME" --query 'data[].name')" \
  || { echo "Availability domain okunamadı." >&2; exit 1; }
mapfile -t ADLAR < <(printf '%s' "$ADLAR_HAM" | python3 -c 'import sys,json; [print(x) for x in json.load(sys.stdin)]')
[ "${#ADLAR[@]}" -gt 0 ] || { echo "AD listesi boş." >&2; exit 1; }

IMAJ="$(israrla compute image list --compartment-id "$BOLME" \
  --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
  --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
  --query 'data[0].id' --raw-output)" || { echo "Ubuntu 24.04 imajı bulunamadı." >&2; exit 1; }

SUBNET="$(israrla network subnet list --compartment-id "$BOLME" \
  --query "data[?\"prohibit-public-ip-on-vnic\"==\`false\`] | [0].id" --raw-output)" \
  || { echo "Public subnet bulunamadı. VCN sihirbazını çalıştırdın mı?" >&2; exit 1; }

cat <<OZET | tee -a "$KAYIT"

════════════════════════════════════════════════════════
  Bölge   : $BOLGE
  Shape   : $SHAPE  ($OCPU OCPU / $RAM GB)
  AD      : ${ADLAR[*]}
  Aralık  : ${ARALIK}s     Kayıt: $KAYIT
  Durdur  : Ctrl+C
════════════════════════════════════════════════════════

OZET

TUR=0; KAPASITE=0; GECICI=0; ARDISIK_GECICI=0
while true; do
  TUR=$((TUR+1))
  for AD in "${ADLAR[@]}"; do
    CIKTI="$("$OCI" compute instance launch \
      --availability-domain "$AD" \
      --compartment-id "$BOLME" \
      --shape "$SHAPE" \
      --shape-config "{\"ocpus\":$OCPU,\"memoryInGBs\":$RAM}" \
      --image-id "$IMAJ" \
      --subnet-id "$SUBNET" \
      --assign-public-ip true \
      --display-name "$AD_ADI" \
      --metadata "{\"ssh_authorized_keys\":\"$SSH_ANAHTAR\"}" \
      --wait-for-state RUNNING --wait-interval-seconds 10 2>&1)"
    KOD=$?

    # ─── başarı
    if [ $KOD -eq 0 ] && printf '%s' "$CIKTI" | grep -q 'ocid1\.instance\.'; then
      ID="$(printf '%s' "$CIKTI" | grep -o 'ocid1\.instance\.[a-zA-Z0-9._-]*' | head -1)"
      IP="$(israrla compute instance list-vnics --instance-id "$ID" \
            --query 'data[0]."public-ip"' --raw-output)"
      printf '\a'
      command -v notify-send >/dev/null && notify-send "Midas" "A1 makinesi kuruldu: $IP" || true
      { echo; echo "════════════════════════════════════════════════════════"
        echo "  ✓ MAKİNE KURULDU  ($TUR. tur, $KAPASITE kapasite reddi sonrası)"
        echo "  Public IP : $IP"
        echo "  Shape     : $SHAPE  $OCPU OCPU / $RAM GB"
        echo "════════════════════════════════════════════════════════"; echo
      } | tee -a "$KAYIT"
      if [ -n "$IP" ] && [ -f .env ]; then
        sed -i "s|^MIDAS_SUNUCU=.*|MIDAS_SUNUCU=ubuntu@$IP|" .env
        yaz ".env güncellendi: MIDAS_SUNUCU=ubuntu@$IP"
      fi
      yaz "sıradaki: Security List'te 80/443'ü aç, sonra ./dagit.sh --ilk"
      exit 0
    fi

    # ─── kapasite yok: beklenen durum
    if printf '%s' "$CIKTI" | grep -qi "Out of host capacity\|out of capacity"; then
      KAPASITE=$((KAPASITE+1)); ARDISIK_GECICI=0
      printf '\r%s  tur %-5d kapasite yok (%d red)      ' "$(date '+%H:%M:%S')" "$TUR" "$KAPASITE"
      continue
    fi

    # ─── geçici: yayılma gecikmesi, hız sınırı, ağ. Yut ve devam et.
    if printf '%s' "$CIKTI" | grep -qiE "NotAuthenticated|TooManyRequests|429|503|ServiceUnavailable|InternalError|Timeout|Connection"; then
      GECICI=$((GECICI+1)); ARDISIK_GECICI=$((ARDISIK_GECICI+1))
      MESAJ="$(printf '%s' "$CIKTI" | sed -n 's/.*"message": "\(.*\)".*/\1/p' | head -1)"
      printf '\r%s  tur %-5d geçici hata (%d): %.40s   ' "$(date '+%H:%M:%S')" "$TUR" "$GECICI" "$MESAJ"
      printf '%s  geçici: %s\n' "$(date '+%H:%M:%S')" "${MESAJ:-bilinmeyen}" >> "$KAYIT"
      if [ "$ARDISIK_GECICI" -ge 15 ]; then
        echo; yaz "15 ardışık geçici hata — kimlik ayarlarında sorun olabilir, duruyorum"
        printf '%s\n' "$CIKTI" | head -15 >&2; exit 1
      fi
      sleep 20; continue
    fi

    # ─── gerçek engel
    echo
    { echo "════════════════════════════════════════════════════════"
      echo "  Kapasite dışı hata — betik duruyor:"
      printf '%s\n' "$CIKTI" | head -20
      echo "════════════════════════════════════════════════════════"
    } | tee -a "$KAYIT" >&2
    if printf '%s' "$CIKTI" | grep -qi "LimitExceeded\|QuotaExceeded"; then
      echo "  Ücretsiz kotan dolu olabilir: başka bir A1 makinen ya da" >&2
      echo "  silinmemiş bir boot volume duruyor mu, konsoldan bak." >&2
    fi
    exit 1
  done
  # Her 20 turda bir kayda nabız düş: saatlerce sessiz dönmesin.
  if [ $((TUR % 20)) -eq 0 ]; then
    printf '%s  tur %d — kapasite reddi %d, geçici hata %d\n' \
      "$(date '+%H:%M:%S')" "$TUR" "$KAPASITE" "$GECICI" >> "$KAYIT"
  fi
  sleep "$ARALIK"
done
