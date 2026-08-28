#!/usr/bin/env bash
# Günlük işi her iş günü 19:00'da çalıştıracak şekilde kurar.
# systemd kullanıcı zamanlayıcısı tercih edilir (yeniden başlatmaya dayanır,
# günlüğü journald'a yazar). Yoksa cron'a düşer.
set -euo pipefail
KOK="$(cd "$(dirname "$0")" && pwd)"
SAAT="${SAAT:-19:00}"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/midas-gunluk.service <<SRV
[Unit]
Description=Midas Analist günlük iş
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$KOK
EnvironmentFile=-$KOK/.env
ExecStart=$KOK/gunluk.sh
SRV
  cat > ~/.config/systemd/user/midas-gunluk.timer <<TMR
[Unit]
Description=Midas Analist günlük iş zamanlayıcı (iş günleri $SAAT)

[Timer]
OnCalendar=Mon..Fri *-*-* $SAAT:00
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
TMR
  cat > ~/.config/systemd/user/midas-sabah.service <<SRV
[Unit]
Description=Midas Analist sabah emir hatırlatıcısı
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$KOK
EnvironmentFile=-$KOK/.env
ExecStart=$KOK/sabah.sh
SRV
  cat > ~/.config/systemd/user/midas-sabah.timer <<TMR
[Unit]
Description=Midas Analist sabah hatırlatıcı (iş günleri ${SABAH:-09:45})

[Timer]
OnCalendar=Mon..Fri *-*-* ${SABAH:-09:45}:00
# Persistent yok: kaçırılan sabah hatırlatması sonradan gönderilmemeli.
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
TMR
  systemctl --user daemon-reload
  systemctl --user enable --now midas-gunluk.timer
  systemctl --user enable --now midas-sabah.timer
  loginctl enable-linger "$USER" 2>/dev/null || true
  echo "✓ systemd zamanlayıcı kuruldu — akşam $SAAT, sabah ${SABAH:-09:45}"
  echo
  systemctl --user list-timers midas-gunluk.timer --no-pager 2>/dev/null | head -3
  echo
  echo "  Durum:      systemctl --user status midas-gunluk.timer"
  echo "  Elle çalış: systemctl --user start midas-gunluk.service"
  echo "  Kayıt:      tail -f $KOK/veri/gunluk.log"
  echo "  Kapat:      systemctl --user disable --now midas-gunluk.timer"
else
  SS="${SAAT%%:*}"; DK="${SAAT##*:}"
  SATIR="$DK $SS * * 1-5 $KOK/gunluk.sh"
  ( crontab -l 2>/dev/null | grep -v "midas.*gunluk.sh" ; echo "$SATIR" ) | crontab -
  echo "✓ cron kuruldu: $SATIR"
  echo "  Kontrol: crontab -l"
  echo "  Kayıt:   tail -f $KOK/veri/gunluk.log"
fi
