from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import DailyReport, User
from premarket_operator.db.repositories import require_user_id


@dataclass(frozen=True)
class GeneratedReport:
    user_id: UUID
    trading_day: date
    report_type: str
    body_text: str
    context_json: dict[str, Any]
    generated_at: datetime
    source_version: str


class ReportNotFoundError(LookupError):
    pass


def get_user_for_report(session: Session, *, user_id: UUID) -> User:
    require_user_id(user_id)
    user = session.get(User, user_id)
    if user is None:
        raise ReportNotFoundError(f"User not found: {user_id}")
    return user


def get_daily_report(
    session: Session,
    *,
    user_id: UUID,
    trading_day: date,
    report_type: str = "premarket",
) -> DailyReport | None:
    require_user_id(user_id)
    statement = select(DailyReport).where(
        DailyReport.user_id == user_id,
        DailyReport.trading_day == trading_day,
        DailyReport.report_type == report_type,
    )
    return session.scalars(statement).one_or_none()


def require_daily_report(
    session: Session,
    *,
    user_id: UUID,
    trading_day: date,
    report_type: str = "premarket",
) -> DailyReport:
    report = get_daily_report(
        session,
        user_id=user_id,
        trading_day=trading_day,
        report_type=report_type,
    )
    if report is None:
        raise ReportNotFoundError(
            f"Daily report not found for user_id={user_id}, trading_day={trading_day}, "
            f"report_type={report_type}"
        )
    return report


def save_generated_report(session: Session, generated: GeneratedReport) -> DailyReport:
    require_user_id(generated.user_id)
    get_user_for_report(session, user_id=generated.user_id)

    report = get_daily_report(
        session,
        user_id=generated.user_id,
        trading_day=generated.trading_day,
        report_type=generated.report_type,
    )
    if report is None:
        report = DailyReport(
            user_id=generated.user_id,
            trading_day=generated.trading_day,
            report_type=generated.report_type,
            status="generated",
            body_text=generated.body_text,
            context_json=generated.context_json,
            source_version=generated.source_version,
            generated_at=generated.generated_at,
        )
        session.add(report)
    else:
        report.status = "generated"
        report.body_text = generated.body_text
        report.context_json = generated.context_json
        report.source_version = generated.source_version
        report.generated_at = generated.generated_at
        report.sent_at = None

    session.flush()
    return report
