from __future__ import annotations

from premarket_operator.reports.context_schema import DailyReportContext


def render_premarket_report(context: DailyReportContext) -> str:
    lines = [
        f"{context.title} | {context.trading_day.isoformat()}",
        "",
    ]

    for section in context.sections:
        if section.kind != "gex_shock":
            continue
        lines.append(f"{section.title} | candidates {section.candidate_count}")
        if not section.candidates:
            lines.append("No candidates found.")
            continue

        for candidate in section.candidates:
            percentile = (
                f"p{candidate.negative_gex_percentile:.0f}"
                if candidate.negative_gex_percentile is not None
                else f"history {candidate.history_count}"
            )
            ticker_label = (
                f"{candidate.ticker} [ETF]"
                if candidate.asset_type == "index_etf"
                else candidate.ticker
            )
            lines.append(
                f"{candidate.rank}. {ticker_label} score {candidate.shock_score:.1f} | "
                f"{candidate.label} | neg GEX {candidate.total_negative_gex_below_spot:,.0f} "
                f"({percentile})"
            )
            lines.append(
                f"   spot {_fmt(candidate.spot_price)} flip {_fmt(candidate.gamma_flip)} "
                f"max neg zone {_fmt(candidate.max_negative_gex_strike)} "
                f"regime {candidate.regime or '-'}"
            )
            lines.append(
                f"   put wall {_fmt(candidate.put_wall)} call wall {_fmt(candidate.call_wall)} "
                f"dist flip {_fmt(candidate.dist_to_flip_pct)}% "
                f"dist put {_fmt(candidate.dist_to_put_wall_pct)}% "
                f"dist call {_fmt(candidate.dist_to_call_wall_pct)}%"
            )
            lines.append(
                f"   supports {_fmt_levels(candidate.support_levels)} | "
                f"resistances {_fmt_levels(candidate.resistance_levels)}"
            )
            lines.append(f"   {candidate.summary}")

    return "\n".join(lines).strip()


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "-"


def _fmt_levels(values: list[float]) -> str:
    return ", ".join(f"{value:.2f}" for value in values) if values else "-"
