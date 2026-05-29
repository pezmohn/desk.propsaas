import { FormEvent, useEffect, useState } from "react";
import { apiErrorMessage } from "../api/apiClient";
import { getUserSettings, updateUserSettings } from "../settings/settingsClient";
import type { TelegramConnectionState, UserSettingsReadModel } from "../settings/settingsTypes";

type SettingsState =
  | { status: "loading" }
  | { status: "ready"; settings: UserSettingsReadModel }
  | { status: "empty" }
  | { status: "error"; message: string };

export function SettingsPage() {
  const [state, setState] = useState<SettingsState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    getUserSettings()
      .then((settings) => {
        if (!active) return;
        setState(settings ? { status: "ready", settings } : { status: "empty" });
      })
      .catch((error) => {
        if (!active) return;
        setState({
          status: "error",
          message: apiErrorMessage(error, "Settings could not be loaded."),
        });
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <div className="page-header settings-header">
        <p className="eyebrow">Settings</p>
        <h1 id="settings-title">Account and Telegram</h1>
        <p>Read-only account basics and Telegram connection status.</p>
      </div>

      {state.status === "loading" ? <SettingsLoading /> : null}
      {state.status === "empty" ? <SettingsEmpty /> : null}
      {state.status === "error" ? <SettingsError message={state.message} /> : null}
      {state.status === "ready" ? (
        <SettingsContent
          settings={state.settings}
          onSaved={(settings) => setState({ status: "ready", settings })}
        />
      ) : null}
    </section>
  );
}

function SettingsContent({
  settings,
  onSaved,
}: {
  settings: UserSettingsReadModel;
  onSaved(settings: UserSettingsReadModel): void;
}) {
  const [displayName, setDisplayName] = useState(settings.profile.displayName || "");
  const [timezone, setTimezone] = useState(settings.profile.timezone);
  const [saveState, setSaveState] = useState<
    | { status: "idle" }
    | { status: "saving" }
    | { status: "success"; message: string }
    | { status: "error"; message: string }
  >({ status: "idle" });

  useEffect(() => {
    setDisplayName(settings.profile.displayName || "");
    setTimezone(settings.profile.timezone);
  }, [settings.profile.displayName, settings.profile.timezone]);

  async function handleProfileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveState({ status: "saving" });

    try {
      const updated = await updateUserSettings({
        displayName,
        timezone,
      });
      onSaved(updated);
      setSaveState({ status: "success", message: "Settings saved." });
    } catch (error) {
      setSaveState({
        status: "error",
        message: apiErrorMessage(error, "Settings could not be saved."),
      });
    }
  }

  return (
    <div className="settings-grid">
      <section className="settings-panel" aria-labelledby="profile-title">
        <p className="settings-panel-label">Profile</p>
        <h2 id="profile-title">Profile basics</h2>
        <form className="settings-form" onSubmit={handleProfileSubmit}>
          <label>
            Email
            <input disabled type="email" value={settings.profile.email} />
          </label>
          <label>
            Display name
            <input
              autoComplete="name"
              maxLength={200}
              onChange={(event) => setDisplayName(event.target.value)}
              value={displayName}
            />
          </label>
          <label>
            Timezone
            <input
              autoComplete="off"
              onChange={(event) => setTimezone(event.target.value)}
              required
              value={timezone}
            />
          </label>
          {saveState.status === "success" ? <p className="notice">{saveState.message}</p> : null}
          {saveState.status === "error" ? <p className="form-error">{saveState.message}</p> : null}
          <div className="settings-actions">
            <button
              className="primary-button"
              disabled={saveState.status === "saving"}
              type="submit"
            >
              {saveState.status === "saving" ? "Saving..." : "Save settings"}
            </button>
          </div>
        </form>
      </section>

      <section className="settings-panel" aria-labelledby="account-title">
        <p className="settings-panel-label">Account</p>
        <h2 id="account-title">Plan status</h2>
        <dl className="settings-list">
          <div>
            <dt>Account</dt>
            <dd>{settings.account.status}</dd>
          </div>
          <div>
            <dt>Plan</dt>
            <dd>{settings.account.planName}</dd>
          </div>
          <div>
            <dt>Plan state</dt>
            <dd>{settings.account.planStatus}</dd>
          </div>
        </dl>
      </section>

      <section className="settings-panel telegram-panel" aria-labelledby="telegram-title">
        <div className="telegram-heading">
          <div>
            <p className="settings-panel-label">Telegram</p>
            <h2 id="telegram-title">Connection status</h2>
          </div>
          <span className={`telegram-status ${settings.telegram.state}`}>
            {formatTelegramState(settings.telegram.state)}
          </span>
        </div>

        <dl className="settings-list">
          <div>
            <dt>Username</dt>
            <dd>{settings.telegram.username ? `@${settings.telegram.username}` : "Not available"}</dd>
          </div>
          <div>
            <dt>Chat identity</dt>
            <dd>{settings.telegram.chatId || "Not available"}</dd>
          </div>
        </dl>

        <div className={`telegram-guidance ${settings.telegram.state}`}>
          <strong>{telegramGuidanceTitle(settings.telegram.state)}</strong>
          <span>{settings.telegram.guidance}</span>
        </div>
      </section>
    </div>
  );
}

function SettingsLoading() {
  return (
    <div className="settings-grid" aria-label="Loading settings">
      {[0, 1, 2].map((item) => (
        <div className="settings-panel settings-skeleton" key={item}>
          <span />
          <strong />
          <p />
          <p />
        </div>
      ))}
    </div>
  );
}

function SettingsEmpty() {
  return (
    <div className="dashboard-message">
      <strong>No settings status available.</strong>
      <span>The settings page is ready, but no account read model was returned.</span>
    </div>
  );
}

function SettingsError({ message }: { message: string }) {
  return (
    <div className="dashboard-message error">
      <strong>Settings unavailable.</strong>
      <span>{message}</span>
    </div>
  );
}

function formatTelegramState(state: TelegramConnectionState) {
  const labels: Record<TelegramConnectionState, string> = {
    connected: "Connected",
    not_connected: "Not connected",
    incomplete: "Incomplete",
  };

  return labels[state];
}

function telegramGuidanceTitle(state: TelegramConnectionState) {
  if (state === "connected") {
    return "Telegram is linked.";
  }

  if (state === "incomplete") {
    return "Telegram setup is incomplete.";
  }

  return "Telegram is not connected.";
}
