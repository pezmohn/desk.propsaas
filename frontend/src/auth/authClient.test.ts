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

async function loadApiAuthClient() {
  vi.resetModules();
  vi.stubEnv("VITE_AUTH_MODE", "api");
  return (await import("./authClient")).authClient;
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("authClient API mode", () => {
  it("reads the current user from the authenticated backend session endpoint", async () => {
    const authClient = await loadApiAuthClient();
    mockResponse(200, {
      id: "user-1",
      email: "user@example.com",
      displayName: "User One",
      role: "user",
    });

    await expect(authClient.getCurrentUser()).resolves.toEqual({
      id: "user-1",
      email: "user@example.com",
      displayName: "User One",
      role: "user",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/auth/session",
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("treats getCurrentUser 401 as logged out", async () => {
    const authClient = await loadApiAuthClient();
    mockResponse(401);

    await expect(authClient.getCurrentUser()).resolves.toBeNull();
  });

  it("does not swallow login 401", async () => {
    const authClient = await loadApiAuthClient();
    mockResponse(401);

    await expect(authClient.login({ email: "a@example.com", password: "bad" })).rejects.toMatchObject({
      kind: "unauthorized",
    });
  });

  it("does not convert auth mutation 401s into success", async () => {
    const authClient = await loadApiAuthClient();
    mockResponse(401);

    await expect(authClient.logout()).rejects.toMatchObject({ kind: "unauthorized" });
  });

  it("does not convert optional auth mutation 401s into success when endpoints are configured", async () => {
    vi.stubEnv("VITE_AUTH_FORGOT_PASSWORD_PATH", "/auth/forgot");
    vi.stubEnv("VITE_AUTH_RESET_PASSWORD_PATH", "/auth/reset");
    const authClient = await loadApiAuthClient();
    mockResponse(401);

    await expect(authClient.forgotPassword({ email: "a@example.com" })).rejects.toMatchObject({
      kind: "unauthorized",
    });
    await expect(authClient.resetPassword({ token: "token", password: "new-password" })).rejects.toMatchObject({
      kind: "unauthorized",
    });
  });
});
