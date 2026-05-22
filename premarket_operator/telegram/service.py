from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from premarket_operator.core.time import now_utc
from premarket_operator.db.models import DailyReport, TelegramMessage, User
from premarket_operator.plans.service import reports_enabled_for_user
from premarket_operator.reports.service import require_daily_report
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.message_map import persist_outbound_report_message
from premarket_operator.users.service import require_user, user_can_receive_telegram


class ReportDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportDeliveryResult:
    user_id: UUID
    daily_report_id: UUID
    telegram_message_id: int
    dry_run: bool


def deliver_daily_report_to_user(
    session: Session,
    *,
    user_id: UUID,
    trading_day: date,
    telegram_client: TelegramClient,
    report_type: str = "premarket",
) -> ReportDeliveryResult:
    user = require_user(session, user_id=user_id)
    if not user_can_receive_telegram(user):
        raise ReportDeliveryError(f"User {user_id} is not active or has no telegram_chat_id.")
    if not reports_enabled_for_user(session, user_id=user_id):
        raise ReportDeliveryError(f"Reports are not enabled for user {user_id}.")

    report = require_daily_report(
        session,
        user_id=user_id,
        trading_day=trading_day,
        report_type=report_type,
    )
    message = send_report_body(session, user=user, report=report, telegram_client=telegram_client)
    report.status = "sent"
    report.sent_at = now_utc()
    session.flush()
    return ReportDeliveryResult(
        user_id=user.id,
        daily_report_id=report.id,
        telegram_message_id=message.telegram_message_id,
        dry_run=bool(message.raw_update_json and message.raw_update_json.get("dry_run")),
    )


def send_report_body(
    session: Session,
    *,
    user: User,
    report: DailyReport,
    telegram_client: TelegramClient,
) -> TelegramMessage:
    if report.user_id != user.id:
        raise ReportDeliveryError("Refusing to deliver a report across user_id boundaries.")
    if not user.telegram_chat_id:
        raise ReportDeliveryError(f"User {user.id} has no telegram_chat_id.")

    result = telegram_client.send_message(chat_id=user.telegram_chat_id, text=report.body_text)
    return persist_outbound_report_message(
        session,
        user_id=user.id,
        daily_report_id=report.id,
        result=result,
    )
