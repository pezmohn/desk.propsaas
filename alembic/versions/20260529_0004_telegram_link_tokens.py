"""telegram link tokens

Revision ID: 20260529_0004
Revises: 20260529_0003
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260529_0004"
down_revision = "20260529_0003"
branch_labels = None
depends_on = None


def uuid_type():
    return postgresql.UUID(as_uuid=True).with_variant(sa.String(length=36), "sqlite")


def upgrade() -> None:
    op.create_table(
        "telegram_link_tokens",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "uq_telegram_link_tokens_token_hash",
        "telegram_link_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_telegram_link_tokens_user_active",
        "telegram_link_tokens",
        ["user_id", "expires_at", "used_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_telegram_link_tokens_user_active", table_name="telegram_link_tokens")
    op.drop_index("uq_telegram_link_tokens_token_hash", table_name="telegram_link_tokens")
    op.drop_table("telegram_link_tokens")
