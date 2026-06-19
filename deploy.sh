#!/usr/bin/env bash
#
# Déploiement patrimoine-tracker (à exécuter SUR l'instance, à la racine du repo).
#
#   ssh OVH-instance 'cd ~/patrimoine-tracker && ./deploy.sh'
#
# Étapes : git pull → build → recreate (les migrations Alembic tournent au
# démarrage du conteneur backend) → attente santé → vérif migration → logs.
#
# Options :
#   --no-pull     ne pas faire de git pull (déploie l'état local courant)
#   --no-build    ne pas rebuild les images (reload conf/env uniquement)
#
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DO_PULL=1
DO_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --no-pull)  DO_PULL=0 ;;
    --no-build) DO_BUILD=0 ;;
    *) echo "Option inconnue : $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;34m▶ %s\033[0m\n' "$1"; }

# Choix de la commande compose (v2 plugin vs v1 standalone)
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "docker compose introuvable" >&2; exit 1
fi

if [[ "$DO_PULL" == 1 ]]; then
  log "git pull (fast-forward only)"
  git pull --ff-only
fi

if [[ "$DO_BUILD" == 1 ]]; then
  log "Build des images"
  $COMPOSE build
fi

log "Démarrage / recréation des services (migrations Alembic au boot du backend)"
$COMPOSE up -d

log "Attente de la disponibilité du backend (http://localhost:8000)"
ok=0
for i in $(seq 1 30); do
  if curl -fsS -o /dev/null http://localhost:8000/openapi.json 2>/dev/null; then
    ok=1; break
  fi
  sleep 2
done
if [[ "$ok" != 1 ]]; then
  echo "❌ Backend non disponible après 60s. Logs récents :" >&2
  $COMPOSE logs --tail=50 backend >&2
  exit 1
fi

log "Version de migration appliquée"
$COMPOSE exec -T backend alembic current || true

log "État des conteneurs"
$COMPOSE ps

log "Logs récents du backend"
$COMPOSE logs --tail=20 backend

printf '\n\033[1;32m✓ Déploiement terminé\033[0m\n'
