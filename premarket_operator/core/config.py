import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./state/premarket_operator.sqlite"
    app_env: str = "local"
    app_timezone: str = "America/New_York"
    telegram_bot_token: str | None = None
    telegram_bot_username: str | None = None
    telegram_dry_run: bool = True
    auth_session_cookie_name: str = "desk_propsaas_session"
    auth_session_days: int = 14
    auth_cookie_secure: bool = False
    cors_allowed_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", Settings.app_env)
    auth_cookie_secure_raw = os.getenv("AUTH_COOKIE_SECURE")
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        app_env=app_env,
        app_timezone=os.getenv("APP_TIMEZONE", Settings.app_timezone),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_bot_username=_normalize_bot_username(os.getenv("TELEGRAM_BOT_USERNAME")),
        telegram_dry_run=os.getenv("TELEGRAM_DRY_RUN", "true").lower() in {"1", "true", "yes"},
        auth_session_cookie_name=os.getenv(
            "AUTH_SESSION_COOKIE_NAME",
            Settings.auth_session_cookie_name,
        ),
        auth_session_days=int(os.getenv("AUTH_SESSION_DAYS", str(Settings.auth_session_days))),
        auth_cookie_secure=_bool_env(auth_cookie_secure_raw, default=app_env != "local"),
        cors_allowed_origins=_csv_env(
            os.getenv("CORS_ALLOWED_ORIGINS"),
            Settings.cors_allowed_origins,
        ),
    )


def _bool_env(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes"}


def _csv_env(raw: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _normalize_bot_username(raw: str | None) -> str | None:
    if not raw:
        return None
    normalized = raw.strip().lstrip("@")
    return normalized or None
