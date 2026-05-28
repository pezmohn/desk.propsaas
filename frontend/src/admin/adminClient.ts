import type { AdminLiveDayReadModel, AdminLiveDayUserRow } from "./adminTypes";

const adminMode = import.meta.env.VITE_ADMIN_MODE || "local";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
const adminLiveDayPath = import.meta.env.VITE_ADMIN_LIVE_DAY_PATH;

export async function getAdminLiveDay(): Promise<AdminLiveDayReadModel | null> {
  if (adminMode === "api") {
    return getApiAdminLiveDay();
  }

  return getLocalAdminLiveDay();
}

async function getApiAdminLiveDay(): Promise<AdminLiveDayReadModel | null> {
  if (!adminLiveDayPath) {
    throw new Error("VITE_ADMIN_MODE=api requires VITE_ADMIN_LIVE_DAY_PATH.");
  }

  const response = await fetch(`${apiBaseUrl}${adminLiveDayPath}`, {
    credentials: "include",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Admin live-day request failed with ${response.status}.`);
  }

  return (await response.json()) as AdminLiveDayReadModel;
}

function getLocalAdminLiveDay(): AdminLiveDayReadModel {
  const users: AdminLiveDayUserRow[] = [
    {
      userId: "local-user-1",
      email: "active@example.com",
      displayName: "Active User",
      eligible: true,
      telegramLinked: true,
      reportGenerated: true,
      reportSent: true,
      blocker: null,
    },
    {
      userId: "local-user-2",
      email: "missing-telegram@example.com",
      displayName: "Missing Telegram",
      eligible: false,
      telegramLinked: false,
      reportGenerated: false,
      reportSent: false,
      blocker: "Telegram not linked",
    },
    {
      userId: "local-user-3",
      email: "generated-not-sent@example.com",
      displayName: "Delivery Pending",
      eligible: true,
      telegramLinked: true,
      reportGenerated: true,
      reportSent: false,
      blocker: "Report generated but not sent",
    },
  ];

  return {
    tradingDay: todayIsoDate(),
    generatedAt: new Date().toISOString(),
    summary: summarizeUsers(users),
    users,
  };
}

function summarizeUsers(users: AdminLiveDayUserRow[]) {
  return {
    totalUsers: users.length,
    eligibleUsers: users.filter((user) => user.eligible).length,
    linkedUsers: users.filter((user) => user.telegramLinked).length,
    reportsGenerated: users.filter((user) => user.reportGenerated).length,
    reportsSent: users.filter((user) => user.reportSent).length,
    blockedUsers: users.filter((user) => Boolean(user.blocker)).length,
  };
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}
