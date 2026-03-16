import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    __table_args__ = (
        Index("idx_snapshots_account_captured", "account_id", "captured_at"),
        Index("idx_snapshots_captured_at", "captured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    balance_eur: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    price_eur: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
