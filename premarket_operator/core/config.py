import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./state/premarket_operator.sqlite"
    app_env: str = "local"
    app_timezone: str = "America/New_York"
    telegram_bot_token: str | None = None
    telegram_dry_run: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        app_env=os.getenv("APP_ENV", Settings.app_env),
        app_timezone=os.getenv("APP_TIMEZONE", Settings.app_timezone),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_dry_run=os.getenv("TELEGRAM_DRY_RUN", "true").lower() in {"1", "true", "yes"},
    )
