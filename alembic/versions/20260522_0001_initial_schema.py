"""initial schema

Revision ID: 20260522_0001
Revises:
Create Date: 2026-05-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260522_0001"
down_revision = None
branch_labels = None
depends_on = None


def json_type():
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def uuid_type():
    return postgresql.UUID(as_uuid=True).with_variant(sa.String(length=36), "sqlite")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("email", sa.String(length=320), unique=True),
        sa.Column("display_name", sa.String(length=200)),
        sa.Column("telegram_chat_id", sa.String(length=64), unique=True),
        sa.Column("telegram_username", sa.String(length=128)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "plans",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("daily_reports_enabled", sa.Boolean(), nullable=False),
        sa.Column("daily_chat_reply_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_chat_reply_limit", sa.Integer()),
        sa.Column("monthly_cost_limit_cents", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_plans",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", uuid_type(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "daily_reports",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trading_day", sa.Date(), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("context_json", json_type(), nullable=False),
        sa.Column("source_version", sa.String(length=64)),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_daily_reports_user_day", "daily_reports", ["user_id", "trading_day"])
    op.create_index(
        "uq_daily_reports_user_day_type",
        "daily_reports",
        ["user_id", "trading_day", "report_type"],
        unique=True,
    )

    op.create_table(
        "telegram_messages",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("daily_report_id", uuid_type(), sa.ForeignKey("daily_reports.id")),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text()),
        sa.Column("raw_update_json", json_type()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_messages_user_report", "telegram_messages", ["user_id", "daily_report_id"])
    op.create_index(
        "uq_telegram_chat_message",
        "telegram_messages",
        ["telegram_chat_id", "telegram_message_id"],
        unique=True,
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("daily_report_id", uuid_type(), sa.ForeignKey("daily_reports.id"), nullable=False),
        sa.Column("telegram_message_id", uuid_type(), sa.ForeignKey("telegram_messages.id")),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=120)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_messages_user_report", "chat_messages", ["user_id", "daily_report_id"])

    op.create_table(
        "usage_ledger",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("daily_report_id", uuid_type(), sa.ForeignKey("daily_reports.id")),
        sa.Column("chat_message_id", uuid_type(), sa.ForeignKey("chat_messages.id")),
        sa.Column("feature", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64)),
        sa.Column("model", sa.String(length=120)),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("estimated_cost_cents", sa.Integer()),
        sa.Column("limit_name", sa.String(length=64)),
        sa.Column("limit_allowed", sa.Boolean()),
        sa.Column("metadata_json", json_type()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_ledger_user_created", "usage_ledger", ["user_id", "created_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("user_id", uuid_type(), sa.ForeignKey("users.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", json_type()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_index("ix_usage_ledger_user_created", table_name="usage_ledger")
    op.drop_table("usage_ledger")
    op.drop_index("ix_chat_messages_user_report", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("uq_telegram_chat_message", table_name="telegram_messages")
    op.drop_index("ix_telegram_messages_user_report", table_name="telegram_messages")
    op.drop_table("telegram_messages")
    op.drop_index("uq_daily_reports_user_day_type", table_name="daily_reports")
    op.drop_index("ix_daily_reports_user_day", table_name="daily_reports")
    op.drop_table("daily_reports")
    op.drop_table("user_plans")
    op.drop_table("plans")
    op.drop_table("users")
