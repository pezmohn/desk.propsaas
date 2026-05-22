from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_TARGET_TICKERS = (
    "SPY",
    "QQQ",
    "IWM",
    "SMH",
    "AAPL",
    "MSFT",
    "NVDA",
    "META",
    "AMZN",
    "TSLA",
    "AMD",
    "MU",
    "PLTR",
    "SOXL",
    "COIN",
    "MSTR",
    "NFLX",
    "AVGO",
    "JPM",
    "GOOGL",
)
INDEX_ETFS = frozenset({"QQQ", "SPY", "IWM"})


@dataclass(frozen=True)
class ShockCandidate:
    ticker: str
    trading_day: str
    session_phase: str
    captured_at: str
    spot_price: float | None
    gamma_flip: float | None
    call_wall: float | None
    put_wall: float | None
    regime: str | None
    dist_to_flip_pct: float | None
    dist_to_call_wall_pct: float | None
    dist_to_put_wall_pct: float | None
    total_negative_gex_below_spot: float
    max_negative_gex_strike: float | None
    max_negative_gex_value: float | None
    negative_gex_percentile: float | None
    history_count: int
    nearest_negative_zone_pct: float | None
    near_support_levels: tuple[float, ...]
    near_resistance_levels: tuple[float, ...]
    shock_score: float
    label: str
    summary: str

    @property
    def asset_type(self) -> str:
        return "index_etf" if self.ticker in INDEX_ETFS else "stock"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["asset_type"] = self.asset_type
        payload["near_support_levels"] = list(self.near_support_levels)
        payload["near_resistance_levels"] = list(self.near_resistance_levels)
        return payload


