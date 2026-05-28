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

async function loadLocalReportClient() {
  vi.resetModules();
  return import("./reportClient");
}

async function loadApiReportClient() {
  vi.resetModules();
  vi.stubEnv("VITE_REPORTS_MODE", "api");
  return import("./reportClient");
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("report detail local mode", () => {
  it("returns null for unknown report ids instead of throwing", async () => {
    const { getReportDetail } = await loadLocalReportClient();

    await expect(getReportDetail("unknown-report")).resolves.toBeNull();
  });
});

describe("reportClient API mode", () => {
  it("lists reports from the authenticated backend report endpoint", async () => {
    const { listReports } = await loadApiReportClient();
    mockResponse(200, [
      {
        id: "report-1",
        tradingDay: "2026-05-28",
        title: "Premarket Report",
        deliveryStatus: "not_sent",
        sentAt: null,
        generatedAt: "2026-05-28T12:00:00+00:00",
      },
    ]);

    await expect(listReports()).resolves.toEqual([
      {
        id: "report-1",
        tradingDay: "2026-05-28",
        title: "Premarket Report",
        deliveryStatus: "not_sent",
        sentAt: null,
        generatedAt: "2026-05-28T12:00:00+00:00",
      },
    ]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/me/reports",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("normalizes report detail responses from the backend", async () => {
    const { getReportDetail } = await loadApiReportClient();
    mockResponse(200, {
      id: "report-1",
      tradingDay: "2026-05-28",
      title: "Premarket Report",
      deliveryStatus: "delivered",
      sentAt: "2026-05-28T12:05:00+00:00",
      generatedAt: "2026-05-28T12:00:00+00:00",
      bodyText: "Premarket report body",
    });

    await expect(getReportDetail("report-1")).resolves.toEqual({
      id: "report-1",
      tradingDay: "2026-05-28",
      title: "Premarket Report",
      deliveryStatus: "sent",
      sentAt: "2026-05-28T12:05:00+00:00",
      generatedAt: "2026-05-28T12:00:00+00:00",
      bodyText: "Premarket report body",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/me/reports/report-1",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("returns null for not-found report detail responses", async () => {
    const { getReportDetail } = await loadApiReportClient();
    mockResponse(404);

    await expect(getReportDetail("missing-report")).resolves.toBeNull();
  });

  it("keeps unauthorized report list failures controlled", async () => {
    const { listReports } = await loadApiReportClient();
    mockResponse(401);

    await expect(listReports()).rejects.toMatchObject({ kind: "unauthorized" });
  });
});
