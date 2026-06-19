from app.config import settings
from app.connectors.enablebanking.client import EnableBankingClient


def build_client() -> EnableBankingClient:
    """Construit un client Enable Banking à partir de la configuration."""
    private_key = EnableBankingClient.load_private_key(
        inline=settings.enablebanking_private_key,
        path=settings.enablebanking_private_key_path,
    )
    return EnableBankingClient(
        app_id=settings.enablebanking_app_id,
        private_key_pem=private_key,
        base_url=settings.enablebanking_base_url,
    )
