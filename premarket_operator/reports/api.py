from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.auth.dependencies import get_db_session, require_current_user
from premarket_operator.db.models import User
from premarket_operator.reports.read_models import (
    ReportDetailReadModel,
    ReportListItemReadModel,
    get_report_detail_for_user,
    list_report_history_for_user,
)

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class ReportListItemResponse(BaseModel):
    id: str
    tradingDay: str
    title: str
    deliveryStatus: str
    sentAt: str | None
    generatedAt: str


class ReportDetailResponse(ReportListItemResponse):
    bodyText: str


@router.get("/reports", response_model=list[ReportListItemResponse])
def list_reports(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> list[ReportListItemResponse]:
    reports = list_report_history_for_user(session, user_id=current_user.id)
    return [_list_response(report) for report in reports]


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(
    report_id: UUID,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> ReportDetailResponse:
    report = get_report_detail_for_user(
        session,
        user_id=current_user.id,
        report_id=report_id,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return _detail_response(report)


def _list_response(report: ReportListItemReadModel) -> ReportListItemResponse:
    return ReportListItemResponse(**report.__dict__)


def _detail_response(report: ReportDetailReadModel) -> ReportDetailResponse:
    return ReportDetailResponse(**report.__dict__)
