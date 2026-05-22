from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.db.base import Base
from premarket_operator.db.models import User
from premarket_operator.reports.generator import generate_premarket_report_from_gex_rows
from premarket_operator.reports.service import get_daily_report, save_generated_report


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _rows(trading_day: date) -> list[dict]:
    day = trading_day.isoformat()
    return [
        {
            "ticker": "MU",
            "trading_day": day,
            "captured_at": f"{day}T13:15:00+00:00",
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
            "extra": {"signed_gex_by_strike": {97.0: -20_000.0, 99.0: -15_000.0}},
        }
    ]


def test_generate_and_store_daily_report_for_one_user() -> None:
    session = _session()
    user = User(email="one@example.com", display_name="One")
    session.add(user)
    session.commit()

    trading_day = date(2026, 5, 22)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
        history_by_ticker={"MU": [1_000.0, 2_000.0, 3_000.0, 4_000.0, 5_000.0]},
    )
    report = save_generated_report(session, generated)
    session.commit()

    stored = get_daily_report(session, user_id=user.id, trading_day=trading_day)
    assert stored is not None
    assert stored.id == report.id
    assert stored.user_id == user.id
    assert stored.body_text.startswith("Premarket Report | 2026-05-22")
    assert stored.context_json["watchlist"] == ["MU"]
    assert stored.context_json["chat_boundaries"]["disallowed"].startswith("No autotrading")


def test_report_fetch_is_scoped_by_user_id() -> None:
    session = _session()
    user_one = User(email="one@example.com", display_name="One")
    user_two = User(email="two@example.com", display_name="Two")
    session.add_all([user_one, user_two])
    session.commit()

    trading_day = date(2026, 5, 22)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user_one.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
    )
    save_generated_report(session, generated)
    session.commit()

    assert get_daily_report(session, user_id=user_one.id, trading_day=trading_day) is not None
    assert get_daily_report(session, user_id=user_two.id, trading_day=trading_day) is None


def test_save_generated_report_is_idempotent_for_user_day_type() -> None:
    session = _session()
    user = User(email="one@example.com", display_name="One")
    session.add(user)
    session.commit()

    trading_day = date(2026, 5, 22)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
    )
    first = save_generated_report(session, generated)
    session.commit()

    second_generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
        limit=1,
    )
    second = save_generated_report(session, second_generated)
    session.commit()

    assert second.id == first.id
    assert get_daily_report(session, user_id=user.id, trading_day=trading_day).id == first.id
