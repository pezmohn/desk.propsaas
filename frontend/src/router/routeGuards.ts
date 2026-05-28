import type { AuthRole } from "../auth/authTypes";

const publicRoutes = new Set(["/login", "/forgot-password", "/reset-password"]);

export function isPublicRoute(path: string): boolean {
  return publicRoutes.has(path);
}

export function unauthenticatedRedirectFor(path: string, search: string): string {
  return `/login?next=${encodeURIComponent(`${path}${search}`)}`;
}

export function authenticatedLoginRedirect(search: string): string {
  const params = new URLSearchParams(search);
  return params.get("next") || "/";
}

export function canAccessAdmin(role: AuthRole): boolean {
  return role === "admin";
}

export type ReportRouteResolution =
  | { kind: "detail"; reportId: string }
  | { kind: "redirect"; to: string }
  | { kind: "none" };

export function resolveReportRoute(path: string): ReportRouteResolution {
  if (!path.startsWith("/reports/")) {
    return { kind: "none" };
  }

  const reportId = decodeURIComponent(path.replace("/reports/", ""));
  return reportId ? { kind: "detail", reportId } : { kind: "redirect", to: "/reports" };
}
