from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enablebanking_session import EnableBankingSession

# Alerte avant expiration du consentement (ré-authentification forte requise)
CONSENT_ALERT_DAYS = 7


def parse_valid_until(value: Optional[str]) -> Optional[datetime]:
    """Parse l'ISO 8601 renvoyé par Enable Banking (souvent suffixé 'Z')."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def upsert_session(
    db: AsyncSession,
    *,
    session_id: str,
    aspsp_name: str,
    aspsp_country: str,
    valid_until: Optional[datetime],
    metadata: Optional[dict] = None,
) -> EnableBankingSession:
    """Crée ou met à jour une session par son session_id (idempotent)."""
    existing = await db.scalar(
        select(EnableBankingSession).where(EnableBankingSession.session_id == session_id)
    )
    now = datetime.now(timezone.utc)
    if existing is None:
        row = EnableBankingSession(
            session_id=session_id,
            aspsp_name=aspsp_name,
            aspsp_country=aspsp_country,
            status="AUTHORIZED",
            valid_until=valid_until,
            authorized_at=now,
            metadata_=metadata,
        )
        db.add(row)
        return row

    existing.aspsp_name = aspsp_name
    existing.aspsp_country = aspsp_country
    existing.status = "AUTHORIZED"
    existing.valid_until = valid_until
    existing.authorized_at = now
    existing.metadata_ = metadata
    return existing


async def get_active_sessions(db: AsyncSession) -> list[EnableBankingSession]:
    """Sessions exploitables : statut AUTHORIZED et non expirées."""
    now = datetime.now(timezone.utc)
    rows = await db.scalars(
        select(EnableBankingSession).where(EnableBankingSession.status == "AUTHORIZED")
    )
    active: list[EnableBankingSession] = []
    for row in rows:
        if row.valid_until is not None and row.valid_until <= now:
            continue
        active.append(row)
    return active


def days_remaining(session: EnableBankingSession) -> Optional[int]:
    if session.valid_until is None:
        return None
    delta = session.valid_until - datetime.now(timezone.utc)
    return delta.days
