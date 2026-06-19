import asyncio
import time
from pathlib import Path
from typing import Any, Optional

import httpx
import jwt
import structlog

from app.connectors.base import ConnectorAuthError

logger = structlog.get_logger(__name__)

# Durée de validité du JWT d'authentification (Enable Banking impose <= 1h)
JWT_TTL_SECONDS = 3600
JWT_ISS = "enablebanking.com"
JWT_AUD = "api.enablebanking.com"


class EnableBankingClient:
    """
    Client HTTP pour l'API Enable Banking (agrégation PSD2).

    Authentification : chaque appel porte un JWT signé RS256 avec la clé privée
    de l'application. Le header `kid` contient l'Application ID. Le JWT est
    régénéré quand il approche de son expiration.

    Docs : https://enablebanking.com/docs/api/reference/
    """

    def __init__(
        self,
        app_id: str,
        private_key_pem: str,
        base_url: str = "https://api.enablebanking.com",
    ) -> None:
        self._app_id = app_id
        self._private_key_pem = private_key_pem
        self._base_url = base_url.rstrip("/")
        self._jwt: Optional[str] = None
        self._jwt_expires_at: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def load_private_key(*, inline: str = "", path: str = "") -> str:
        """
        Retourne le PEM de la clé privée. Le contenu inline est prioritaire ;
        sinon on lit le fichier `path`. Lève ConnectorAuthError si introuvable.
        """
        if inline.strip():
            return inline
        if path.strip():
            key_file = Path(path).expanduser()
            if not key_file.is_file():
                raise ConnectorAuthError(f"Enable Banking private key not found at {key_file}")
            return key_file.read_text()
        raise ConnectorAuthError("Enable Banking private key is not configured")

    async def __aenter__(self) -> "EnableBankingClient":
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _build_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iss": JWT_ISS,
            "aud": JWT_AUD,
            "iat": now,
            "exp": now + JWT_TTL_SECONDS,
        }
        headers = {"typ": "JWT", "alg": "RS256", "kid": self._app_id}
        try:
            return jwt.encode(payload, self._private_key_pem, algorithm="RS256", headers=headers)
        except Exception as e:
            raise ConnectorAuthError(f"Enable Banking JWT signing failed: {e}") from e

    def _ensure_jwt(self) -> str:
        # Régénère 60s avant l'expiration pour éviter les courses
        if not self._jwt or time.time() >= (self._jwt_expires_at - 60):
            if not self._app_id:
                raise ConnectorAuthError("Enable Banking app_id is not configured")
            self._jwt = self._build_jwt()
            self._jwt_expires_at = time.time() + JWT_TTL_SECONDS
        return self._jwt

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._ensure_jwt()}"}

    async def _request(self, method: str, path: str, *, json: dict | None = None, retries: int = 3) -> Any:
        assert self._client is not None
        for attempt in range(retries):
            response = await self._client.request(method, path, json=json, headers=self._headers())
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning("enablebanking_rate_limited", attempt=attempt, wait=wait)
                await asyncio.sleep(wait)
                continue
            if response.status_code == 401:
                # JWT possiblement expiré : on le force à régénérer puis on retente une fois
                self._jwt = None
                if attempt == 0:
                    continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError(f"Max retries exceeded for {method} {path}")

    async def _get(self, path: str) -> Any:
        return await self._request("GET", path)

    async def _post(self, path: str, json: dict) -> Any:
        return await self._request("POST", path, json=json)

    # ── Application / santé ──────────────────────────────────────────────────

    async def get_application(self) -> dict:
        """Détails de l'application (ASPSP autorisés, redirect_urls). Sert de health-check."""
        return await self._get("/application")

    async def get_aspsps(self, country: Optional[str] = None) -> list[dict]:
        """Liste des banques (ASPSP) disponibles, filtrable par pays ISO (ex: 'DE')."""
        path = "/aspsps" + (f"?country={country}" if country else "")
        data = await self._get(path)
        return data.get("aspsps", [])

    # ── Flux de consentement ─────────────────────────────────────────────────

    async def start_authorization(
        self,
        *,
        aspsp_name: str,
        aspsp_country: str,
        redirect_url: str,
        valid_until: str,
        state: str = "",
        psu_type: str = "personal",
    ) -> dict:
        """
        Démarre une autorisation. Retourne `{url, authorization_id, ...}`.
        L'utilisateur ouvre `url`, consent côté banque, puis est redirigé vers
        `redirect_url?code=...&state=...`.
        """
        body = {
            "access": {"valid_until": valid_until},
            "aspsp": {"name": aspsp_name, "country": aspsp_country},
            "state": state,
            "redirect_url": redirect_url,
            "psu_type": psu_type,
        }
        return await self._post("/auth", body)

    async def create_session(self, code: str) -> dict:
        """Échange le `code` de redirection contre une session. Retourne `{session_id, accounts, aspsp, ...}`."""
        return await self._post("/sessions", {"code": code})

    async def get_session(self, session_id: str) -> dict:
        """État d'une session existante, incluant la liste des comptes."""
        return await self._get(f"/sessions/{session_id}")

    # ── Données comptes ──────────────────────────────────────────────────────

    async def get_account_details(self, account_uid: str) -> dict:
        """Métadonnées du compte : name, cash_account_type, currency, account_id (IBAN)..."""
        return await self._get(f"/accounts/{account_uid}/details")

    async def get_account_balances(self, account_uid: str) -> list[dict]:
        data = await self._get(f"/accounts/{account_uid}/balances")
        return data.get("balances", [])
