import { describe, expect, it } from "vitest";
import { buildDashboardView, buildXdayDurationCurve, calculateCoinRows, normalizeChartHistory } from "./dashboard";

describe("dashboard domain", () => {
  it("keeps live status visible while the first stats snapshot is missing", () => {
    const view = buildDashboardView({
      settings: { refreshRate: 30 },
      status: { last_status: "Lending running", last_update: "2026-05-13 22:47:59" },
      stats: {},
      recent_successful_loans: {},
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

  it("attaches recent successful loans to the matching coin row", () => {
    const view = buildDashboardView({
      settings: { refreshRate: 30 },
      status: { last_status: "Lending running" },
      stats: {
        raw_data: {
          USD: {
            averageLendingRate: "0.04",
            lentSum: "50",
            totalCoins: "100"
          }
        }
      },
      recent_successful_loans: {
        USD: [
          {
            amount: "300.0",
            rate: "0.00033",
            date: "2026-05-24 09:06:00"
          }
        ]
      },
      lending_paused: false,
      lending_strategies: { USD: "FRR" },
      plugins: {}
    });

    expect((view.coinRows[0] as any).recentSuccessfulLoans).toEqual([
      {
        amount: 300,
        rate: 0.00033,
        date: "2026-05-24 09:06:00"
      }
    ]);
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

  it("builds a clamped rate-to-days curve from xday thresholds", () => {
    const points = buildXdayDurationCurve(
      [
        { rate: 0.05, days: 120 },
        { rate: 0.03, days: 30 }
      ],
      5
    );

    // Sorted by rate with flat clamps on both ends of the range.
    expect(points).toEqual([
      [0, 30],
      [0.03, 30],
      [0.05, 120],
      [0.055, 120]
    ]);
  });

  it("returns an empty curve when xday thresholds are disabled or invalid", () => {
    expect(buildXdayDurationCurve([], 5)).toEqual([]);
    expect(buildXdayDurationCurve(undefined, 5)).toEqual([]);
    expect(
      buildXdayDurationCurve(
        [
          { rate: Number.NaN, days: 30 },
          { rate: 0.03, days: Number.NaN }
        ],
        5
      )
    ).toEqual([]);
  });

  it("caps the preview range at the configured rate limit", () => {
    const points = buildXdayDurationCurve([{ rate: 4.8, days: 120 }], 5);

    expect(points[points.length - 1][0]).toBe(5);
  });
});
