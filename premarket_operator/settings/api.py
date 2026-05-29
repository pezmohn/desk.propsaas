from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
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


class UserSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displayName: str | None = None
    timezone: str | None = None

    @model_validator(mode="after")
    def validate_partial_payload(self) -> "UserSettingsUpdateRequest":
        if "timezone" in self.model_fields_set and self.timezone is None:
            raise ValueError("Timezone is required when provided.")
        return self

    @field_validator("displayName")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) > 200:
            raise ValueError("Display name must be 200 characters or fewer.")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Timezone is required when provided.")
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Timezone must be a valid IANA timezone.") from exc
        return normalized


@router.get("/settings", response_model=UserSettingsResponse)
def read_settings(
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> UserSettingsResponse:
    settings = get_user_settings_read_model(session, user=current_user)
    return _settings_response(settings)


@router.patch("/settings", response_model=UserSettingsResponse)
def update_settings(
    update: UserSettingsUpdateRequest,
    current_user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> UserSettingsResponse:
    updated_fields = update.model_fields_set
    if "displayName" in updated_fields:
        current_user.display_name = update.displayName
    if "timezone" in updated_fields and update.timezone is not None:
        current_user.timezone = update.timezone

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

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
