import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { DashboardStateResponse } from "../domain/types";

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

    await waitFor(() =>
      expect(onSaveSettings).toHaveBeenCalledWith(expect.objectContaining({ frrdelta_min: -3, frrdelta_max: 9 }))
    );
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
