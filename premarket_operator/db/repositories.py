from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select

from premarket_operator.core.errors import TenantScopeError


def require_user_id(user_id: UUID | str | None) -> UUID | str:
    if user_id is None:
        raise TenantScopeError("Tenant-scoped queries require user_id.")
    return user_id


def scoped_by_user(statement: Select, model, user_id: UUID | str | None) -> Select:
    require_user_id(user_id)
    return statement.where(model.user_id == user_id)
