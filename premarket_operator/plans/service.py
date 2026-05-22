from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import Plan, UserPlan
from premarket_operator.db.repositories import require_user_id

DEFAULT_PLAN_CODE = "starter"


def get_or_create_default_plan(session: Session) -> Plan:
    plan = session.scalars(select(Plan).where(Plan.code == DEFAULT_PLAN_CODE)).one_or_none()
    if plan is None:
        plan = Plan(
            code=DEFAULT_PLAN_CODE,
            name="Starter",
            daily_reports_enabled=True,
            daily_chat_reply_limit=20,
            is_active=True,
        )
        session.add(plan)
        session.flush()
    return plan


def get_active_user_plan(session: Session, *, user_id: UUID) -> UserPlan | None:
    require_user_id(user_id)
    statement = (
        select(UserPlan)
        .join(Plan)
        .where(
            UserPlan.user_id == user_id,
            UserPlan.status == "active",
            UserPlan.ended_at.is_(None),
            Plan.is_active.is_(True),
        )
        .order_by(UserPlan.started_at.desc())
    )
    return session.scalars(statement).first()


def ensure_default_plan_for_user(session: Session, *, user_id: UUID) -> UserPlan:
    require_user_id(user_id)
    existing = get_active_user_plan(session, user_id=user_id)
    if existing is not None:
        return existing

    plan = get_or_create_default_plan(session)
    user_plan = UserPlan(
        user_id=user_id,
        plan_id=plan.id,
        status="active",
        started_at=datetime.now(UTC),
    )
    session.add(user_plan)
    session.flush()
    return user_plan


def reports_enabled_for_user(session: Session, *, user_id: UUID) -> bool:
    require_user_id(user_id)
    user_plan = get_active_user_plan(session, user_id=user_id)
    return bool(
        user_plan
        and user_plan.plan
        and user_plan.plan.is_active
        and user_plan.plan.daily_reports_enabled
    )
