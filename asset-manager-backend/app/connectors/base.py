from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class NormalizedAccount:
    """Représentation unifiée d'un compte, indépendante de la source."""

    external_id: str
    source: str
    account_type: str
    label: str
    currency: str
    balance: Decimal
    balance_eur: Optional[Decimal]
    price_eur: Optional[Decimal]
    institution: Optional[str]
    iban: Optional[str]
    metadata: dict


ACCOUNT_TYPES = {
    # Bancaires DSP2
    "checking",
    "savings",
    "loan",
    # Patrimoine
    "pea",
    "pee",
    "per",
    "life_insurance",
    "brokerage",
    # Crypto
    "crypto_spot",
    "crypto_staking",
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

    SOURCE_NAME: str = ""
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
