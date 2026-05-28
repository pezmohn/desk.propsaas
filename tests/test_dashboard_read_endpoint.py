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
from premarket_operator.core.time import trading_day_for
from premarket_operator.dashboard.api import router as dashboard_router
from premarket_operator.db.base import Base
from premarket_operator.db.models import DailyReport, Plan, User, UserPlan


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(dashboard_router)

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


def _add_active_plan(session: Session, user: User, *, reports_enabled: bool = True) -> Plan:
    plan = Plan(
        code=f"starter-{user.id}",
        name="Starter",
        daily_reports_enabled=reports_enabled,
        is_active=True,
    )
    session.add(plan)
    session.flush()
    session.add(
        UserPlan(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            started_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
        )
    )
    session.flush()
    return plan


def test_dashboard_read_requires_authentication() -> None:
    session = _session()
    client = _client(session)

    response = client.get("/api/v1/me/dashboard")

    assert response.status_code == 401


def test_dashboard_read_returns_authenticated_user_status() -> None:
    session = _session()
    user = User(
        email="one@example.com",
        display_name="One",
        status="active",
        telegram_chat_id="12345",
    )
    session.add(user)
    session.flush()
    _add_active_plan(session, user)
    today = trading_day_for()
    session.add(
        DailyReport(
            user_id=user.id,
            trading_day=today,
            report_type="premarket",
            status="sent",
            body_text="Premarket Report",
            context_json={"watchlist": ["MU"]},
            source_version="test",
            generated_at=datetime(2026, 5, 28, 12, 0, tzinfo=UTC),
            sent_at=datetime(2026, 5, 28, 12, 5, tzinfo=UTC),
        )
    )
    session.commit()

    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/me/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["generatedAt"]
    items = {item["id"]: item for item in payload["items"]}
    assert items["plan"]["value"] == "Starter"
    assert items["plan"]["tone"] == "ready"
    assert items["telegram"]["value"] == "Connected"
    assert items["report"]["value"] == "Sent"
    assert items["delivery"]["value"] == "2026-05-28T12:05:00+00:00"
    assert items["blocker"]["value"] == "None detected"


def test_dashboard_read_keeps_missing_truth_explicit() -> None:
    session = _session()
    user = User(
        email="one@example.com",
        display_name=None,
        status="active",
        telegram_username="desk_user",
    )
    session.add(user)
    session.commit()

    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/me/dashboard")

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert items["plan"]["value"] == "Unknown"
    assert items["plan"]["tone"] == "unknown"
    assert items["telegram"]["value"] == "Incomplete"
    assert items["report"]["value"] == "No report found"
    assert items["report"]["tone"] == "unknown"
    assert items["delivery"]["value"] == "No delivery recorded"
    assert items["blocker"]["value"] == "No active plan"
    assert items["blocker"]["tone"] == "blocked"
