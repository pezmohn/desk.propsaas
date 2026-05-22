from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from premarket_operator.db.models import User
from premarket_operator.plans.service import reports_enabled_for_user
from premarket_operator.reports.service import get_daily_report
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.service import ReportDeliveryError, ReportDeliveryResult, deliver_daily_report_to_user
from premarket_operator.users.service import list_active_users, user_can_receive_telegram


@dataclass(frozen=True)
class DeliveryJobResult:
    delivered: list[ReportDeliveryResult]
    skipped: list[dict[str, str]]


def deliver_reports_for_all_eligible_users(
    session: Session,
    *,
    trading_day: date,
    telegram_client: TelegramClient,
    report_type: str = "premarket",
) -> DeliveryJobResult:
    delivered: list[ReportDeliveryResult] = []
    skipped: list[dict[str, str]] = []

    for user in list_active_users(session):
        skip_reason = _skip_reason(session, user=user, trading_day=trading_day, report_type=report_type)
        if skip_reason is not None:
            skipped.append({"user_id": str(user.id), "reason": skip_reason})
            continue
        try:
            delivered.append(
                deliver_daily_report_to_user(
                    session,
                    user_id=user.id,
                    trading_day=trading_day,
                    report_type=report_type,
                    telegram_client=telegram_client,
                )
            )
        except ReportDeliveryError as exc:
            skipped.append({"user_id": str(user.id), "reason": str(exc)})

    return DeliveryJobResult(delivered=delivered, skipped=skipped)


def _skip_reason(session: Session, *, user: User, trading_day: date, report_type: str) -> str | None:
    if not user_can_receive_telegram(user):
        return "missing_telegram_chat_id_or_inactive"
    if not reports_enabled_for_user(session, user_id=user.id):
        return "reports_not_enabled"
    if get_daily_report(
        session,
        user_id=user.id,
        trading_day=trading_day,
        report_type=report_type,
    ) is None:
        return "missing_daily_report"
    return None
