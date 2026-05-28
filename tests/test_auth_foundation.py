from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from premarket_operator.auth.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from premarket_operator.auth.service import (
    AuthError,
    authenticate_user,
    create_auth_session,
    get_user_for_session_token,
    revoke_auth_session,
    set_user_password,
)
from premarket_operator.db.base import Base
from premarket_operator.db.models import AuthSession, User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_password_hash_verification() -> None:
    stored = hash_password("secret")

    assert verify_password("secret", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("secret", None)


def test_authenticate_user_requires_active_user_with_password_hash() -> None:
    session = _session()
    user = User(email="one@example.com", display_name="One", status="active")
    session.add(user)
    session.commit()

    try:
        authenticate_user(session, email="one@example.com", password="secret")
    except AuthError:
        pass
    else:
        raise AssertionError("Authentication should fail before a password is set.")

    set_user_password(session, user=user, password="secret")
    session.commit()

    authenticated = authenticate_user(session, email="ONE@example.com", password="secret")
    assert authenticated.id == user.id


def test_session_token_resolves_current_user_and_can_be_revoked() -> None:
    session = _session()
    user = User(email="one@example.com", display_name="One", status="active")
    session.add(user)
    session.commit()

    created = create_auth_session(session, user=user, ttl_days=14)
    session.commit()

    resolved = get_user_for_session_token(session, token=created.token)
    assert resolved is not None
    assert resolved.id == user.id

    assert revoke_auth_session(session, token=created.token)
    session.commit()

    assert get_user_for_session_token(session, token=created.token) is None


def test_expired_session_token_does_not_resolve_user() -> None:
    session = _session()
    user = User(email="one@example.com", display_name="One", status="active")
    session.add(user)
    session.commit()

    token = new_session_token()
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    session.commit()

    assert get_user_for_session_token(session, token=token) is None
