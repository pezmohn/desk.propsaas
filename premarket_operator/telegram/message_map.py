from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import TelegramMessage
from premarket_operator.db.repositories import require_user_id
from premarket_operator.telegram.client import TelegramSendResult
from premarket_operator.telegram.schemas import TelegramInboundMessage


def persist_outbound_report_message(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
    result: TelegramSendResult,
) -> TelegramMessage:
    require_user_id(user_id)
    message = TelegramMessage(
        user_id=user_id,
        daily_report_id=daily_report_id,
        telegram_chat_id=str(result.chat_id),
        telegram_message_id=result.message_id,
        direction="outbound",
        message_type="daily_report",
        text=result.text,
        raw_update_json=result.raw_response,
    )
    session.add(message)
    session.flush()
    return message


def persist_outbound_assistant_message(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
    result: TelegramSendResult,
) -> TelegramMessage:
    require_user_id(user_id)
    message = TelegramMessage(
        user_id=user_id,
        daily_report_id=daily_report_id,
        telegram_chat_id=str(result.chat_id),
        telegram_message_id=result.message_id,
        direction="outbound",
        message_type="assistant_reply",
        text=result.text,
        raw_update_json=result.raw_response,
    )
    session.add(message)
    session.flush()
    return message


def find_outbound_report_message(
    session: Session,
    *,
    user_id: UUID,
    telegram_chat_id: str,
    telegram_message_id: int,
) -> TelegramMessage | None:
    require_user_id(user_id)
    statement = select(TelegramMessage).where(
        TelegramMessage.user_id == user_id,
        TelegramMessage.telegram_chat_id == str(telegram_chat_id),
        TelegramMessage.telegram_message_id == telegram_message_id,
        TelegramMessage.direction == "outbound",
        TelegramMessage.message_type == "daily_report",
        TelegramMessage.daily_report_id.is_not(None),
    )
    return session.scalars(statement).one_or_none()


def find_inbound_message(
    session: Session,
    *,
    telegram_chat_id: str,
    telegram_message_id: int,
) -> TelegramMessage | None:
    statement = select(TelegramMessage).where(
        TelegramMessage.telegram_chat_id == str(telegram_chat_id),
        TelegramMessage.telegram_message_id == telegram_message_id,
        TelegramMessage.direction == "inbound",
    )
    return session.scalars(statement).one_or_none()


def persist_inbound_user_reply(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
    inbound: TelegramInboundMessage,
) -> TelegramMessage:
    require_user_id(user_id)
    existing = find_inbound_message(
        session,
        telegram_chat_id=inbound.chat_id,
        telegram_message_id=inbound.message_id,
    )
    if existing is not None:
        if existing.user_id != user_id or existing.daily_report_id != daily_report_id:
            raise ValueError("Inbound Telegram message already exists for a different context.")
        return existing

    message = TelegramMessage(
        user_id=user_id,
        daily_report_id=daily_report_id,
        telegram_chat_id=inbound.chat_id,
        telegram_message_id=inbound.message_id,
        direction="inbound",
        message_type="user_reply",
        text=inbound.text,
        raw_update_json=inbound.raw_update,
    )
    session.add(message)
    session.flush()
    return message
