import type { UserDashboardReadModel } from "./dashboardTypes";
import { requestJson } from "../api/apiClient";
import { asRecord, readArray, readString } from "../api/normalize";
import type { DashboardStatusItem, DashboardStatusTone } from "./dashboardTypes";

const dashboardMode = import.meta.env.VITE_DASHBOARD_MODE || "local";
const dashboardStatusPath = import.meta.env.VITE_DASHBOARD_STATUS_PATH || "/api/v1/me/dashboard";

export async function getUserDashboard(): Promise<UserDashboardReadModel | null> {
  if (dashboardMode === "api") {
    return getApiDashboard();
  }

  return getLocalDashboard();
}

async function getApiDashboard(): Promise<UserDashboardReadModel | null> {
  const payload = await requestJson(dashboardStatusPath, { notFoundAsNull: true });
  return payload ? normalizeDashboard(payload) : null;
}

function getLocalDashboard(): UserDashboardReadModel {
  return {
    generatedAt: new Date().toISOString(),
    items: [
      {
        id: "plan",
        label: "Plan status",
        value: "Pending backend status",
        detail: "This card is reserved for the account plan read model.",
        tone: "unknown",
      },
      {
        id: "telegram",
        label: "Telegram link",
        value: "Pending backend status",
        detail: "This card will show whether Telegram delivery is connected.",
        tone: "unknown",
      },
      {
        id: "report",
        label: "Today's report",
        value: "Pending backend status",
        detail: "This card will show whether today's report exists.",
        tone: "unknown",
      },
      {
        id: "delivery",
        label: "Last delivery",
        value: "Not available yet",
        detail: "This card will show the latest report delivery timestamp.",
        tone: "unknown",
      },
      {
        id: "blocker",
        label: "Current blocker",
        value: "No blocker data loaded",
        detail: "This card will surface the current account or delivery blocker.",
        tone: "unknown",
      },
    ],
  };
}

function normalizeDashboard(payload: unknown): UserDashboardReadModel {
  const record = asRecord(payload, "Dashboard read model");
  const items = readArray(record, "items").map(normalizeDashboardItem);

  return {
    generatedAt: readString(record, "generatedAt", new Date().toISOString()),
    items,
  };
}

function normalizeDashboardItem(value: unknown): DashboardStatusItem {
  const record = asRecord(value, "Dashboard status item");
  const id = normalizeDashboardItemId(readString(record, "id"));

  return {
    id,
    label: readString(record, "label"),
    value: readString(record, "value", "Unavailable"),
    detail: readString(record, "detail", ""),
    tone: normalizeTone(readString(record, "tone", "unknown")),
  };
}

function normalizeDashboardItemId(value: string): DashboardStatusItem["id"] {
  if (["plan", "telegram", "report", "delivery", "blocker"].includes(value)) {
    return value as DashboardStatusItem["id"];
  }

  return "blocker";
}

function normalizeTone(value: string): DashboardStatusTone {
  if (value === "ready" || value === "pending" || value === "blocked" || value === "unknown") {
    return value;
  }

  return "unknown";
}
