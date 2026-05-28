import { useAuth } from "../auth/AuthProvider";

type AppShellProps = {
  activePath: string;
  navigate(to: string, options?: { replace?: boolean }): void;
  children: React.ReactNode;
};

const navItems = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "Reports", path: "/reports" },
  { label: "Settings", path: "/settings" },
];

export function AppShell({ activePath, navigate, children }: AppShellProps) {
  const { user, logout } = useAuth();
  const allNavItems =
    user?.role === "admin" ? [...navItems, { label: "Admin", path: "/admin" }] : navItems;

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <button className="brand" type="button" onClick={() => navigate("/dashboard")}>
          <span className="brand-mark">dp</span>
          <span>
            <strong>desk-propsaas</strong>
            <small>Report desk</small>
          </span>
        </button>

        <nav className="nav-list">
          {allNavItems.map((item) => (
            <button
              className={isActive(activePath, item.path) ? "nav-item active" : "nav-item"}
              key={item.path}
              type="button"
              onClick={() => navigate(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-chip">
            <span>{user?.displayName || user?.email}</span>
            <small>{user?.role}</small>
          </div>
          <button className="secondary-button" type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="content-shell">{children}</main>
    </div>
  );
}

function isActive(activePath: string, itemPath: string) {
  return (
    activePath === itemPath ||
    (itemPath === "/dashboard" && activePath === "/") ||
    (itemPath === "/reports" && activePath.startsWith("/reports/"))
  );
}
