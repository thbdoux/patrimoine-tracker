# Notice d'implémentation — Backend Patrimoine Tracker

> **Destinataire :** Claude Code  
> **Objectif :** Construire un backend Python qui agrège les données financières depuis Powens (banques françaises + patrimoine) et Binance (crypto), les stocke dans PostgreSQL avec historisation complète, et est conçu pour accueillir facilement de nouvelles sources de données.

---

## 1. Vue d'ensemble de l'architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SCHEDULER (APScheduler)               │
│   - sync toutes les 6h (banques)                        │
│   - sync toutes les 5min (crypto)                       │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │     CONNECTOR REGISTRY     │
         │  (découverte automatique)  │
         └──┬──────────────────┬──────┘
            │                  │
  ┌─────────▼──────┐  ┌────────▼────────┐  ┌─── (futur) ───┐
  │ PowensConnector│  │BinanceConnector │  │  NewConnector  │
  │  (Bank+Wealth) │  │  (spot+staking) │  │   (plug-in)    │
  └────────┬───────┘  └────────┬────────┘  └───────────────┘
           │                   │
           └─────────┬─────────┘
                     │
         ┌───────────▼───────────┐
         │   DATA NORMALIZER     │
         │  → modèle unifié      │
         │    AccountSnapshot    │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   PostgreSQL (async)  │
         │  - accounts           │
         │  - account_snapshots  │
         │  - sync_logs          │
         └───────────────────────┘
```

---

## 2. Stack technique

| Composant | Choix | Justification |
|---|---|---|
| Langage | Python 3.12 | Standard, bon écosystème fintech |
| Framework async | `asyncio` + `httpx` | Requêtes parallèles vers les API |
| ORM | SQLAlchemy 2.0 (async) | Migrations propres, support PostgreSQL natif |
| Migrations | Alembic | Versioning du schéma DB |
| Scheduler | APScheduler 4.x | Gestion des tâches récurrentes, async-native |
| Config | Pydantic Settings | Validation des variables d'environnement |
| Logs | `structlog` | Logs JSON structurés, idéal pour debugging |
| Tests | pytest + pytest-asyncio | Tests unitaires et d'intégration |
| Containerisation | Docker + docker-compose | PostgreSQL local + app |

---

## 3. Structure des fichiers

```
patrimoine-tracker/
│
├── docker-compose.yml              # PostgreSQL + app
├── .env.example                    # Template des variables d'env
├── pyproject.toml                  # Dépendances (uv ou pip)
├── alembic.ini
│
├── alembic/
│   └── versions/                   # Migrations DB
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # Point d'entrée, démarre le scheduler
│   ├── config.py                   # Pydantic Settings (variables d'env)
│   ├── database.py                 # Engine SQLAlchemy async, session factory
│   │
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── account.py              # Table accounts
│   │   ├── snapshot.py             # Table account_snapshots
│   │   └── sync_log.py             # Table sync_logs
│   │
│   ├── connectors/                 # ← Cœur extensible du système
│   │   ├── __init__.py
│   │   ├── base.py                 # Classe abstraite BaseConnector
│   │   ├── registry.py             # ConnectorRegistry (auto-découverte)
│   │   ├── powens/
│   │   │   ├── __init__.py
│   │   │   ├── connector.py        # PowensConnector (Bank + Wealth)
│   │   │   ├── client.py           # HTTP client Powens (auth, retry)
│   │   │   └── normalizer.py       # Mapping réponses Powens → modèle unifié
│   │   └── binance/
│   │       ├── __init__.py
│   │       ├── connector.py        # BinanceConnector
│   │       ├── client.py           # HTTP client Binance (HMAC signing)
│   │       └── normalizer.py       # Mapping réponses Binance → modèle unifié
│   │
│   ├── schemas/                    # Pydantic schemas (validation données)
│   │   ├── account.py
│   │   └── snapshot.py
│   │
│   ├── services/
│   │   ├── sync_service.py         # Orchestration d'une sync complète
│   │   └── snapshot_service.py     # Écriture des snapshots en DB
│   │
│   └── scheduler/
│       └── jobs.py                 # Définition des jobs APScheduler
│
└── tests/
    ├── conftest.py
    ├── connectors/
    │   ├── test_powens.py
    │   └── test_binance.py
    └── services/
        └── test_sync_service.py
