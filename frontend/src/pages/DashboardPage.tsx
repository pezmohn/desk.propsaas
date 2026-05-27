import { useEffect, useState } from "react";
import { getUserDashboard } from "../dashboard/dashboardClient";
import type { DashboardStatusItem, UserDashboardReadModel } from "../dashboard/dashboardTypes";

type DashboardState =
  | { status: "loading" }
  | { status: "ready"; dashboard: UserDashboardReadModel }
  | { status: "empty" }
  | { status: "error"; message: string };

export function DashboardPage() {
  const [state, setState] = useState<DashboardState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    getUserDashboard()
      .then((dashboard) => {
        if (!active) return;
        setState(dashboard ? { status: "ready", dashboard } : { status: "empty" });
      })
      .catch((error) => {
        if (!active) return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Dashboard status could not be loaded.",
        });
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="dashboard-page" aria-labelledby="dashboard-title">
      <div className="page-header dashboard-header">
        <p className="eyebrow">User dashboard</p>
        <h1 id="dashboard-title">Account status</h1>
        <p>Read-only status structure for the daily report service.</p>
      </div>

      {state.status === "loading" ? <DashboardLoading /> : null}
      {state.status === "empty" ? <DashboardEmpty /> : null}
      {state.status === "error" ? <DashboardError message={state.message} /> : null}
      {state.status === "ready" ? <DashboardContent dashboard={state.dashboard} /> : null}
    </section>
  );
}

function DashboardContent({ dashboard }: { dashboard: UserDashboardReadModel }) {
  return (
    <>
      <div className="status-summary" aria-label="Dashboard freshness">
        <span>Dashboard skeleton</span>
        <strong>{formatGeneratedAt(dashboard.generatedAt)}</strong>
      </div>

      <div className="status-grid">
        {dashboard.items.map((item) => (
          <StatusCard item={item} key={item.id} />
        ))}
      </div>
    </>
  );
}

function StatusCard({ item }: { item: DashboardStatusItem }) {
  return (
    <article className="status-card">
      <div className="status-card-heading">
        <span className={`status-dot ${item.tone}`} aria-hidden="true" />
        <h2>{item.label}</h2>
      </div>
      <p className="status-value">{item.value}</p>
      <p className="status-detail">{item.detail}</p>
    </article>
  );
}

function DashboardLoading() {
  return (
    <div className="status-grid" aria-label="Loading dashboard status">
      {["plan", "telegram", "report", "delivery", "blocker"].map((item) => (
        <div className="status-card skeleton-card" key={item}>
          <span />
          <strong />
          <p />
        </div>
      ))}
    </div>
  );
}

function DashboardEmpty() {
  return (
    <div className="dashboard-message">
      <strong>No dashboard status available.</strong>
      <span>The page structure is ready, but no user status read model was returned.</span>
    </div>
  );
}

function DashboardError({ message }: { message: string }) {
  return (
    <div className="dashboard-message error">
      <strong>Dashboard status unavailable.</strong>
      <span>{message}</span>
    </div>
  );
}

function formatGeneratedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Freshness unavailable";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
