"""enablebanking sessions

Revision ID: 002
Revises: 001
Create Date: 2026-06-19 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enablebanking_sessions",
        sa.Column("id", UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("aspsp_name", sa.String(255), nullable=False),
        sa.Column("aspsp_country", sa.String(2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'AUTHORIZED'")),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_enablebanking_sessions_session_id"),
    )
    op.create_index(
        "idx_enablebanking_sessions_status",
        "enablebanking_sessions",
        ["status", "valid_until"],
    )


def downgrade() -> None:
    op.drop_index("idx_enablebanking_sessions_status", table_name="enablebanking_sessions")
    op.drop_table("enablebanking_sessions")