def connect_snapshot_db(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _placeholders(values: Sequence[str]) -> str:
    return ", ".join("?" for _ in values)


def _row_get(row: sqlite3.Row | Mapping[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(row, sqlite3.Row):
        return row[key] if key in row.keys() else default
    return row.get(key, default)


def _load_extra(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    raw = _row_get(row, "extra_json")
    if not raw:
        extra = _row_get(row, "extra")
        return extra if isinstance(extra, dict) else {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _signed_map(row: sqlite3.Row | Mapping[str, Any]) -> dict[float, float]:
    raw = _load_extra(row).get("signed_gex_by_strike", {})
    if not isinstance(raw, dict):
        return {}

    result: dict[float, float] = {}
    for key, value in raw.items():
        try:
            result[float(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return dict(sorted(result.items()))


def _level_tuple(row: sqlite3.Row | Mapping[str, Any], column: str) -> tuple[float, ...]:
    raw = _row_get(row, column)
    if not raw:
        return ()
    if isinstance(raw, list):
        parsed = raw
    else:
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return ()
    if not isinstance(parsed, list):
        return ()

    levels: list[float] = []
    for value in parsed:
        try:
            levels.append(float(value))
        except (TypeError, ValueError):
            continue
    return tuple(levels)


def _negative_metrics(row: sqlite3.Row | Mapping[str, Any]) -> tuple[float, float | None, float | None, float | None]:
    spot = _row_get(row, "spot_price")
    signed = _signed_map(row)
    if spot is None or not signed:
        return (0.0, None, None, None)

    below_spot = [(strike, value) for strike, value in signed.items() if strike <= spot and value < 0]
    if not below_spot:
        return (0.0, None, None, None)

    total_negative = sum(abs(value) for _, value in below_spot)
    max_strike, max_value = min(below_spot, key=lambda item: item[1])
    nearest_pct = (spot - max_strike) / spot * 100.0 if spot else None
    return (total_negative, max_strike, max_value, nearest_pct)


def _percentile(value: float, history: list[float]) -> float | None:
    clean = sorted(item for item in history if item is not None)
    if not clean:
        return None
    below_or_equal = sum(1 for item in clean if item <= value)
    return below_or_equal / len(clean) * 100.0


def _latest_rows(
    conn: sqlite3.Connection,
    tickers: Sequence[str],
    trading_day: str | None,
) -> list[sqlite3.Row]:
    if not tickers:
        return []

    filters = [f"ticker IN ({_placeholders(tickers)})"]
    params: list[str] = [ticker.upper() for ticker in tickers]
    if trading_day:
        filters.append("trading_day = ?")
        params.append(trading_day)
    where = " AND ".join(filters)
    return conn.execute(
        f"""
        WITH ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY ticker
                    ORDER BY captured_at DESC
                ) AS row_num
            FROM barchart_levels_history
            WHERE {where}
        )
        SELECT *
        FROM ranked
        WHERE row_num = 1
        """,
        params,
    ).fetchall()


def _history_values(conn: sqlite3.Connection, ticker: str, before_captured_at: str | None) -> list[float]:
    params: list[str] = [ticker]
    where = "ticker = ?"
    if before_captured_at:
        where += " AND captured_at < ?"
        params.append(before_captured_at)
    rows = conn.execute(
        f"""
        SELECT *
        FROM barchart_levels_history
        WHERE {where}
        ORDER BY captured_at
        """,
        params,
    ).fetchall()
    return [_negative_metrics(row)[0] for row in rows]


def build_shock_candidates_from_rows(
    rows: Sequence[sqlite3.Row | Mapping[str, Any]],
    *,
    history_by_ticker: Mapping[str, Sequence[float]] | None = None,
    min_history: int = 5,
) -> list[ShockCandidate]:
    history_by_ticker = history_by_ticker or {}
    candidates: list[ShockCandidate] = []

    for row in rows:
        ticker = str(_row_get(row, "ticker")).upper()
        total_negative, max_strike, max_value, nearest_pct = _negative_metrics(row)
        history = list(history_by_ticker.get(ticker, ()))
        percentile = _percentile(total_negative, history) if len(history) >= min_history else None

        spot_price = _row_get(row, "spot_price")
        gamma_flip = _row_get(row, "gamma_flip")
        dist_to_flip_pct = _row_get(row, "dist_to_flip_pct")
        below_flip = spot_price is not None and gamma_flip is not None and spot_price < gamma_flip
        near_flip = dist_to_flip_pct is not None and abs(float(dist_to_flip_pct)) <= 1.5
        nearest_zone = nearest_pct is not None and 0.0 <= nearest_pct <= 3.0

        score = percentile if percentile is not None else min(55.0, total_negative / 1_000_000.0)
        if below_flip:
            score += 20.0
        if near_flip:
            score += 10.0
        if nearest_zone:
            score += 10.0
        score = round(min(score, 100.0), 2)

        if percentile is None:
            label = "building_history"
        elif score >= 90:
            label = "negative_gamma_shock"
        elif score >= 75:
            label = "elevated_negative_gamma"
        else:
            label = "normal"

        zone = f"{max_strike:.2f}" if max_strike is not None else "n/a"
        pct = f"p{percentile:.0f}" if percentile is not None else f"history {len(history)}/{min_history}"
        regime = _row_get(row, "regime")
        summary = (
            f"{ticker} {label}: neg GEX below spot {total_negative:,.0f} ({pct}), "
            f"max negative zone {zone}, regime {regime or '-'}."
        )

        candidates.append(
            ShockCandidate(
                ticker=ticker,
                trading_day=str(_row_get(row, "trading_day")),
                session_phase=str(_row_get(row, "session_phase", "")),
                captured_at=str(_row_get(row, "captured_at")),
                spot_price=spot_price,
                gamma_flip=gamma_flip,
                call_wall=_row_get(row, "call_wall"),
                put_wall=_row_get(row, "put_wall"),
                regime=regime,
                dist_to_flip_pct=dist_to_flip_pct,
                dist_to_call_wall_pct=_row_get(row, "dist_to_call_wall_pct"),
                dist_to_put_wall_pct=_row_get(row, "dist_to_put_wall_pct"),
                total_negative_gex_below_spot=round(total_negative, 2),
                max_negative_gex_strike=max_strike,
                max_negative_gex_value=max_value,
                negative_gex_percentile=round(percentile, 2) if percentile is not None else None,
                history_count=len(history),
                nearest_negative_zone_pct=round(nearest_pct, 2) if nearest_pct is not None else None,
                near_support_levels=_level_tuple(row, "near_support_levels_json"),
                near_resistance_levels=_level_tuple(row, "near_resistance_levels_json"),
                shock_score=score,
                label=label,
                summary=summary,
            )
        )

    return sorted(candidates, key=lambda item: item.shock_score, reverse=True)


def build_shock_candidates(
    conn: sqlite3.Connection,
    *,
    tickers: Sequence[str] = DEFAULT_TARGET_TICKERS,
    trading_day: str | None = None,
    min_history: int = 5,
) -> list[ShockCandidate]:
    rows = _latest_rows(conn, tickers=tickers, trading_day=trading_day)
    history_by_ticker = {
        str(row["ticker"]).upper(): _history_values(conn, row["ticker"], row["captured_at"])
        for row in rows
    }
    return build_shock_candidates_from_rows(rows, history_by_ticker=history_by_ticker, min_history=min_history)


def format_rank_table(candidates: Sequence[ShockCandidate], *, limit: int) -> str:
    lines = [
        "ticker score label spot flip neg_gex_below_spot percentile max_neg_zone dist_zone_pct regime"
    ]
    for item in candidates[:limit]:
        ticker_label = f"{item.ticker}[ETF]" if item.ticker in INDEX_ETFS else item.ticker
        lines.append(
            " ".join(
                [
                    ticker_label,
                    f"{item.shock_score:.2f}",
                    item.label,
                    f"{item.spot_price:.2f}" if item.spot_price is not None else "-",
                    f"{item.gamma_flip:.2f}" if item.gamma_flip is not None else "-",
                    f"{item.total_negative_gex_below_spot:.0f}",
                    f"{item.negative_gex_percentile:.1f}" if item.negative_gex_percentile is not None else "-",
                    f"{item.max_negative_gex_strike:.2f}" if item.max_negative_gex_strike is not None else "-",
                    f"{item.nearest_negative_zone_pct:.2f}" if item.nearest_negative_zone_pct is not None else "-",
                    item.regime or "-",
                ]
            )
        )
    return "\n".join(lines)


def format_report(candidates: Sequence[ShockCandidate], *, limit: int) -> str:
    def format_level(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "-"

    def format_levels(values: tuple[float, ...]) -> str:
        return ", ".join(f"{value:.2f}" for value in values) if values else "-"

    shown = candidates[:limit]
    lines = [f"Negative Gamma Shock Report | candidates {len(candidates)}"]
    if not shown:
        lines.append("No candidates found. Run collect first or widen the ticker list.")
        return "\n".join(lines)
    for index, item in enumerate(shown, start=1):
        ticker_label = f"{item.ticker} [ETF]" if item.ticker in INDEX_ETFS else item.ticker
        percentile = (
            f"p{item.negative_gex_percentile:.0f}"
            if item.negative_gex_percentile is not None
            else f"history {item.history_count}"
        )
        spot_text = f"{item.spot_price:.2f}" if item.spot_price is not None else "-"
        flip_text = f"{item.gamma_flip:.2f}" if item.gamma_flip is not None else "-"
        max_zone_text = (
            f"{item.max_negative_gex_strike:.2f}"
            if item.max_negative_gex_strike is not None
            else "-"
        )
        lines.append(
            f"{index}. {ticker_label} score {item.shock_score:.1f} | {item.label} | "
            f"neg GEX {item.total_negative_gex_below_spot:,.0f} ({percentile})"
        )
        lines.append(
            f"   spot {spot_text} flip {flip_text} "
            f"max neg zone {max_zone_text} regime {item.regime or '-'}"
        )
        lines.append(
            f"   put wall {format_level(item.put_wall)} call wall {format_level(item.call_wall)} "
            f"dist flip {format_level(item.dist_to_flip_pct)}% "
            f"dist put {format_level(item.dist_to_put_wall_pct)}% "
            f"dist call {format_level(item.dist_to_call_wall_pct)}%"
        )
        lines.append(
            f"   supports {format_levels(item.near_support_levels)} | "
            f"resistances {format_levels(item.near_resistance_levels)}"
        )
        lines.append(f"   {item.summary}")
    return "\n".join(lines)
