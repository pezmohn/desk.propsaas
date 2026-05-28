import { useEffect, useState } from "react";
import { getAdminLiveDay } from "../admin/adminClient";
import type { AdminLiveDayReadModel, AdminLiveDayUserRow } from "../admin/adminTypes";
import { formatDateTime, formatTradingDay } from "./ReportsPage";

type AdminState =
  | { status: "loading" }
  | { status: "ready"; liveDay: AdminLiveDayReadModel }
  | { status: "empty" }
  | { status: "error"; message: string };

export function AdminPage() {
  const [state, setState] = useState<AdminState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    getAdminLiveDay()
      .then((liveDay) => {
        if (!active) return;
        setState(liveDay ? { status: "ready", liveDay } : { status: "empty" });
      })
      .catch((error) => {
        if (!active) return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Admin live-day status could not be loaded.",
        });
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="admin-page" aria-labelledby="admin-title">
      <div className="page-header admin-header">
        <p className="eyebrow">Admin</p>
        <h1 id="admin-title">Live-day operations</h1>
        <p>Read-only delivery visibility for today’s premarket report run.</p>
      </div>

      {state.status === "loading" ? <AdminLoading /> : null}
      {state.status === "empty" ? <AdminEmpty /> : null}
      {state.status === "error" ? <AdminError message={state.message} /> : null}
      {state.status === "ready" ? <AdminContent liveDay={state.liveDay} /> : null}
    </section>
  );
}

function AdminContent({ liveDay }: { liveDay: AdminLiveDayReadModel }) {
  return (
    <>
      <div className="admin-run-summary">
        <span>{formatTradingDay(liveDay.tradingDay)}</span>
        <strong>Updated {formatDateTime(liveDay.generatedAt)}</strong>
      </div>

      <div className="admin-counter-grid" aria-label="Live-day summary">
        <AdminCounter label="Users" value={liveDay.summary.totalUsers} />
        <AdminCounter label="Eligible" value={liveDay.summary.eligibleUsers} />
        <AdminCounter label="Telegram linked" value={liveDay.summary.linkedUsers} />
        <AdminCounter label="Generated" value={liveDay.summary.reportsGenerated} />
        <AdminCounter label="Sent" value={liveDay.summary.reportsSent} />
        <AdminCounter label="Blocked" value={liveDay.summary.blockedUsers} />
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Eligible</th>
              <th>Telegram linked</th>
              <th>Report generated</th>
              <th>Report sent</th>
              <th>Blocker</th>
            </tr>
          </thead>
          <tbody>
            {liveDay.users.map((user) => (
              <AdminUserRow key={user.userId} user={user} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AdminCounter({ label, value }: { label: string; value: number }) {
  return (
    <div className="admin-counter">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AdminUserRow({ user }: { user: AdminLiveDayUserRow }) {
  return (
    <tr>
      <td>
        <strong>{user.displayName || user.email}</strong>
        <span>{user.email}</span>
      </td>
      <td>{booleanBadge(user.eligible)}</td>
      <td>{booleanBadge(user.telegramLinked)}</td>
      <td>{booleanBadge(user.reportGenerated)}</td>
      <td>{booleanBadge(user.reportSent)}</td>
      <td>
        {user.blocker ? (
          <span className="admin-blocker">{user.blocker}</span>
        ) : (
          <span className="admin-muted">None</span>
        )}
      </td>
    </tr>
  );
}

function booleanBadge(value: boolean) {
  return <span className={value ? "admin-badge yes" : "admin-badge no"}>{value ? "Yes" : "No"}</span>;
}

function AdminLoading() {
  return (
    <div className="admin-loading" aria-label="Loading admin live-day status">
      <div className="admin-counter-grid">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <div className="admin-counter admin-skeleton" key={item}>
            <span />
            <strong />
          </div>
        ))}
      </div>
      <div className="admin-table-skeleton" />
    </div>
  );
}

function AdminEmpty() {
  return (
    <div className="dashboard-message">
      <strong>No live-day status available.</strong>
      <span>The admin view is ready, but no live-day read model was returned.</span>
    </div>
  );
}

function AdminError({ message }: { message: string }) {
  return (
    <div className="dashboard-message error">
      <strong>Admin live-day status unavailable.</strong>
      <span>{message}</span>
    </div>
  );
}
