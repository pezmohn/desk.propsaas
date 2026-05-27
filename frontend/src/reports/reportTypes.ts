export type ReportDeliveryStatus = "sent" | "pending" | "failed" | "not_sent" | "unknown";

export type ReportListItem = {
  id: string;
  tradingDay: string;
  title: string;
  deliveryStatus: ReportDeliveryStatus;
  sentAt: string | null;
  generatedAt: string;
};

export type ReportDetail = ReportListItem & {
  bodyText: string;
};
