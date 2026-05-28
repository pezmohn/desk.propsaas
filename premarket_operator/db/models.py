from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from premarket_operator.db.base import Base

UUID_TYPE = Uuid(as_uuid=True)
JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)


def timestamp_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/New_York")
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    daily_reports: Mapped[list[DailyReport]] = relationship(back_populates="user")
    user_plans: Mapped[list[UserPlan]] = relationship(back_populates="user")
    auth_sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_active", "user_id", "expires_at", "revoked_at"),
        Index("uq_auth_sessions_token_hash", "token_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = timestamp_column()

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    daily_reports_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_chat_reply_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    monthly_chat_reply_limit: Mapped[int | None] = mapped_column(Integer)
    monthly_cost_limit_cents: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_plans: Mapped[list[UserPlan]] = relationship(back_populates="plan")


class UserPlan(Base):
    __tablename__ = "user_plans"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("plans.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="user_plans")
    plan: Mapped[Plan] = relationship(back_populates="user_plans")


class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (
        Index("ix_daily_reports_user_day", "user_id", "trading_day"),
        Index("uq_daily_reports_user_day_type", "user_id", "trading_day", "report_type", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    trading_day: Mapped[date] = mapped_column(Date, nullable=False)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False, default="premarket")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="daily_reports")
    telegram_messages: Mapped[list[TelegramMessage]] = relationship(back_populates="daily_report")
    chat_messages: Mapped[list[ChatMessage]] = relationship(back_populates="daily_report")


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    __table_args__ = (
        Index("ix_telegram_messages_user_report", "user_id", "daily_report_id"),
        Index("uq_telegram_chat_message", "telegram_chat_id", "telegram_message_id", unique=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    daily_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("daily_reports.id")
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str | None] = mapped_column(Text)
    raw_update_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = timestamp_column()

    daily_report: Mapped[DailyReport | None] = relationship(back_populates="telegram_messages")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_user_report", "user_id", "daily_report_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("daily_reports.id"), nullable=False
    )
    telegram_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("telegram_messages.id")
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = timestamp_column()

    daily_report: Mapped[DailyReport] = relationship(back_populates="chat_messages")


class UsageLedger(Base):
    __tablename__ = "usage_ledger"
    __table_args__ = (Index("ix_usage_ledger_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    daily_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("daily_reports.id")
    )
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("chat_messages.id")
    )
    feature: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(120))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_cents: Mapped[int | None] = mapped_column(Integer)
    limit_name: Mapped[str | None] = mapped_column(String(64))
    limit_allowed: Mapped[bool | None] = mapped_column(Boolean)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = timestamp_column()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = timestamp_column()
