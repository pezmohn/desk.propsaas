import { useEffect, useMemo, useState } from "react";
import { AppShell } from "./components/AppShell";
import { useAuth } from "./auth/AuthProvider";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { LoginPage } from "./pages/LoginPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { SettingsPage } from "./pages/SettingsPage";
import { AdminPage } from "./pages/AdminPage";
import {
  authenticatedLoginRedirect,
  canAccessAdmin,
  isPublicRoute,
  resolveReportRoute,
  unauthenticatedRedirectFor,
} from "./router/routeGuards";

type Route = {
  path: string;
  search: string;
};

function currentRoute(): Route {
  return {
    path: window.location.pathname,
    search: window.location.search,
  };
}

export function App() {
  const [route, setRoute] = useState<Route>(() => currentRoute());
  const { status, user } = useAuth();

  useEffect(() => {
    const onPopState = () => setRoute(currentRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useMemo(
    () => (to: string, options?: { replace?: boolean }) => {
      if (options?.replace) {
        window.history.replaceState({}, "", to);
      } else {
        window.history.pushState({}, "", to);
      }
      setRoute(currentRoute());
    },
    [],
  );

  if (status === "loading") {
    return <div className="boot-screen">Loading desk...</div>;
  }

  const isPublic = isPublicRoute(route.path);

  if (!user && !isPublic) {
    return <Redirect to={unauthenticatedRedirectFor(route.path, route.search)} navigate={navigate} />;
  }

  if (user && route.path === "/login") {
    return <Redirect to={authenticatedLoginRedirect(route.search)} navigate={navigate} />;
  }

  if (route.path === "/login") {
    return <LoginPage navigate={navigate} search={route.search} />;
  }

  if (route.path === "/forgot-password") {
    return <ForgotPasswordPage navigate={navigate} />;
  }

  if (route.path === "/reset-password") {
    return <ResetPasswordPage navigate={navigate} search={route.search} />;
  }

  return (
    <AppShell activePath={route.path} navigate={navigate}>
      <ProtectedPage path={route.path} userRole={user?.role || "user"} navigate={navigate} />
    </AppShell>
  );
}

function Redirect({
  to,
  navigate,
}: {
  to: string;
  navigate(to: string, options?: { replace?: boolean }): void;
}) {
  useEffect(() => {
    navigate(to, { replace: true });
  }, [navigate, to]);

  return null;
}

function ProtectedPage({
  path,
  userRole,
  navigate,
}: {
  path: string;
  userRole: "user" | "admin";
  navigate(to: string, options?: { replace?: boolean }): void;
}) {
  if (path === "/" || path === "/dashboard") {
    return <DashboardPage />;
  }

  if (path === "/reports") {
    return <ReportsPage navigate={navigate} />;
  }

  const reportRoute = resolveReportRoute(path);
  if (reportRoute.kind === "redirect") {
    return <Redirect to={reportRoute.to} navigate={navigate} />;
  }
  if (reportRoute.kind === "detail") {
    return <ReportDetailPage reportId={reportRoute.reportId} navigate={navigate} />;
  }

  if (path === "/settings") {
    return <SettingsPage />;
  }

  if (path === "/admin") {
    if (!canAccessAdmin(userRole)) {
      return (
        <PlaceholderPage
          title="Access restricted"
          eyebrow="403"
          description="Your account does not have access to the admin operations view."
        />
      );
    }

    return <AdminPage />;
  }

  return (
    <PlaceholderPage
      title="Not found"
      eyebrow="404"
      description="This route is not part of the current frontend shell."
    />
  );
}
