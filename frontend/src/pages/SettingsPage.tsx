import { useEffect, useState } from "react";
import { getUserSettings } from "../settings/settingsClient";
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
          message: error instanceof Error ? error.message : "Settings could not be loaded.",
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
      {state.status === "ready" ? <SettingsContent settings={state.settings} /> : null}
    </section>
  );
}

function SettingsContent({ settings }: { settings: UserSettingsReadModel }) {
  return (
    <div className="settings-grid">
      <section className="settings-panel" aria-labelledby="profile-title">
        <p className="settings-panel-label">Profile</p>
        <h2 id="profile-title">Profile basics</h2>
        <dl className="settings-list">
          <div>
            <dt>Email</dt>
            <dd>{settings.profile.email}</dd>
          </div>
          <div>
            <dt>Name</dt>
            <dd>{settings.profile.displayName || "Not set"}</dd>
          </div>
          <div>
            <dt>Timezone</dt>
            <dd>{settings.profile.timezone}</dd>
          </div>
        </dl>
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
