from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.connectors.base import NormalizedAccount, ConnectorAuthError, ConnectorFetchError
from app.connectors.registry import ConnectorRegistry
from app.services.snapshot_service import SnapshotService
from app.services.sync_service import SyncService


def make_account(external_id: str = "spot_BTC", source: str = "binance") -> NormalizedAccount:
    return NormalizedAccount(
        external_id=external_id,
        source=source,
        account_type="crypto_spot",
        label="BTC Spot",
        currency="BTC",
        balance=Decimal("0.5"),
        balance_eur=Decimal("22500"),
        price_eur=Decimal("45000"),
        institution="Binance",
        iban=None,
        metadata={},
    )


class TestSyncService:
    @pytest.fixture
    def mock_connector(self):
        connector = AsyncMock()
        connector.SOURCE_NAME = "binance"
        connector.authenticate = AsyncMock()
        connector.fetch_accounts = AsyncMock(return_value=[make_account()])
        return connector

    @pytest.fixture
    def mock_registry(self, mock_connector):
        registry = MagicMock(spec=ConnectorRegistry)
        registry.get = MagicMock(return_value=mock_connector)
        return registry

    @pytest.fixture
    def mock_snapshot_service(self):
        service = AsyncMock(spec=SnapshotService)
        service.upsert_account = AsyncMock(return_value=uuid.uuid4())
        service.insert_snapshot = AsyncMock()
        return service

    @pytest.fixture
    def sync_service(self, mock_registry, mock_snapshot_service):
        return SyncService(mock_registry, mock_snapshot_service)

    @pytest.mark.asyncio
    async def test_successful_sync(self, sync_service, mock_connector, mock_snapshot_service):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.get = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.services.sync_service.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await sync_service.run_sync("binance")

        mock_connector.authenticate.assert_called_once()
        mock_connector.fetch_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_auth_failure(self, sync_service, mock_connector):
        mock_connector.authenticate = AsyncMock(side_effect=ConnectorAuthError("Invalid API key"))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.get = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.services.sync_service.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Should not raise — errors are logged and sync_log is updated
            await sync_service.run_sync("binance")

        mock_connector.fetch_accounts.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_fetch_failure(self, sync_service, mock_connector):
        mock_connector.fetch_accounts = AsyncMock(side_effect=ConnectorFetchError("Network error"))

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.get = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.services.sync_service.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await sync_service.run_sync("binance")

    @pytest.mark.asyncio
    async def test_sync_unknown_source(self, mock_snapshot_service):
        registry = MagicMock(spec=ConnectorRegistry)
        registry.get = MagicMock(side_effect=KeyError("unknown"))
        sync_service = SyncService(registry, mock_snapshot_service)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.get = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.services.sync_service.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # Should not raise
            await sync_service.run_sync("nonexistent")
