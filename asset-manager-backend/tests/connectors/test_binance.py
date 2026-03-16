from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.binance.normalizer import is_dust, normalize_earn, normalize_spot
from app.connectors.binance.connector import BinanceConnector
from app.connectors.base import ConnectorFetchError


# ── Normalizer tests ────────────────────────────────────────────────────────

class TestNormalizeSpot:
    def test_basic_btc(self):
        acc = normalize_spot(
            asset="BTC",
            free=Decimal("0.3"),
            locked=Decimal("0.2"),
            price_usdt=Decimal("50000"),
            eurusdt_rate=Decimal("1.1"),
            raw={"asset": "BTC", "free": "0.3", "locked": "0.2"},
        )
        assert acc.currency == "BTC"
        assert acc.balance == Decimal("0.5")
        assert acc.account_type == "crypto_spot"
        assert acc.source == "binance"
        assert acc.external_id == "spot_BTC"
        # price_eur = 50000 / 1.1 ≈ 45454.54
        assert acc.price_eur is not None
        assert abs(acc.price_eur - Decimal("50000") / Decimal("1.1")) < Decimal("0.01")
        assert acc.balance_eur is not None

    def test_usdt_account(self):
        acc = normalize_spot(
            asset="USDT",
            free=Decimal("1000"),
            locked=Decimal("0"),
            price_usdt=Decimal("1"),
            eurusdt_rate=Decimal("1.1"),
            raw={},
        )
        assert acc.balance == Decimal("1000")
        assert acc.balance_eur is not None
        assert abs(acc.balance_eur - Decimal("1000") / Decimal("1.1")) < Decimal("0.01")

    def test_no_price_gives_no_balance_eur(self):
        acc = normalize_spot(
            asset="BTC",
            free=Decimal("1"),
            locked=Decimal("0"),
            price_usdt=None,
            eurusdt_rate=Decimal("1.1"),
            raw={},
        )
        assert acc.balance_eur is None
        assert acc.price_eur is None

    def test_eur_account(self):
        acc = normalize_spot(
            asset="EUR",
            free=Decimal("500"),
            locked=Decimal("0"),
            price_usdt=None,
            eurusdt_rate=Decimal("1.1"),
            raw={},
        )
        assert acc.balance_eur == Decimal("500")
        assert acc.price_eur == Decimal("1")


class TestNormalizeEarn:
    def test_basic_earn(self):
        acc = normalize_earn(
            asset="ETH",
            amount=Decimal("2.0"),
            price_usdt=Decimal("3000"),
            eurusdt_rate=Decimal("1.1"),
            raw={"asset": "ETH", "totalAmount": "2.0"},
        )
        assert acc.account_type == "crypto_staking"
        assert acc.external_id == "earn_ETH"
        assert acc.balance == Decimal("2.0")
        assert acc.balance_eur is not None


class TestIsDust:
    def test_dust(self):
        assert is_dust(Decimal("0.000000001")) is True
        assert is_dust(Decimal("0.00000001")) is False
        assert is_dust(Decimal("0.1")) is False


# ── Connector integration tests ─────────────────────────────────────────────

class TestBinanceConnector:
    @pytest.fixture
    def mock_account_response(self):
        return {
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0.0"},
                {"asset": "ETH", "free": "2.0", "locked": "0.0"},
                {"asset": "DUST", "free": "0.000000001", "locked": "0.0"},  # dust — filtered
            ]
        }

    @pytest.fixture
    def mock_prices_response(self):
        return [
            {"symbol": "BTCUSDT", "price": "50000.00"},
            {"symbol": "ETHUSDT", "price": "3000.00"},
        ]

    @pytest.fixture
    def mock_eurusdt_response(self):
        return {"symbol": "EURUSDT", "price": "1.1"}

    @pytest.mark.asyncio
    async def test_fetch_accounts_filters_dust(
        self, mock_account_response, mock_prices_response, mock_eurusdt_response
    ):
        connector = BinanceConnector()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_account = AsyncMock(return_value=mock_account_response)
        mock_client.get_earn_flexible_positions = AsyncMock(return_value=[])
        mock_client.get_prices = AsyncMock(return_value=mock_prices_response)
        mock_client.get_price = AsyncMock(return_value=mock_eurusdt_response)

        with patch("app.connectors.binance.connector.BinanceClient", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        # DUST should be filtered out
        assets = [a.currency for a in accounts]
        assert "DUST" not in assets
        assert "BTC" in assets
        assert "ETH" in assets
        assert len(accounts) == 2

    @pytest.mark.asyncio
    async def test_fetch_accounts_includes_earn(
        self, mock_account_response, mock_prices_response, mock_eurusdt_response
    ):
        connector = BinanceConnector()
        earn_response = [
            {"asset": "BNB", "totalAmount": "10.0"},
        ]

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_account = AsyncMock(return_value={"balances": []})
        mock_client.get_earn_flexible_positions = AsyncMock(return_value=earn_response)
        mock_client.get_prices = AsyncMock(return_value=[{"symbol": "BNBUSDT", "price": "400.0"}])
        mock_client.get_price = AsyncMock(return_value=mock_eurusdt_response)

        with patch("app.connectors.binance.connector.BinanceClient", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        assert len(accounts) == 1
        assert accounts[0].account_type == "crypto_staking"
        assert accounts[0].currency == "BNB"

    @pytest.mark.asyncio
    async def test_fetch_accounts_raises_on_error(self):
        connector = BinanceConnector()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_account = AsyncMock(side_effect=Exception("Network error"))
        mock_client.get_earn_flexible_positions = AsyncMock(return_value=[])

        with patch("app.connectors.binance.connector.BinanceClient", return_value=mock_client):
            with pytest.raises(ConnectorFetchError):
                await connector.fetch_accounts()
