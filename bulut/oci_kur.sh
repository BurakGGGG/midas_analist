#!/usr/bin/env bash
# OCI CLI'yi kurar ve hesap erişimini ayarlar. Bir kereliktir.
# Sonrasında a1_kovala.sh kapasiteyi otomatik kovalayabilir.
set -euo pipefail

VENV="$HOME/.oci-cli-venv"

if [ ! -x "$VENV/bin/oci" ]; then
  echo "→ OCI CLI kuruluyor ($VENV)"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet oci-cli
else
  echo "✓ OCI CLI zaten kurulu"
fi

# PATH'e kalıcı olarak ekle (yeni kabuklarda da bulunsun).
if ! grep -q 'oci-cli-venv' "$HOME/.bashrc" 2>/dev/null; then
  echo "export PATH=\"\$HOME/.oci-cli-venv/bin:\$PATH\"" >> "$HOME/.bashrc"
  echo "→ PATH ~/.bashrc'ye eklendi"
fi
export PATH="$VENV/bin:$PATH"
echo "  sürüm: $(oci --version)"

if [ -f "$HOME/.oci/config" ]; then
  echo "✓ ~/.oci/config zaten var — yapılandırma atlanıyor"
else
  cat <<'BILGI'

────────────────────────────────────────────────────────
  Şimdi `oci setup config` çalışacak. Soracakları:

  1) Config konumu           → Enter (varsayılan)
  2) User OCID               → Oracle konsolu, sağ üst profil ikonu >
                               "User settings" (veya "My profile") >
                               sayfadaki OCID'yi kopyala
  3) Tenancy OCID            → Profil ikonu > "Tenancy: ..." > OCID
  4) Region                  → sağ üstteki bölge (örn. eu-frankfurt-1)
  5) API imzalama anahtarı   → "Y" (yeni üret)
  6) Anahtar dizini/adı      → Enter, Enter
  7) Parola                  → boş bırak, Enter
────────────────────────────────────────────────────────

BILGI
  read -rp "Hazırsan Enter'a bas..." _
  oci setup config
fi

ANAHTAR="$(ls -t "$HOME"/.oci/*_public.pem "$HOME"/.oci/oci_api_key_public.pem 2>/dev/null | head -1 || true)"
cat <<BILGI

────────────────────────────────────────────────────────
  SON ADIM — API anahtarını Oracle'a yükle:

  Konsol > sağ üst profil ikonu > User settings >
  sol altta "API keys" > "Add API key" >
  "Paste a public key" > aşağıdaki metni yapıştır > Add

BILGI
if [ -n "$ANAHTAR" ]; then
  echo "  ($ANAHTAR)"; echo
  cat "$ANAHTAR"
else
  echo "  Açık anahtar bulunamadı; ~/.oci/ içine bak."
fi
echo
echo "────────────────────────────────────────────────────────"
echo "  Yükledikten sonra doğrula:"
echo "    ~/.oci-cli-venv/bin/oci iam region list --output table | head -5"
echo "────────────────────────────────────────────────────────"
