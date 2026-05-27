import { useEffect, useState } from "react";
import { getReportDetail } from "../reports/reportClient";
import type { ReportDetail } from "../reports/reportTypes";
import { formatDateTime, formatDeliveryStatus, formatTradingDay } from "./ReportsPage";

type ReportDetailState =
  | { status: "loading" }
  | { status: "ready"; report: ReportDetail }
  | { status: "empty" }
  | { status: "error"; message: string };

type ReportDetailPageProps = {
  reportId: string;
  navigate(to: string, options?: { replace?: boolean }): void;
};

export function ReportDetailPage({ reportId, navigate }: ReportDetailPageProps) {
  const [state, setState] = useState<ReportDetailState>({ status: "loading" });

  useEffect(() => {
    let active = true;

    getReportDetail(reportId)
      .then((report) => {
        if (!active) return;
        setState(report ? { status: "ready", report } : { status: "empty" });
      })
      .catch((error) => {
        if (!active) return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Report detail could not be loaded.",
        });
      });

    return () => {
      active = false;
    };
  }, [reportId]);

  return (
    <section className="reports-page" aria-labelledby="report-detail-title">
      <button type="button" className="link-button back-link" onClick={() => navigate("/reports")}>
        Back to reports
      </button>

      {state.status === "loading" ? <ReportDetailLoading /> : null}
      {state.status === "empty" ? <ReportDetailEmpty /> : null}
      {state.status === "error" ? <ReportDetailError message={state.message} /> : null}
      {state.status === "ready" ? <ReportDetailContent report={state.report} /> : null}
    </section>
  );
}

function ReportDetailContent({ report }: { report: ReportDetail }) {
  return (
    <>
      <div className="page-header reports-header">
        <p className="eyebrow">{formatTradingDay(report.tradingDay)}</p>
        <h1 id="report-detail-title">{report.title}</h1>
        <p>Read-only rendered report detail.</p>
      </div>

      <div className="report-detail-meta">
        <span className={`delivery-badge ${report.deliveryStatus}`}>
          {formatDeliveryStatus(report.deliveryStatus)}
        </span>
        <span>Generated {formatDateTime(report.generatedAt)}</span>
        <span>{report.sentAt ? `Sent ${formatDateTime(report.sentAt)}` : "Delivery timestamp unavailable"}</span>
      </div>

      <article className="report-body" aria-label="Rendered report body">
        <pre>{report.bodyText}</pre>
      </article>
    </>
  );
}

function ReportDetailLoading() {
  return (
    <div className="report-detail-skeleton" aria-label="Loading report detail">
      <span />
      <strong />
      <p />
      <p />
    </div>
  );
}

function ReportDetailEmpty() {
  return (
    <div className="dashboard-message">
      <strong>Report not found.</strong>
      <span>The requested report detail was not returned by the read model.</span>
    </div>
  );
}

function ReportDetailError({ message }: { message: string }) {
  return (
    <div className="dashboard-message error">
      <strong>Report detail unavailable.</strong>
      <span>{message}</span>
    </div>
  );
}
