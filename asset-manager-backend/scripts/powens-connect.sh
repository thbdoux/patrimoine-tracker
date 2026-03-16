#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [[ -f "$ENV_FILE" ]]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

: "${POWENS_DOMAIN:?Variable POWENS_DOMAIN manquante}"
: "${POWENS_CLIENT_ID:?Variable POWENS_CLIENT_ID manquante}"
: "${POWENS_USER_TOKEN:?Variable POWENS_USER_TOKEN manquante}"

REDIRECT_URI="https://www.google.com"

echo "Génération du code temporaire..."

RESPONSE=$(curl -sf -X GET \
  "https://${POWENS_DOMAIN}/2.0/auth/token/code" \
  -H "Authorization: Bearer ${POWENS_USER_TOKEN}")

CODE=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['code'])")

URL="https://webview.powens.com/connect?domain=${POWENS_DOMAIN}&client_id=${POWENS_CLIENT_ID}&redirect_uri=${REDIRECT_URI}&code=${CODE}"

echo ""
echo "Ouvre cette URL dans ton navigateur (valide 30 min) :"
echo ""
echo "$URL"
echo ""

if command -v open &>/dev/null; then
  read -rp "Ouvrir automatiquement dans le navigateur ? [O/n] " REPLY
  if [[ "${REPLY:-O}" =~ ^[Oo]$ ]]; then
    open "$URL"
  fi
fi
