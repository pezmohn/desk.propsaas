from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.db.base import Base
from premarket_operator.db.models import DailyReport, User
from premarket_operator.reports.read_models import (
    get_report_detail_for_user,
    list_report_history_for_user,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _create_user(session: Session, *, email: str) -> User:
    user = User(email=email, display_name=email.split("@")[0], status="active")
    session.add(user)
    session.commit()
    return user


def _create_report(
    session: Session,
    *,
    user: User,
    trading_day: date,
    status: str = "generated",
    sent_at: datetime | None = None,
) -> DailyReport:
    report = DailyReport(
        user_id=user.id,
        trading_day=trading_day,
        report_type="premarket",
        status=status,
        body_text=f"Premarket Report | {trading_day.isoformat()}",
        context_json={"watchlist": ["MU"]},
        source_version="test",
        generated_at=datetime(2026, 5, trading_day.day, 13, 15, tzinfo=UTC),
        sent_at=sent_at,
    )
    session.add(report)
    session.commit()
    return report


def test_report_history_is_scoped_to_current_user() -> None:
    session = _session()
    user_one = _create_user(session, email="one@example.com")
    user_two = _create_user(session, email="two@example.com")
    _create_report(session, user=user_one, trading_day=date(2026, 5, 27))
    _create_report(session, user=user_two, trading_day=date(2026, 5, 28))

    reports = list_report_history_for_user(session, user_id=user_one.id)

    assert len(reports) == 1
    assert reports[0].tradingDay == "2026-05-27"


def test_report_history_ordering_is_deterministic() -> None:
    session = _session()
    user = _create_user(session, email="one@example.com")
    _create_report(session, user=user, trading_day=date(2026, 5, 27))
    _create_report(session, user=user, trading_day=date(2026, 5, 28))

    reports = list_report_history_for_user(session, user_id=user.id)

    assert [report.tradingDay for report in reports] == ["2026-05-28", "2026-05-27"]


def test_report_detail_is_scoped_to_current_user() -> None:
    session = _session()
    owner = _create_user(session, email="owner@example.com")
    other = _create_user(session, email="other@example.com")
    report = _create_report(session, user=owner, trading_day=date(2026, 5, 28))

    visible = get_report_detail_for_user(session, user_id=owner.id, report_id=report.id)
    cross_tenant = get_report_detail_for_user(session, user_id=other.id, report_id=report.id)

    assert visible is not None
    assert visible.bodyText == "Premarket Report | 2026-05-28"
    assert cross_tenant is None


def test_delivery_status_uses_real_sent_at_and_status_truth() -> None:
    session = _session()
    user = _create_user(session, email="one@example.com")
    _create_report(
        session,
        user=user,
        trading_day=date(2026, 5, 28),
        status="generated",
    )
    _create_report(
        session,
        user=user,
        trading_day=date(2026, 5, 27),
        status="generated",
        sent_at=datetime(2026, 5, 27, 13, 20, tzinfo=UTC),
    )

    reports = list_report_history_for_user(session, user_id=user.id)

    assert reports[0].deliveryStatus == "not_sent"
    assert reports[0].sentAt is None
    assert reports[1].deliveryStatus == "sent"
    assert reports[1].sentAt == "2026-05-27T13:20:00+00:00"
