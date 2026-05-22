from premarket_operator.reports.gex_shock import (
    build_shock_candidates_from_rows,
    format_report,
)


def _row(
    ticker: str,
    *,
    spot: float = 100.0,
    flip: float = 101.0,
    signed_gex_by_strike: dict[float, float] | None = None,
) -> dict:
    signed_gex_by_strike = signed_gex_by_strike or {99.0: -12_000.0, 103.0: 1_000.0}
    return {
        "ticker": ticker,
        "trading_day": "2026-05-22",
        "captured_at": "2026-05-22T13:15:00+00:00",
        "session_phase": "premarket",
        "spot_price": spot,
        "gamma_flip": flip,
        "call_wall": 104.0,
        "put_wall": 96.0,
        "dist_to_flip_pct": (spot - flip) / spot * 100.0,
        "dist_to_call_wall_pct": (spot - 104.0) / spot * 100.0,
        "dist_to_put_wall_pct": (spot - 96.0) / spot * 100.0,
        "regime": "VOLATIL" if spot < flip else "STABIL",
        "near_support_levels_json": [96.0, 98.0],
        "near_resistance_levels_json": [102.0, 104.0],
        "extra": {"signed_gex_by_strike": signed_gex_by_strike},
    }


def test_shock_candidates_rank_negative_gex_against_history() -> None:
    candidates = build_shock_candidates_from_rows(
        [
            _row("MU", signed_gex_by_strike={97.0: -20_000.0, 99.0: -15_000.0}),
            _row("AAPL", signed_gex_by_strike={98.0: -500.0, 102.0: 500.0}),
        ],
        history_by_ticker={
            "MU": [1_000.0, 2_000.0, 3_000.0, 4_000.0, 5_000.0],
            "AAPL": [1_000.0, 1_200.0, 1_300.0, 1_400.0, 1_500.0],
        },
        min_history=5,
    )

    assert candidates[0].ticker == "MU"
    assert candidates[0].label == "negative_gamma_shock"
    assert candidates[0].negative_gex_percentile == 100.0
    assert candidates[0].total_negative_gex_below_spot == 35_000.0
    assert candidates[0].max_negative_gex_strike == 97.0
    assert candidates[0].shock_score == 100.0


def test_report_formatter_keeps_legacy_compact_shape() -> None:
    candidates = build_shock_candidates_from_rows([_row("PLTR")], min_history=5)

    report = format_report(candidates, limit=3)

    assert "Negative Gamma Shock Report" in report
    assert "history 0" in report
    assert "put wall 96.00 call wall 104.00" in report
    assert "supports 96.00, 98.00 | resistances 102.00, 104.00" in report
