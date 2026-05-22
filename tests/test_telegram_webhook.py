from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.db.base import Base
from premarket_operator.db.models import TelegramMessage, UsageLedger
from premarket_operator.plans.service import ensure_default_plan_for_user
from premarket_operator.reports.generator import generate_premarket_report_from_gex_rows
from premarket_operator.reports.service import save_generated_report
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.service import deliver_daily_report_to_user
from premarket_operator.telegram.webhook import TelegramWebhookError, process_telegram_webhook_update
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


def _update(*, chat_id: str, message_id: int, text: str, reply_to_message_id: int | None = None) -> dict:
    message = {"message_id": message_id, "chat": {"id": chat_id}, "text": text}
    if reply_to_message_id is not None:
        message["reply_to_message"] = {"message_id": reply_to_message_id}
    return {"update_id": message_id, "message": message}


def _create_user_with_report(session: Session, *, trading_day: date):
    user = get_or_create_user(
        session,
        email="one@example.com",
        display_name="One",
        telegram_chat_id="12345",
    )
    ensure_default_plan_for_user(session, user_id=user.id)
    generated = generate_premarket_report_from_gex_rows(
        user_id=user.id,
        trading_day=trading_day,
        rows=_rows(trading_day),
        history_by_ticker={"MU": [1_000.0, 2_000.0, 3_000.0, 4_000.0, 5_000.0]},
    )
    report = save_generated_report(session, generated)
    session.commit()
    delivered = deliver_daily_report_to_user(
        session,
        user_id=user.id,
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()
    return user, report, delivered


def test_webhook_loop_sends_and_persists_assistant_telegram_message() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, report, delivered = _create_user_with_report(session, trading_day=trading_day)

    result = process_telegram_webhook_update(
        session,
        update=_update(
            chat_id="12345",
            message_id=930001,
            text="What matters most on MU?",
            reply_to_message_id=delivered.telegram_message_id,
        ),
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()

    outbound = session.get(TelegramMessage, result.outbound_telegram_message_id)
    usage_features = [entry.feature for entry in session.query(UsageLedger).all()]
    assert result.user_id == user.id
    assert result.daily_report_id == report.id
    assert result.dry_run is True
    assert "MU" in result.response_text
    assert outbound.user_id == user.id
    assert outbound.daily_report_id == report.id
    assert outbound.direction == "outbound"
    assert outbound.message_type == "assistant_reply"
    assert outbound.text == result.response_text
    assert "telegram_assistant_delivery" in usage_features


def test_webhook_failure_records_usage_when_user_is_known() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user = get_or_create_user(
        session,
        email="one@example.com",
        display_name="One",
        telegram_chat_id="12345",
    )
    ensure_default_plan_for_user(session, user_id=user.id)
    session.commit()

    with pytest.raises(TelegramWebhookError):
        process_telegram_webhook_update(
            session,
            update=_update(chat_id="12345", message_id=930002, text="What matters most on MU?"),
            trading_day=trading_day,
            telegram_client=TelegramClient(dry_run=True),
        )
    session.commit()

    failed = session.query(UsageLedger).one()
    assert failed.user_id == user.id
    assert failed.feature == "telegram_webhook_failed_attempt"
    assert failed.limit_allowed is False
