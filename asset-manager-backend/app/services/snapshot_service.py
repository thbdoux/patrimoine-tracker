import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import NormalizedAccount
from app.models.account import Account
from app.models.snapshot import AccountSnapshot


class SnapshotService:
    async def upsert_account(self, session: AsyncSession, normalized: NormalizedAccount) -> uuid.UUID:
        """
        Insère ou met à jour le compte. Retourne l'UUID interne.
        Utilise INSERT ... ON CONFLICT DO UPDATE pour l'idempotence.
        """
        stmt = (
            insert(Account)
            .values(
                external_id=normalized.external_id,
                source=normalized.source,
                account_type=normalized.account_type,
                label=normalized.label,
                currency=normalized.currency,
                institution=normalized.institution,
                iban=normalized.iban,
                is_active=True,
            )
            .on_conflict_do_update(
                constraint="uq_accounts_external_source",
                set_={
                    "account_type": normalized.account_type,
                    "label": normalized.label,
                    "currency": normalized.currency,
                    "institution": normalized.institution,
                    "iban": normalized.iban,
                    "is_active": True,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            .returning(Account.id)
        )
        result = await session.execute(stmt)
        account_id: uuid.UUID = result.scalar_one()
        return account_id

    async def insert_snapshot(
        self,
        session: AsyncSession,
        account_id: uuid.UUID,
        normalized: NormalizedAccount,
        captured_at: datetime,
    ) -> None:
        """
        Insère un snapshot. Ne fait jamais de UPDATE — append-only.
        """
        snapshot = AccountSnapshot(
            account_id=account_id,
            captured_at=captured_at,
            balance=normalized.balance,
            balance_eur=normalized.balance_eur,
            price_eur=normalized.price_eur,
            raw_data=normalized.metadata,
        )
        session.add(snapshot)
