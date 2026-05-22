from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.chat.service import InboundReplyRoutingError, route_inbound_report_reply
from premarket_operator.db.base import Base
from premarket_operator.db.models import ChatMessage, TelegramMessage
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


def _update(
    *,
    chat_id: str,
    message_id: int,
    text: str,
    reply_to_message_id: int | None = None,
) -> dict:
    message = {
        "message_id": message_id,
        "chat": {"id": chat_id},
        "text": text,
    }
    if reply_to_message_id is not None:
        message["reply_to_message"] = {"message_id": reply_to_message_id}
    return {"update_id": message_id, "message": message}


def test_reply_to_report_mapping_resolves_and_persists_user_message() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, report = _create_user_with_report(
        session,
        email="one@example.com",
        chat_id="12345",
        trading_day=trading_day,
    )
    delivered = deliver_daily_report_to_user(
        session,
        user_id=user.id,
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()

    route = route_inbound_report_reply(
        session,
        update=_update(
            chat_id="12345",
            message_id=700001,
            text="What matters most on MU?",
            reply_to_message_id=delivered.telegram_message_id,
        ),
        trading_day=trading_day,
    )
    session.commit()

    assert route.user_id == user.id
    assert route.daily_report_id == report.id
    assert route.resolution_method == "reply_to_report_message"
    telegram_message = session.get(TelegramMessage, route.telegram_message_id)
    chat_message = session.get(ChatMessage, route.chat_message_id)
    assert telegram_message.user_id == user.id
    assert telegram_message.daily_report_id == report.id
    assert telegram_message.direction == "inbound"
    assert chat_message.role == "user"
    assert chat_message.content == "What matters most on MU?"


def test_same_user_same_day_fallback_when_no_reply_mapping_exists() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user, report = _create_user_with_report(
        session,
        email="one@example.com",
        chat_id="12345",
        trading_day=trading_day,
    )

    route = route_inbound_report_reply(
        session,
        update=_update(chat_id="12345", message_id=700002, text="Any key levels?"),
        trading_day=trading_day,
    )

    assert route.user_id == user.id
    assert route.daily_report_id == report.id
    assert route.resolution_method == "same_user_same_day_fallback"


def test_unresolved_context_fails_safe_without_same_day_report() -> None:
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

    with pytest.raises(InboundReplyRoutingError):
        route_inbound_report_reply(
            session,
            update=_update(chat_id="12345", message_id=700003, text="Any key levels?"),
            trading_day=trading_day,
        )


def test_cross_user_reply_mapping_does_not_leak_context() -> None:
    session = _session()
    trading_day = date(2026, 5, 22)
    user_one, _ = _create_user_with_report(
        session,
        email="one@example.com",
        chat_id="11111",
        trading_day=trading_day,
    )
    user_two, report_two = _create_user_with_report(
        session,
        email="two@example.com",
        chat_id="22222",
        trading_day=trading_day,
    )
    delivered_one = deliver_daily_report_to_user(
        session,
        user_id=user_one.id,
        trading_day=trading_day,
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()

    route = route_inbound_report_reply(
        session,
        update=_update(
            chat_id="22222",
            message_id=700004,
            text="Can I see that report?",
            reply_to_message_id=delivered_one.telegram_message_id,
        ),
        trading_day=trading_day,
    )

    assert route.user_id == user_two.id
    assert route.daily_report_id == report_two.id
    assert route.resolution_method == "same_user_same_day_fallback"
