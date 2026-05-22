from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from premarket_operator.db.models import User


class UserNotFoundError(LookupError):
    pass


def get_user(session: Session, *, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def require_user(session: Session, *, user_id: UUID) -> User:
    user = get_user(session, user_id=user_id)
    if user is None:
        raise UserNotFoundError(f"User not found: {user_id}")
    return user


def get_user_by_email(session: Session, *, email: str) -> User | None:
    return session.scalars(select(User).where(User.email == email)).one_or_none()


def get_user_by_telegram_chat_id(session: Session, *, telegram_chat_id: str) -> User | None:
    return session.scalars(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    ).one_or_none()


def get_or_create_user(
    session: Session,
    *,
    email: str | None = None,
    display_name: str | None = None,
    telegram_chat_id: str | None = None,
    telegram_username: str | None = None,
) -> User:
    user = None
    if email:
        user = get_user_by_email(session, email=email)
    if user is None and telegram_chat_id:
        user = get_user_by_telegram_chat_id(session, telegram_chat_id=telegram_chat_id)
    if user is None:
        user = User(
            email=email,
            display_name=display_name,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
            status="active",
        )
        session.add(user)
        session.flush()
    else:
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        if telegram_chat_id and user.telegram_chat_id != telegram_chat_id:
            user.telegram_chat_id = telegram_chat_id
        if telegram_username and user.telegram_username != telegram_username:
            user.telegram_username = telegram_username
    return user


def list_active_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).where(User.status == "active")).all())


def user_can_receive_telegram(user: User) -> bool:
    return user.status == "active" and bool(user.telegram_chat_id)
