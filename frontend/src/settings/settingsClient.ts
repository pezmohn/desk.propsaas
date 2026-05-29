import type { UserSettingsReadModel, UserSettingsUpdateInput } from "./settingsTypes";
import { requestJson } from "../api/apiClient";
import { asRecord, readNullableString, readString } from "../api/normalize";
import type { TelegramConnectionState } from "./settingsTypes";

const settingsMode = import.meta.env.VITE_SETTINGS_MODE || "local";
const settingsStatusPath = import.meta.env.VITE_SETTINGS_STATUS_PATH || "/api/v1/me/settings";

export async function getUserSettings(): Promise<UserSettingsReadModel | null> {
  if (settingsMode === "api") {
    return getApiSettings();
  }

  return getLocalSettings();
}

export async function updateUserSettings(
  update: UserSettingsUpdateInput,
): Promise<UserSettingsReadModel> {
  if (settingsMode === "api") {
    return updateApiSettings(update);
  }

  return {
    ...getLocalSettings(),
    profile: {
      ...getLocalSettings().profile,
      displayName:
        Object.prototype.hasOwnProperty.call(update, "displayName")
          ? normalizeLocalDisplayName(update.displayName)
          : getLocalSettings().profile.displayName,
      timezone: update.timezone?.trim() || getLocalSettings().profile.timezone,
    },
  };
}

async function getApiSettings(): Promise<UserSettingsReadModel | null> {
  const payload = await requestJson(settingsStatusPath, { notFoundAsNull: true });
  return payload ? normalizeSettings(payload) : null;
}

async function updateApiSettings(update: UserSettingsUpdateInput): Promise<UserSettingsReadModel> {
  const payload = await requestJson(settingsStatusPath, {
    method: "PATCH",
    body: update,
  });
  return normalizeSettings(payload);
}

function getLocalSettings(): UserSettingsReadModel {
  return {
    profile: {
      email: "local@example.com",
      displayName: "Local User",
      timezone: "America/New_York",
    },
    account: {
      status: "Active",
      planName: "MVP access",
      planStatus: "Pending backend confirmation",
    },
    telegram: {
      state: "incomplete",
      username: null,
      chatId: null,
      guidance:
        "Telegram status will show connected once the backend returns a linked chat identity. Use the current manual linking process until the connection flow is finalized.",
    },
  };
}

function normalizeSettings(payload: unknown): UserSettingsReadModel {
  const record = asRecord(payload, "Settings read model");
  const profile = asRecord(record.profile, "Settings profile");
  const account = asRecord(record.account, "Settings account");
  const telegram = asRecord(record.telegram, "Settings Telegram");

  return {
    profile: {
      email: readString(profile, "email"),
      displayName: readNullableString(profile, "displayName"),
      timezone: readString(profile, "timezone", "America/New_York"),
    },
    account: {
      status: readString(account, "status", "Unknown"),
      planName: readString(account, "planName", "Unknown"),
      planStatus: readString(account, "planStatus", "Unknown"),
    },
    telegram: {
      state: normalizeTelegramState(readString(telegram, "state", "incomplete")),
      username: readNullableString(telegram, "username"),
      chatId: readNullableString(telegram, "chatId"),
      guidance: readString(telegram, "guidance", "Telegram connection status is unavailable."),
    },
  };
}

function normalizeLocalDisplayName(value: string | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return value.trim() || null;
}

function normalizeTelegramState(value: string): TelegramConnectionState {
  const normalized = value.toLowerCase().replace("-", "_");
  if (normalized === "connected" || normalized === "linked") {
    return "connected";
  }
  if (normalized === "not_connected" || normalized === "unlinked" || normalized === "missing") {
    return "not_connected";
  }

  return "incomplete";
}
