from collections.abc import Generator
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from premarket_operator.auth.dependencies import get_db_session
from premarket_operator.auth.service import create_auth_session
from premarket_operator.core.config import Settings
from premarket_operator.db.base import Base
from premarket_operator.db.models import Plan, User, UserPlan
from premarket_operator.settings.api import router as settings_router


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(settings_router)

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


def _authenticate(client: TestClient, session: Session, user: User) -> None:
    created = create_auth_session(session, user=user, ttl_days=14)
    session.commit()
    client.cookies.set(Settings.auth_session_cookie_name, created.token)


def test_settings_read_requires_authentication() -> None:
    session = _session()
    client = _client(session)

    response = client.get("/api/v1/me/settings")

    assert response.status_code == 401


def test_settings_read_returns_authenticated_user_status() -> None:
    session = _session()
    user = User(
        email="one@example.com",
        display_name="One",
        status="active",
        timezone="America/New_York",
        telegram_chat_id="12345",
        telegram_username="desk_user",
    )
    plan = Plan(code="starter", name="Starter", daily_reports_enabled=True, is_active=True)
    session.add_all([user, plan])
    session.flush()
    session.add(
        UserPlan(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            started_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
        )
    )
    session.commit()

    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/me/settings")

    assert response.status_code == 200
    assert response.json() == {
        "profile": {
            "email": "one@example.com",
            "displayName": "One",
            "timezone": "America/New_York",
        },
        "account": {
            "status": "Active",
            "planName": "Starter",
            "planStatus": "Active",
        },
        "telegram": {
            "state": "connected",
            "username": "desk_user",
            "chatId": "12345",
            "guidance": "Telegram is linked for report delivery.",
        },
    }


def test_settings_read_keeps_missing_plan_and_telegram_truth_unknown() -> None:
    session = _session()
    user = User(
        email="one@example.com",
        display_name=None,
        status="active",
        timezone="America/New_York",
    )
    session.add(user)
    session.commit()

    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/me/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"] == {
        "status": "Active",
        "planName": "Unknown",
        "planStatus": "Unknown",
    }
    assert payload["telegram"]["state"] == "not_connected"
    assert payload["telegram"]["username"] is None
    assert payload["telegram"]["chatId"] is None
