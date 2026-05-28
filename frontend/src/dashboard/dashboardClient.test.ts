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

async function loadApiDashboardClient() {
  vi.resetModules();
  vi.stubEnv("VITE_DASHBOARD_MODE", "api");
  return import("./dashboardClient");
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("dashboardClient API mode", () => {
  it("reads dashboard status from the authenticated backend dashboard endpoint", async () => {
    const { getUserDashboard } = await loadApiDashboardClient();
    mockResponse(200, {
      generatedAt: "2026-05-28T12:00:00+00:00",
      items: [
        {
          id: "plan",
          label: "Plan status",
          value: "Starter",
          detail: "Plan state: Active.",
          tone: "ready",
        },
      ],
    });

    await expect(getUserDashboard()).resolves.toEqual({
      generatedAt: "2026-05-28T12:00:00+00:00",
      items: [
        {
          id: "plan",
          label: "Plan status",
          value: "Starter",
          detail: "Plan state: Active.",
          tone: "ready",
        },
      ],
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/me/dashboard",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("normalizes unknown item ids and tones into controlled fallback values", async () => {
    const { getUserDashboard } = await loadApiDashboardClient();
    mockResponse(200, {
      generatedAt: "2026-05-28T12:00:00+00:00",
      items: [
        {
          id: "unexpected",
          label: "Unexpected",
          value: "Unexpected",
          detail: "Unexpected",
          tone: "surprising",
        },
      ],
    });

    const dashboard = await getUserDashboard();

    expect(dashboard?.items[0]).toEqual({
      id: "blocker",
      label: "Unexpected",
      value: "Unexpected",
      detail: "Unexpected",
      tone: "unknown",
    });
  });

  it("keeps unauthorized dashboard failures controlled", async () => {
    const { getUserDashboard } = await loadApiDashboardClient();
    mockResponse(401);

    await expect(getUserDashboard()).rejects.toMatchObject({ kind: "unauthorized" });
  });
});
