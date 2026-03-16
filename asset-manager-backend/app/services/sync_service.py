from datetime import datetime, timezone

import structlog

from app.connectors.base import ConnectorAuthError, ConnectorFetchError
from app.connectors.registry import ConnectorRegistry
from app.database import get_session
from app.models.sync_log import SyncLog
from app.services.snapshot_service import SnapshotService

logger = structlog.get_logger(__name__)


class SyncService:
    def __init__(self, registry: ConnectorRegistry, snapshot_service: SnapshotService) -> None:
        self._registry = registry
        self._snapshot_service = snapshot_service

    async def run_sync(self, source_name: str) -> None:
        log = logger.bind(source=source_name)
        started_at = datetime.now(timezone.utc)
        log.info("sync_started")

        async with get_session() as session:
            sync_log = SyncLog(
                source=source_name,
                started_at=started_at,
                status="running",
            )
            session.add(sync_log)
            await session.flush()
            sync_log_id = sync_log.id

        try:
            connector = self._registry.get(source_name)
        except KeyError:
            await self._finish_sync(sync_log_id, "failed", 0, f"Unknown source: {source_name}")
            log.error("sync_unknown_source")
            return

        try:
            await connector.authenticate()
        except ConnectorAuthError as e:
            await self._finish_sync(sync_log_id, "failed", 0, str(e))
            log.error("sync_auth_failed", error=str(e))
            return

        try:
            accounts = await connector.fetch_accounts()
        except ConnectorFetchError as e:
            await self._finish_sync(sync_log_id, "failed", 0, str(e))
            log.error("sync_fetch_failed", error=str(e))
            return

        captured_at = datetime.now(timezone.utc)
        accounts_synced = 0
        errors = 0

        for normalized in accounts:
            try:
                async with get_session() as session:
                    account_id = await self._snapshot_service.upsert_account(session, normalized)
                    await self._snapshot_service.insert_snapshot(session, account_id, normalized, captured_at)
                accounts_synced += 1
                log.debug(
                    "account_synced",
                    external_id=normalized.external_id,
                    balance=str(normalized.balance),
                    balance_eur=str(normalized.balance_eur) if normalized.balance_eur else None,
                )
            except Exception as e:
                errors += 1
                log.warning(
                    "account_sync_error",
                    external_id=normalized.external_id,
                    error=str(e),
                )

        status = "success" if errors == 0 else "partial"
        await self._finish_sync(sync_log_id, status, accounts_synced)

        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        log.info(
            "sync_completed",
            status=status,
            accounts_synced=accounts_synced,
            errors=errors,
            duration_ms=duration_ms,
        )

    async def _finish_sync(
        self,
        sync_log_id,
        status: str,
        accounts_synced: int,
        error_message: str | None = None,
    ) -> None:
        async with get_session() as session:
            sync_log = await session.get(SyncLog, sync_log_id)
            if sync_log:
                sync_log.finished_at = datetime.now(timezone.utc)
                sync_log.status = status
                sync_log.accounts_synced = accounts_synced
                sync_log.error_message = error_message
