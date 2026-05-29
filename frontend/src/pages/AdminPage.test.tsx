import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AdminContent } from "./AdminPage";
import type { AdminLiveDayReadModel } from "../admin/adminTypes";

describe("AdminContent", () => {
  it("renders summary counters and live-day user rows", () => {
    const liveDay: AdminLiveDayReadModel = {
      tradingDay: "2026-05-29",
      generatedAt: "2026-05-29T13:00:00+00:00",
      summary: {
        totalUsers: 2,
        eligibleUsers: 1,
        linkedUsers: 1,
        reportsGenerated: 1,
        reportsSent: 1,
        blockedUsers: 1,
      },
      users: [
        {
          userId: "user-1",
          email: "ready@example.com",
          displayName: "Ready User",
          eligible: true,
          telegramLinked: true,
          reportGenerated: true,
          reportSent: true,
          blocker: null,
          reportStatus: "sent",
          sentAt: "2026-05-29T12:05:00+00:00",
        },
        {
          userId: "user-2",
          email: "blocked@example.com",
          displayName: null,
          eligible: false,
          telegramLinked: false,
          reportGenerated: false,
          reportSent: false,
          blocker: "Telegram not linked",
          reportStatus: null,
          sentAt: null,
        },
      ],
    };

    const html = renderToStaticMarkup(<AdminContent liveDay={liveDay} />);

    expect(html).toContain("Users");
    expect(html).toContain("Ready User");
    expect(html).toContain("blocked@example.com");
    expect(html).toContain("Telegram not linked");
    expect(html).toContain("Sent at");
  });
});
