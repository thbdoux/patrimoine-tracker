import pytest
from unittest.mock import AsyncMock, MagicMock

from app.connectors.base import NormalizedAccount
from decimal import Decimal


@pytest.fixture
def mock_normalized_account() -> NormalizedAccount:
    return NormalizedAccount(
        external_id="spot_BTC",
        source="binance",
        account_type="crypto_spot",
        label="BTC Spot",
        currency="BTC",
        balance=Decimal("0.5"),
        balance_eur=Decimal("22500.0"),
        price_eur=Decimal("45000.0"),
        institution="Binance",
        iban=None,
        metadata={"asset": "BTC", "free": "0.3", "locked": "0.2"},
    )
