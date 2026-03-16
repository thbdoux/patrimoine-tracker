import asyncio
import time
from typing import Any, Optional

import httpx
import structlog

from app.connectors.base import ConnectorAuthError

logger = structlog.get_logger(__name__)


class PowensClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        domain: str,
        user_token: str,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._domain = domain
        self._user_token = user_token
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _base_url(self) -> str:
        return f"https://{self._domain}/2.0"

    async def __aenter__(self) -> "PowensClient":
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def authenticate(self) -> None:
        # Le user_token est un access token permanent, on l'utilise directement
        if not self._user_token:
            raise ConnectorAuthError("Powens auth failed: user_token is not configured")
        self._access_token = self._user_token
        self._token_expires_at = float("inf")
        logger.info("powens_authenticated")

    def _is_token_expired(self) -> bool:
        return time.time() >= self._token_expires_at

    async def _ensure_authenticated(self) -> None:
        if not self._access_token or self._is_token_expired():
            await self.authenticate()

    async def _get(self, path: str, params: dict | None = None, retries: int = 3) -> Any:
        assert self._client is not None
        await self._ensure_authenticated()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        for attempt in range(retries):
            try:
                response = await self._client.get(path, params=params, headers=headers)
                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("powens_rate_limited", attempt=attempt, wait=wait)
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    self._access_token = None
                    await self._ensure_authenticated()
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    continue
                raise
        raise RuntimeError(f"Max retries exceeded for {path}")

    async def _put(self, path: str) -> Any:
        assert self._client is not None
        await self._ensure_authenticated()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = await self._client.put(path, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_user_info(self) -> dict:
        return await self._get("/users/me")

    async def get_accounts(self) -> list[dict]:
        data = await self._get("/users/me/accounts")
        return data.get("accounts", [])

    async def get_wealth_accounts(self) -> list[dict]:
        data = await self._get("/users/me/accounts", params={"type": "investment"})
        return data.get("accounts", [])

    async def get_investments(self, account_id: int) -> list[dict]:
        data = await self._get(f"/users/me/accounts/{account_id}/investments")
        return data.get("investments", [])

    async def refresh_connections(self) -> None:
        try:
            await self._put("/users/me/connections")
        except Exception as e:
            logger.warning("powens_refresh_connections_failed", error=str(e))
