import type { UserDashboardReadModel } from "./dashboardTypes";

const dashboardMode = import.meta.env.VITE_DASHBOARD_MODE || "local";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const dashboardStatusPath = import.meta.env.VITE_DASHBOARD_STATUS_PATH;

export async function getUserDashboard(): Promise<UserDashboardReadModel | null> {
  if (dashboardMode === "api") {
    return getApiDashboard();
  }

  return getLocalDashboard();
}

async function getApiDashboard(): Promise<UserDashboardReadModel | null> {
  if (!dashboardStatusPath) {
    throw new Error("VITE_DASHBOARD_MODE=api requires VITE_DASHBOARD_STATUS_PATH.");
  }

  const response = await fetch(`${apiBaseUrl}${dashboardStatusPath}`, {
    credentials: "include",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Dashboard request failed with ${response.status}.`);
  }

  return (await response.json()) as UserDashboardReadModel;
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
