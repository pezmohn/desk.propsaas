from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Literal

from premarket_operator.reports.gex_shock import ShockCandidate


@dataclass(frozen=True)
class ChatBoundaries:
    allowed: str = "Answer only using this daily report context plus basic market mechanics."
    disallowed: str = (
        "No autotrading, order execution, personalized financial advice, or unrelated market chat."
    )


@dataclass(frozen=True)
class ReportLevel:
    ticker: str
    type: str
    price: float


@dataclass(frozen=True)
class GexShockCandidateContext:
    rank: int
    ticker: str
    asset_type: Literal["stock", "index_etf"]
    label: str
    shock_score: float
    trading_day: str
    session_phase: str
    captured_at: str
    total_negative_gex_below_spot: float
    history_count: int
    summary: str
    spot_price: float | None = None
    gamma_flip: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    regime: str | None = None
    dist_to_flip_pct: float | None = None
    dist_to_call_wall_pct: float | None = None
    dist_to_put_wall_pct: float | None = None
    max_negative_gex_strike: float | None = None
    max_negative_gex_value: float | None = None
    negative_gex_percentile: float | None = None
    nearest_negative_zone_pct: float | None = None
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class ReportSection:
    kind: Literal["gex_shock"]
    title: str
    candidate_count: int
    source: str
    candidates: list[GexShockCandidateContext]


@dataclass(frozen=True)
class DailyReportContext:
    trading_day: date
    generated_at: datetime
    schema_version: Literal["2026-05-22.v1"] = "2026-05-22.v1"
    report_type: Literal["premarket"] = "premarket"
    market_timezone: str = "America/New_York"
    title: str = "Premarket Report"
    sections: list[ReportSection] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)
    key_levels: list[ReportLevel] = field(default_factory=list)
    chat_boundaries: ChatBoundaries = field(default_factory=ChatBoundaries)

    def to_storage_dict(self) -> dict:
        payload = asdict(self)
        payload["trading_day"] = self.trading_day.isoformat()
        payload["generated_at"] = self.generated_at.isoformat()
        return payload


def _candidate_to_context(candidate: ShockCandidate, rank: int) -> GexShockCandidateContext:
    return GexShockCandidateContext(
        rank=rank,
        ticker=candidate.ticker,
        asset_type=candidate.asset_type,
        label=candidate.label,
        shock_score=candidate.shock_score,
        trading_day=candidate.trading_day,
        session_phase=candidate.session_phase,
        captured_at=candidate.captured_at,
        spot_price=candidate.spot_price,
        gamma_flip=candidate.gamma_flip,
        call_wall=candidate.call_wall,
        put_wall=candidate.put_wall,
        regime=candidate.regime,
        dist_to_flip_pct=candidate.dist_to_flip_pct,
        dist_to_call_wall_pct=candidate.dist_to_call_wall_pct,
        dist_to_put_wall_pct=candidate.dist_to_put_wall_pct,
        total_negative_gex_below_spot=candidate.total_negative_gex_below_spot,
        max_negative_gex_strike=candidate.max_negative_gex_strike,
        max_negative_gex_value=candidate.max_negative_gex_value,
        negative_gex_percentile=candidate.negative_gex_percentile,
        history_count=candidate.history_count,
        nearest_negative_zone_pct=candidate.nearest_negative_zone_pct,
        support_levels=list(candidate.near_support_levels),
        resistance_levels=list(candidate.near_resistance_levels),
        summary=candidate.summary,
    )


def _levels_for_candidate(candidate: ShockCandidate) -> list[ReportLevel]:
    levels: list[ReportLevel] = []
    for level_type, price in (
        ("gamma_flip", candidate.gamma_flip),
        ("put_wall", candidate.put_wall),
        ("call_wall", candidate.call_wall),
        ("max_negative_gex", candidate.max_negative_gex_strike),
    ):
        if price is not None:
            levels.append(ReportLevel(ticker=candidate.ticker, type=level_type, price=price))

    levels.extend(
        ReportLevel(ticker=candidate.ticker, type="support", price=price)
        for price in candidate.near_support_levels
    )
    levels.extend(
        ReportLevel(ticker=candidate.ticker, type="resistance", price=price)
        for price in candidate.near_resistance_levels
    )
    return levels


def build_daily_report_context(
    *,
    trading_day: date,
    generated_at: datetime,
    gex_candidates: list[ShockCandidate],
    limit: int = 10,
) -> DailyReportContext:
    shown = gex_candidates[:limit]
    candidate_contexts = [
        _candidate_to_context(candidate, rank=index)
        for index, candidate in enumerate(shown, start=1)
    ]
    watchlist = [candidate.ticker for candidate in shown]
    key_levels = [level for candidate in shown for level in _levels_for_candidate(candidate)]

    return DailyReportContext(
        trading_day=trading_day,
        generated_at=generated_at,
        sections=[
            ReportSection(
                kind="gex_shock",
                title="Negative Gamma Shock Report",
                candidate_count=len(gex_candidates),
                source="barchart_gex_shock",
                candidates=candidate_contexts,
            )
        ],
        watchlist=watchlist,
        key_levels=key_levels,
    )
