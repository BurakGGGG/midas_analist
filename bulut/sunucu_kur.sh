#!/usr/bin/env bash
# Bulut sunucusunu kurar. SUNUCUDA çalışır, kendi PC'nde değil.
# Hedef: Ubuntu 24.04 (Oracle Cloud Always Free / ARM Ampere A1 ya da x86).
#
# dagit.sh --ilk bunu kendisi yükleyip çalıştırır; elle de çağırabilirsin:
#     ssh ubuntu@SUNUCU 'bash ~/midas/bulut/sunucu_kur.sh'
#
# Betik yeniden çalıştırılabilir: her adım "zaten varsa dokunma" mantığında.
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# iptables-persistent kurulumu debconf penceresi açar; bu olmadan betik
# etkileşimsiz bir SSH oturumunda sessizce asılı kalır.
export DEBIAN_FRONTEND=noninteractive
KULLANICI="$(id -un)"

if [ "$KULLANICI" = "root" ]; then
  echo "Bu betiği root olarak değil, normal kullanıcı (ubuntu) olarak çalıştır." >&2
  exit 1
fi

echo "════════════════════════════════════════════════════════"
echo "  Midas Analist — bulut sunucu kurulumu"
echo "  Dizin: $KOK   Kullanıcı: $KULLANICI"
echo "════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────── 1) saat dilimi
# EN KRİTİK ADIM. Kod her yerde çıplak date.today() kullanıyor
# (cekirdek/gunluk.py, cekirdek/ambar.py). Sunucu UTC kalırsa 18:10 işi
# Türkiye saatiyle 21:10'da çalışır ve gün kaydı yanlış tarihe yazılır.
MEVCUT_TZ="$(timedatectl show -p Timezone --value 2>/dev/null || echo bilinmiyor)"
if [ "$MEVCUT_TZ" != "Europe/Istanbul" ]; then
  echo "→ saat dilimi: $MEVCUT_TZ → Europe/Istanbul"
  sudo timedatectl set-timezone Europe/Istanbul
else
  echo "✓ saat dilimi zaten Europe/Istanbul"
fi
echo "  şu an: $(date '+%Y-%m-%d %H:%M:%S %Z')"

# ─────────────────────────────────────────────── 2) sistem paketleri
echo "→ sistem paketleri"
sudo apt-get update -qq
# python3-dev/build-essential: aarch64 tekerleği bulunmayan bir paket
# çıkarsa kaynaktan derleyebilsin diye. libxml2/libxslt: lxml için.
sudo apt-get install -y -qq --no-install-recommends \
  python3-venv python3-dev build-essential curl rsync \
  libxml2-dev libxslt1-dev ca-certificates

# ─────────────────────────────────────────────── 2b) takas alanı
# Ücretsiz x86 shape'inde (E2.1.Micro) yalnızca 1 GB RAM var. Takas alanı
# olmadan iki yer patlar: pip'in scipy/pandas tekerleklerini açması ve
# 100 hisselik önbellek ısıtması. Oracle imajları takas alanısız gelir.
BELLEK_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
TAKAS_MB=$(awk '/SwapTotal/{print int($2/1024)}' /proc/meminfo)
if [ "$BELLEK_MB" -lt 4000 ] && [ "$TAKAS_MB" -lt 1000 ]; then
  echo "→ takas alanı açılıyor (RAM ${BELLEK_MB} MB, mevcut takas ${TAKAS_MB} MB)"
  sudo fallocate -l 4G /takas 2>/dev/null || sudo dd if=/dev/zero of=/takas bs=1M count=4096 status=none
  sudo chmod 600 /takas
  sudo mkswap /takas >/dev/null
  sudo swapon /takas
  grep -q '^/takas' /etc/fstab || echo '/takas none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  # Az RAM'de erken takas kullanımı OOM'dan iyidir.
  echo 'vm.swappiness=30' | sudo tee /etc/sysctl.d/99-midas.conf >/dev/null
  sudo sysctl -q -p /etc/sysctl.d/99-midas.conf
  echo "  takas: $(free -h | awk '/Swap/{print $2}')"
else
  echo "✓ takas alanı gerekmiyor (RAM ${BELLEK_MB} MB, takas ${TAKAS_MB} MB)"
fi

# ─────────────────────────────────────────────── 3) python ortamı
if [ ! -x "$KOK/.venv/bin/python" ]; then
  echo "→ sanal ortam kuruluyor"
  python3 -m venv "$KOK/.venv"
