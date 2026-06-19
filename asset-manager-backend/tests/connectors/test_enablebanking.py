from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.enablebanking.connector import EnableBankingConnector
from app.connectors.enablebanking.normalizer import _map_type, _pick_balance, normalize_account
from app.connectors.enablebanking.repository import parse_valid_until


# ── Normalizer tests ────────────────────────────────────────────────────────

class TestTypeMapping:
    def test_known_types(self):
        assert _map_type("CACC") == "checking"
        assert _map_type("SVGS") == "savings"
        assert _map_type("LOAN") == "loan"

    def test_case_insensitive(self):
        assert _map_type("cacc") == "checking"

    def test_unknown_and_none(self):
        assert _map_type("ZZZZ") == "other"
        assert _map_type(None) == "other"


class TestPickBalance:
    def test_prefers_available_over_booked(self):
        balances = [
            {"balance_type": "CLBD", "balance_amount": {"amount": "100.00", "currency": "EUR"}},
            {"balance_type": "ITAV", "balance_amount": {"amount": "90.00", "currency": "EUR"}},
        ]
        amount, currency = _pick_balance(balances)
        assert amount == Decimal("90.00")
        assert currency == "EUR"

    def test_empty(self):
        amount, currency = _pick_balance([])
        assert amount == Decimal("0")
        assert currency == "EUR"

    def test_fallback_first_when_no_priority_match(self):
        balances = [{"balance_type": "WTF", "balance_amount": {"amount": "5", "currency": "USD"}}]
        amount, currency = _pick_balance(balances)
        assert amount == Decimal("5")
        assert currency == "USD"


class TestNormalizeAccount:
    def test_checking_account_with_iban(self):
        account = {
            "uid": "acc-uid-1",
            "name": "Trade Republic Cash",
            "cash_account_type": "CACC",
            "account_id": {"iban": "DE89370400440532013000"},
            "aspsp": {"name": "Trade Republic"},
        }
        balances = [{"balance_type": "ITAV", "balance_amount": {"amount": "1234.56", "currency": "EUR"}}]
        acc = normalize_account(account, balances)
        assert acc.external_id == "acc-uid-1"
        assert acc.source == "enablebanking"
        assert acc.account_type == "checking"
        assert acc.balance == Decimal("1234.56")
        assert acc.balance_eur == Decimal("1234.56")
        assert acc.currency == "EUR"
        assert acc.iban == "DE89370400440532013000"
        assert acc.institution == "Trade Republic"

    def test_non_eur_has_no_balance_eur(self):
        account = {"uid": "x", "cash_account_type": "SVGS"}
        balances = [{"balance_type": "CLBD", "balance_amount": {"amount": "10", "currency": "USD"}}]
        acc = normalize_account(account, balances)
        assert acc.account_type == "savings"
        assert acc.currency == "USD"
        assert acc.balance_eur is None


class TestParseValidUntil:
    def test_parses_z_suffix(self):
        dt = parse_valid_until("2026-09-17T10:30:00.000Z")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 9 and dt.day == 17

    def test_none_and_invalid(self):
        assert parse_valid_until(None) is None
        assert parse_valid_until("") is None
        assert parse_valid_until("not-a-date") is None


# ── Connector integration tests ─────────────────────────────────────────────

def _mock_client(**methods):
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    for name, value in methods.items():
        setattr(client, name, value)
    return client


class TestEnableBankingConnector:
    @pytest.mark.asyncio
    async def test_fetch_accounts_no_consent_returns_empty(self):
        connector = EnableBankingConnector()
        with patch.object(EnableBankingConnector, "_list_consents", AsyncMock(return_value=[])):
            accounts = await connector.fetch_accounts()
        assert accounts == []

    @pytest.mark.asyncio
    async def test_not_configured_is_silent(self):
        connector = EnableBankingConnector()
        with patch.object(EnableBankingConnector, "_is_configured", return_value=False):
            # authenticate ne lève pas, fetch_accounts renvoie [] (sync "réussie" à 0)
            await connector.authenticate()
            assert await connector.fetch_accounts() == []
            assert await connector.health_check() is False

    @pytest.mark.asyncio
    async def test_fetch_accounts_returns_normalized(self):
        connector = EnableBankingConnector()

        # GET /sessions ne renvoie que les UID
        session = {"accounts": ["u1", "u2"]}
        details = {
            "u1": {"uid": "u1", "name": "Cash", "cash_account_type": "CACC", "currency": "EUR"},
            "u2": {"uid": "u2", "name": "Savings", "cash_account_type": "SVGS", "currency": "EUR"},
        }
        mock_client = _mock_client(
            get_session=AsyncMock(return_value=session),
            get_account_details=AsyncMock(side_effect=lambda uid: details[uid]),
            get_account_balances=AsyncMock(
                return_value=[{"balance_type": "ITAV", "balance_amount": {"amount": "500", "currency": "EUR"}}]
            ),
        )

        with patch.object(EnableBankingConnector, "_list_consents",
                          AsyncMock(return_value=[("sess-123", "Trade Republic")])), \
             patch.object(EnableBankingConnector, "_get_client", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        assert len(accounts) == 2
        assert {a.account_type for a in accounts} == {"checking", "savings"}
        assert all(a.institution == "Trade Republic" for a in accounts)
        assert all(a.balance == Decimal("500") for a in accounts)

    @pytest.mark.asyncio
    async def test_fetch_accounts_continues_on_account_error(self):
        connector = EnableBankingConnector()
        session = {"accounts": ["ok", "bad"]}

        async def details(uid):
            if uid == "bad":
                raise RuntimeError("boom")
            return {"uid": "ok", "name": "OK", "cash_account_type": "CACC", "currency": "EUR"}

        mock_client = _mock_client(
            get_session=AsyncMock(return_value=session),
            get_account_details=AsyncMock(side_effect=details),
            get_account_balances=AsyncMock(
                return_value=[{"balance_type": "CLBD", "balance_amount": {"amount": "1", "currency": "EUR"}}]
            ),
        )

        with patch.object(EnableBankingConnector, "_list_consents",
                          AsyncMock(return_value=[("sess-123", "Mock ASPSP")])), \
             patch.object(EnableBankingConnector, "_get_client", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        # Le compte en erreur est ignoré, l'autre passe — pas de crash
        assert len(accounts) == 1
        assert accounts[0].label == "OK"

    @pytest.mark.asyncio
    async def test_fetch_accounts_aggregates_multiple_sessions(self):
        connector = EnableBankingConnector()
        sessions = {
            "s1": {"accounts": ["u1"]},
            "s2": {"accounts": ["u2"]},
        }
        details = {
            "u1": {"uid": "u1", "name": "TR Cash", "cash_account_type": "CACC", "currency": "EUR"},
            "u2": {"uid": "u2", "name": "N26 Save", "cash_account_type": "SVGS", "currency": "EUR"},
        }
        mock_client = _mock_client(
            get_session=AsyncMock(side_effect=lambda sid: sessions[sid]),
            get_account_details=AsyncMock(side_effect=lambda uid: details[uid]),
            get_account_balances=AsyncMock(
                return_value=[{"balance_type": "CLBD", "balance_amount": {"amount": "10", "currency": "EUR"}}]
            ),
        )
        with patch.object(EnableBankingConnector, "_list_consents",
                          AsyncMock(return_value=[("s1", "Trade Republic"), ("s2", "N26")])), \
             patch.object(EnableBankingConnector, "_get_client", return_value=mock_client):
            accounts = await connector.fetch_accounts()

        assert len(accounts) == 2
        assert {a.institution for a in accounts} == {"Trade Republic", "N26"}
