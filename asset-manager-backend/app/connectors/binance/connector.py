import asyncio
from decimal import Decimal
from typing import Optional

import structlog

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorAuthError, ConnectorFetchError, NormalizedAccount
from app.connectors.binance.client import BinanceClient
from app.connectors.binance.normalizer import DUST_THRESHOLD, normalize_earn, normalize_spot

logger = structlog.get_logger(__name__)

# Assets Binance avec un prix équivalent à un autre actif
PRICE_ALIAS: dict[str, str] = {
    "BETH": "ETH",   # Beacon ETH (staked ETH pre-merge) ≈ ETH
    "WBTC": "BTC",   # Wrapped BTC ≈ BTC
}


def _underlying_asset(asset: str) -> str:
    """
    Retourne l'asset sous-jacent pour la recherche de prix.
    - Les assets LD-préfixés (LDxx) sont des positions Simple Earn affichées
      en solde spot : on strip le 'LD' pour obtenir l'asset réel.
    - Certains assets ont un alias de prix (BETH→ETH, etc.)
    """
    if asset.startswith("LD") and len(asset) > 2:
        asset = asset[2:]
    return PRICE_ALIAS.get(asset, asset)


class BinanceConnector(BaseConnector):
    SOURCE_NAME = "binance"
    SYNC_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(self) -> None:
        self._client: Optional[BinanceClient] = None

    def _get_client(self) -> BinanceClient:
        return BinanceClient(
            api_key=settings.binance_api_key,
            api_secret=settings.binance_api_secret,
            testnet=settings.binance_testnet,
        )

    async def authenticate(self) -> None:
        try:
            async with self._get_client() as client:
                ok = await client.ping()
            if not ok:
                raise ConnectorAuthError("Binance ping failed")
            logger.info("binance_authenticated")
        except ConnectorAuthError:
            raise
        except Exception as e:
            raise ConnectorAuthError(f"Binance auth error: {e}") from e

    async def health_check(self) -> bool:
        try:
            async with self._get_client() as client:
                return await client.ping()
        except Exception:
            return False

    async def fetch_accounts(self) -> list[NormalizedAccount]:
        try:
            async with self._get_client() as client:
                account_data, earn_data = await asyncio.gather(
                    client.get_account(),
                    client.get_earn_flexible_positions(),
                )

                # Filtre les balances non-dust
                balances = [
                    b for b in account_data.get("balances", [])
                    if (Decimal(b["free"]) + Decimal(b["locked"])) >= DUST_THRESHOLD
                ]
                earn_positions = [
                    p for p in earn_data
                    if Decimal(p.get("totalAmount", "0")) >= DUST_THRESHOLD
                ]

                # Collecte les symboles USDT nécessaires pour le pricing
                # On strip le préfixe LD et on applique les alias pour les assets spéciaux
                pricing_symbols: set[str] = set()
                for b in balances:
                    underlying = _underlying_asset(b["asset"])
                    if underlying not in ("USDT", "EUR", "BUSD"):
                        pricing_symbols.add(f"{underlying}USDT")
                for p in earn_positions:
                    underlying = _underlying_asset(p.get("asset", ""))
                    if underlying not in ("USDT", "EUR", "BUSD"):
                        pricing_symbols.add(f"{underlying}USDT")

                # Récupère les prix + taux EUR/USDT
                prices_data, eurusdt_data = await asyncio.gather(
                    client.get_prices(list(pricing_symbols)) if pricing_symbols else _empty(),
                    client.get_price("EURUSDT"),
                )

                # Construit la price map : symbol → prix USDT
                price_map: dict[str, Decimal] = {}
                for p in (prices_data or []):
                    price_map[p["symbol"]] = Decimal(p["price"])

                eurusdt_rate = Decimal(eurusdt_data["price"]) if eurusdt_data else None

                accounts: list[NormalizedAccount] = []

                for b in balances:
                    asset = b["asset"]
                    free = Decimal(b["free"])
                    locked = Decimal(b["locked"])

                    underlying = _underlying_asset(asset)
                    if underlying == "USDT":
                        price_usdt = Decimal("1")
                    else:
                        price_usdt = price_map.get(f"{underlying}USDT")

                    # Les assets LD-préfixés sont des positions earn affichées en spot
                    is_ld_earn = asset.startswith("LD") and len(asset) > 2
                    if is_ld_earn:
                        acc = normalize_earn(asset, free + locked, price_usdt, eurusdt_rate, b)
                    else:
                        acc = normalize_spot(asset, free, locked, price_usdt, eurusdt_rate, b)
                    accounts.append(acc)

                for p in earn_positions:
                    asset = p.get("asset", "")
                    amount = Decimal(p.get("totalAmount", "0"))
                    underlying = _underlying_asset(asset)
                    price_usdt = Decimal("1") if underlying == "USDT" else price_map.get(f"{underlying}USDT")

                    acc = normalize_earn(asset, amount, price_usdt, eurusdt_rate, p)
                    accounts.append(acc)

                logger.info("binance_fetched", count=len(accounts))
                return accounts

        except Exception as e:
            raise ConnectorFetchError(f"Binance fetch error: {e}") from e


async def _empty() -> list:
    return []
