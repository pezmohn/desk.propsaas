from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from premarket_operator.db.models import DailyReport


class ContextAssemblyError(RuntimeError):
    pass


def load_report_context(
    session: Session,
    *,
    user_id: UUID,
    daily_report_id: UUID,
) -> dict:
    report = session.get(DailyReport, daily_report_id)
    if report is None or report.user_id != user_id:
        raise ContextAssemblyError("Report context not found for user.")
    return report.context_json
