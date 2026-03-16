import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

logger = structlog.get_logger(__name__)

BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_TESTNET_URL = "https://testnet.binance.vision"


class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = BINANCE_TESTNET_URL if testnet else BINANCE_BASE_URL
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BinanceClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-MBX-APIKEY": self._api_key},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    async def _get(self, path: str, params: dict | None = None, signed: bool = False) -> Any:
        assert self._client is not None
        if params is None:
            params = {}
        if signed:
            params = self._sign(params)
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def ping(self) -> bool:
        try:
            await self._get("/api/v3/ping")
            return True
        except Exception:
            return False

    async def get_account(self) -> dict:
        return await self._get("/api/v3/account", signed=True)

    async def get_earn_flexible_positions(self) -> list[dict]:
        try:
            data = await self._get("/sapi/v1/earn/flexible/position", signed=True)
            if isinstance(data, dict):
                return data.get("rows", [])
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 404):
                # Endpoint non disponible sur testnet ou compte sans earn
                logger.warning("binance_earn_not_available", status=e.response.status_code)
                return []
            raise

    async def get_prices(self, symbols: list[str]) -> list[dict]:
        if not symbols:
            return []
        symbols_json = "[" + ",".join(f'"{s}"' for s in symbols) + "]"
        try:
            return await self._get("/api/v3/ticker/price", params={"symbols": symbols_json})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Un ou plusieurs symbols invalides → fallback en requêtes individuelles
                logger.warning("binance_bulk_price_failed_fallback", count=len(symbols))
                return await self._get_prices_individually(symbols)
            raise

    async def _get_prices_individually(self, symbols: list[str]) -> list[dict]:
        results = []
        for symbol in symbols:
            try:
                data = await self._get("/api/v3/ticker/price", params={"symbol": symbol})
                results.append(data)
            except httpx.HTTPStatusError:
                logger.debug("binance_symbol_price_unavailable", symbol=symbol)
        return results

    async def get_price(self, symbol: str) -> dict:
        return await self._get("/api/v3/ticker/price", params={"symbol": symbol})
