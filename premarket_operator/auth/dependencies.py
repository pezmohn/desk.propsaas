from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from premarket_operator.auth.service import get_user_for_session_token
from premarket_operator.core.config import Settings, get_settings
from premarket_operator.db.models import User
from premarket_operator.db.session import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def get_optional_current_user(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User | None:
    token = request.cookies.get(settings.auth_session_cookie_name)
    return get_user_for_session_token(session, token=token)


def require_current_user(
    current_user: User | None = Depends(get_optional_current_user),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return current_user
