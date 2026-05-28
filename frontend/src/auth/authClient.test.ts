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
  vi.stubEnv("VITE_AUTH_ME_PATH", "/auth/me");
  vi.stubEnv("VITE_AUTH_LOGIN_PATH", "/auth/login");
  vi.stubEnv("VITE_AUTH_LOGOUT_PATH", "/auth/logout");
  vi.stubEnv("VITE_AUTH_FORGOT_PASSWORD_PATH", "/auth/forgot");
  vi.stubEnv("VITE_AUTH_RESET_PASSWORD_PATH", "/auth/reset");
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
    await expect(authClient.forgotPassword({ email: "a@example.com" })).rejects.toMatchObject({
      kind: "unauthorized",
    });
    await expect(authClient.resetPassword({ token: "token", password: "new-password" })).rejects.toMatchObject({
      kind: "unauthorized",
    });
  });
});
