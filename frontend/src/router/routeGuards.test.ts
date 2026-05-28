import { describe, expect, it } from "vitest";
import {
  authenticatedLoginRedirect,
  canAccessAdmin,
  isPublicRoute,
  resolveReportRoute,
  unauthenticatedRedirectFor,
} from "./routeGuards";
import { isActive } from "../components/AppShell";

describe("route guards", () => {
  it("redirects protected anonymous routes to login with next", () => {
    expect(unauthenticatedRedirectFor("/reports/local-report", "?tab=detail")).toBe(
      "/login?next=%2Freports%2Flocal-report%3Ftab%3Ddetail",
    );
  });

  it("keeps auth routes public", () => {
    expect(isPublicRoute("/login")).toBe(true);
    expect(isPublicRoute("/dashboard")).toBe(false);
  });

  it("resolves login next target for authenticated users", () => {
    expect(authenticatedLoginRedirect("?next=%2Freports")).toBe("/reports");
    expect(authenticatedLoginRedirect("")).toBe("/");
  });

  it("guards admin access by role", () => {
    expect(canAccessAdmin("user")).toBe(false);
    expect(canAccessAdmin("admin")).toBe(true);
  });

  it("resolves report detail routes and redirects empty report ids", () => {
    expect(resolveReportRoute("/reports/local-report-1")).toEqual({
      kind: "detail",
      reportId: "local-report-1",
    });
    expect(resolveReportRoute("/reports/")).toEqual({ kind: "redirect", to: "/reports" });
    expect(resolveReportRoute("/dashboard")).toEqual({ kind: "none" });
  });

  it("keeps reports navigation active on report detail routes", () => {
    expect(isActive("/reports/local-report-1", "/reports")).toBe(true);
    expect(isActive("/settings", "/reports")).toBe(false);
  });
});
