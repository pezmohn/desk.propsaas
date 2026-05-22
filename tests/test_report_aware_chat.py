from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.chat.service import answer_inbound_report_reply
from premarket_operator.db.base import Base
from premarket_operator.db.models import ChatMessage, UsageLedger
from premarket_operator.plans.service import ensure_default_plan_for_user
from premarket_operator.reports.generator import generate_premarket_report_from_gex_rows
from premarket_operator.reports.service import save_generated_report
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.service import deliver_daily_report_to_user
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


def _create_delivered_report(session: Session, *, trading_day: date):
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


def test_report_aware_reply_persists_grounded_assistant_message_and_usage() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, report, delivered = _create_delivered_report(session, trading_day=trading_day)

    result = answer_inbound_report_reply(
        session,
        update=_update(
            chat_id="12345",
            message_id=800001,
            text="What matters most on MU?",
            reply_to_message_id=delivered.telegram_message_id,
        ),
        trading_day=trading_day,
    )
    session.commit()

    assistant = session.get(ChatMessage, result.assistant_chat_message_id)
    usage_entries = session.query(UsageLedger).order_by(UsageLedger.created_at).all()
    assert result.route.daily_report_id == report.id
    assert result.guardrail_reason is None
    assert assistant.role == "assistant"
    assert "MU" in assistant.content
    assert "gamma flip 101.00" in assistant.content
    assert [entry.feature for entry in usage_entries] == [
        "inbound_reply_attempt",
        "assistant_report_reply",
    ]
    assert usage_entries[-1].model == "local-report-aware-v1"
    assert "REPORT CONTEXT" in usage_entries[-1].metadata_json["prompt"]


def test_autotrading_request_gets_guardrail_response() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    _, _, delivered = _create_delivered_report(session, trading_day=trading_day)

    result = answer_inbound_report_reply(
        session,
        update=_update(
            chat_id="12345",
            message_id=800002,
            text="Buy MU now and tell me how many shares",
            reply_to_message_id=delivered.telegram_message_id,
        ),
        trading_day=trading_day,
    )

    assert result.guardrail_reason == "autotrading_or_order_request"
    assert "cannot place orders" in result.response_text


def test_unrelated_request_gets_guardrail_response() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    _, _, delivered = _create_delivered_report(session, trading_day=trading_day)

    result = answer_inbound_report_reply(
        session,
        update=_update(
            chat_id="12345",
            message_id=800003,
            text="What is the best long-term crypto portfolio?",
            reply_to_message_id=delivered.telegram_message_id,
        ),
        trading_day=trading_day,
    )

    assert result.guardrail_reason == "unrelated_or_too_broad"
    assert "today's premarket report" in result.response_text
