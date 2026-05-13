import { describe, expect, it } from "vitest";
import { buildDashboardView, calculateCoinRows, normalizeChartHistory } from "./dashboard";

describe("dashboard domain", () => {
  it("keeps live status visible while the first stats snapshot is missing", () => {
    const view = buildDashboardView({
      settings: { refreshRate: 30 },
      status: { last_status: "Lending running", last_update: "2026-05-13 22:47:59" },
      stats: {},
      recent_logs: ["startup"],
      lending_paused: false,
      lending_strategies: { USD: "FRR" },
      plugins: {}
    });

    expect(view.statusText).toBe("Lending running");
    expect(view.statsReady).toBe(false);
    expect(view.emptyStatsMessage).toBe("Waiting for the first statistics snapshot");
  });

  it("calculates responsive coin rows without losing existing earnings math", () => {
    const rows = calculateCoinRows(
      {
        USD: {
          averageLendingRate: "0.04",
          lentSum: "50",
          totalCoins: "100",
          maxToLend: "100",
          highestBid: "1"
        }
      },
      { currency: "USD", highestBid: "1" },
      ["Day"]
    );

    expect(rows).toHaveLength(1);
    expect(rows[0].currency).toBe("USD");
    expect(rows[0].lentPercent).toBeCloseTo(50);
    expect(rows[0].effectiveDailyRate).toBeCloseTo(0.017);
    expect(rows[0].earnings[0].value).toBeCloseTo(0.017);
  });

  it("normalizes chart history into sorted timestamp series", () => {
    const series = normalizeChartHistory({
      USD: [
        [200, "2", "12"],
        [100, "1", "10"]
      ]
    });

    expect(series[0].coin).toBe("USD");
    expect(series[0].points.map((point) => point.timestamp)).toEqual([100, 200]);
  });
});
