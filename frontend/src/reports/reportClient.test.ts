import { describe, expect, it } from "vitest";
import { getReportDetail } from "./reportClient";

describe("report detail local mode", () => {
  it("returns null for unknown report ids instead of throwing", async () => {
    await expect(getReportDetail("unknown-report")).resolves.toBeNull();
  });
});
