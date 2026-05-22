from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence
from uuid import UUID

from premarket_operator.core.time import now_utc
from premarket_operator.reports.context_schema import build_daily_report_context
from premarket_operator.reports.gex_shock import ShockCandidate, build_shock_candidates_from_rows
from premarket_operator.reports.renderer import render_premarket_report
from premarket_operator.reports.service import GeneratedReport

REPORT_SOURCE_VERSION = "gex_shock.manual_rows.v1"


def generate_premarket_report_from_gex_rows(
    *,
    user_id: UUID,
    trading_day: date,
    rows: Sequence[Mapping[str, Any]],
    history_by_ticker: Mapping[str, Sequence[float]] | None = None,
    generated_at: datetime | None = None,
    limit: int = 10,
    min_history: int = 5,
) -> GeneratedReport:
    generated_at = generated_at or now_utc()
    candidates = build_shock_candidates_from_rows(
        rows,
        history_by_ticker=history_by_ticker,
        min_history=min_history,
    )
    return build_premarket_report_from_candidates(
        user_id=user_id,
        trading_day=trading_day,
        generated_at=generated_at,
        candidates=candidates,
        limit=limit,
        source_version=REPORT_SOURCE_VERSION,
    )


def build_premarket_report_from_candidates(
    *,
    user_id: UUID,
    trading_day: date,
    generated_at: datetime,
    candidates: list[ShockCandidate],
    limit: int = 10,
    source_version: str = REPORT_SOURCE_VERSION,
) -> GeneratedReport:
    context = build_daily_report_context(
        trading_day=trading_day,
        generated_at=generated_at,
        gex_candidates=candidates,
        limit=limit,
    )
    body_text = render_premarket_report(context)
    return GeneratedReport(
        user_id=user_id,
        trading_day=trading_day,
        report_type="premarket",
        body_text=body_text,
        context_json=context.to_storage_dict(),
        generated_at=generated_at,
        source_version=source_version,
    )
