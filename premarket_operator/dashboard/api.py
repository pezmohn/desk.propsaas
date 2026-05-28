from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.auth.dependencies import get_db_session, require_current_user
from premarket_operator.dashboard.read_models import (
    DashboardStatusItemReadModel,
    UserDashboardReadModel,
    get_user_dashboard_read_model,
)
from premarket_operator.db.models import User

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class DashboardStatusItemResponse(BaseModel):
    id: str
    label: str
    value: str
    detail: str
    tone: str


class UserDashboardResponse(BaseModel):
    generatedAt: str
    items: list[DashboardStatusItemResponse]


@router.get("/dashboard", response_model=UserDashboardResponse)
def read_dashboard(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> UserDashboardResponse:
    dashboard = get_user_dashboard_read_model(session, user=current_user)
    return _dashboard_response(dashboard)


def _dashboard_response(dashboard: UserDashboardReadModel) -> UserDashboardResponse:
    return UserDashboardResponse(
        generatedAt=dashboard.generatedAt,
        items=[_item_response(item) for item in dashboard.items],
    )


def _item_response(item: DashboardStatusItemReadModel) -> DashboardStatusItemResponse:
    return DashboardStatusItemResponse(**item.__dict__)
