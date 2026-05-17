import type {
  ChartSeries,
  CoinRow,
  DashboardStateResponse,
  DashboardView,
  OutputCurrency,
  RawChartPoint,
  TimespanName
} from "./types";

const DEFAULT_TIMESPANS: TimespanName[] = ["Year", "Month", "Week", "Day", "Hour"];

const TIMESPAN_MULTIPLIER: Record<TimespanName, number> = {
  Hour: 1 / 24,
  Day: 1,
  Week: 7,
  Month: 30,
  Year: 365
};

export function buildDashboardView(state: DashboardStateResponse): DashboardView {
  const rawData = state.stats.raw_data ?? {};
  const statsReady = Object.keys(rawData).length > 0;
  const statusText =
    state.status.last_status ||
    state.stats.last_status ||
    (statsReady ? "Stats updated" : "Waiting for bot status update");
  const title = [state.stats.exchange, state.stats.label].filter(Boolean).join(" ") || "Lending Bot";
  const timespans = state.settings.timespanNames?.length
    ? state.settings.timespanNames
    : DEFAULT_TIMESPANS;

  return {
    title,
    statusText,
    lastUpdate: state.status.last_update || state.stats.last_update || "Not updated",
    statsReady,
    emptyStatsMessage: statsReady ? "" : "Waiting for the first statistics snapshot",
    logs: state.recent_logs ?? [],
    coinRows: calculateCoinRows(rawData, state.stats.outputCurrency ?? {}, timespans),
    strategies: uniqueValues(Object.values(state.lending_strategies)),
    paused: state.lending_paused
  };
}

export function calculateCoinRows(
  rawData: NonNullable<DashboardStateResponse["stats"]["raw_data"]>,
  outputCurrency: OutputCurrency,
  timespans: TimespanName[]
): CoinRow[] {
  const outputCoin = outputCurrency.currency || "BTC";

  return Object.entries(rawData)
    .map(([currency, stats]) => {
      const averageDailyRate = toNumber(stats.averageLendingRate);
      const lentSum = toNumber(stats.lentSum);
      let totalCoins = toNumber(stats.totalCoins);
      let maxToLend = toNumber(stats.maxToLend);

      if (!Number.isFinite(totalCoins) && Number.isFinite(lentSum)) {
        totalCoins = lentSum;
      }
      if (!Number.isFinite(maxToLend) || maxToLend <= 0) {
        maxToLend = totalCoins;
      }
      if (!Number.isFinite(totalCoins) || totalCoins <= 0) {
        return null;
      }

      const lendingRate = Number.isFinite(averageDailyRate) ? (averageDailyRate * 0.85) / 100 : 0;
      const lentPercentRatio = Number.isFinite(lentSum) ? lentSum / totalCoins : 0;

      return {
        currency,
        lentSum,
        totalCoins,
        maxToLend,
        lentPercent: lentPercentRatio * 100,
        averageDailyRate,
        effectiveDailyRate: lendingRate * 100 * lentPercentRatio,
        yearlyRate: lendingRate * 100 * 365 * lentPercentRatio,
        yearlyCompoundRate: (Math.pow(lendingRate + 1, 365) - 1) * 100 * lentPercentRatio,
        earnings: timespans.map((timespan) => ({
          timespan,
          value: calculateEarnings(lentSum, lendingRate, TIMESPAN_MULTIPLIER[timespan]),
          currency: currency === outputCoin ? currency : outputCoin
        }))
      };
    })
    .filter((row): row is CoinRow => row !== null);
}

export function normalizeChartHistory(
  history: Record<string, RawChartPoint[]> | null | undefined
): ChartSeries[] {
  return Object.entries(history ?? {}).map(([coin, points]) => ({
    coin,
    points: points
      .map(([timestamp, daily, total]) => ({
        timestamp,
        daily: toNumber(daily),
        total: toNumber(total)
      }))
      .sort((left, right) => left.timestamp - right.timestamp)
  }));
}

export function formatNumber(value: number, precision = 4): string {
  if (!Number.isFinite(value)) return "0";
  return value.toLocaleString(undefined, {
    maximumFractionDigits: precision,
    minimumFractionDigits: 0
  });
}

function calculateEarnings(sum: number, rate: number, multiplier: number): number {
  if (!Number.isFinite(sum) || !Number.isFinite(rate)) return 0;
  return sum * Math.pow(1 + rate, multiplier) - sum;
}

function toNumber(value: string | number | undefined): number {
  if (value === undefined || value === "") return Number.NaN;
  return typeof value === "number" ? value : Number.parseFloat(value);
}

function uniqueValues(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}
