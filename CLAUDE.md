# CLAUDE.md — patrimoine-tracker

Monorepo : `asset-manager-backend` (FastAPI/async, PostgreSQL, Alembic) + `asset-manager-frontend-react` (Vite/React). Orchestré par `docker-compose.yml`. GitHub : `https://github.com/thbdoux/patrimoine-tracker` (branche `main`).

## Déploiement — instance OVH

Le prod tourne sur un VPS OVH via Docker Compose. Le repo y est cloné dans `~/patrimoine-tracker` et suit `origin/main`.

| Élément | Valeur |
|---|---|
| Host SSH (alias) | `OVH-instance` (dans `~/.ssh/config`) |
| IP publique | `51.38.234.74` (interface `ens3`) |
| IP Tailscale | `100.70.12.83` (tailnet `douxthibault@`, hostname `vps-adba7614`) |
| User | `thbdoux` |
| Path du projet | `~/patrimoine-tracker` |
| OS | Ubuntu, Docker + `docker compose` v2 (v5.1.0 CLI), Certbot, nginx |

### Se connecter

```bash
ssh OVH-instance                       # session interactive
ssh OVH-instance 'cd ~/patrimoine-tracker && <cmd>'   # commande one-shot
```

### Stack Docker (services)

`docker-compose.yml` à la racine du repo, 3 services :

- **db** — `postgres:16-alpine`. User/pass/db = `patrimoine` / `patrimoine` / `patrimoine_db`. Volume `pgdata`. Pas de port exposé sur l'hôte (réseau Docker interne `db:5432`).
- **backend** — build `./asset-manager-backend`. Lit `./asset-manager-backend/.env` (présent sur l'instance, **non versionné**). `DATABASE_URL` est surchargé dans le compose vers `postgresql+asyncpg://patrimoine:patrimoine@db:5432/patrimoine_db`. Commande de démarrage : `alembic upgrade head && python -m app.main` (les **migrations Alembic s'appliquent automatiquement au boot**). Exposé sur `0.0.0.0:8000`.
- **frontend** — build `./asset-manager-frontend-react`, nginx interne, exposé sur `0.0.0.0:3000` (→ port 80 du conteneur).

### Redéployer (après un push sur `main`)

Script versionné `deploy.sh` (racine du repo) : pull → build → recreate → attente santé → vérif migration → logs.

```bash
ssh OVH-instance 'cd ~/patrimoine-tracker && ./deploy.sh'
# Options : --no-pull (état local courant), --no-build (reload conf/env sans rebuild)
```

Équivalent manuel : `git pull && docker compose up -d --build`.

- Les **migrations Alembic tournent automatiquement** au démarrage du conteneur backend (`alembic upgrade head && python -m app.main`) ; pas d'étape séparée.
- Le volume `pgdata` est conservé (les données DB survivent au redéploiement).

### Commandes d'exploitation utiles

```bash
# État des conteneurs
ssh OVH-instance 'docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"'

# Logs
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose logs -f backend'
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose logs --tail=100 backend'

# Redémarrer un service sans rebuild
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose restart backend'

# Shell dans le backend / psql
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose exec backend sh'
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose exec db psql -U patrimoine -d patrimoine_db'

# Migrations manuelles (normalement auto au boot)
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose exec backend alembic upgrade head'
ssh OVH-instance 'cd ~/patrimoine-tracker && docker compose exec backend alembic current'

# Stats DB (script présent sur l'instance)
ssh OVH-instance 'cd ~/patrimoine-tracker/asset-manager-backend && ./db_stats.sh'
```

### Variables d'environnement / secrets

Le backend lit `asset-manager-backend/.env` sur l'instance (jamais commité). Pour ajouter/modifier un secret (clés Powens, Binance, Enable Banking, etc.) : éditer ce fichier sur l'instance puis `docker compose up -d backend` pour recréer le conteneur avec le nouvel env. Voir les clés attendues dans `asset-manager-backend/app/config.py`.

## Réseau & exposition (important pour les redirect URLs OAuth/PSD2)

nginx tourne sur l'hôte (pas dans Docker). Sites dans `/etc/nginx/sites-enabled/` :

- `patrimoine-tracker` → écoute **uniquement sur `100.70.12.83:80`** (IP Tailscale, privée), HTTP seul, proxy `/` → `127.0.0.1:3000` (frontend). **Aucune route vers le backend (8000)**, aucun HTTPS, aucun domaine public.
- `dou-social.fr` / `admin.dou-social.fr` → domaines publics avec SSL Let's Encrypt (Certbot, port 443). C'est le pattern de référence si on doit exposer patrimoine-tracker publiquement.
- Les ports `8000` (backend) et `3000` (frontend) sont bindés sur `0.0.0.0` côté Docker, donc joignables sur l'IP publique sans passer par nginx.

**Conséquence** : pour un callback PSD2/OAuth public en production (ex. Enable Banking), il faut d'abord créer un vhost nginx public + Certbot routant `/api/` → `backend:8000` (p.ex. `patrimoine.dou-social.fr`). Ça n'existe pas encore. Le frontend pointe par défaut sur `http://localhost:8000/api/v1` (`asset-manager-frontend-react/src/lib/api.ts`, surchargeable via `VITE_API_URL`).

## Connecteurs (architecture d'agrégation)

`asset-manager-backend/app/connectors/` : `BaseConnector` (`base.py`) + auto-découverte (`registry.py` scanne `*/connector.py`). Connecteurs actuels : `powens`, `binance`. Contrat unifié = `NormalizedAccount`. Sync planifié dans `app/scheduler/jobs.py` (1×/h par source). Pour ajouter une source : créer `app/connectors/<source>/{client,connector,normalizer}.py`, hériter de `BaseConnector`, définir `SOURCE_NAME` → découverte automatique, puis ajouter un job dans le scheduler.

> Migration Enable Banking en cours (support Trade Republic) — voir `asset-manager-backend/IMPLEMENTATION_NOTICE.md`.
