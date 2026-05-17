import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchChartHistory, fetchDashboardState, pauseLending, resumeLending, saveSettings } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches the aggregated dashboard state endpoint", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardState();

    expect(fetchMock).toHaveBeenCalledWith("/api/dashboard/state", undefined);
  });

  it("can request dashboard state without recent logs", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardState({ includeLogs: false });

    expect(fetchMock).toHaveBeenCalledWith("/api/dashboard/state?include_logs=false", undefined);
  });

  it("posts settings as JSON", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ success: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await saveSettings({ refreshRate: 45, frrdelta_min: -3, frrdelta_max: 9 });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/settings",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refreshRate: 45, frrdelta_min: -3, frrdelta_max: 9 })
      })
    );
  });

  it("uses POST for pause and resume actions", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ success: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await pauseLending();
    await resumeLending();

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/lending/pause", { method: "POST" });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/lending/resume", { method: "POST" });
  });

  it("throws readable errors for failed requests", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 500, statusText: "Broken" })));

    await expect(fetchChartHistory()).rejects.toThrow("500 Broken");
  });
});
