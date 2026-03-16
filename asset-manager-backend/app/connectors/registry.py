import importlib
import inspect
import logging
from pathlib import Path

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registre des connecteurs avec auto-découverte.
    Scanne app/connectors/*/connector.py et instancie les classes héritant de BaseConnector.
    """

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def discover(self) -> None:
        """Découvre et instancie automatiquement tous les connecteurs disponibles."""
        connectors_dir = Path(__file__).parent
        for connector_path in sorted(connectors_dir.glob("*/connector.py")):
            source_name = connector_path.parent.name
            module_path = f"app.connectors.{source_name}.connector"
            try:
                module = importlib.import_module(module_path)
                for _, cls in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(cls, BaseConnector)
                        and cls is not BaseConnector
                        and cls.SOURCE_NAME
                    ):
                        instance = cls()
                        self._connectors[cls.SOURCE_NAME] = instance
                        logger.info(f"Connecteur découvert : {cls.SOURCE_NAME}")
            except Exception as e:
                logger.warning(f"Impossible de charger le connecteur {source_name}: {e}")

    def get(self, source_name: str) -> BaseConnector:
        if source_name not in self._connectors:
            raise KeyError(f"Connecteur inconnu : {source_name}")
        return self._connectors[source_name]

    def all(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def source_names(self) -> list[str]:
        return list(self._connectors.keys())
