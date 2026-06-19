import asyncio
from typing import Optional

import structlog

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorAuthError, ConnectorFetchError, NormalizedAccount
from app.connectors.enablebanking.client import EnableBankingClient
from app.connectors.enablebanking.normalizer import normalize_account
from app.connectors.enablebanking.repository import CONSENT_ALERT_DAYS, days_remaining, get_active_sessions
from app.connectors.enablebanking.service import build_client
from app.database import get_session

logger = structlog.get_logger(__name__)


class EnableBankingConnector(BaseConnector):
    SOURCE_NAME = "enablebanking"
    SYNC_INTERVAL_SECONDS = 21600  # 6 heures

    def _get_client(self) -> EnableBankingClient:
        return build_client()

    @staticmethod
    def _is_configured() -> bool:
        """Vrai si l'App ID et une clé privée (inline ou chemin) sont fournis."""
        return bool(
            settings.enablebanking_app_id
            and (settings.enablebanking_private_key or settings.enablebanking_private_key_path)
        )

    async def authenticate(self) -> None:
        """
        Vérifie que la signature JWT fonctionne en interrogeant /application.
        Le consentement bancaire (session) est obtenu via le flux de redirection
        (endpoint /connect/enablebanking ou script scripts/enablebanking-connect.py).
        Si le connecteur n'est pas configuré, on ne fait rien (pas d'erreur).
        """
        if not self._is_configured():
            logger.info("enablebanking_not_configured")
            return
        try:
            async with self._get_client() as client:
                await client.get_application()
            logger.info("enablebanking_authenticated")
        except ConnectorAuthError:
            raise
        except Exception as e:
            raise ConnectorAuthError(f"Enable Banking auth error: {e}") from e

    async def health_check(self) -> bool:
        if not self._is_configured():
            return False
        try:
            async with self._get_client() as client:
                await client.get_application()
            return True
        except Exception:
            return False

    async def _list_consents(self) -> list[tuple[str, Optional[str]]]:
        """
        Retourne les consentements à synchroniser : (session_id, institution).
        Source primaire = sessions persistées en DB ; fallback = ENABLEBANKING_SESSION_ID
        (utile en sandbox/dev avant la mise en place du flux complet).
        """
        async with get_session() as db:
            sessions = await get_active_sessions(db)

        if sessions:
            consents: list[tuple[str, Optional[str]]] = []
            for s in sessions:
                remaining = days_remaining(s)
                if remaining is not None and remaining <= CONSENT_ALERT_DAYS:
                    logger.warning(
                        "enablebanking_consent_expiry_soon",
                        aspsp=s.aspsp_name,
                        days_remaining=remaining,
                        message=(
                            f"Le consentement {s.aspsp_name} expire dans {remaining} jour(s). "
                            "Une ré-authentification forte via le flux de redirection est requise."
                        ),
                    )
                consents.append((s.session_id, s.aspsp_name))
            return consents

        if settings.enablebanking_session_id:
            return [(settings.enablebanking_session_id, None)]

        return []

    async def _fetch_session_accounts(
        self, client: EnableBankingClient, session_id: str, institution: Optional[str]
    ) -> list[NormalizedAccount]:
        session = await client.get_session(session_id)
        aspsp = session.get("aspsp")
        institution = institution or (aspsp.get("name") if isinstance(aspsp, dict) else None)

        # GET /sessions ne renvoie que les UID ; les métadonnées sont sur /details
        uids = [
            (entry.get("uid") if isinstance(entry, dict) else str(entry))
            for entry in session.get("accounts", [])
        ]
        uids = [u for u in uids if u]

        # Pour chaque compte : détails (nom, type, IBAN) + soldes, en parallèle
        results = await asyncio.gather(
            *(
                asyncio.gather(
                    client.get_account_details(uid),
                    client.get_account_balances(uid),
                )
                for uid in uids
            ),
            return_exceptions=True,
        )

        accounts: list[NormalizedAccount] = []
        for uid, result in zip(uids, results):
            try:
                if isinstance(result, Exception):
                    logger.warning("enablebanking_account_error", account_uid=uid, error=str(result))
                    continue
                details, balances = result
                if institution and not details.get("aspsp"):
                    details = {**details, "aspsp": {"name": institution}}
                accounts.append(normalize_account(details, balances))
            except Exception as e:
                logger.warning("enablebanking_account_error", account_uid=uid, error=str(e))
        return accounts

    async def fetch_accounts(self) -> list[NormalizedAccount]:
        if not self._is_configured():
            logger.info("enablebanking_not_configured")
            return []
        consents = await self._list_consents()
        if not consents:
            # Aucune banque liée pour l'instant : sync "réussie" à 0 compte (pas une erreur)
            logger.info("enablebanking_no_active_session")
            return []
        try:
            async with self._get_client() as client:
                per_session = await asyncio.gather(
                    *(self._fetch_session_accounts(client, sid, inst) for sid, inst in consents),
                    return_exceptions=True,
                )

            accounts: list[NormalizedAccount] = []
            for (sid, _), result in zip(consents, per_session):
                if isinstance(result, Exception):
                    logger.warning("enablebanking_session_error", session_id=sid, error=str(result))
                    continue
                accounts.extend(result)

            logger.info("enablebanking_fetched", count=len(accounts))
            return accounts

        except ConnectorFetchError:
            raise
        except Exception as e:
            raise ConnectorFetchError(f"Enable Banking fetch error: {e}") from e
