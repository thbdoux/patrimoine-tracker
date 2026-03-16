# Architecture — Patrimoine Tracker

## Ajouter un nouveau connecteur

Pour intégrer une nouvelle source de données (ex : Degiro, Boursorama, Interactive Brokers...) en 4 étapes :

### Étape 1 — Créer le dossier

```
app/connectors/<source_name>/
├── __init__.py
├── client.py       # HTTP client spécifique à la source
├── normalizer.py   # Mapping réponses → NormalizedAccount
└── connector.py    # Classe principale héritant de BaseConnector
```

### Étape 2 — Implémenter le connecteur

```python
# app/connectors/<source_name>/connector.py

from app.connectors.base import BaseConnector, NormalizedAccount

class MyConnector(BaseConnector):
    SOURCE_NAME = "<source_name>"          # Identifiant unique
    SYNC_INTERVAL_SECONDS = 21600          # Fréquence de sync (secondes)

    async def authenticate(self) -> None:
        # Initialise la connexion/token
        ...

    async def fetch_accounts(self) -> list[NormalizedAccount]:
        # Retourne tous les comptes normalisés
        ...

    async def health_check(self) -> bool:
        # Vérifie que la source est accessible
        ...
```

### Étape 3 — Le ConnectorRegistry découvre automatiquement

Le `ConnectorRegistry` scanne `app/connectors/*/connector.py` au démarrage et instancie toute classe héritant de `BaseConnector`. Aucune modification du code existant n'est nécessaire.

### Étape 4 — Ajouter les variables d'environnement

Ajouter les credentials dans `app/config.py` (Pydantic Settings) et `.env.example`.

---

## Modèle de données

```
accounts               → Registre des comptes (un par source/external_id)
account_snapshots      → Historique append-only des valorisations
sync_logs              → Traçabilité de chaque synchronisation
```

**Règle fondamentale** : `account_snapshots` ne reçoit jamais de UPDATE. Chaque sync insère de nouveaux snapshots, ce qui permet de reconstruire l'historique complet.

---

## Types de comptes acceptés

| Type | Description |
|------|-------------|
| `checking` | Compte courant |
| `savings` | Livret (A, LDDS, LEP...) |
| `loan` | Crédit |
| `pea` | Plan d'Épargne en Actions |
| `pee` | Plan d'Épargne Entreprise |
| `per` | Plan d'Épargne Retraite |
| `life_insurance` | Assurance vie |
| `brokerage` | Compte-titres ordinaire |
| `crypto_spot` | Crypto spot wallet |
| `crypto_staking` | Staking / earn |
| `other` | Autre |

---

## Scheduler

- **Powens** : sync toutes les 6h (contraintes DSP2)
- **Binance** : sync toutes les 5 minutes

Chaque job tourne avec `max_instances=1` + `coalesce=True` pour éviter les overlaps.

---

## Points d'attention

### Powens — Token DSP2
Le `USER_TOKEN` est obtenu **une seule fois** via la Webview Powens (processus OAuth interactif hors scope backend). Les connexions DSP2 expirent après **90 jours** : une alerte est loggée 7 jours avant.

### Binance — Clés API
Créer les clés avec **uniquement la permission "Read Info"** (sans trading, sans retrait). Tester d'abord avec `BINANCE_TESTNET=true`.
