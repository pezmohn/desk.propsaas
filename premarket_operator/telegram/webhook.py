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
from premarket_operator.telegram.linking import (
    TelegramLinkError,
    complete_telegram_link,
    maybe_parse_link_token,
)
from premarket_operator.telegram.message_map import find_inbound_message, persist_outbound_assistant_message
from premarket_operator.telegram.schemas import TelegramUpdateParseError, parse_inbound_text_message
from premarket_operator.usage.ledger import record_usage
from premarket_operator.users.service import get_user_by_telegram_chat_id
from premarket_operator.db.models import TelegramMessage


class TelegramWebhookError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramWebhookResult:
    user_id: UUID | None
    daily_report_id: UUID | None
    inbound_telegram_message_id: UUID | None
    user_chat_message_id: UUID | None
    assistant_chat_message_id: UUID | None
    outbound_telegram_message_id: UUID | None
    telegram_message_id: int
    response_text: str
    dry_run: bool
    guardrail_reason: str | None
    event_type: str = "report_reply"


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
        inbound = parse_inbound_text_message(update)
        link_token = maybe_parse_link_token(inbound.text)
        if link_token is not None:
            return _process_telegram_link_update(
                session,
                inbound=inbound,
                token=link_token,
                telegram_client=telegram_client,
            )
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


def _process_telegram_link_update(
    session: Session,
    *,
    inbound,
    token: str,
    telegram_client: TelegramClient,
) -> TelegramWebhookResult:
    try:
        completion = complete_telegram_link(session, token=token, inbound=inbound)
    except TelegramLinkError:
        send_result = telegram_client.send_message(
            chat_id=inbound.chat_id,
            text="This Telegram link is invalid or expired. Open Settings and request a fresh link.",
        )
        return TelegramWebhookResult(
            user_id=None,
            daily_report_id=None,
            inbound_telegram_message_id=None,
            user_chat_message_id=None,
            assistant_chat_message_id=None,
            outbound_telegram_message_id=None,
            telegram_message_id=send_result.message_id,
            response_text=send_result.text,
            dry_run=send_result.dry_run,
            guardrail_reason=None,
            event_type="telegram_link_failed",
        )

    inbound_message = _persist_telegram_link_inbound(
        session,
        user_id=completion.user.id,
        inbound=inbound,
    )
    send_result = telegram_client.send_message(
        chat_id=inbound.chat_id,
        text="Telegram is now linked for report delivery.",
    )
    outbound = TelegramMessage(
        user_id=completion.user.id,
        daily_report_id=None,
        telegram_chat_id=inbound.chat_id,
        telegram_message_id=send_result.message_id,
        direction="outbound",
        message_type="telegram_link_confirmation",
        text=send_result.text,
        raw_update_json=send_result.raw_response,
    )
    session.add(outbound)
    session.flush()
    record_usage(
        session,
        user_id=completion.user.id,
        feature="telegram_link_completed",
        provider="telegram",
        limit_allowed=True,
        metadata_json={
            "telegram_chat_id": completion.chat_id,
            "telegram_username": completion.username,
            "dry_run": send_result.dry_run,
        },
    )
    return TelegramWebhookResult(
        user_id=completion.user.id,
        daily_report_id=None,
        inbound_telegram_message_id=inbound_message.id,
        user_chat_message_id=None,
        assistant_chat_message_id=None,
        outbound_telegram_message_id=outbound.id,
        telegram_message_id=send_result.message_id,
        response_text=send_result.text,
        dry_run=send_result.dry_run,
        guardrail_reason=None,
        event_type="telegram_link_completed",
    )


def _persist_telegram_link_inbound(session: Session, *, user_id: UUID, inbound) -> TelegramMessage:
    existing = find_inbound_message(
        session,
        telegram_chat_id=inbound.chat_id,
        telegram_message_id=inbound.message_id,
    )
    if existing is not None:
        return existing

    message = TelegramMessage(
        user_id=user_id,
        daily_report_id=None,
        telegram_chat_id=inbound.chat_id,
        telegram_message_id=inbound.message_id,
        direction="inbound",
        message_type="telegram_link",
        text=inbound.text,
        raw_update_json=inbound.raw_update,
    )
    session.add(message)
    session.flush()
    return message


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
