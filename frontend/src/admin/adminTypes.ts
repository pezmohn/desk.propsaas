export type AdminLiveDayUserRow = {
  userId: string;
  email: string;
  displayName: string | null;
  eligible: boolean;
  telegramLinked: boolean;
  reportGenerated: boolean;
  reportSent: boolean;
  blocker: string | null;
};

export type AdminLiveDaySummary = {
  totalUsers: number;
  eligibleUsers: number;
  linkedUsers: number;
  reportsGenerated: number;
  reportsSent: number;
  blockedUsers: number;
};

export type AdminLiveDayReadModel = {
  tradingDay: string;
  generatedAt: string;
  summary: AdminLiveDaySummary;
  users: AdminLiveDayUserRow[];
};
