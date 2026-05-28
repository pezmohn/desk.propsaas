from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.auth.dependencies import get_db_session, require_current_user
from premarket_operator.auth.service import (
    AuthError,
    authenticate_user,
    create_auth_session,
    revoke_auth_session,
)
from premarket_operator.core.config import Settings, get_settings
from premarket_operator.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUserResponse(BaseModel):
    id: str
    email: str
    displayName: str | None = None
    role: str


@router.post("/login", response_model=AuthUserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthUserResponse:
    try:
        user = authenticate_user(session, email=payload.email, password=payload.password)
        created = create_auth_session(session, user=user, ttl_days=settings.auth_session_days)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    session.commit()
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=created.token,
        max_age=settings.auth_session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return _auth_user_response(created.user)


@router.get("/session", response_model=AuthUserResponse)
def read_session(current_user: User = Depends(require_current_user)) -> AuthUserResponse:
    return _auth_user_response(current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    token = request.cookies.get(settings.auth_session_cookie_name)
    revoke_auth_session(session, token=token)
    session.commit()
    response.delete_cookie(key=settings.auth_session_cookie_name, path="/")
    return response


def _auth_user_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=str(user.id),
        email=user.email or "",
        displayName=user.display_name,
        role="user",
    )
