from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_ny() -> datetime:
    return datetime.now(NY_TZ)


def trading_day_for(value: datetime | None = None) -> date:
    current = value.astimezone(NY_TZ) if value else now_ny()
    return current.date()


def is_weekday_ny(value: datetime | None = None) -> bool:
    current = value.astimezone(NY_TZ) if value else now_ny()
    return current.isoweekday() <= 5


def is_premarket_report_time(value: datetime | None = None) -> bool:
    current = value.astimezone(NY_TZ) if value else now_ny()
    return is_weekday_ny(current) and current.strftime("%H:%M") == "09:15"
