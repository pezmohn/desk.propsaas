from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.core.time import now_utc, trading_day_for
from premarket_operator.db.models import DailyReport, User
from premarket_operator.jobs.daily_reports import _skip_reason
from premarket_operator.users.service import list_active_users, user_can_receive_telegram


@dataclass(frozen=True)
class AdminLiveDaySummaryReadModel:
    totalUsers: int
    eligibleUsers: int
    linkedUsers: int
    reportsGenerated: int
    reportsSent: int
    blockedUsers: int


@dataclass(frozen=True)
class AdminLiveDayUserRowReadModel:
    userId: str
    email: str
    displayName: str | None
    eligible: bool
    telegramLinked: bool
    reportGenerated: bool
    reportSent: bool
    blocker: str | None
    reportStatus: str | None
    sentAt: str | None


@dataclass(frozen=True)
class AdminLiveDayReadModel:
    tradingDay: str
    generatedAt: str
    summary: AdminLiveDaySummaryReadModel
    users: list[AdminLiveDayUserRowReadModel]


def get_admin_live_day_read_model(
    session: Session,
    *,
    trading_day: date | None = None,
    current_time: datetime | None = None,
) -> AdminLiveDayReadModel:
    generated_at = current_time or now_utc()
    live_day = trading_day or trading_day_for(generated_at)
    users = [user for user in list_active_users(session) if user.role != "admin"]
    rows = [
        _user_live_day_row(session, user=user, trading_day=live_day)
        for user in users
    ]

    return AdminLiveDayReadModel(
        tradingDay=live_day.isoformat(),
        generatedAt=_datetime_iso(generated_at) or "",
        summary=AdminLiveDaySummaryReadModel(
            totalUsers=len(rows),
            eligibleUsers=sum(1 for row in rows if row.eligible),
            linkedUsers=sum(1 for row in rows if row.telegramLinked),
            reportsGenerated=sum(1 for row in rows if row.reportGenerated),
            reportsSent=sum(1 for row in rows if row.reportSent),
            blockedUsers=sum(1 for row in rows if row.blocker),
        ),
        users=rows,
    )


def _user_live_day_row(
    session: Session,
    *,
    user: User,
    trading_day: date,
) -> AdminLiveDayUserRowReadModel:
    report = _get_daily_report(session, user=user, trading_day=trading_day)
    skip_reason = _skip_reason(
        session,
        user=user,
        trading_day=trading_day,
        report_type="premarket",
    )

    return AdminLiveDayUserRowReadModel(
        userId=str(user.id),
        email=user.email or "",
        displayName=user.display_name,
        eligible=skip_reason is None,
        telegramLinked=user_can_receive_telegram(user),
        reportGenerated=report is not None,
        reportSent=_report_sent(report),
        blocker=_display_blocker(skip_reason),
        reportStatus=report.status if report is not None else None,
        sentAt=_datetime_iso(report.sent_at if report is not None else None),
    )


def _get_daily_report(
    session: Session,
    *,
    user: User,
    trading_day: date,
) -> DailyReport | None:
    statement = select(DailyReport).where(
        DailyReport.user_id == user.id,
        DailyReport.trading_day == trading_day,
        DailyReport.report_type == "premarket",
    )
    return session.scalars(statement).one_or_none()


def _report_sent(report: DailyReport | None) -> bool:
    if report is None:
        return False
    normalized = report.status.lower().replace("-", "_")
    return report.sent_at is not None or normalized in {"sent", "delivered"}


def _display_blocker(reason: str | None) -> str | None:
    if reason is None:
        return None
    return {
        "missing_telegram_chat_id_or_inactive": "Telegram not linked or account inactive",
        "reports_not_enabled": "Reports not enabled",
        "missing_daily_report": "Missing daily report",
    }.get(reason, reason.replace("_", " ").title())


def _datetime_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
