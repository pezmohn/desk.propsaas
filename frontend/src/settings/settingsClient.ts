import type { UserSettingsReadModel } from "./settingsTypes";

const settingsMode = import.meta.env.VITE_SETTINGS_MODE || "local";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const settingsStatusPath = import.meta.env.VITE_SETTINGS_STATUS_PATH;

export async function getUserSettings(): Promise<UserSettingsReadModel | null> {
  if (settingsMode === "api") {
    return getApiSettings();
  }

  return getLocalSettings();
}

async function getApiSettings(): Promise<UserSettingsReadModel | null> {
  if (!settingsStatusPath) {
    throw new Error("VITE_SETTINGS_MODE=api requires VITE_SETTINGS_STATUS_PATH.");
  }

  const response = await fetch(`${apiBaseUrl}${settingsStatusPath}`, {
    credentials: "include",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Settings request failed with ${response.status}.`);
  }

  return (await response.json()) as UserSettingsReadModel;
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
