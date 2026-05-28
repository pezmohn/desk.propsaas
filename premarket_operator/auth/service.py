from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from premarket_operator.auth.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from premarket_operator.db.models import AuthSession, User


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class CreatedSession:
    user: User
    token: str
    expires_at: datetime


def set_user_password(session: Session, *, user: User, password: str) -> None:
    user.password_hash = hash_password(password)
    session.flush()


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    user = _get_user_by_normalized_email(session, email=email)
    if user is None or user.status != "active":
        raise AuthError("Invalid email or password.")
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    return user


def create_auth_session(session: Session, *, user: User, ttl_days: int) -> CreatedSession:
    if user.status != "active":
        raise AuthError("Inactive users cannot start sessions.")

    token = new_session_token()
    expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=expires_at,
    )
    session.add(auth_session)
    session.flush()
    return CreatedSession(user=user, token=token, expires_at=expires_at)


def get_user_for_session_token(session: Session, *, token: str | None) -> User | None:
    if not token:
        return None

    now = datetime.now(UTC)
    statement = (
        select(AuthSession)
        .join(User)
        .where(
            AuthSession.token_hash == hash_session_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
            User.status == "active",
        )
    )
    auth_session = session.scalars(statement).one_or_none()
    if auth_session is None:
        return None

    return auth_session.user


def revoke_auth_session(session: Session, *, token: str | None) -> bool:
    if not token:
        return False

    auth_session = session.scalars(
        select(AuthSession).where(
            AuthSession.token_hash == hash_session_token(token),
            AuthSession.revoked_at.is_(None),
        )
    ).one_or_none()
    if auth_session is None:
        return False

    auth_session.revoked_at = datetime.now(UTC)
    session.flush()
    return True


def _get_user_by_normalized_email(session: Session, *, email: str) -> User | None:
    normalized = email.strip().lower()
    if not normalized:
        return None
    return session.scalars(select(User).where(func.lower(User.email) == normalized)).one_or_none()
