from collections.abc import Generator
from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from premarket_operator.auth.api import router as auth_router
from premarket_operator.auth.dependencies import get_db_session
from premarket_operator.auth.service import create_auth_session
from premarket_operator.core.config import Settings
from premarket_operator.db.base import Base
from premarket_operator.db.models import DailyReport, User
from premarket_operator.reports.api import router as reports_router


def _client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(reports_router)

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


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0], status="active")
    session.add(user)
    session.commit()
    return user


def _authenticate(client: TestClient, session: Session, user: User) -> None:
    created = create_auth_session(session, user=user, ttl_days=14)
    session.commit()
    client.cookies.set(Settings.auth_session_cookie_name, created.token)


def _create_report(
    session: Session,
    *,
    user: User,
    trading_day: date,
    sent_at: datetime | None = None,
) -> DailyReport:
    report = DailyReport(
        user_id=user.id,
        trading_day=trading_day,
        report_type="premarket",
        status="sent" if sent_at else "generated",
        body_text=f"Premarket Report | {trading_day.isoformat()}",
        context_json={"watchlist": ["MU"]},
        source_version="test",
        generated_at=datetime(2026, 5, trading_day.day, 13, 15, tzinfo=UTC),
        sent_at=sent_at,
    )
    session.add(report)
    session.commit()
    return report


def test_session_read_requires_authentication() -> None:
    session = _session()
    client = _client(session)

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 401


def test_session_read_returns_authenticated_user() -> None:
    session = _session()
    user = _create_user(session, email="one@example.com")
    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": "one@example.com",
        "displayName": "one",
        "role": "user",
    }


def test_logout_revokes_session_and_returns_clean_no_content() -> None:
    session = _session()
    user = _create_user(session, email="one@example.com")
    client = _client(session)
    _authenticate(client, session, user)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/v1/auth/session").status_code == 401


def test_session_read_returns_persisted_admin_role() -> None:
    session = _session()
    user = _create_user(session, email="admin@example.com")
    user.role = "admin"
    session.commit()
    client = _client(session)
    _authenticate(client, session, user)

    response = client.get("/api/v1/auth/session")

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_report_list_is_scoped_to_authenticated_user() -> None:
    session = _session()
    user_one = _create_user(session, email="one@example.com")
    user_two = _create_user(session, email="two@example.com")
    _create_report(session, user=user_one, trading_day=date(2026, 5, 27))
    _create_report(session, user=user_two, trading_day=date(2026, 5, 28))
    client = _client(session)
    _authenticate(client, session, user_one)

    response = client.get("/api/v1/me/reports")

    assert response.status_code == 200
    assert [item["tradingDay"] for item in response.json()] == ["2026-05-27"]


def test_report_detail_is_scoped_to_authenticated_user() -> None:
    session = _session()
    owner = _create_user(session, email="owner@example.com")
    other = _create_user(session, email="other@example.com")
    report = _create_report(session, user=owner, trading_day=date(2026, 5, 28))
    client = _client(session)
    _authenticate(client, session, owner)

    visible = client.get(f"/api/v1/me/reports/{report.id}")

    assert visible.status_code == 200
    assert visible.json()["bodyText"] == "Premarket Report | 2026-05-28"

    other_client = _client(session)
    _authenticate(other_client, session, other)
    cross_tenant = other_client.get(f"/api/v1/me/reports/{report.id}")

    assert cross_tenant.status_code == 404
    assert cross_tenant.json()["detail"] == "Report not found."


def test_report_detail_unknown_id_returns_same_not_found_shape() -> None:
    session = _session()
    user = _create_user(session, email="one@example.com")
    client = _client(session)
    _authenticate(client, session, user)

    response = client.get(f"/api/v1/me/reports/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found."