fi
echo "→ python bağımlılıkları (ilk seferde birkaç dakika sürer)"
"$KOK/.venv/bin/pip" install --quiet --no-cache-dir --upgrade pip
"$KOK/.venv/bin/pip" install --quiet --no-cache-dir -r "$KOK/requirements.txt"

# scikit-learn sessiz tuzağı: yoksa yfinance repair=True toplu indirmede
# boş döner ve sahte çöküşler üretir. Kurulumu burada doğrula.
"$KOK/.venv/bin/python" - <<'PY'
import importlib.util, sys   # importlib tek başına .util'i getirmez
eksik = [m for m in ("sklearn", "scipy", "yfinance", "fastapi", "uvicorn")
         if not importlib.util.find_spec(m)]
if eksik:
    print("EKSİK PAKET:", ", ".join(eksik), file=sys.stderr); sys.exit(1)
print("✓ paketler yerinde (sklearn dahil)")
PY

# ─────────────────────────────────────────────── 4) .env
if [ ! -f "$KOK/.env" ]; then
  echo "! .env yok. dagit.sh --ilk bunu göndermeliydi." >&2
  echo "  Bulutta MIDAS_API_ANAHTARI ZORUNLU — anahtarsız API herkese açık olur." >&2
  exit 1
fi
chmod 600 "$KOK/.env"
if ! grep -qE '^MIDAS_API_ANAHTARI=.+' "$KOK/.env"; then
  echo "! .env içindeki MIDAS_API_ANAHTARI boş." >&2
  echo "  Anahtarsız açılan bir bulut API'si herkese açıktır. Kurulum durdu." >&2
  exit 1
fi
echo "✓ .env yerinde, API anahtarı dolu"

mkdir -p "$KOK/veri/temel"

# ─────────────────────────────────────────────── 5) systemd birimleri
# Kullanıcı birimi DEĞİL sistem birimi: sunucuda oturum açmıyoruz,
# makine yeniden başladığında da kendiliğinden kalkması gerekiyor.
echo "→ systemd birimleri"

sudo tee /etc/systemd/system/midas-api.service >/dev/null <<SRV
[Unit]
Description=Midas Analist API
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=$KULLANICI
WorkingDirectory=$KOK
EnvironmentFile=$KOK/.env
# Yalnızca 127.0.0.1'e bağlan: dışarıya Caddy TLS ile açıyor.
# 0.0.0.0 olsaydı 8000 portu şifresiz de erişilebilir kalırdı.
ExecStart=$KOK/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SRV

sudo tee /etc/systemd/system/midas-gunluk.service >/dev/null <<SRV
[Unit]
Description=Midas Analist günlük iş
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$KULLANICI
WorkingDirectory=$KOK
EnvironmentFile=$KOK/.env
ExecStart=$KOK/gunluk.sh
SRV

# BIST 18:00'de kapanır, iş 18:10'da çalışır. Sunucu saati 1. adımda
# Europe/Istanbul yapıldı; OnCalendar de yerel saati kullanır.
sudo tee /etc/systemd/system/midas-gunluk.timer >/dev/null <<TMR
[Unit]
Description=Midas Analist günlük iş zamanlayıcı (iş günleri 18:10)

[Timer]
OnCalendar=Mon..Fri *-*-* 18:10:00
# Sunucu o an kapalıysa (bakım, yeniden başlatma) açılışta telafi et.
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
TMR


# Sabah emir hatırlatıcısı. Sinyal akşam üretilir, işlem ertesi sabah
# AÇILIŞTA yapılır — arada 16 saat vardır ve kimse hatırlatmıyordu.
# 09:45: sürekli işlem 10:00'da başlıyor, mesajı görüp emri yetiştirecek
# kadar erken. Yeni analiz yapmaz, ambardaki kaydı okur; saniyeler sürer.
sudo tee /etc/systemd/system/midas-sabah.service >/dev/null <<SRV
[Unit]
Description=Midas Analist sabah emir hatırlatıcısı
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$KULLANICI
WorkingDirectory=$KOK
EnvironmentFile=$KOK/.env
ExecStart=$KOK/sabah.sh
SRV

sudo tee /etc/systemd/system/midas-sabah.timer >/dev/null <<TMR
[Unit]
Description=Midas Analist sabah hatırlatıcı (iş günleri 09:45)

[Timer]
OnCalendar=Mon..Fri *-*-* 09:45:00
# Persistent BİLEREK yok: kaçırılan sabah hatırlatması sonradan
# gönderilmemeli. Öğlen gelen "bugün açılışta şunu al" mesajı yanlış
# bilgidir — açılış çoktan geçmiştir.
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
TMR

