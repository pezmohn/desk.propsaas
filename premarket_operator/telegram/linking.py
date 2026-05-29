from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.auth.security import hash_session_token
from premarket_operator.db.models import TelegramLinkToken, User
from premarket_operator.telegram.schemas import TelegramInboundMessage
from premarket_operator.users.service import get_user_by_telegram_chat_id

LINK_PREFIX = "link_"
LINK_TTL_MINUTES = 15


class TelegramLinkError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramLinkStart:
    token: str
    start_payload: str
    start_command: str
    expires_at: datetime


@dataclass(frozen=True)
class TelegramLinkCompletion:
    user: User
    chat_id: str
    username: str | None


def create_telegram_link_token(
    session: Session,
    *,
    user: User,
    current_time: datetime | None = None,
    ttl_minutes: int = LINK_TTL_MINUTES,
) -> TelegramLinkStart:
    now = current_time or datetime.now(UTC)
    token = secrets.token_urlsafe(18)
    start_payload = f"{LINK_PREFIX}{token}"
    link_token = TelegramLinkToken(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=now + timedelta(minutes=ttl_minutes),
    )
    session.add(link_token)
    session.flush()
    return TelegramLinkStart(
        token=token,
        start_payload=start_payload,
        start_command=f"/start {start_payload}",
        expires_at=link_token.expires_at,
    )


def maybe_parse_link_token(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "/start":
        return None
    payload = parts[1].strip()
    if not payload.startswith(LINK_PREFIX):
        return None
    token = payload.removeprefix(LINK_PREFIX).strip()
    return token or None


def complete_telegram_link(
    session: Session,
    *,
    token: str,
    inbound: TelegramInboundMessage,
    current_time: datetime | None = None,
) -> TelegramLinkCompletion:
    now = current_time or datetime.now(UTC)
    link_token = session.scalars(
        select(TelegramLinkToken).where(
            TelegramLinkToken.token_hash == hash_session_token(token),
            TelegramLinkToken.used_at.is_(None),
            TelegramLinkToken.expires_at > now,
        )
    ).one_or_none()
    if link_token is None:
        raise TelegramLinkError("Telegram link token is invalid or expired.")

    user = link_token.user
    if user is None or user.status != "active":
        raise TelegramLinkError("Telegram link token no longer belongs to an active user.")

    existing_user = get_user_by_telegram_chat_id(session, telegram_chat_id=inbound.chat_id)
    if existing_user is not None and existing_user.id != user.id:
        raise TelegramLinkError("Telegram chat identity is already linked to another user.")

    username = _username_from_update(inbound.raw_update)
    user.telegram_chat_id = inbound.chat_id
    user.telegram_username = username
    link_token.used_at = now
    session.add(user)
    session.add(link_token)
    session.flush()
    return TelegramLinkCompletion(user=user, chat_id=inbound.chat_id, username=username)


def _username_from_update(update: dict) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    sender = message.get("from")
    if not isinstance(sender, dict):
        return None
    username = sender.get("username")
    if not isinstance(username, str):
        return None
    normalized = username.strip().lstrip("@")
    return normalized or None