```

---

## 4. Schéma de base de données

### Table `accounts`
Registre de tous les comptes connus. Un compte est créé la première fois qu'il est détecté, puis mis à jour.

```sql
CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     VARCHAR(255) NOT NULL,   -- ID chez la source (Powens account_id, Binance "BTC", etc.)
    source          VARCHAR(50) NOT NULL,    -- 'powens', 'binance', 'degiro'...
    account_type    VARCHAR(50) NOT NULL,    -- 'checking', 'savings', 'pea', 'pee', 'crypto_spot', 'life_insurance'...
    label           VARCHAR(255),            -- Nom lisible ("Compte courant BNP", "Bitcoin Spot")
    currency        VARCHAR(10),             -- 'EUR', 'BTC', 'USDT'...
    institution     VARCHAR(255),            -- 'BNP Paribas', 'Binance', 'Crédit Agricole'...
    iban            VARCHAR(50),             -- Optionnel, pour les comptes bancaires
    is_active       BOOLEAN DEFAULT TRUE,
    metadata        JSONB,                   -- Données brutes source spécifiques (ISIN, etc.)
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (external_id, source)
);
```

### Table `account_snapshots`
Historique des valorisations. **Jamais de UPDATE, uniquement des INSERT.** C'est le cœur du tracking.

```sql
CREATE TABLE account_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL REFERENCES accounts(id),
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- Moment de la capture
    balance         NUMERIC(20, 6) NOT NULL,             -- Valeur dans la devise du compte
    balance_eur     NUMERIC(20, 6),                      -- Valeur convertie en EUR (si dispo)
    price_eur       NUMERIC(20, 6),                      -- Prix unitaire en EUR (pour crypto/titres)
    raw_data        JSONB,                               -- Réponse brute de l'API (pour audit)
    
    -- Index pour les requêtes temporelles fréquentes
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_snapshots_account_captured ON account_snapshots (account_id, captured_at DESC);
CREATE INDEX idx_snapshots_captured_at ON account_snapshots (captured_at DESC);
```

### Table `sync_logs`
Traçabilité de chaque synchronisation (succès, erreurs, durée).

```sql
CREATE TABLE sync_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source          VARCHAR(50) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL,    -- 'running', 'success', 'partial', 'failed'
    accounts_synced INTEGER DEFAULT 0,
    error_message   TEXT,
    metadata        JSONB
);
```

---

## 5. Interface des connecteurs (contrat à respecter)

Tout nouveau connecteur **doit** hériter de `BaseConnector` et implémenter ces méthodes. C'est le seul fichier à lire pour ajouter une nouvelle source.

```python
# app/connectors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class NormalizedAccount:
    """Représentation unifiée d'un compte, indépendante de la source."""
    external_id: str
    source: str                  # 'powens', 'binance', 'degiro'...
    account_type: str            # Voir liste des types acceptés ci-dessous
    label: str
    currency: str
    balance: Decimal
    balance_eur: Optional[Decimal]
    price_eur: Optional[Decimal]  # Prix unitaire (crypto, action)
    institution: Optional[str]
    iban: Optional[str]
    metadata: dict               # Données brutes pour traçabilité


# Types de comptes acceptés (extensible)
ACCOUNT_TYPES = {
    # Bancaires DSP2
    "checking",       # Compte courant
    "savings",        # Livret (A, LDDS, LEP...)
    "loan",           # Crédit
    # Patrimoine
    "pea",            # Plan d'Épargne en Actions
    "pee",            # Plan d'Épargne Entreprise
    "per",            # Plan d'Épargne Retraite
    "life_insurance", # Assurance vie
    "brokerage",      # Compte titres ordinaire
    # Crypto
    "crypto_spot",    # Spot wallet
    "crypto_staking", # Staking/earn
    # Autres
    "other",
}


class BaseConnector(ABC):
    """
    Classe de base pour tous les connecteurs de sources de données.
    
    Pour ajouter une nouvelle source :
    1. Créer un dossier app/connectors/<source_name>/
    2. Créer connector.py avec une classe héritant de BaseConnector
    3. Implémenter les 3 méthodes abstraites
    4. Le ConnectorRegistry la découvrira automatiquement
    """

    SOURCE_NAME: str = ""  # À définir dans chaque sous-classe ex: "binance"
    SYNC_INTERVAL_SECONDS: int = 21600  # 6h par défaut

    @abstractmethod
    async def authenticate(self) -> None:
        """
        Initialise l'authentification avec la source.
        Appelé une fois au démarrage et si un token expire.
        Doit lever ConnectorAuthError en cas d'échec.
        """
        ...

    @abstractmethod
    async def fetch_accounts(self) -> list[NormalizedAccount]:
        """
        Récupère la liste de tous les comptes et leur solde actuel.
        Doit retourner une liste de NormalizedAccount.
        Doit lever ConnectorFetchError en cas d'erreur réseau/API.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Vérifie que la connexion à la source est opérationnelle.
        Retourne True si OK, False sinon.
        """
        ...


