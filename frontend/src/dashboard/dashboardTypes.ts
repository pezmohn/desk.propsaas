export type DashboardStatusTone = "ready" | "pending" | "blocked" | "unknown";

export type DashboardStatusItem = {
  id: "plan" | "telegram" | "report" | "delivery" | "blocker";
  label: string;
  value: string;
  detail: string;
  tone: DashboardStatusTone;
};

export type UserDashboardReadModel = {
  generatedAt: string;
  items: DashboardStatusItem[];
};
