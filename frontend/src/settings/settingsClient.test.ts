import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function mockResponse(status: number, body?: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      }),
    ),
  );
}

async function loadApiSettingsClient() {
  vi.resetModules();
  vi.stubEnv("VITE_SETTINGS_MODE", "api");
  return import("./settingsClient");
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("settingsClient API mode", () => {
  it("reads settings from the authenticated backend settings endpoint", async () => {
    const { getUserSettings } = await loadApiSettingsClient();
    mockResponse(200, {
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
      telegram: {
        state: "connected",
        username: "desk_user",
        chatId: "12345",
        guidance: "Telegram is linked for report delivery.",
      },
    });

    await expect(getUserSettings()).resolves.toEqual({
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
      telegram: {
        state: "connected",
        username: "desk_user",
        chatId: "12345",
        guidance: "Telegram is linked for report delivery.",
      },
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/me/settings",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("normalizes missing Telegram status without inventing a connection", async () => {
    const { getUserSettings } = await loadApiSettingsClient();
    mockResponse(200, {
      profile: {
        email: "one@example.com",
        displayName: null,
        timezone: "America/New_York",
      },
      account: {
        status: "Active",
        planName: "Unknown",
        planStatus: "Unknown",
      },
      telegram: {
        state: "missing",
        username: null,
        chatId: null,
        guidance: "Telegram is not linked yet.",
      },
    });

    const settings = await getUserSettings();

    expect(settings?.telegram).toEqual({
      state: "not_connected",
      username: null,
      chatId: null,
      guidance: "Telegram is not linked yet.",
    });
  });

  it("keeps unauthorized settings failures controlled", async () => {
    const { getUserSettings } = await loadApiSettingsClient();
    mockResponse(401);

    await expect(getUserSettings()).rejects.toMatchObject({ kind: "unauthorized" });
  });
});
