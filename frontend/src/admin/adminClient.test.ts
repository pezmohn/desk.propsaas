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

async function loadApiAdminClient() {
  vi.resetModules();
  vi.stubEnv("VITE_ADMIN_MODE", "api");
  return import("./adminClient");
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("adminClient API mode", () => {
  it("reads live-day state from the authenticated admin endpoint", async () => {
    const { getAdminLiveDay } = await loadApiAdminClient();
    mockResponse(200, {
      tradingDay: "2026-05-29",
      generatedAt: "2026-05-29T13:00:00+00:00",
      summary: {
        totalUsers: 1,
        eligibleUsers: 1,
        linkedUsers: 1,
        reportsGenerated: 1,
        reportsSent: 1,
        blockedUsers: 0,
      },
      users: [
        {
          userId: "user-1",
          email: "ready@example.com",
          displayName: "Ready User",
          eligible: true,
          telegramLinked: true,
          reportGenerated: true,
          reportSent: true,
          blocker: null,
          reportStatus: "sent",
          sentAt: "2026-05-29T12:05:00+00:00",
        },
      ],
    });

    await expect(getAdminLiveDay()).resolves.toMatchObject({
      tradingDay: "2026-05-29",
      summary: { totalUsers: 1, reportsSent: 1 },
      users: [
        {
          email: "ready@example.com",
          reportStatus: "sent",
          sentAt: "2026-05-29T12:05:00+00:00",
        },
      ],
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/admin/live-day",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("keeps forbidden admin failures explicit", async () => {
    const { getAdminLiveDay } = await loadApiAdminClient();
    mockResponse(403);

    await expect(getAdminLiveDay()).rejects.toMatchObject({
      kind: "forbidden",
      message: "You do not have access to this view.",
    });
  });

  it("returns null for not-found live-day responses", async () => {
    const { getAdminLiveDay } = await loadApiAdminClient();
    mockResponse(404);

    await expect(getAdminLiveDay()).resolves.toBeNull();
  });
});