# Telegram botu: gelen komutları işler ve seans içinde stop/hedef kontrolü
# yapar. 5 dakikada bir çalışır — sürekli açık bir süreç değil, çökerse
# bir sonraki turda kendiliğinden toparlanır.
#
# Yapılandırma yoksa betik çıkış kodu 1 ile biter; timer bunu sorun
# saymaz, sadece hiçbir şey yapmaz. Yani Telegram kurulmadan da sistem
# tam çalışır.
sudo tee /etc/systemd/system/midas-bot.service >/dev/null <<SRV
[Unit]
Description=Midas Telegram botu
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$KULLANICI
WorkingDirectory=$KOK
EnvironmentFile=$KOK/.env
ExecStart=$KOK/.venv/bin/python -m cekirdek.bot_calistir
SRV

sudo tee /etc/systemd/system/midas-bot.timer >/dev/null <<TMR
[Unit]
Description=Midas Telegram botu (1 dakikada bir)

[Timer]
OnBootSec=2min
# 1 dakika + betikteki 45 sn uzun yoklama = komut neredeyse anında
# cevaplanır. Tur 0,01 sn'de açılıyor, maliyeti yok.
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
TMR

sudo systemctl daemon-reload
sudo systemctl enable --now midas-api.service
sudo systemctl enable --now midas-gunluk.timer
sudo systemctl enable --now midas-sabah.timer
sudo systemctl enable --now midas-bot.timer

# ─────────────────────────────────────────────── 6) Caddy + HTTPS
# Telefon halka açık internetten bağlanacak. Düz HTTP olsaydı API anahtarın
# ve tüm portföy verin açık metin gider; ayrıca Android 9+ release yapısı
# şifresiz HTTP'yi zaten engeller.
#
# Alan adı satın almaya gerek yok: sslip.io herhangi bir IP'yi ad olarak
# çözer (1-2-3-4.sslip.io -> 1.2.3.4), Let's Encrypt de bu ada gerçek
# sertifika verir.
if ! command -v caddy >/dev/null 2>&1; then
  echo "→ Caddy kuruluyor"
  sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
  curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq caddy
fi

GENEL_IP="${MIDAS_GENEL_IP:-$(curl -fsS --max-time 10 https://api.ipify.org || true)}"
if [ -z "$GENEL_IP" ]; then
  echo "! Genel IP saptanamadı. MIDAS_GENEL_IP=1.2.3.4 ile tekrar çalıştır." >&2
  exit 1
fi
ALAN="${GENEL_IP//./-}.sslip.io"

sudo tee /etc/caddy/Caddyfile >/dev/null <<CADDY
# Sertifikayı Caddy kendi alır ve yeniler. 80/443 dışarıya açık olmalı.
$ALAN {
	reverse_proxy 127.0.0.1:8000
}
CADDY
sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy

# ─────────────────────────────────────────────── 7) güvenlik duvarı
# Oracle Ubuntu imajları 22 dışındaki her portu kapatan iptables kuralları
# ile gelir. Bu, insanların "Security List'i açtım ama yine bağlanamıyorum"
# diye takıldığı klasik yer — iki katman var, ikisi de açılmalı.
echo "→ güvenlik duvarı (sunucu içi)"
for PORT in 80 443; do
  if sudo iptables -C INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null; then
    echo "  $PORT zaten açık"
    continue
  fi
  # Zincirin EN ÜSTÜNE ekle. Oracle imajı INPUT'un sonuna bir REJECT koyar;
  # kuralı ortaya sokmaya çalışmak zincir düzeni değişirse REJECT'in altına
  # düşürür ve port sessizce kapalı kalır.
  sudo iptables -I INPUT 1 -p tcp --dport $PORT -j ACCEPT
  echo "  $PORT açıldı"
done
sudo apt-get install -y -qq iptables-persistent >/dev/null 2>&1 || true
sudo netfilter-persistent save >/dev/null 2>&1 || true

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Kurulum bitti."
echo ""
echo "  Adres  : https://$ALAN"
echo "  Sağlık : curl https://$ALAN/saglik"
echo ""
echo "  API    : systemctl status midas-api"
echo "  Zaman  : systemctl list-timers 'midas-*'"
echo "  Kayıt  : tail -f $KOK/veri/gunluk.log"
echo ""
echo "  Oracle konsolunda Security List'te 80 ve 443 açık DEĞİLSE"
echo "  yukarıdaki adres dışarıdan yanıt vermez."
echo "════════════════════════════════════════════════════════"
