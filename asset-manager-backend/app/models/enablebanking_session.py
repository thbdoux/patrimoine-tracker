import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnableBankingSession(Base):
    """
    Consentement PSD2 Enable Banking persisté.

    Un enregistrement = une session autorisée pour une banque (ASPSP) donnée.
    Les consentements expirent (~90-180j) et nécessitent une ré-authentification
    forte de l'utilisateur via le flux de redirection.
    """

    __tablename__ = "enablebanking_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    aspsp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aspsp_country: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTHORIZED")  # AUTHORIZED, EXPIRED, REVOKED
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
