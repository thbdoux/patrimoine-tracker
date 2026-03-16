#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [[ -f "$ENV_FILE" ]]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

: "${POWENS_DOMAIN:?Variable POWENS_DOMAIN manquante}"
: "${POWENS_USER_TOKEN:?Variable POWENS_USER_TOKEN manquante}"

curl -sf -X GET \
  "https://${POWENS_DOMAIN}/2.0/users/me/connections?expand=accounts" \
  -H "Authorization: Bearer ${POWENS_USER_TOKEN}" \
| python3 -c "
import json, sys

data = json.load(sys.stdin)
connections = data.get('connections', [])

if not connections:
    print('Aucune connexion trouvée.')
    sys.exit(0)

print(f'{len(connections)} connexion(s) trouvée(s)\n')

for conn in connections:
    state = conn['state'] or 'OK'
    accounts = conn.get('accounts', [])
    total = sum(a['balance'] for a in accounts if a['balance'] is not None)
    print(f\"── Connexion #{conn['id']}  bank_id={conn['id_connector']}  état={state}\")
    for acc in accounts:
        balance = f\"{acc['balance']:>10.2f} EUR\" if acc['balance'] is not None else '           N/A'
        print(f\"   [{acc['id']:>3}] {acc['name']:<40} {acc['type']:<12} {balance}\")
    print(f\"   {'TOTAL':<45} {total:>10.2f} EUR\")
    print()
"
