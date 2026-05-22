from datetime import UTC, date, datetime

from premarket_operator.reports.context_schema import build_daily_report_context
from premarket_operator.reports.gex_shock import build_shock_candidates_from_rows
from premarket_operator.reports.renderer import render_premarket_report


def test_daily_report_context_is_storage_ready() -> None:
    candidates = build_shock_candidates_from_rows(
        [
            {
                "ticker": "QQQ",
                "trading_day": "2026-05-22",
                "captured_at": "2026-05-22T13:15:00+00:00",
                "session_phase": "premarket",
                "spot_price": 100.0,
                "gamma_flip": 101.0,
                "call_wall": 104.0,
                "put_wall": 96.0,
                "dist_to_flip_pct": -1.0,
                "dist_to_call_wall_pct": -4.0,
                "dist_to_put_wall_pct": 4.0,
                "regime": "VOLATIL",
                "near_support_levels_json": [96.0, 98.0],
                "near_resistance_levels_json": [102.0, 104.0],
                "extra": {"signed_gex_by_strike": {99.0: -12_000.0, 103.0: 1_000.0}},
            }
        ]
    )
    context = build_daily_report_context(
        trading_day=date(2026, 5, 22),
        generated_at=datetime(2026, 5, 22, 13, 15, tzinfo=UTC),
        gex_candidates=candidates,
    )
    payload = context.to_storage_dict()

    assert payload["report_type"] == "premarket"
    assert payload["sections"][0]["kind"] == "gex_shock"
    assert payload["sections"][0]["candidates"][0]["asset_type"] == "index_etf"
    assert payload["chat_boundaries"]["disallowed"].startswith("No autotrading")
    assert "QQQ" in payload["watchlist"]


def test_renderer_uses_context_as_source() -> None:
    candidates = build_shock_candidates_from_rows(
        [
            {
                "ticker": "MU",
                "trading_day": "2026-05-22",
                "captured_at": "2026-05-22T13:15:00+00:00",
                "session_phase": "premarket",
                "spot_price": 100.0,
                "gamma_flip": 101.0,
                "call_wall": 104.0,
                "put_wall": 96.0,
                "dist_to_flip_pct": -1.0,
                "dist_to_call_wall_pct": -4.0,
                "dist_to_put_wall_pct": 4.0,
                "regime": "VOLATIL",
                "near_support_levels_json": [96.0, 98.0],
                "near_resistance_levels_json": [102.0, 104.0],
                "extra": {"signed_gex_by_strike": {99.0: -12_000.0, 103.0: 1_000.0}},
            }
        ]
    )
    context = build_daily_report_context(
        trading_day=date(2026, 5, 22),
        generated_at=datetime(2026, 5, 22, 13, 15, tzinfo=UTC),
        gex_candidates=candidates,
    )

    body_text = render_premarket_report(context)

    assert body_text.startswith("Premarket Report | 2026-05-22")
    assert "Negative Gamma Shock Report" in body_text
    assert "MU score" in body_text
