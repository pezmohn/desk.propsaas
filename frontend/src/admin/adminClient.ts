import type { AdminLiveDayReadModel, AdminLiveDayUserRow } from "./adminTypes";
import { requestJson } from "../api/apiClient";
import { asRecord, readArray, readBoolean, readNullableString, readNumber, readString } from "../api/normalize";

const adminMode = import.meta.env.VITE_ADMIN_MODE || "local";
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

  const payload = await requestJson(adminLiveDayPath, { notFoundAsNull: true });
  return payload ? normalizeAdminLiveDay(payload) : null;
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

function normalizeAdminLiveDay(payload: unknown): AdminLiveDayReadModel {
  const record = asRecord(payload, "Admin live-day read model");
  const users = readArray(record, "users").map(normalizeAdminUser);
  const summary = record.summary ? normalizeSummary(record.summary, users) : summarizeUsers(users);

  return {
    tradingDay: readString(record, "tradingDay", todayIsoDate()),
    generatedAt: readString(record, "generatedAt", new Date().toISOString()),
    summary,
    users,
  };
}

function normalizeAdminUser(value: unknown): AdminLiveDayUserRow {
  const record = asRecord(value, "Admin live-day user");

  return {
    userId: readString(record, "userId"),
    email: readString(record, "email"),
    displayName: readNullableString(record, "displayName"),
    eligible: readBoolean(record, "eligible"),
    telegramLinked: readBoolean(record, "telegramLinked"),
    reportGenerated: readBoolean(record, "reportGenerated"),
    reportSent: readBoolean(record, "reportSent"),
    blocker: readNullableString(record, "blocker"),
  };
}

function normalizeSummary(value: unknown, users: AdminLiveDayUserRow[]) {
  const record = asRecord(value, "Admin live-day summary");
  const fallback = summarizeUsers(users);

  return {
    totalUsers: readNumber(record, "totalUsers", fallback.totalUsers),
    eligibleUsers: readNumber(record, "eligibleUsers", fallback.eligibleUsers),
    linkedUsers: readNumber(record, "linkedUsers", fallback.linkedUsers),
    reportsGenerated: readNumber(record, "reportsGenerated", fallback.reportsGenerated),
    reportsSent: readNumber(record, "reportsSent", fallback.reportsSent),
    blockedUsers: readNumber(record, "blockedUsers", fallback.blockedUsers),
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
