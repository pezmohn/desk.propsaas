from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from premarket_operator.auth.dependencies import get_db_session
from premarket_operator.auth.service import create_auth_session
from premarket_operator.core.config import Settings
from premarket_operator.db.base import Base
from premarket_operator.db.models import TelegramMessage, User
from premarket_operator.telegram.client import TelegramClient
from premarket_operator.telegram.link_api import router as telegram_link_router
from premarket_operator.telegram.linking import (
    TelegramLinkError,
    complete_telegram_link,
    create_telegram_link_token,
)
from premarket_operator.telegram.schemas import parse_inbound_text_message
from premarket_operator.telegram.webhook import process_telegram_webhook_update


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(telegram_link_router)

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app)


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _user(session: Session, *, email: str, chat_id: str | None = None) -> User:
    user = User(
        email=email,
        display_name=email.split("@")[0],
        status="active",
        telegram_chat_id=chat_id,
    )
    session.add(user)
    session.commit()
    return user


def _authenticate(client: TestClient, session: Session, user: User) -> None:
    created = create_auth_session(session, user=user, ttl_days=14)
    session.commit()
    client.cookies.set(Settings.auth_session_cookie_name, created.token)


def _update(*, chat_id: str, text: str, username: str = "desk_user") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1001,
            "from": {"id": 5001, "username": username},
            "chat": {"id": chat_id},
            "text": text,
        },
    }


def test_telegram_link_state_requires_authentication() -> None:
    session = _session()
    client = _client(session)

    response = client.get("/api/v1/me/telegram-link")

    assert response.status_code == 401


def test_telegram_link_state_returns_authenticated_user_state() -> None:
    session = _session()
    user = _user(session, email="one@example.com", chat_id="12345")
    user.telegram_username = "desk_user"
    session.commit()
    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/me/telegram-link")

    assert response.status_code == 200
    assert response.json()["state"] == "connected"
    assert response.json()["chatId"] == "12345"
    assert response.json()["username"] == "desk_user"


def test_telegram_link_start_creates_short_lived_command_for_current_user() -> None:
    session = _session()
    user = _user(session, email="one@example.com")
    client = _client(session)
    _authenticate(client, session, user)

    response = client.post("/api/v1/me/telegram-link")

    assert response.status_code == 200
    payload = response.json()
    assert payload["startCommand"].startswith("/start link_")
    assert payload["expiresAt"]
    assert "Telegram" in payload["instructions"]


def test_telegram_link_completion_binds_chat_identity_to_token_owner() -> None:
    session = _session()
    owner = _user(session, email="owner@example.com")
    other = _user(session, email="other@example.com")
    link = create_telegram_link_token(session, user=owner)
    session.commit()

    inbound = parse_inbound_text_message(
        _update(chat_id="77777", text=link.start_command, username="owner_telegram")
    )
    completion = complete_telegram_link(session, token=link.token, inbound=inbound)
    session.commit()
    session.refresh(owner)
    session.refresh(other)

    assert completion.user.id == owner.id
    assert owner.telegram_chat_id == "77777"
    assert owner.telegram_username == "owner_telegram"
    assert other.telegram_chat_id is None


def test_telegram_link_completion_rejects_expired_token() -> None:
    session = _session()
    user = _user(session, email="one@example.com")
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    link = create_telegram_link_token(session, user=user, current_time=now, ttl_minutes=1)
    session.commit()
    inbound = parse_inbound_text_message(_update(chat_id="77777", text=link.start_command))

    try:
        complete_telegram_link(
            session,
            token=link.token,
            inbound=inbound,
            current_time=now + timedelta(minutes=2),
        )
    except TelegramLinkError as exc:
        assert "invalid or expired" in str(exc)
    else:
        raise AssertionError("Expected expired Telegram link token to be rejected.")


def test_telegram_link_completion_rejects_chat_already_linked_to_another_user() -> None:
    session = _session()
    owner = _user(session, email="owner@example.com")
    _user(session, email="other@example.com", chat_id="77777")
    link = create_telegram_link_token(session, user=owner)
    session.commit()
    inbound = parse_inbound_text_message(_update(chat_id="77777", text=link.start_command))

    try:
        complete_telegram_link(session, token=link.token, inbound=inbound)
    except TelegramLinkError as exc:
        assert "already linked" in str(exc)
    else:
        raise AssertionError("Expected linked Telegram chat identity to be rejected.")


def test_telegram_webhook_completes_link_and_persists_messages() -> None:
    session = _session()
    user = _user(session, email="one@example.com")
    link = create_telegram_link_token(session, user=user)
    session.commit()

    result = process_telegram_webhook_update(
        session,
        update=_update(chat_id="77777", text=link.start_command, username="desk_user"),
        trading_day=datetime.now(UTC).date(),
        telegram_client=TelegramClient(dry_run=True),
    )
    session.commit()
    session.refresh(user)

    messages = session.query(TelegramMessage).order_by(TelegramMessage.direction).all()
    assert result.event_type == "telegram_link_completed"
    assert result.user_id == user.id
    assert user.telegram_chat_id == "77777"
    assert user.telegram_username == "desk_user"
    assert {message.message_type for message in messages} == {
        "telegram_link",
        "telegram_link_confirmation",
    }
