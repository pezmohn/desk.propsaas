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

const publicRoutes = new Set(["/login", "/forgot-password", "/reset-password"]);

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

  const isPublic = publicRoutes.has(route.path);

  if (!user && !isPublic) {
    const next = encodeURIComponent(`${route.path}${route.search}`);
    return <Redirect to={`/login?next=${next}`} navigate={navigate} />;
  }

  if (user && route.path === "/login") {
    const params = new URLSearchParams(route.search);
    return <Redirect to={params.get("next") || "/"} navigate={navigate} />;
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

  if (path.startsWith("/reports/")) {
    const reportId = decodeURIComponent(path.replace("/reports/", ""));
    if (!reportId) {
      return <Redirect to="/reports" navigate={navigate} />;
    }
    return <ReportDetailPage reportId={reportId} navigate={navigate} />;
  }

  if (path === "/settings") {
    return <SettingsPage />;
  }

  if (path === "/admin") {
    if (userRole !== "admin") {
      return (
        <PlaceholderPage
          title="Not found"
          eyebrow="404"
          description="This route is not part of the current frontend shell."
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
