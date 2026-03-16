import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import structlog

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorAuthError, ConnectorFetchError, NormalizedAccount
from app.connectors.powens.client import PowensClient
from app.connectors.powens.normalizer import normalize_bank_account, normalize_wealth_account

logger = structlog.get_logger(__name__)

# Alerte DSP2 : 90 jours d'expiration
DSP2_EXPIRY_DAYS = 90
DSP2_ALERT_DAYS = 7  # Alerte si expiration dans moins de 7 jours


class PowensConnector(BaseConnector):
    SOURCE_NAME = "powens"
    SYNC_INTERVAL_SECONDS = 21600  # 6 heures

    def __init__(self) -> None:
        self._connection_created_at: Optional[datetime] = None

    def _get_client(self) -> PowensClient:
        return PowensClient(
            client_id=settings.powens_client_id,
            client_secret=settings.powens_client_secret,
            domain=settings.powens_domain,
            user_token=settings.powens_user_token,
        )

    async def authenticate(self) -> None:
        try:
            async with self._get_client() as client:
                await client.authenticate()
            self._connection_created_at = datetime.now(timezone.utc)
            self._check_dsp2_expiry()
            logger.info("powens_authenticated")
        except ConnectorAuthError:
            raise
        except Exception as e:
            raise ConnectorAuthError(f"Powens auth error: {e}") from e

    def _check_dsp2_expiry(self) -> None:
        if self._connection_created_at is None:
            return
        now = datetime.now(timezone.utc)
        delta = now - self._connection_created_at
        days_since = delta.days
        days_remaining = DSP2_EXPIRY_DAYS - days_since
        if days_remaining <= DSP2_ALERT_DAYS:
            logger.warning(
                "dsp2_expiry_soon",
                days_remaining=days_remaining,
                message=(
                    f"ATTENTION : La connexion Powens expire dans {days_remaining} jour(s). "
                    "Une ré-authentification forte via la Webview Powens est requise."
                ),
            )

    async def health_check(self) -> bool:
        try:
            async with self._get_client() as client:
                await client.authenticate()
                await client.get_user_info()
            return True
        except Exception:
            return False

    async def fetch_accounts(self) -> list[NormalizedAccount]:
        try:
            async with self._get_client() as client:
                await client.authenticate()

                bank_accounts, wealth_accounts = await asyncio.gather(
                    client.get_accounts(),
                    client.get_wealth_accounts(),
                )

                accounts: list[NormalizedAccount] = []

                # Comptes bancaires
                for account in bank_accounts:
                    try:
                        acc = normalize_bank_account(account)
                        accounts.append(acc)
                    except Exception as e:
                        logger.warning("powens_bank_account_error", account_id=account.get("id"), error=str(e))

                # Comptes patrimoine avec investissements
                invest_tasks = [client.get_investments(acc["id"]) for acc in wealth_accounts]
                investments_list = await asyncio.gather(*invest_tasks, return_exceptions=True)

                for account, investments in zip(wealth_accounts, investments_list):
                    try:
                        if isinstance(investments, Exception):
                            logger.warning(
                                "powens_wealth_investments_error",
                                account_id=account.get("id"),
                                error=str(investments),
                            )
                            investments = []
                        acc = normalize_wealth_account(account, investments)
                        accounts.append(acc)
                    except Exception as e:
                        logger.warning("powens_wealth_account_error", account_id=account.get("id"), error=str(e))

                logger.info("powens_fetched", count=len(accounts))
                return accounts

        except Exception as e:
            raise ConnectorFetchError(f"Powens fetch error: {e}") from e
