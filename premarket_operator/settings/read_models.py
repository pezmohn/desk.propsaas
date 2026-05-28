from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from premarket_operator.db.models import User
from premarket_operator.plans.service import get_active_user_plan


@dataclass(frozen=True)
class SettingsProfileReadModel:
    email: str
    displayName: str | None
    timezone: str


@dataclass(frozen=True)
class SettingsAccountReadModel:
    status: str
    planName: str
    planStatus: str


@dataclass(frozen=True)
class SettingsTelegramReadModel:
    state: str
    username: str | None
    chatId: str | None
    guidance: str


@dataclass(frozen=True)
class UserSettingsReadModel:
    profile: SettingsProfileReadModel
    account: SettingsAccountReadModel
    telegram: SettingsTelegramReadModel


def get_user_settings_read_model(
    session: Session,
    *,
    user: User,
) -> UserSettingsReadModel:
    user_plan = get_active_user_plan(session, user_id=user.id)
    return UserSettingsReadModel(
        profile=SettingsProfileReadModel(
            email=user.email or "",
            displayName=user.display_name,
            timezone=user.timezone,
        ),
        account=SettingsAccountReadModel(
            status=_display_status(user.status),
            planName=user_plan.plan.name if user_plan and user_plan.plan else "Unknown",
            planStatus=_display_status(user_plan.status) if user_plan else "Unknown",
        ),
        telegram=_telegram_read_model(
            chat_id=user.telegram_chat_id,
            username=user.telegram_username,
        ),
    )


def _telegram_read_model(
    *,
    chat_id: str | None,
    username: str | None,
) -> SettingsTelegramReadModel:
    if chat_id:
        return SettingsTelegramReadModel(
            state="connected",
            username=username,
            chatId=chat_id,
            guidance="Telegram is linked for report delivery.",
        )
    if username:
        return SettingsTelegramReadModel(
            state="incomplete",
            username=username,
            chatId=None,
            guidance="Telegram username is present, but no chat identity is linked for delivery yet.",
        )
    return SettingsTelegramReadModel(
        state="not_connected",
        username=None,
        chatId=None,
        guidance="Telegram is not linked yet. Report delivery requires a Telegram chat identity.",
    )


def _display_status(value: str | None) -> str:
    if not value:
        return "Unknown"
    return value.replace("_", " ").replace("-", " ").title()
