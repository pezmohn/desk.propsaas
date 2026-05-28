import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, requestJson } from "./apiClient";

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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("requestJson", () => {
  it("returns null for 401 only when unauthorizedAsNull is set", async () => {
    mockResponse(401);

    await expect(requestJson("/me", { unauthorizedAsNull: true })).resolves.toBeNull();
  });

  it("classifies 401 as unauthorized by default", async () => {
    mockResponse(401);

    await expect(requestJson("/private")).rejects.toMatchObject({
      kind: "unauthorized",
      status: 401,
    } satisfies Partial<ApiError>);
  });

  it("classifies 403 as forbidden", async () => {
    mockResponse(403);

    await expect(requestJson("/admin")).rejects.toMatchObject({
      kind: "forbidden",
      status: 403,
    } satisfies Partial<ApiError>);
  });

  it("can return null for a controlled 404", async () => {
    mockResponse(404);

    await expect(requestJson("/missing", { notFoundAsNull: true })).resolves.toBeNull();
  });
});