class ConnectorAuthError(Exception):
    """Erreur d'authentification avec la source."""
    pass


class ConnectorFetchError(Exception):
    """Erreur lors de la récupération des données."""
    pass
```

---

## 6. Implémentation des connecteurs

### 6.1 Powens Connector

**Variables d'environnement requises :**
```
POWENS_CLIENT_ID=
POWENS_CLIENT_SECRET=
POWENS_DOMAIN=              # ex: sandbox.biapi.pro ou votre domaine prod
POWENS_USER_TOKEN=          # Token utilisateur Powens (généré une fois via Webview)
```

**Comportement attendu :**
- Authentification via OAuth2 client credentials
- Appel à `GET /users/me/accounts` → Produit **Bank** (comptes courants, livrets, PEA...)
- Appel à `GET /users/me/accounts?type=investment` → Produit **Wealth** (PEE, assurance vie, PER...)
- Pour chaque compte wealth, appel à `GET /users/me/accounts/{id}/investments` pour obtenir la valorisation détaillée
- Rafraîchissement des données via `PUT /users/me/connections` si le cache Powens est > 6h
- Retry automatique sur 429 (rate limit) avec backoff exponentiel
- Mapping des types Powens → types normalisés :
  - `checking` → `checking`
  - `savings` → `savings`
  - `market` → `pea` ou `brokerage` selon le sous-type
  - `employee-savings` → `pee`
  - `retirement` → `per`
  - `life-insurance` → `life_insurance`

**Gestion du token Powens :**
Le token utilisateur Powens est obtenu une seule fois via la Webview (processus manuel, hors scope du backend). Stocker le token en variable d'environnement ou en DB chiffrée. Implémenter le refresh automatique si le token expire (endpoint `POST /auth/token/refresh`).

### 6.2 Binance Connector

**Variables d'environnement requises :**
```
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=false       # true pour les tests
```

**Comportement attendu :**
- Authentification HMAC-SHA256 sur chaque requête signée
- Appel à `GET /api/v3/account` → balances spot (filtrer `free + locked > 0`)
- Appel à `GET /sapi/v1/earn/flexible/position` → staking/earn flexible
- Appel à `GET /api/v3/ticker/price?symbols=[...]` → prix spot en USDT pour toutes les cryptos détenues
- Appel à `GET /api/v3/ticker/price?symbol=EURUSDT` → taux EUR/USDT pour conversion
- Calcul de `balance_eur = (free + locked) * price_usdt / eurusdt_rate`
- Sync toutes les **5 minutes** (override de `SYNC_INTERVAL_SECONDS = 300`)
- Filtrer les balances < 0.00000001 (dust)

---

## 7. Variables d'environnement complètes

Créer `.env` à partir de `.env.example` :

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://patrimoine:password@localhost:5432/patrimoine_db

# Powens
POWENS_CLIENT_ID=your_client_id
POWENS_CLIENT_SECRET=your_client_secret
POWENS_DOMAIN=sandbox.biapi.pro
POWENS_USER_TOKEN=your_user_token

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true

# App
LOG_LEVEL=INFO
SYNC_ON_STARTUP=true        # Lance une sync immédiate au démarrage
```

---

## 8. Service de synchronisation

```
SyncService.run_sync(source_name: str)
  │
  ├─ 1. Crée un SyncLog (status=running)
  ├─ 2. Appelle connector.authenticate() si nécessaire
  ├─ 3. Appelle connector.fetch_accounts()
  ├─ 4. Pour chaque NormalizedAccount :
  │     ├─ Upsert dans accounts (INSERT ON CONFLICT UPDATE)
  │     └─ INSERT dans account_snapshots
  ├─ 5. Met à jour SyncLog (status=success, accounts_synced=N)
  └─ 6. En cas d'exception : SyncLog (status=failed, error_message=...)
```

**Règles importantes :**
- La sync d'une source ne doit **jamais bloquer** la sync des autres sources
- Chaque sync tourne dans sa propre transaction DB
- Les erreurs sur un compte individuel ne doivent pas stopper la sync des autres comptes → logger l'erreur et continuer (`partial` status)
- Utiliser `asyncio.gather` pour paralléliser les appels API internes quand possible

