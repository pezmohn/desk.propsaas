from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import DailyReport


@dataclass(frozen=True)
class ReportListItemReadModel:
    id: str
    tradingDay: str
    title: str
    deliveryStatus: str
    sentAt: str | None
    generatedAt: str


@dataclass(frozen=True)
class ReportDetailReadModel(ReportListItemReadModel):
    bodyText: str


def list_report_history_for_user(
    session: Session,
    *,
    user_id: UUID,
    limit: int = 50,
) -> list[ReportListItemReadModel]:
    statement = (
        select(DailyReport)
        .where(DailyReport.user_id == user_id)
        .order_by(DailyReport.trading_day.desc(), DailyReport.generated_at.desc())
        .limit(limit)
    )
    return [_report_list_item(report) for report in session.scalars(statement).all()]


def get_report_detail_for_user(
    session: Session,
    *,
    user_id: UUID,
    report_id: UUID,
) -> ReportDetailReadModel | None:
    statement = select(DailyReport).where(
        DailyReport.id == report_id,
        DailyReport.user_id == user_id,
    )
    report = session.scalars(statement).one_or_none()
    if report is None:
        return None
    return ReportDetailReadModel(
        **_report_list_item(report).__dict__,
        bodyText=report.body_text,
    )


def _report_list_item(report: DailyReport) -> ReportListItemReadModel:
    return ReportListItemReadModel(
        id=str(report.id),
        tradingDay=report.trading_day.isoformat(),
        title=_report_title(report.report_type),
        deliveryStatus=_delivery_status(report),
        sentAt=_datetime_iso(report.sent_at),
        generatedAt=_datetime_iso(report.generated_at) or "",
    )


def _report_title(report_type: str) -> str:
    if report_type == "premarket":
        return "Premarket Report"
    return f"{report_type.replace('_', ' ').title()} Report"


def _delivery_status(report: DailyReport) -> str:
    normalized = report.status.lower().replace("-", "_")
    if report.sent_at is not None or normalized in {"sent", "delivered"}:
        return "sent"
    if normalized in {"failed", "error"}:
        return "failed"
    if normalized in {"generated", "draft", "pending"}:
        return "not_sent"
    return "unknown"


def _datetime_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
