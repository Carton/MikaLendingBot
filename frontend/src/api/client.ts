import type { DashboardSettings, DashboardStateResponse, RawChartPoint } from "../domain/types";

interface FetchDashboardStateOptions {
  includeLogs?: boolean;
}

export async function fetchDashboardState(options: FetchDashboardStateOptions = {}): Promise<DashboardStateResponse> {
  const url = options.includeLogs === false ? "/api/dashboard/state?include_logs=false" : "/api/dashboard/state";
  return requestJson<DashboardStateResponse>(url);
}

export async function saveSettings(settings: DashboardSettings): Promise<void> {
  await requestJson("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
}

export async function pauseLending(): Promise<void> {
  await requestJson("/api/lending/pause", { method: "POST" });
}

export async function resumeLending(): Promise<void> {
  await requestJson("/api/lending/resume", { method: "POST" });
}

export async function fetchChartHistory(): Promise<Record<string, RawChartPoint[]>> {
  return requestJson<Record<string, RawChartPoint[]>>("/api/charts/history");
}

async function requestJson<T = unknown>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}
