import type { ReportDetail, ReportListItem } from "./reportTypes";

const reportsMode = import.meta.env.VITE_REPORTS_MODE || "local";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const reportsListPath = import.meta.env.VITE_REPORTS_LIST_PATH;
const reportDetailPath = import.meta.env.VITE_REPORT_DETAIL_PATH;

const localReports: ReportDetail[] = [
  {
    id: "local-report-2026-05-27",
    tradingDay: "2026-05-27",
    title: "Premarket Report",
    deliveryStatus: "sent",
    sentAt: "2026-05-27T09:16:00-04:00",
    generatedAt: "2026-05-27T09:05:00-04:00",
    bodyText:
      "Premarket Report\n\nThis local preview shows where the rendered report body will appear. It is intentionally read-only and does not include chat, editing, or report generation controls.\n\nKey context will stay grounded in the persisted daily report.",
  },
  {
    id: "local-report-2026-05-26",
    tradingDay: "2026-05-26",
    title: "Premarket Report",
    deliveryStatus: "pending",
    sentAt: null,
    generatedAt: "2026-05-26T09:06:00-04:00",
    bodyText:
      "Premarket Report\n\nThis older local preview represents a generated report whose delivery status still needs backend confirmation.",
  },
];

export async function listReports(): Promise<ReportListItem[]> {
  if (reportsMode === "api") {
    return listApiReports();
  }

  return localReports.map(({ bodyText: _bodyText, ...item }) => item);
}

export async function getReportDetail(reportId: string): Promise<ReportDetail | null> {
  if (reportsMode === "api") {
    return getApiReportDetail(reportId);
  }

  return localReports.find((report) => report.id === reportId) || null;
}

async function listApiReports(): Promise<ReportListItem[]> {
  if (!reportsListPath) {
    throw new Error("VITE_REPORTS_MODE=api requires VITE_REPORTS_LIST_PATH.");
  }

  const response = await fetch(`${apiBaseUrl}${reportsListPath}`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Reports request failed with ${response.status}.`);
  }

  return (await response.json()) as ReportListItem[];
}

async function getApiReportDetail(reportId: string): Promise<ReportDetail | null> {
  if (!reportDetailPath) {
    throw new Error("VITE_REPORTS_MODE=api requires VITE_REPORT_DETAIL_PATH.");
  }

  const path = reportDetailPath.replace(":reportId", encodeURIComponent(reportId));
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Report detail request failed with ${response.status}.`);
  }

  return (await response.json()) as ReportDetail;
}
