import type { ReportDetail, ReportListItem } from "./reportTypes";
import { requestJson } from "../api/apiClient";
import { asRecord, readArray, readNullableString, readString } from "../api/normalize";
import type { ReportDeliveryStatus } from "./reportTypes";

const reportsMode = import.meta.env.VITE_REPORTS_MODE || "local";
const reportsListPath = import.meta.env.VITE_REPORTS_LIST_PATH || "/api/v1/me/reports";
const reportDetailPath = import.meta.env.VITE_REPORT_DETAIL_PATH || "/api/v1/me/reports/:reportId";

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

  const payload = await requestJson(reportsListPath);
  return normalizeReportList(payload);
}

async function getApiReportDetail(reportId: string): Promise<ReportDetail | null> {
  if (!reportDetailPath) {
    throw new Error("VITE_REPORTS_MODE=api requires VITE_REPORT_DETAIL_PATH.");
  }

  const path = reportDetailPath.replace(":reportId", encodeURIComponent(reportId));
  const payload = await requestJson(path, { notFoundAsNull: true });
  return payload ? normalizeReportDetail(payload) : null;
}

function normalizeReportList(payload: unknown): ReportListItem[] {
  const records = Array.isArray(payload) ? payload : readArray(asRecord(payload, "Reports response"), "reports");
  return records.map(normalizeReportListItem);
}

function normalizeReportListItem(value: unknown): ReportListItem {
  const record = asRecord(value, "Report list item");

  return {
    id: readString(record, "id"),
    tradingDay: readString(record, "tradingDay"),
    title: readString(record, "title", "Premarket Report"),
    deliveryStatus: normalizeDeliveryStatus(readString(record, "deliveryStatus", "unknown")),
    sentAt: readNullableString(record, "sentAt"),
    generatedAt: readString(record, "generatedAt"),
  };
}

function normalizeReportDetail(payload: unknown): ReportDetail {
  const record = asRecord(payload, "Report detail");

  return {
    ...normalizeReportListItem(record),
    bodyText: readString(record, "bodyText", ""),
  };
}

function normalizeDeliveryStatus(value: string): ReportDeliveryStatus {
  const normalized = value.toLowerCase().replace("-", "_");
  if (normalized === "sent" || normalized === "delivered") {
    return "sent";
  }
  if (normalized === "pending" || normalized === "queued") {
    return "pending";
  }
  if (normalized === "failed" || normalized === "error") {
    return "failed";
  }
  if (normalized === "not_sent" || normalized === "unsent") {
    return "not_sent";
  }

  return "unknown";
}
