"""auth foundation

Revision ID: 20260528_0002
Revises: 20260522_0001
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260528_0002"
down_revision = "20260522_0001"
branch_labels = None
depends_on = None


def uuid_type():
    return postgresql.UUID(as_uuid=True).with_variant(sa.String(length=36), "sqlite")


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255)))

    op.create_table(
        "auth_sessions",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("uq_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index(
        "ix_auth_sessions_user_active",
        "auth_sessions",
        ["user_id", "expires_at", "revoked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions")
    op.drop_index("uq_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_column("users", "password_hash")
