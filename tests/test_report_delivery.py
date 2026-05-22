from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.db.base import Base
from premarket_operator.db.models import TelegramMessage
from premarket_operator.plans.service import ensure_default_plan_for_user
from premarket_operator.reports.generator import generate_premarket_report_from_gex_rows
from premarket_operator.reports.service import save_generated_report
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.service import deliver_daily_report_to_user
from premarket_operator.jobs.daily_reports import deliver_reports_for_all_eligible_users
from premarket_operator.users.service import get_or_create_user


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


def _create_user_with_report(session: Session, *, email: str, chat_id: str, trading_day: date):
    user = get_or_create_user(
        session,
        email=email,
        display_name=email,
        telegram_chat_id=chat_id,
    )
    ensure_default_plan_for_user(session, user_id=user.id)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
    )
    report = save_generated_report(session, generated)
    session.commit()
    return user, report


def test_dry_run_delivery_persists_outbound_report_message() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, report = _create_user_with_report(
        session,
        email="one@example.com",
        chat_id="12345",
        trading_day=trading_day,
    )

    result = deliver_daily_report_to_user(
        session,
        user_id=user.id,
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()

    message = session.query(TelegramMessage).one()
    assert result.daily_report_id == report.id
    assert result.dry_run is True
    assert message.user_id == user.id
    assert message.daily_report_id == report.id
    assert message.direction == "outbound"
    assert message.message_type == "daily_report"
    assert message.raw_update_json["dry_run"] is True
    assert report.status == "sent"
    assert report.sent_at is not None


def test_all_user_delivery_skips_users_without_report_or_chat() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, _ = _create_user_with_report(
        session,
        email="one@example.com",
        chat_id="12345",
        trading_day=trading_day,
    )
    missing_report = get_or_create_user(
        session,
        email="two@example.com",
        display_name="Two",
        telegram_chat_id="67890",
    )
    ensure_default_plan_for_user(session, user_id=missing_report.id)
    missing_chat = get_or_create_user(session, email="three@example.com", display_name="Three")
    ensure_default_plan_for_user(session, user_id=missing_chat.id)
    session.commit()

    result = deliver_reports_for_all_eligible_users(
        session,
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )

    assert [item.user_id for item in result.delivered] == [user.id]
    assert {item["reason"] for item in result.skipped} == {
        "missing_daily_report",
        "missing_telegram_chat_id_or_inactive",
    }
