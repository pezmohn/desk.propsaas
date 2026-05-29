from collections.abc import Generator
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from premarket_operator.admin.api import router as admin_router
from premarket_operator.auth.dependencies import get_db_session
from premarket_operator.auth.service import create_auth_session
from premarket_operator.core.config import Settings
from premarket_operator.core.time import trading_day_for
from premarket_operator.db.base import Base
from premarket_operator.db.models import DailyReport, Plan, User, UserPlan


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(admin_router)

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


def _user(
    session: Session,
    *,
    email: str,
    role: str = "user",
    telegram_chat_id: str | None = None,
    display_name: str | None = None,
) -> User:
    user = User(
        email=email,
        display_name=display_name,
        role=role,
        status="active",
        telegram_chat_id=telegram_chat_id,
    )
    session.add(user)
    session.flush()
    return user


def _add_plan(session: Session, user: User, *, reports_enabled: bool = True) -> None:
    plan = Plan(
        code=f"plan-{user.id}",
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
            started_at=datetime(2026, 5, 29, 12, 0, tzinfo=UTC),
        )
    )
    session.flush()


def _add_report(
    session: Session,
    user: User,
    *,
    trading_day: date,
    status: str = "generated",
    sent_at: datetime | None = None,
) -> DailyReport:
    report = DailyReport(
        user_id=user.id,
        trading_day=trading_day,
        report_type="premarket",
        status=status,
        body_text="Premarket Report",
        context_json={"watchlist": []},
        source_version="test",
        generated_at=datetime(2026, 5, 29, 12, 0, tzinfo=UTC),
        sent_at=sent_at,
    )
    session.add(report)
    session.flush()
    return report


def test_admin_live_day_requires_authentication() -> None:
    session = _session()
    client = _client(session)

    response = client.get("/api/v1/admin/live-day")

    assert response.status_code == 401


def test_admin_live_day_rejects_non_admin_user() -> None:
    session = _session()
    user = _user(session, email="user@example.com", role="user")
    session.commit()
    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/admin/live-day")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_live_day_returns_empty_shape_for_admin_with_no_users() -> None:
    session = _session()
    admin = _user(session, email="admin@example.com", role="admin")
    session.commit()
    client = _client(session)
    _authenticate(client, session, admin)

    response = client.get("/api/v1/admin/live-day")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tradingDay"]
    assert payload["summary"] == {
        "totalUsers": 0,
        "eligibleUsers": 0,
        "linkedUsers": 0,
        "reportsGenerated": 0,
        "reportsSent": 0,
        "blockedUsers": 0,
    }
    assert payload["users"] == []


def test_admin_live_day_returns_populated_delivery_state() -> None:
    session = _session()
    trading_day = trading_day_for()
    admin = _user(session, email="admin@example.com", role="admin", telegram_chat_id="admin-chat")
    ready = _user(
        session,
        email="ready@example.com",
        display_name="Ready User",
        telegram_chat_id="ready-chat",
    )
    missing_report = _user(
        session,
        email="missing-report@example.com",
        telegram_chat_id="missing-report-chat",
    )
    missing_telegram = _user(session, email="missing-telegram@example.com")
    _add_plan(session, admin)
    for user in (ready, missing_report, missing_telegram):
        _add_plan(session, user)
    sent_at = datetime(2026, 5, 29, 12, 5, tzinfo=UTC)
    _add_report(session, ready, trading_day=trading_day, status="sent", sent_at=sent_at)
    session.commit()

    client = _client(session)
    _authenticate(client, session, admin)

    response = client.get("/api/v1/admin/live-day")

    assert response.status_code == 200
    payload = response.json()
    rows = {row["email"]: row for row in payload["users"]}
    assert payload["summary"]["totalUsers"] == 3
    assert payload["summary"]["eligibleUsers"] == 1
    assert payload["summary"]["linkedUsers"] == 2
    assert payload["summary"]["reportsGenerated"] == 1
    assert payload["summary"]["reportsSent"] == 1
    assert payload["summary"]["blockedUsers"] == 2
    assert rows["ready@example.com"] == {
        "userId": rows["ready@example.com"]["userId"],
        "email": "ready@example.com",
        "displayName": "Ready User",
        "eligible": True,
        "telegramLinked": True,
        "reportGenerated": True,
        "reportSent": True,
        "blocker": None,
        "reportStatus": "sent",
        "sentAt": "2026-05-29T12:05:00+00:00",
    }
    assert rows["missing-report@example.com"]["blocker"] == "Missing daily report"
    assert rows["missing-telegram@example.com"]["blocker"] == "Telegram not linked or account inactive"
