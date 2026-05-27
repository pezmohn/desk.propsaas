import { useEffect, useState } from "react";
import { listReports } from "../reports/reportClient";
import type { ReportListItem } from "../reports/reportTypes";

type ReportsState =
  | { status: "loading" }
  | { status: "ready"; reports: ReportListItem[] }
  | { status: "empty" }
  | { status: "error"; message: string };

type ReportsPageProps = {
  navigate(to: string, options?: { replace?: boolean }): void;
};

export function ReportsPage({ navigate }: ReportsPageProps) {
  const [state, setState] = useState<ReportsState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    listReports()
      .then((reports) => {
        if (!active) return;
        setState(reports.length > 0 ? { status: "ready", reports } : { status: "empty" });
      })
      .catch((error) => {
        if (!active) return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Reports could not be loaded.",
        });
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="reports-page" aria-labelledby="reports-title">
      <div className="page-header reports-header">
        <p className="eyebrow">Reports</p>
        <h1 id="reports-title">Report history</h1>
        <p>Read-only access to recent premarket reports and delivery state.</p>
      </div>

      {state.status === "loading" ? <ReportsLoading /> : null}
      {state.status === "empty" ? <ReportsEmpty /> : null}
      {state.status === "error" ? <ReportsError message={state.message} /> : null}
      {state.status === "ready" ? (
        <ReportList reports={state.reports} navigate={navigate} />
      ) : null}
    </section>
  );
}

function ReportList({ reports, navigate }: { reports: ReportListItem[]; navigate: ReportsPageProps["navigate"] }) {
  return (
    <div className="reports-list">
      {reports.map((report) => (
        <article className="report-row" key={report.id}>
          <div>
            <p className="report-day">{formatTradingDay(report.tradingDay)}</p>
            <h2>{report.title}</h2>
            <p className="report-meta">
              Generated {formatDateTime(report.generatedAt)}
              {report.sentAt ? ` · Sent ${formatDateTime(report.sentAt)}` : ""}
            </p>
          </div>

          <div className="report-row-actions">
            <span className={`delivery-badge ${report.deliveryStatus}`}>
              {formatDeliveryStatus(report.deliveryStatus)}
            </span>
            <button type="button" className="secondary-button" onClick={() => navigate(`/reports/${report.id}`)}>
              Open
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}

function ReportsLoading() {
  return (
    <div className="reports-list" aria-label="Loading reports">
      {[0, 1, 2].map((item) => (
        <div className="report-row report-skeleton" key={item}>
          <div>
            <span />
            <strong />
            <p />
          </div>
          <em />
        </div>
      ))}
    </div>
  );
}

function ReportsEmpty() {
  return (
    <div className="dashboard-message">
      <strong>No reports available.</strong>
      <span>Report history is ready, but no report read model was returned.</span>
    </div>
  );
}

function ReportsError({ message }: { message: string }) {
  return (
    <div className="dashboard-message error">
      <strong>Reports unavailable.</strong>
      <span>{message}</span>
    </div>
  );
}

export function formatDeliveryStatus(status: ReportListItem["deliveryStatus"]) {
  const labels: Record<ReportListItem["deliveryStatus"], string> = {
    sent: "Sent",
    pending: "Pending",
    failed: "Failed",
    not_sent: "Not sent",
    unknown: "Unknown",
  };

  return labels[status];
}

export function formatTradingDay(value: string) {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

export function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "time unavailable";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
