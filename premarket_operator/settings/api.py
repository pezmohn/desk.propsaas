from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from premarket_operator.auth.dependencies import get_db_session, require_current_user
from premarket_operator.db.models import User
from premarket_operator.settings.read_models import (
    SettingsAccountReadModel,
    SettingsProfileReadModel,
    SettingsTelegramReadModel,
    UserSettingsReadModel,
    get_user_settings_read_model,
)

router = APIRouter(prefix="/api/v1/me", tags=["me"])


class SettingsProfileResponse(BaseModel):
    email: str
    displayName: str | None
    timezone: str


class SettingsAccountResponse(BaseModel):
    status: str
    planName: str
    planStatus: str


class SettingsTelegramResponse(BaseModel):
    state: str
    username: str | None
    chatId: str | None
    guidance: str


class UserSettingsResponse(BaseModel):
    profile: SettingsProfileResponse
    account: SettingsAccountResponse
    telegram: SettingsTelegramResponse


@router.get("/settings", response_model=UserSettingsResponse)
def read_settings(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> UserSettingsResponse:
    settings = get_user_settings_read_model(session, user=current_user)
    return _settings_response(settings)


def _settings_response(settings: UserSettingsReadModel) -> UserSettingsResponse:
    return UserSettingsResponse(
        profile=_profile_response(settings.profile),
        account=_account_response(settings.account),
        telegram=_telegram_response(settings.telegram),
    )


def _profile_response(profile: SettingsProfileReadModel) -> SettingsProfileResponse:
    return SettingsProfileResponse(**profile.__dict__)


def _account_response(account: SettingsAccountReadModel) -> SettingsAccountResponse:
    return SettingsAccountResponse(**account.__dict__)


def _telegram_response(telegram: SettingsTelegramReadModel) -> SettingsTelegramResponse:
    return SettingsTelegramResponse(**telegram.__dict__)