---

## 9. Scheduler

```python
# app/scheduler/jobs.py
# Jobs à configurer :

# Powens — toutes les 6h (respecte les limites de re-auth DSP2 90 jours)
scheduler.add_job(
    sync_service.run_sync,
    trigger="interval",
    args=["powens"],
    hours=6,
    id="sync_powens",
    max_instances=1,          # Empêche les overlaps
    coalesce=True,
)

# Binance — toutes les 5 minutes
scheduler.add_job(
    sync_service.run_sync,
    trigger="interval",
    args=["binance"],
    minutes=5,
    id="sync_binance",
    max_instances=1,
    coalesce=True,
)
```

---

## 10. Docker Compose

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: patrimoine
      POSTGRES_PASSWORD: password
      POSTGRES_DB: patrimoine_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  app:
    build: .
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    command: python -m app.main

volumes:
  pgdata:
```

---

## 11. Ordre de construction recommandé pour Claude Code

Voici l'ordre optimal des tâches, du plus fondamental au plus applicatif :

### Phase 1 — Fondations
1. `pyproject.toml` avec toutes les dépendances
2. `docker-compose.yml`
3. `app/config.py` (Pydantic Settings)
4. `app/database.py` (engine async SQLAlchemy)
5. `app/models/` (3 tables ORM)
6. Migration Alembic initiale (`alembic init` + première version)

### Phase 2 — Connecteurs
7. `app/connectors/base.py` (BaseConnector, NormalizedAccount, exceptions)
8. `app/connectors/registry.py` (ConnectorRegistry avec auto-découverte par sous-dossiers)
9. `app/connectors/binance/client.py` (HTTP client HMAC)
10. `app/connectors/binance/normalizer.py`
11. `app/connectors/binance/connector.py`
12. Tests unitaires Binance (avec mocks httpx)
13. `app/connectors/powens/client.py` (HTTP client OAuth2)
14. `app/connectors/powens/normalizer.py`
15. `app/connectors/powens/connector.py`
16. Tests unitaires Powens

### Phase 3 — Orchestration
17. `app/services/snapshot_service.py` (upsert accounts + insert snapshots)
18. `app/services/sync_service.py` (orchestration + sync_logs)
19. `app/scheduler/jobs.py`
20. `app/main.py` (point d'entrée, démarre le scheduler)

### Phase 4 — Qualité
21. Tests d'intégration avec DB de test (pytest + fixture PostgreSQL)
22. `ARCHITECTURE.md` expliquant comment ajouter un nouveau connecteur
23. Script CLI `python -m app.main --sync-now powens` pour déclencher une sync manuelle

---

## 12. Règles de code à respecter

- **Typage strict** : toutes les fonctions publiques typées avec annotations Python 3.12
- **Pas de secrets dans le code** : tout via variables d'environnement
- **Async partout** : aucun appel bloquant dans les connecteurs (`httpx.AsyncClient`, pas `requests`)
- **Logs structurés** : utiliser `structlog` avec les champs `source`, `account_id`, `duration_ms` sur chaque opération significative
- **Decimal pour les montants** : jamais de `float` pour les valeurs financières
- **Idempotence** : une sync peut être rejouée sans créer de doublons (grâce au UNIQUE sur `accounts` et à l'INSERT pur sur `snapshots`)
- **`raw_data` dans les snapshots** : toujours stocker la réponse brute de l'API pour permettre le re-traitement futur sans rappel API

---

## 13. Points d'attention spécifiques

### Powens — Token utilisateur
Le `USER_TOKEN` Powens est obtenu une seule fois via la Webview interactive (processus OAuth hors scope). Pour le développement en sandbox, Powens fournit des tokens de test. Documenter clairement cette étape manuelle dans le README.

### Binance — Sécurité des clés API
Les clés Binance doivent être créées avec **uniquement la permission "Read Info"** (pas de trading, pas de retrait). Le documenter dans le README.

### DSP2 — Reconnexion périodique
Les connexions Powens (DSP2) expirent après **90 jours** et nécessitent une ré-authentification forte de l'utilisateur via la Webview. Implémenter une alerte dans les logs quand une connexion expire, avec le message exact à afficher.

### Taux de change
Pour la conversion en EUR des cryptos Binance, utiliser le prix Binance `EURUSDT` en temps réel. Pour les comptes Powens, la conversion EUR est déjà fournie par l'API pour les comptes en devise étrangère.
