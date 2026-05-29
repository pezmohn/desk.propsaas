from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.admin.read_models import (
    AdminLiveDayReadModel,
    AdminLiveDaySummaryReadModel,
    AdminLiveDayUserRowReadModel,
    get_admin_live_day_read_model,
)
from premarket_operator.auth.dependencies import get_db_session, require_admin_user
from premarket_operator.db.models import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AdminLiveDaySummaryResponse(BaseModel):
    totalUsers: int
    eligibleUsers: int
    linkedUsers: int
    reportsGenerated: int
    reportsSent: int
    blockedUsers: int


class AdminLiveDayUserResponse(BaseModel):
    userId: str
    email: str
    displayName: str | None = None
    eligible: bool
    telegramLinked: bool
    reportGenerated: bool
    reportSent: bool
    blocker: str | None = None
    reportStatus: str | None = None
    sentAt: str | None = None


class AdminLiveDayResponse(BaseModel):
    tradingDay: str
    generatedAt: str
    summary: AdminLiveDaySummaryResponse
    users: list[AdminLiveDayUserResponse]


@router.get("/live-day", response_model=AdminLiveDayResponse)
def read_admin_live_day(
    _: User = Depends(require_admin_user),
    session: Session = Depends(get_db_session),
) -> AdminLiveDayResponse:
    live_day = get_admin_live_day_read_model(session)
    return _live_day_response(live_day)


def _live_day_response(live_day: AdminLiveDayReadModel) -> AdminLiveDayResponse:
    return AdminLiveDayResponse(
        tradingDay=live_day.tradingDay,
        generatedAt=live_day.generatedAt,
        summary=_summary_response(live_day.summary),
        users=[_user_response(row) for row in live_day.users],
    )


def _summary_response(summary: AdminLiveDaySummaryReadModel) -> AdminLiveDaySummaryResponse:
    return AdminLiveDaySummaryResponse(**summary.__dict__)


def _user_response(row: AdminLiveDayUserRowReadModel) -> AdminLiveDayUserResponse:
    return AdminLiveDayUserResponse(**row.__dict__)
