import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DashboardPage } from "./DashboardPage";
import type { DashboardStateResponse } from "../domain/types";

const baseState: DashboardStateResponse = {
  settings: { refreshRate: 30, timespanNames: ["Day"] },
  status: { last_status: "Lending running", last_update: "2026-05-13 22:47:59" },
  stats: { exchange: "Bitfinex", label: "Lending Bot", raw_data: {} },
  recent_logs: ["startup log"],
  lending_paused: false,
  lending_strategies: { USD: "FRR" },
  plugins: {}
};

describe("DashboardPage", () => {
  it("shows live status while waiting for the first stats snapshot", () => {
    render(<DashboardPage state={baseState} loading={false} onRefresh={() => undefined} />);

    expect(screen.getByText("Lending running")).toBeInTheDocument();
    expect(screen.getByText("Waiting for the first statistics snapshot")).toBeInTheDocument();
    expect(screen.getByText("startup log")).toBeInTheDocument();
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
    fireEvent.change(refreshInput, { target: { value: "45" } });
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    await waitFor(() => expect(onSaveSettings).toHaveBeenCalledWith(expect.objectContaining({ refreshRate: 45 })));
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
