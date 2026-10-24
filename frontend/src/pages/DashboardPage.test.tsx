import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { DashboardStateResponse } from "../domain/types";

vi.mock("echarts-for-react", () => ({
  default: ({ option }: { option: unknown }) => (
    <div data-option={JSON.stringify(option)} data-testid="xday-echarts" />
  )
}));

const baseState: DashboardStateResponse = {
  settings: { refreshRate: 30, timespanNames: ["Day"] },
  status: { last_status: "Lending running", last_update: "2026-05-13 22:47:59" },
  stats: { exchange: "Bitfinex", label: "Lending Bot", raw_data: {} },
  recent_successful_loans: {},
  recent_logs: ["startup log"],
  lending_paused: false,
  lending_strategies: { USD: "FRR" },
  plugins: {}
} as DashboardStateResponse;

const xdayState: DashboardStateResponse = {
  ...baseState,
  settings: {
    ...baseState.settings,
    frrdelta_min: -3,
    frrdelta_max: 9,
    xday_thresholds: [
      { rate: 0.03, days: 30 },
      { rate: 0.05, days: 120 }
    ]
  }
} as DashboardStateResponse;

describe("DashboardPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    Object.defineProperty(window.navigator, "languages", {
      configurable: true,
      value: ["en-US"]
    });
  });

  it("shows live status while waiting for the first stats snapshot", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.getByText("Lending running")).toBeInTheDocument();
    expect(screen.getByText("Waiting for lending position data")).toBeInTheDocument();
    expect(screen.getByText("startup log")).toBeInTheDocument();
  });

  it("shows a clear empty position message when raw stats cannot produce coin rows", () => {
    render(
      <DashboardPage
        loading={false}
        onRefresh={() => undefined}
        state={{
          ...baseState,
          stats: {
            ...baseState.stats,
            raw_data: {
              USD: {
                averageLendingRate: "0.04",
                totalCoins: "0"
              }
            }
          }
        }}
      />
    );

    expect(screen.getByText("Waiting for lending position data")).toBeInTheDocument();
    expect(screen.queryByText("No data")).not.toBeInTheDocument();
  });

  it("renders coin lending rows when stats are present", () => {
    render(
      <DashboardPage
        loading={false}
        onRefresh={() => undefined}
        state={{
          ...baseState,
          stats: {
            ...baseState.stats,
            raw_data: {
              USD: {
                averageLendingRate: "0.04",
                lentSum: "50",
                totalCoins: "100",
                maxToLend: "100",
                highestBid: "1"
              }
            },
            outputCurrency: { currency: "USD", highestBid: "1" }
          }
        }}
      />
    );

    expect(screen.getAllByText("USD").length).toBeGreaterThan(0);
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("renders recent successful loans in the desktop positions table", () => {
    render(
      <DashboardPage
        loading={false}
        onRefresh={() => undefined}
        state={{
          ...baseState,
          recent_successful_loans: {
            USD: [
              {
                amount: "300.0",
                rate: "0.00033",
                date: "2026-05-24 09:06:00"
              }
            ]
          },
          stats: {
            ...baseState.stats,
            raw_data: {
              USD: {
                averageLendingRate: "0.04",
                lentSum: "50",
                totalCoins: "100"
              }
            },
            outputCurrency: { currency: "USD", highestBid: "1" }
          }
        }}
      />
    );

    expect(screen.getByText("Recent Loans")).toBeInTheDocument();
    expect(screen.getByText("300 USD")).toBeInTheDocument();
    expect(screen.getByText("0.03300%")).toBeInTheDocument();
    expect(screen.getByText("2026-05-24 09:06:00")).toBeInTheDocument();
  });

  it("renders mobile-friendly coin cards for narrow portrait screens", () => {
    render(
      <DashboardPage
        loading={false}
        onRefresh={() => undefined}
        compact
        state={{
          ...baseState,
          stats: {
            ...baseState.stats,
            raw_data: {
              USD: {
                averageLendingRate: "0.04",
                lentSum: "50",
                totalCoins: "100",
                maxToLend: "100",
                highestBid: "1"
              }
            },
            outputCurrency: { currency: "USD", highestBid: "1" }
          }
        }}
      />
    );

    expect(screen.getByTestId("mobile-coin-list")).toBeInTheDocument();
    expect(screen.queryByTestId("desktop-coin-table")).not.toBeInTheDocument();
  });

  it("renders recent successful loans in compact coin cards", () => {
    render(
      <DashboardPage
        loading={false}
        onRefresh={() => undefined}
        compact
        state={{
          ...baseState,
          recent_successful_loans: {
            USD: [
              {
                amount: "300.0",
                rate: "0.00033",
                date: "2026-05-24 09:06:00"
              }
            ]
          },
          stats: {
            ...baseState.stats,
            raw_data: {
              USD: {
                averageLendingRate: "0.04",
                lentSum: "50",
                totalCoins: "100",
                maxToLend: "100"
              }
            },
            outputCurrency: { currency: "USD", highestBid: "1" }
          }
        }}
      />
    );

    expect(screen.getByTestId("mobile-coin-list")).toBeInTheDocument();
    expect(screen.getByText("Recent Loans")).toBeInTheDocument();
    expect(screen.getByText("300 USD")).toBeInTheDocument();
    expect(screen.getByText("0.03300%")).toBeInTheDocument();
  });

  it("omits the low-value snapshot metadata card", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.queryByText("Snapshot")).not.toBeInTheDocument();
    expect(screen.queryByText("Exchange")).not.toBeInTheDocument();
    expect(screen.getByText("Recent Logs")).toBeInTheDocument();
  });

  it("orders header actions from navigation to utilities to state change", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    const charts = screen.getByRole("link", { name: "Charts" });
    const refresh = screen.getByRole("button", { name: "Refresh Dashboard" });
    const settings = screen.getByRole("button", { name: /settings/i });
    const pause = screen.getByRole("button", { name: /pause/i });

    expect(charts.compareDocumentPosition(refresh)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(refresh.compareDocumentPosition(settings)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(settings.compareDocumentPosition(pause)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("opens the settings modal and saves edited values", async () => {
    const onSaveSettings = vi.fn();
    render(
      <DashboardPage
        state={{ ...baseState, settings: { ...baseState.settings, frrdelta_min: -3, frrdelta_max: 9 } }}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument();

    const refreshInput = screen.getByLabelText("Refresh interval");
    await waitFor(() => expect(refreshInput).toHaveValue("30"));
    fireEvent.change(refreshInput, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() => expect(onSaveSettings).toHaveBeenCalledWith(expect.objectContaining({ refreshRate: 45 })));
  });

  it("places language at the top of the settings modal", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    const languageLabel = screen.getByText("Language");
    const refreshLabel = screen.getByText("Refresh interval");
    expect(languageLabel.compareDocumentPosition(refreshLabel)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("uses a compact settings layout with one FRR range slider", async () => {
    const onSaveSettings = vi.fn();
    render(
      <DashboardPage
        state={{ ...baseState, settings: { ...baseState.settings, frrdelta_min: -3, frrdelta_max: 9 } }}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    expect(screen.getByTestId("refresh-interval-control")).toBeInTheDocument();
    expect(screen.getByText("Min -3%")).toBeInTheDocument();
    expect(screen.getByText("Max 9%")).toBeInTheDocument();
    expect(screen.queryByLabelText("FRR minimum adjustment")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("FRR maximum adjustment")).not.toBeInTheDocument();
    const rangeHandles = screen.getAllByRole("slider");
    expect(rangeHandles).toHaveLength(2);
    expect(rangeHandles[0]).toHaveAttribute("aria-valuemin", "-30");
    expect(screen.getByRole("slider", { name: "Minimum FRR adjustment" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Maximum FRR adjustment" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    // Untouched strategy values are not resubmitted: they would otherwise be
    // entity-ified into web overrides shadowing per-coin TOML config.
    await waitFor(() => expect(onSaveSettings).toHaveBeenCalled());
    const payload = onSaveSettings.mock.calls[0][0] as Record<string, unknown>;
    expect(payload).not.toHaveProperty("frrdelta_min");
    expect(payload).not.toHaveProperty("frrdelta_max");
  });

  it("edits per-currency FRR and duration settings from coin tabs", async () => {
    const onSaveSettings = vi.fn();
    const coinState: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USD", "USDt"],
        coin_settings: {
          USD: { frrdelta_min: -2, frrdelta_max: 4, xday_thresholds: [] },
          USDt: { frrdelta_min: -1, frrdelta_max: 5, xday_thresholds: [{ rate: 0.03, days: 30 }] }
        }
      }
    };
    render(
      <DashboardPage
        state={coinState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    // The default tab is active first and shows the global values.
    expect(screen.getByRole("tab", { name: "Default" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "USDt" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "USDt" }));
    expect(screen.getByText("Min -1%")).toBeInTheDocument();
    expect(screen.getByText("Max 5%")).toBeInTheDocument();

    const daysInput = screen.getByLabelText("Lending days");
    await waitFor(() => expect(daysInput).toHaveValue("30"));
    fireEvent.change(daysInput, { target: { value: "40" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    // Only the edited field becomes an explicit override; untouched coins
    // (and untouched fields like the FRR range) keep inheriting.
    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          coin_settings: {
            USDt: { xday_thresholds: [{ rate: 0.03, days: 40 }] }
          }
        })
      )
    );
  });

  it("saving default-tab edits does not create coin overrides", async () => {
    const onSaveSettings = vi.fn();
    const coinState: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USD", "USDt"],
        frrdelta_min: -3,
        frrdelta_max: 9,
        coin_settings: {
          USD: { frrdelta_min: -5, frrdelta_max: 5, xday_thresholds: [] },
          USDt: { frrdelta_min: -3, frrdelta_max: 9, xday_thresholds: [] }
        }
      }
    };
    render(
      <DashboardPage
        state={coinState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    const refreshInput = screen.getByLabelText("Refresh interval");
    fireEvent.change(refreshInput, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ refreshRate: 45, coin_settings: {} })
      )
    );
  });

  it("preserves existing overrides of tabs the user never opened", async () => {
    const onSaveSettings = vi.fn();
    const usdtOverride = {
      frrdelta_min: -1,
      frrdelta_max: 5,
      xday_thresholds: [{ rate: 0.03, days: 40 }]
    };
    const coinState: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USD", "USDt"],
        coin_settings: { USDt: usdtOverride },
        coin_overrides: { USDt: usdtOverride }
      }
    };
    render(
      <DashboardPage
        state={coinState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    // Only touch the Default tab; the USDt tab is never opened.
    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    const refreshInput = screen.getByLabelText("Refresh interval");
    fireEvent.change(refreshInput, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() => expect(onSaveSettings).toHaveBeenCalled());
    const payload = onSaveSettings.mock.calls[0][0] as { coin_settings?: unknown };
    // The untouched override must survive byte-for-byte, not be wiped or
    // partially rebuilt from unvisited-tab defaults.
    expect(payload.coin_settings).toEqual({ USDt: usdtOverride });
  });

  it("preserves an existing override that exceeds the slider range", async () => {
    const onSaveSettings = vi.fn();
    const override = { frrdelta_min: -1, frrdelta_max: 55, xday_thresholds: [] };
    const coinState: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USDt"],
        coin_settings: { USDt: override },
        coin_overrides: { USDt: override }
      }
    };
    render(
      <DashboardPage
        state={coinState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    // The slider clamps the display to its max (50); the untouched override
    // must still round-trip with its original value (55).
    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    expect(screen.getByText("Max 50%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() => expect(onSaveSettings).toHaveBeenCalled());
    const payload = onSaveSettings.mock.calls[0][0] as {
      coin_settings?: Record<string, { frrdelta_max?: number }>;
    };
    expect(payload.coin_settings?.USDt?.frrdelta_max).toBe(55);
  });

  it("keeps a pending reset across background settings refreshes", async () => {
    const onSaveSettings = vi.fn();
    const override = { frrdelta_min: -1, frrdelta_max: 5, xday_thresholds: [] };
    const makeState = (): DashboardStateResponse => ({
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USDt"],
        coin_settings: { USDt: override },
        coin_overrides: { USDt: override }
      }
    });
    const { rerender } = render(
      <DashboardPage
        state={makeState()}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    fireEvent.click(screen.getByRole("tab", { name: "USDt" }));
    fireEvent.click(screen.getByRole("button", { name: /reset overrides/i }));

    // A poll delivers a new state object while the modal is open.
    rerender(
      <DashboardPage
        state={makeState()}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() => expect(onSaveSettings).toHaveBeenCalled());
    const payload = onSaveSettings.mock.calls[0][0] as { coin_settings?: unknown };
    expect(payload.coin_settings).toEqual({});
  });

  it("does not resubmit stale values when settings change behind an open modal", async () => {
    const onSaveSettings = vi.fn();
    const stateA: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USDt"],
        coin_settings: { USDt: { frrdelta_min: -10, frrdelta_max: 10, xday_thresholds: [] } }
      }
    };
    const { rerender } = render(
      <DashboardPage
        state={stateA}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    const refreshInput = screen.getByLabelText("Refresh interval");
    fireEvent.change(refreshInput, { target: { value: "45" } });

    // While the modal is open, another client saves a new global FRR range.
    const stateB: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USDt"],
        frrdelta_min: -2,
        frrdelta_max: 6,
        coin_settings: { USDt: { frrdelta_min: -2, frrdelta_max: 6, xday_thresholds: [] } }
      }
    };
    rerender(
      <DashboardPage
        state={stateB}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    // The stale -10/10 sitting in the form must be judged against the
    // baseline captured at open time, not the refreshed -2/6.
    await waitFor(() => expect(onSaveSettings).toHaveBeenCalled());
    const payload = onSaveSettings.mock.calls[0][0] as Record<string, unknown>;
    expect(payload.refreshRate).toBe(45);
    expect(payload).not.toHaveProperty("frrdelta_min");
    expect(payload).not.toHaveProperty("frrdelta_max");
    expect(payload.coin_settings).toEqual({});
  });

  it("resets saved per-currency overrides from the coin tab", async () => {
    const onSaveSettings = vi.fn();
    const coinState: DashboardStateResponse = {
      ...baseState,
      settings: {
        ...baseState.settings,
        currencies: ["USDt"],
        coin_settings: {
          USDt: { frrdelta_min: -1, frrdelta_max: 5, xday_thresholds: [{ rate: 0.03, days: 30 }] }
        },
        coin_overrides: {
          USDt: { frrdelta_min: -1, frrdelta_max: 5, xday_thresholds: [{ rate: 0.03, days: 30 }] }
        }
      }
    };
    render(
      <DashboardPage
        state={coinState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    fireEvent.click(screen.getByRole("tab", { name: "USDt" }));
    expect(screen.getByText("Overridden")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /reset overrides/i }));
    expect(screen.getByText(/Applies after saving/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(expect.objectContaining({ coin_settings: {} }))
    );
  });

  it("edits and saves xday duration thresholds", async () => {
    const onSaveSettings = vi.fn();
    render(
      <DashboardPage
        state={xdayState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    const rateInputs = screen.getAllByLabelText("Daily rate");
    const daysInputs = screen.getAllByLabelText("Lending days");
    expect(rateInputs.map((input) => (input as HTMLInputElement).value)).toEqual(["0.030", "0.050"]);
    expect(daysInputs.map((input) => (input as HTMLInputElement).value)).toEqual(["30", "120"]);

    fireEvent.change(daysInputs[0], { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          xday_thresholds: [
            { rate: 0.03, days: 45 },
            { rate: 0.05, days: 120 }
          ]
        })
      )
    );
  });

  it("adds and removes xday threshold rows", async () => {
    const onSaveSettings = vi.fn();
    render(
      <DashboardPage
        state={baseState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    expect(screen.getByText(/No thresholds configured/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Daily rate")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /add threshold/i }));
    fireEvent.click(screen.getByRole("button", { name: /add threshold/i }));
    expect(screen.getAllByLabelText("Daily rate")).toHaveLength(2);

    fireEvent.click(screen.getAllByRole("button", { name: "Remove threshold" })[0]);
    expect(screen.getAllByLabelText("Daily rate")).toHaveLength(1);

    const rateInput = screen.getByLabelText("Daily rate");
    const daysInput = screen.getByLabelText("Lending days");
    fireEvent.change(rateInput, { target: { value: "0.04" } });
    fireEvent.change(daysInput, { target: { value: "60" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ xday_thresholds: [{ rate: 0.04, days: 60 }] })
      )
    );
  });

  it("shows the duration mapping preview when thresholds exist", async () => {
    render(
      <DashboardPage state={xdayState} loading={false} onRefresh={() => undefined} />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    const chart = await screen.findByTestId("xday-echarts");
    const option = JSON.parse(chart.dataset.option ?? "{}");
    expect(option.series[0].data).toEqual([
      [0, 30],
      [0.03, 30],
      [0.05, 120],
      [0.055, 120]
    ]);
    expect(screen.getByText("Duration mapping preview")).toBeInTheDocument();
  });

  it("blocks saving when days decrease as the rate increases", async () => {
    const onSaveSettings = vi.fn();
    render(
      <DashboardPage
        state={xdayState}
        loading={false}
        onRefresh={() => undefined}
        onSaveSettings={onSaveSettings}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    const daysInputs = screen.getAllByLabelText("Lending days");
    fireEvent.change(daysInputs[1], { target: { value: "20" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() =>
      expect(screen.getByText("Days must not decrease as the rate increases")).toBeInTheDocument()
    );
    expect(onSaveSettings).not.toHaveBeenCalled();
  });

  it("switches dashboard UI labels from settings while leaving logs unchanged", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.queryByRole("radio", { name: "简体中文" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    fireEvent.click(screen.getByRole("radio", { name: "简体中文" }));

    expect(screen.getByRole("link", { name: /图\s*表/ })).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "设置" })).toBeInTheDocument();
    expect(screen.getByText("运行中")).toBeInTheDocument();
    expect(screen.getByText("借贷运行中")).toBeInTheDocument();
    expect(screen.getByText("状态")).toBeInTheDocument();
    expect(screen.getByText("借出仓位")).toBeInTheDocument();
    expect(screen.getByText("最近日志")).toBeInTheDocument();
    expect(screen.getByText("startup log")).toBeInTheDocument();
  });

  it("keeps recent logs pinned to the newest entry until the user scrolls up", async () => {
    const scrolledState = {
      ...baseState,
      recent_logs: ["first log", "second log", "third log"]
    };
    const { rerender } = render(
      <DashboardPage
        state={{ ...scrolledState, recent_logs: ["first log", "second log"] }}
        loading={false}
        onRefresh={() => undefined}
      />
    );
    const logList = screen.getByTestId("recent-log-list");
    setScrollMetrics(logList, { scrollHeight: 1000, clientHeight: 100, scrollTop: 900 });

    rerender(<DashboardPage state={scrolledState} loading={false} onRefresh={() => undefined} />);

    await waitFor(() => expect(logList.scrollTop).toBe(1000));

    logList.scrollTop = 200;
    fireEvent.scroll(logList);

    rerender(
      <DashboardPage
        state={{ ...scrolledState, recent_logs: [...scrolledState.recent_logs, "newest log"] }}
        loading={false}
        onRefresh={() => undefined}
      />
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "New Logs" })).toBeInTheDocument());
    expect(logList.scrollTop).toBe(200);

    logList.scrollTop = 900;
    fireEvent.scroll(logList);

    await waitFor(() => expect(screen.queryByRole("button", { name: "New Logs" })).not.toBeInTheDocument());
  });

  it("uses simplified Chinese when the browser default language is supported", () => {
    Object.defineProperty(window.navigator, "languages", {
      configurable: true,
      value: ["zh-CN", "en-US"]
    });

    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.getByRole("link", { name: /图\s*表/ })).toBeInTheDocument();
    expect(screen.getByText("借贷运行中")).toBeInTheDocument();
  });

  it("falls back to English when the browser default language is unsupported", () => {
    Object.defineProperty(window.navigator, "languages", {
      configurable: true,
      value: ["fr-FR"]
    });

    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.getByRole("link", { name: "Charts" })).toBeInTheDocument();
    expect(screen.getByText("Lending running")).toBeInTheDocument();
  });

  it("calls pause and resume actions from the header", () => {
    const onSetPaused = vi.fn();
    const { rerender } = render(
      <DashboardPage state={baseState} loading={false} onRefresh={() => undefined} onSetPaused={onSetPaused} />
    );

    fireEvent.click(screen.getByRole("button", { name: /pause/i }));
    expect(onSetPaused).toHaveBeenCalledWith(true);

    rerender(
      <DashboardPage
        state={{ ...baseState, lending_paused: true }}
        loading={false}
        onRefresh={() => undefined}
        onSetPaused={onSetPaused}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /resume/i }));
    expect(onSetPaused).toHaveBeenCalledWith(false);
  });

  it("shows refresh errors without hiding current dashboard content", () => {
    render(
      <DashboardPage
        state={baseState}
        loading={false}
        error="503 Unavailable"
        onRefresh={() => undefined}
      />
    );

    expect(screen.getByText("Dashboard refresh failed")).toBeInTheDocument();
    expect(screen.getByText("Lending running")).toBeInTheDocument();
  });
});

function setScrollMetrics(
  element: HTMLElement,
  metrics: { clientHeight: number; scrollHeight: number; scrollTop: number }
) {
  Object.defineProperties(element, {
    clientHeight: { configurable: true, value: metrics.clientHeight },
    scrollHeight: { configurable: true, value: metrics.scrollHeight },
    scrollTop: { configurable: true, value: metrics.scrollTop, writable: true }
  });
}
