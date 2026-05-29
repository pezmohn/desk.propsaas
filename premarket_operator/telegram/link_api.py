from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.auth.dependencies import get_db_session, require_current_user
from premarket_operator.core.config import Settings, get_settings
from premarket_operator.db.models import User
from premarket_operator.settings.api import SettingsTelegramResponse, _telegram_response
from premarket_operator.settings.read_models import get_user_settings_read_model
from premarket_operator.telegram.linking import create_telegram_link_token

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class TelegramLinkStartResponse(BaseModel):
    expiresAt: str
    startCommand: str
    deepLink: str | None = None
    instructions: str


@router.get("/telegram-link", response_model=SettingsTelegramResponse)
def read_telegram_link_state(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> SettingsTelegramResponse:
    settings = get_user_settings_read_model(session, user=current_user)
    return _telegram_response(settings.telegram)


@router.post("/telegram-link", response_model=TelegramLinkStartResponse)
def start_telegram_link(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> TelegramLinkStartResponse:
    link = create_telegram_link_token(session, user=current_user)
    session.commit()
    return TelegramLinkStartResponse(
        expiresAt=link.expires_at.isoformat(),
        startCommand=link.start_command,
        deepLink=_deep_link(settings.telegram_bot_username, link.start_payload),
        instructions=(
            "Open the Telegram bot and send the start command shown here. "
            "Settings will show connected after the bot receives that command."
        ),
    )


def _deep_link(bot_username: str | None, payload: str) -> str | None:
    if not bot_username:
        return None
    return f"https://t.me/{bot_username}?start={payload}"
