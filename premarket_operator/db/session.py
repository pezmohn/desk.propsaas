from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import make_url

from premarket_operator.core.config import get_settings
from premarket_operator.db.base import Base
import premarket_operator.db.models  # noqa: F401


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    parsed = make_url(database_url)
    if parsed.drivername != "sqlite" or not parsed.database:
        return
    if parsed.database in (":memory:",):
        return
    Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    _ensure_sqlite_parent_dir(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def create_all_tables(database_url: str | None = None) -> None:
    target_engine = make_engine(database_url) if database_url else engine
    Base.metadata.create_all(bind=target_engine)
