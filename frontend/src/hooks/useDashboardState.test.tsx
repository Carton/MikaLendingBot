import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDashboardState } from "./useDashboardState";
import type { DashboardStateResponse } from "../domain/types";

const state: DashboardStateResponse = {
  settings: { refreshRate: 30 },
  status: { last_status: "Lending running", last_update: "2026-05-13 22:47:59" },
  stats: { raw_data: {} },
  recent_logs: ["startup"],
  lending_paused: false,
  lending_strategies: { USD: "FRR" },
  plugins: {}
};

class EventSourceMock {
  static instances: EventSourceMock[] = [];
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    EventSourceMock.instances.push(this);
  }

  close = vi.fn();
}

describe("useDashboardState", () => {
  beforeEach(() => {
    EventSourceMock.instances = [];
    vi.stubGlobal("EventSource", EventSourceMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("loads dashboard state and subscribes to SSE logs", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(state), { status: 200 })));

    const { result } = renderHook(() => useDashboardState());

    await waitFor(() => expect(result.current.state?.status.last_status).toBe("Lending running"));
    expect(EventSourceMock.instances[0].url).toBe("/stream-logs");

    act(() => {
      EventSourceMock.instances[0].onmessage?.({ data: "new log" } as MessageEvent<string>);
    });

    expect(result.current.state?.recent_logs[0]).toBe("new log");
  });

  it("optimistically pauses lending then refreshes state", async () => {
    const pausedState = { ...state, lending_paused: true };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(state), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ success: true }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(pausedState), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useDashboardState());
    await waitFor(() => expect(result.current.state).not.toBeNull());

    await act(async () => {
      await result.current.setPaused(true);
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/lending/pause", { method: "POST" });
    expect(result.current.state?.lending_paused).toBe(true);
  });

  it("surfaces refresh errors without clearing existing state", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(state), { status: 200 }))
      .mockResolvedValueOnce(new Response("fail", { status: 503, statusText: "Unavailable" }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useDashboardState());
    await waitFor(() => expect(result.current.state).not.toBeNull());

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.error).toBe("503 Unavailable");
    expect(result.current.state?.status.last_status).toBe("Lending running");
  });
});
