import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { TelegramConnectionPanel } from "./SettingsPage";
import type { UserSettingsReadModel } from "../settings/settingsTypes";

function settingsWithTelegram(
  telegram: UserSettingsReadModel["telegram"],
): UserSettingsReadModel {
  return {
    profile: {
      email: "one@example.com",
      displayName: "One",
      timezone: "America/New_York",
    },
    account: {
      status: "Active",
      planName: "Starter",
      planStatus: "Active",
    },
    telegram,
  };
}

describe("TelegramConnectionPanel", () => {
  it("renders linked Telegram state", () => {
    const html = renderToStaticMarkup(
      <TelegramConnectionPanel
        onReload={vi.fn()}
        settings={settingsWithTelegram({
          state: "connected",
          username: "desk_user",
          chatId: "12345",
          guidance: "Telegram is linked for report delivery.",
        })}
      />,
    );

    expect(html).toContain("Connected");
    expect(html).toContain("@desk_user");
    expect(html).toContain("12345");
    expect(html).toContain("Request relink");
  });

  it("renders not-linked Telegram state with connect action", () => {
    const html = renderToStaticMarkup(
      <TelegramConnectionPanel
        onReload={vi.fn()}
        settings={settingsWithTelegram({
          state: "not_connected",
          username: null,
          chatId: null,
          guidance: "Telegram is not linked yet.",
        })}
      />,
    );

    expect(html).toContain("Not connected");
    expect(html).toContain("Not available");
    expect(html).toContain("Connect Telegram");
  });
});
