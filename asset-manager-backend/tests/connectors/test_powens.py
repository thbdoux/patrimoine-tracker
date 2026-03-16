from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.powens.normalizer import _map_type, normalize_bank_account, normalize_wealth_account
from app.connectors.powens.connector import PowensConnector
from app.connectors.base import ConnectorFetchError


# ── Normalizer tests ────────────────────────────────────────────────────────

class TestTypeMapping:
    def test_known_types(self):
        assert _map_type("checking") == "checking"
        assert _map_type("savings") == "savings"
        assert _map_type("employee-savings") == "pee"
        assert _map_type("retirement") == "per"
        assert _map_type("life-insurance") == "life_insurance"
        assert _map_type("pea") == "pea"

    def test_market_with_pea_name(self):
        assert _map_type("market", "Mon PEA BNP") == "pea"

    def test_market_without_pea_name(self):
        assert _map_type("market", "Compte Titres") == "brokerage"

    def test_unknown_type(self):
        assert _map_type("unknown_type") == "other"


class TestNormalizeBankAccount:
    def test_checking_account(self):
        account = {
            "id": 123,
            "name": "Compte courant",
            "type": "checking",
            "balance": 1500.50,
            "balance_eur": 1500.50,
            "currency": {"id": "EUR"},
            "iban": "FR7612345678901234567890189",
            "company_name": "BNP Paribas",
        }
        acc = normalize_bank_account(account)
        assert acc.external_id == "123"
        assert acc.account_type == "checking"
        assert acc.balance == Decimal("1500.50")
        assert acc.currency == "EUR"
        assert acc.iban == "FR7612345678901234567890189"
        assert acc.institution == "BNP Paribas"
        assert acc.source == "powens"

    def test_savings_account(self):
        account = {
            "id": 456,
            "name": "Livret A",
            "type": "savings",
            "balance": 10000,
            "balance_eur": 10000,
            "currency": {"id": "EUR"},
            "iban": None,
            "company_name": "Crédit Agricole",
        }
        acc = normalize_bank_account(account)
        assert acc.account_type == "savings"
        assert acc.balance == Decimal("10000")


class TestNormalizeWealthAccount:
    def test_pee_with_investments(self):
        account = {
            "id": 789,
            "name": "Plan Épargne Entreprise",
            "type": "employee-savings",
            "balance": 5000,
            "currency": {"id": "EUR"},
            "company_name": "Amundi",
        }
        investments = [
            {"id": 1, "label": "FCPE A", "valuation": 3000},
            {"id": 2, "label": "FCPE B", "valuation": 2500},
        ]
        acc = normalize_wealth_account(account, investments)
        assert acc.account_type == "pee"
        assert acc.balance == Decimal("5500")  # 3000 + 2500
        assert acc.balance_eur == Decimal("5500")

    def test_life_insurance_no_investments(self):
        account = {
            "id": 101,
            "name": "Assurance Vie",
            "type": "life-insurance",
            "balance": 20000,
            "currency": {"id": "EUR"},
            "company_name": "AXA",
        }
        acc = normalize_wealth_account(account, [])
        assert acc.account_type == "life_insurance"
        # Falls back to account balance
        assert acc.balance == Decimal("20000")


# ── Connector integration tests ─────────────────────────────────────────────

class TestPowensConnector:
    @pytest.fixture
    def mock_bank_accounts(self):
        return [
            {"id": 1, "name": "Compte courant", "type": "checking", "balance": 1000, "balance_eur": 1000, "currency": {"id": "EUR"}, "iban": None, "company_name": "BNP"},
            {"id": 2, "name": "Livret A", "type": "savings", "balance": 5000, "balance_eur": 5000, "currency": {"id": "EUR"}, "iban": None, "company_name": "BNP"},
        ]

    @pytest.fixture
    def mock_wealth_accounts(self):
        return [
            {"id": 3, "name": "PEE", "type": "employee-savings", "balance": 10000, "currency": {"id": "EUR"}, "company_name": "Amundi"},
        ]

    @pytest.mark.asyncio
    async def test_fetch_accounts_returns_all(self, mock_bank_accounts, mock_wealth_accounts):
        connector = PowensConnector()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.authenticate = AsyncMock()
        mock_client.get_accounts = AsyncMock(return_value=mock_bank_accounts)
        mock_client.get_wealth_accounts = AsyncMock(return_value=mock_wealth_accounts)
        mock_client.get_investments = AsyncMock(return_value=[{"id": 1, "valuation": 10500}])

        with patch("app.connectors.powens.connector.PowensClient", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        assert len(accounts) == 3
        types = [a.account_type for a in accounts]
        assert "checking" in types
        assert "savings" in types
        assert "pee" in types

    @pytest.mark.asyncio
    async def test_fetch_accounts_continues_on_partial_error(self, mock_bank_accounts):
        connector = PowensConnector()

        bad_account = {"id": 99, "name": "Bad", "type": "checking"}  # missing fields

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.authenticate = AsyncMock()
        mock_client.get_accounts = AsyncMock(return_value=[*mock_bank_accounts, bad_account])
        mock_client.get_wealth_accounts = AsyncMock(return_value=[])
        mock_client.get_investments = AsyncMock(return_value=[])

        with patch("app.connectors.powens.connector.PowensClient", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        # Good accounts still returned despite one bad one
        assert len(accounts) >= 2
