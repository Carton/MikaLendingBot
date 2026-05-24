export type TimespanName = "Hour" | "Day" | "Week" | "Month" | "Year";

export interface DashboardSettings {
  refreshRate?: number;
  timespanNames?: TimespanName[];
  btcDisplayUnit?: string;
  outputCurrencyDisplayMode?: "all" | "summary";
  frrdelta_min?: number;
  frrdelta_max?: number;
  recentSuccessfulLoans?: number;
}

export interface DashboardStatus {
  last_status?: string;
  last_update?: string;
}

export interface CoinStats {
  averageLendingRate?: string;
  lentSum?: string;
  totalCoins?: string;
  maxToLend?: string;
  highestBid?: string;
  couple?: string;
}

export interface OutputCurrency {
  currency?: string;
  highestBid?: string;
}

export interface StatsSnapshot {
  exchange?: string;
  label?: string;
  last_status?: string;
  last_update?: string;
  raw_data?: Record<string, CoinStats>;
  outputCurrency?: OutputCurrency;
  plugins?: PluginMetadata;
  log?: string[];
}

export interface PluginMetadata {
  enabled?: string[];
  [pluginName: string]: unknown;
}

export interface DashboardStateResponse {
  settings: DashboardSettings;
  status: DashboardStatus;
  stats: StatsSnapshot;
  recent_successful_loans: Record<string, RecentSuccessfulLoan[]>;
  recent_logs?: string[];
  lending_paused: boolean;
  lending_strategies: Record<string, string>;
  plugins: PluginMetadata;
}

export interface CoinEarning {
  timespan: TimespanName;
  value: number;
  currency: string;
}

export interface CoinRow {
  currency: string;
  lentSum: number;
  totalCoins: number;
  maxToLend: number;
  lentPercent: number;
  averageDailyRate: number;
  effectiveDailyRate: number;
  yearlyRate: number;
  yearlyCompoundRate: number;
  earnings: CoinEarning[];
  recentSuccessfulLoans: RecentLoan[];
}

export interface RecentSuccessfulLoan {
  amount?: string;
  rate?: string;
  date?: string;
}

export interface RecentLoan {
  amount: number;
  rate: number;
  date: string;
}

export interface DashboardView {
  title: string;
  statusText: string;
  lastUpdate: string;
  statsReady: boolean;
  emptyStatsMessage: string;
  logs: string[];
  coinRows: CoinRow[];
  strategies: string[];
  paused: boolean;
}

export type RawChartPoint = [number, string | number, string | number];

export interface ChartSeries {
  coin: string;
  points: Array<{
    timestamp: number;
    daily: number;
    total: number;
  }>;
}
