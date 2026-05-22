from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from premarket_operator.chat.service import (
    InboundReplyRoute,
    ReportAwareReplyResult,
    answer_inbound_report_reply,
    route_inbound_report_reply,
)
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.message_map import persist_outbound_assistant_message
from premarket_operator.telegram.schemas import TelegramUpdateParseError, parse_inbound_text_message
from premarket_operator.usage.ledger import record_usage
from premarket_operator.users.service import get_user_by_telegram_chat_id


class TelegramWebhookError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramWebhookResult:
    user_id: UUID
    daily_report_id: UUID
    inbound_telegram_message_id: UUID
    user_chat_message_id: UUID
    assistant_chat_message_id: UUID
    outbound_telegram_message_id: UUID
    telegram_message_id: int
    response_text: str
    dry_run: bool
    guardrail_reason: str | None


def handle_telegram_update(
    session: Session,
    *,
    update: dict,
    trading_day: date,
) -> InboundReplyRoute:
    return route_inbound_report_reply(session, update=update, trading_day=trading_day)


def process_telegram_webhook_update(
    session: Session,
    *,
    update: dict,
    trading_day: date,
    telegram_client: TelegramClient,
) -> TelegramWebhookResult:
    try:
        answer = answer_inbound_report_reply(session, update=update, trading_day=trading_day)
        send_result = telegram_client.send_message(
            chat_id=_chat_id_from_update(update),
            text=answer.response_text,
        )
        outbound = persist_outbound_assistant_message(
            session,
            user_id=answer.route.user_id,
            daily_report_id=answer.route.daily_report_id,
            result=send_result,
        )
        record_usage(
            session,
            user_id=answer.route.user_id,
            daily_report_id=answer.route.daily_report_id,
            chat_message_id=answer.assistant_chat_message_id,
            feature="telegram_assistant_delivery",
            provider="telegram",
            limit_allowed=True,
            metadata_json={
                "telegram_message_id": send_result.message_id,
                "dry_run": send_result.dry_run,
                "guardrail_reason": answer.guardrail_reason,
            },
        )
        if answer.guardrail_reason is not None:
            record_usage(
                session,
                user_id=answer.route.user_id,
                daily_report_id=answer.route.daily_report_id,
                chat_message_id=answer.assistant_chat_message_id,
                feature="telegram_guardrail_blocked_reply",
                provider="local",
                model=answer.model,
                limit_allowed=False,
                metadata_json={"guardrail_reason": answer.guardrail_reason},
            )
        return _webhook_result(answer=answer, outbound_id=outbound.id, send_result=send_result)
    except Exception as exc:
        _record_failed_webhook_attempt(session, update=update, error=exc)
        raise TelegramWebhookError(str(exc)) from exc


def _webhook_result(
    *,
    answer: ReportAwareReplyResult,
    outbound_id: UUID,
    send_result,
) -> TelegramWebhookResult:
    return TelegramWebhookResult(
        user_id=answer.route.user_id,
        daily_report_id=answer.route.daily_report_id,
        inbound_telegram_message_id=answer.route.telegram_message_id,
        user_chat_message_id=answer.route.chat_message_id,
        assistant_chat_message_id=answer.assistant_chat_message_id,
        outbound_telegram_message_id=outbound_id,
        telegram_message_id=send_result.message_id,
        response_text=answer.response_text,
        dry_run=send_result.dry_run,
        guardrail_reason=answer.guardrail_reason,
    )


def _chat_id_from_update(update: dict) -> str:
    inbound = parse_inbound_text_message(update)
    return inbound.chat_id


def _record_failed_webhook_attempt(session: Session, *, update: dict, error: Exception) -> None:
    try:
        inbound = parse_inbound_text_message(update)
    except TelegramUpdateParseError:
        return

    user = get_user_by_telegram_chat_id(session, telegram_chat_id=inbound.chat_id)
    if user is None:
        return

    record_usage(
        session,
        user_id=user.id,
        feature="telegram_webhook_failed_attempt",
        provider="telegram",
        limit_allowed=False,
        metadata_json={
            "telegram_chat_id": inbound.chat_id,
            "telegram_message_id": inbound.message_id,
            "error": str(error),
        },
    )
