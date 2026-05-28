from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.core.time import now_utc, trading_day_for
from premarket_operator.db.models import DailyReport, User
from premarket_operator.plans.service import get_active_user_plan


@dataclass(frozen=True)
class DashboardStatusItemReadModel:
    id: str
    label: str
    value: str
    detail: str
    tone: str


@dataclass(frozen=True)
class UserDashboardReadModel:
    generatedAt: str
    items: list[DashboardStatusItemReadModel]


def get_user_dashboard_read_model(
    session: Session,
    *,
    user: User,
    current_time: datetime | None = None,
) -> UserDashboardReadModel:
    generated_at = current_time or now_utc()
    trading_day = trading_day_for(generated_at)
    user_plan = get_active_user_plan(session, user_id=user.id)
    todays_report = _get_todays_report(session, user=user, trading_day=trading_day)
    last_delivery = _get_last_delivery_report(session, user=user)

    return UserDashboardReadModel(
        generatedAt=_datetime_iso(generated_at) or "",
        items=[
            _plan_item(user_plan),
            _telegram_item(user),
            _report_item(todays_report, trading_day=trading_day),
            _delivery_item(last_delivery),
            _blocker_item(user=user, user_plan=user_plan),
        ],
    )


def _get_todays_report(
    session: Session,
    *,
    user: User,
    trading_day,
) -> DailyReport | None:
    statement = select(DailyReport).where(
        DailyReport.user_id == user.id,
        DailyReport.trading_day == trading_day,
        DailyReport.report_type == "premarket",
    )
    return session.scalars(statement).one_or_none()


def _get_last_delivery_report(session: Session, *, user: User) -> DailyReport | None:
    statement = (
        select(DailyReport)
        .where(DailyReport.user_id == user.id, DailyReport.sent_at.is_not(None))
        .order_by(DailyReport.sent_at.desc())
        .limit(1)
    )
    return session.scalars(statement).one_or_none()


def _plan_item(user_plan) -> DashboardStatusItemReadModel:
    if user_plan is None or user_plan.plan is None:
        return DashboardStatusItemReadModel(
            id="plan",
            label="Plan status",
            value="Unknown",
            detail="No active plan record is available for this user.",
            tone="unknown",
        )
    if not user_plan.plan.daily_reports_enabled:
        return DashboardStatusItemReadModel(
            id="plan",
            label="Plan status",
            value=user_plan.plan.name,
            detail="The active plan exists, but daily reports are not enabled.",
            tone="blocked",
        )
    return DashboardStatusItemReadModel(
        id="plan",
        label="Plan status",
        value=user_plan.plan.name,
        detail=f"Plan state: {_display_status(user_plan.status)}.",
        tone="ready",
    )


def _telegram_item(user: User) -> DashboardStatusItemReadModel:
    if user.telegram_chat_id:
        return DashboardStatusItemReadModel(
            id="telegram",
            label="Telegram link",
            value="Connected",
            detail="A Telegram chat identity is linked for report delivery.",
            tone="ready",
        )
    if user.telegram_username:
        return DashboardStatusItemReadModel(
            id="telegram",
            label="Telegram link",
            value="Incomplete",
            detail="A Telegram username is present, but no chat identity is linked.",
            tone="pending",
        )
    return DashboardStatusItemReadModel(
        id="telegram",
        label="Telegram link",
        value="Not connected",
        detail="No Telegram chat identity is linked for delivery.",
        tone="blocked",
    )


def _report_item(report: DailyReport | None, *, trading_day) -> DashboardStatusItemReadModel:
    if report is None:
        return DashboardStatusItemReadModel(
            id="report",
            label="Today's report",
            value="No report found",
            detail=f"No premarket report record exists for {trading_day.isoformat()}.",
            tone="unknown",
        )
    status = _normalized_status(report.status)
    if report.sent_at is not None or status in {"sent", "delivered"}:
        tone = "ready"
    elif status in {"failed", "error"}:
        tone = "blocked"
    elif status in {"generated", "draft", "pending"}:
        tone = "pending"
    else:
        tone = "unknown"
    return DashboardStatusItemReadModel(
        id="report",
        label="Today's report",
        value=_display_status(report.status),
        detail=f"Report record exists for {report.trading_day.isoformat()}.",
        tone=tone,
    )


def _delivery_item(report: DailyReport | None) -> DashboardStatusItemReadModel:
    if report is None or report.sent_at is None:
        return DashboardStatusItemReadModel(
            id="delivery",
            label="Last delivery",
            value="No delivery recorded",
            detail="No report has a sent_at timestamp yet.",
            tone="unknown",
        )
    return DashboardStatusItemReadModel(
        id="delivery",
        label="Last delivery",
        value=_datetime_iso(report.sent_at) or "Unavailable",
        detail=f"Latest sent report trading day: {report.trading_day.isoformat()}.",
        tone="ready",
    )


def _blocker_item(user: User, user_plan) -> DashboardStatusItemReadModel:
    if user.status != "active":
        return DashboardStatusItemReadModel(
            id="blocker",
            label="Current blocker",
            value="Account inactive",
            detail="The user status is not active.",
            tone="blocked",
        )
    if user_plan is None or user_plan.plan is None:
        return DashboardStatusItemReadModel(
            id="blocker",
            label="Current blocker",
            value="No active plan",
            detail="Daily report delivery requires an active plan record.",
            tone="blocked",
        )
    if not user_plan.plan.daily_reports_enabled:
        return DashboardStatusItemReadModel(
            id="blocker",
            label="Current blocker",
            value="Reports disabled",
            detail="The active plan does not enable daily reports.",
            tone="blocked",
        )
    if not user.telegram_chat_id:
        return DashboardStatusItemReadModel(
            id="blocker",
            label="Current blocker",
            value="Telegram not linked",
            detail="Daily report delivery requires a Telegram chat identity.",
            tone="blocked",
        )
    return DashboardStatusItemReadModel(
        id="blocker",
        label="Current blocker",
        value="None detected",
        detail="No blocker is detected from the current account, plan, and Telegram delivery prerequisites.",
        tone="ready",
    )


def _normalized_status(value: str | None) -> str:
    return (value or "").lower().replace("-", "_")


def _display_status(value: str | None) -> str:
    if not value:
        return "Unknown"
    return value.replace("_", " ").replace("-", " ").title()


def _datetime_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
