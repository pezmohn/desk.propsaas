from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import ChatMessage, DailyReport, TelegramMessage, User
from premarket_operator.chat.context_assembler import load_report_context
from premarket_operator.chat.engine import ChatEngineResult, answer_from_report_context
from premarket_operator.reports.service import get_daily_report
from premarket_operator.telegram.message_map import (
    find_outbound_report_message,
    persist_inbound_user_reply,
)
from premarket_operator.telegram.schemas import TelegramInboundMessage, parse_inbound_text_message
from premarket_operator.usage.ledger import record_usage
from premarket_operator.users.service import get_user_by_telegram_chat_id


class InboundReplyRoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class InboundReplyRoute:
    user_id: UUID
    daily_report_id: UUID
    telegram_message_id: UUID
    chat_message_id: UUID
    text: str
    resolution_method: str


@dataclass(frozen=True)
class ReportAwareReplyResult:
    route: InboundReplyRoute
    assistant_chat_message_id: UUID
    response_text: str
    model: str
    guardrail_reason: str | None


def route_inbound_report_reply(
    session: Session,
    *,
    update: dict,
    trading_day: date,
) -> InboundReplyRoute:
    inbound = parse_inbound_text_message(update)
    user = _resolve_active_user(session, inbound=inbound)
    report, resolution_method = _resolve_report_context(
        session,
        user=user,
        inbound=inbound,
        trading_day=trading_day,
    )

    telegram_message = persist_inbound_user_reply(
        session,
        user_id=user.id,
        daily_report_id=report.id,
        inbound=inbound,
    )
    chat_message = persist_user_chat_message(
        session,
        user_id=user.id,
        daily_report_id=report.id,
        telegram_message=telegram_message,
        text=inbound.text,
    )

    return InboundReplyRoute(
        user_id=user.id,
        daily_report_id=report.id,
        telegram_message_id=telegram_message.id,
        chat_message_id=chat_message.id,
        text=inbound.text,
        resolution_method=resolution_method,
    )


def answer_inbound_report_reply(
    session: Session,
    *,
    update: dict,
    trading_day: date,
) -> ReportAwareReplyResult:
    route = route_inbound_report_reply(session, update=update, trading_day=trading_day)
    record_usage(
        session,
        user_id=route.user_id,
        daily_report_id=route.daily_report_id,
        chat_message_id=route.chat_message_id,
        feature="inbound_reply_attempt",
        provider="telegram",
        limit_allowed=True,
        metadata_json={"resolution_method": route.resolution_method},
    )

    report_context = load_report_context(
        session,
        user_id=route.user_id,
        daily_report_id=route.daily_report_id,
    )
    engine_result = answer_from_report_context(report_context=report_context, question=route.text)
    assistant_message = persist_assistant_chat_message(
        session,
        user_id=route.user_id,
        daily_report_id=route.daily_report_id,
        engine_result=engine_result,
    )
    record_usage(
        session,
        user_id=route.user_id,
        daily_report_id=route.daily_report_id,
        chat_message_id=assistant_message.id,
        feature="assistant_report_reply",
        provider="local",
        model=engine_result.model,
        input_tokens=engine_result.input_tokens,
        output_tokens=engine_result.output_tokens,
        total_tokens=engine_result.total_tokens,
        estimated_cost_cents=0,
        limit_allowed=True,
        metadata_json={
            "guardrail_reason": engine_result.guardrail_reason,
            "prompt": engine_result.prompt.as_text(),
        },
    )
    return ReportAwareReplyResult(
        route=route,
        assistant_chat_message_id=assistant_message.id,
        response_text=assistant_message.content,
        model=engine_result.model,
        guardrail_reason=engine_result.guardrail_reason,
    )


def persist_user_chat_message(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
    telegram_message: TelegramMessage,
    text: str,
) -> ChatMessage:
    if telegram_message.user_id != user_id or telegram_message.daily_report_id != daily_report_id:
        raise InboundReplyRoutingError("Refusing to persist chat message across user/report boundary.")

    existing = session.scalars(
        select(ChatMessage).where(ChatMessage.telegram_message_id == telegram_message.id)
    ).one_or_none()
    if existing is not None:
        return existing

    chat_message = ChatMessage(
        user_id=user_id,
        daily_report_id=daily_report_id,
        telegram_message_id=telegram_message.id,
        role="user",
        content=text,
    )
    session.add(chat_message)
    session.flush()
    return chat_message


def persist_assistant_chat_message(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
    engine_result: ChatEngineResult,
) -> ChatMessage:
    chat_message = ChatMessage(
        user_id=user_id,
        daily_report_id=daily_report_id,
        role="assistant",
        content=engine_result.response_text,
        model=engine_result.model,
        prompt_tokens=engine_result.input_tokens,
        completion_tokens=engine_result.output_tokens,
        total_tokens=engine_result.total_tokens,
    )
    session.add(chat_message)
    session.flush()
    return chat_message


def _resolve_active_user(session: Session, *, inbound: TelegramInboundMessage) -> User:
    user = get_user_by_telegram_chat_id(session, telegram_chat_id=inbound.chat_id)
    if user is None:
        raise InboundReplyRoutingError(f"No user is bound to Telegram chat_id={inbound.chat_id}.")
    if user.status != "active":
        raise InboundReplyRoutingError(f"User {user.id} is not active.")
    return user


def _resolve_report_context(
    session: Session,
    *,
    user: User,
    inbound: TelegramInboundMessage,
    trading_day: date,
) -> tuple[DailyReport, str]:
    if inbound.reply_to_message_id is not None:
        outbound = find_outbound_report_message(
            session,
            user_id=user.id,
            telegram_chat_id=inbound.chat_id,
            telegram_message_id=inbound.reply_to_message_id,
        )
        if outbound is not None and outbound.daily_report_id is not None:
            report = session.get(DailyReport, outbound.daily_report_id)
            if report is None or report.user_id != user.id:
                raise InboundReplyRoutingError("Reply mapping points to an invalid report context.")
            return report, "reply_to_report_message"

    report = get_daily_report(session, user_id=user.id, trading_day=trading_day)
    if report is None:
        raise InboundReplyRoutingError(
            "No reply mapping found and no same-user active report exists for the trading day."
        )
    if report.status not in {"generated", "sent"}:
        raise InboundReplyRoutingError(f"Daily report {report.id} is not active.")
    return report, "same_user_same_day_fallback"
