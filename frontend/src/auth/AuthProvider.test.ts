import { describe, expect, it } from "vitest";
import { assertValidLoginUser, authStatusForUser } from "./AuthProvider";
import type { AuthUser } from "./authTypes";

const validUser: AuthUser = {
  id: "user-1",
  email: "user@example.com",
  role: "user",
};

describe("AuthProvider guards", () => {
  it("keeps logged-out bootstrap state stable for null sessions", () => {
    expect(authStatusForUser(null)).toBe("anonymous");
  });

  it("marks valid bootstrapped users authenticated", () => {
    expect(authStatusForUser(validUser)).toBe("authenticated");
  });

  it("rejects null login results before authenticated state can be set", () => {
    expect(() => assertValidLoginUser(null)).toThrow("Login did not return a valid user session.");
  });

  it("accepts a valid login user", () => {
    expect(() => assertValidLoginUser(validUser)).not.toThrow();
  });
});
