import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChartsPage } from "./ChartsPage";

vi.mock("echarts-for-react", () => ({
  default: ({ option }: { option: unknown }) => (
    <div data-option={JSON.stringify(option)} data-testid="echarts" />
  )
}));

describe("ChartsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("shows an empty state when no history exists", async () => {
    stubFetch({ "/api/charts/history": {} });

    render(<ChartsPage />);

    await screen.findByText("No chart history available");
  });

  it("renders chart panels for available history", async () => {
    stubFetch({ "/api/charts/history": { USD: [[100, "1", "10"]] } });

    render(<ChartsPage />);

    await waitFor(() => expect(screen.getByTestId("echarts")).toBeInTheDocument());
  });

  it("labels earnings series clearly and enables chart zooming", async () => {
    stubFetch({ "/api/charts/history": { USD: [[100, "1", "10"]] } });

    render(<ChartsPage />);

    const option = JSON.parse((await screen.findByTestId("echarts")).dataset.option ?? "{}");

    expect(option.legend.data).toEqual(["Daily Earnings", "Total Earnings"]);
    expect(option.series.map((series: { name: string }) => series.name)).toEqual([
      "Daily Earnings",
      "Total Earnings"
    ]);
    expect(option.yAxis.map((axis: { name: string }) => axis.name)).toEqual([
      "Daily Earnings",
      "Total Earnings"
    ]);
    expect(option.dataZoom).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "inside", xAxisIndex: 0 }),
        expect.objectContaining({ type: "slider", xAxisIndex: 0 })
      ])
    );
  });

  it("uses the dashboard exchange and label in the page title", async () => {
    stubFetch({
      "/api/dashboard/state": {
        settings: {},
        status: {},
        stats: { exchange: "Bitfinex", label: "Lending Bot", raw_data: {} },
        recent_logs: [],
        lending_paused: false,
        lending_strategies: {},
        plugins: {}
      },
      "/api/charts/history": {}
    });

    render(<ChartsPage />);

    await screen.findByRole("heading", { name: "Bitfinex Lending Bot - Profit Charts" });
  });
});

function stubFetch(responses: Record<string, unknown>) {
  const defaultDashboardState = {
    settings: {},
    status: {},
    stats: { raw_data: {} },
    recent_logs: [],
    lending_paused: false,
    lending_strategies: {},
    plugins: {}
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.pathname : input.url;
      return new Response(JSON.stringify(responses[url] ?? defaultDashboardState), { status: 200 });
    })
  );
}
