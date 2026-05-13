import { useCallback, useEffect, useRef, useState } from "react";
import { notification } from "antd";
import { fetchDashboardState, pauseLending, resumeLending, saveSettings } from "../api/client";
import type { DashboardSettings, DashboardStateResponse } from "../domain/types";

const INITIAL_RETRY_MS = 5000;

export function useDashboardState() {
  const [state, setState] = useState<DashboardStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const stateRef = useRef<DashboardStateResponse | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await fetchDashboardState();
      stateRef.current = next;
      setState(next);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load dashboard state";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const refreshMs = Math.max((state?.settings.refreshRate ?? 30) * 1000, 30000);
    const statsReady = Boolean(state?.stats.raw_data && Object.keys(state.stats.raw_data).length > 0);
    const interval = statsReady ? refreshMs : INITIAL_RETRY_MS;
    const timer = window.setTimeout(() => void refresh(), interval);
    return () => window.clearTimeout(timer);
  }, [refresh, state]);

  useEffect(() => {
    const source = new EventSource("/stream-logs");
    source.onmessage = (event) => {
      setState((current) => {
        if (!current) return current;
        const recent_logs = [event.data, ...current.recent_logs].slice(0, 500);
        const next = { ...current, recent_logs };
        stateRef.current = next;
        return next;
      });
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, []);

  const updateSettings = useCallback(
    async (settings: DashboardSettings) => {
      const previous = stateRef.current;
      if (previous) {
        const next = { ...previous, settings: { ...previous.settings, ...settings } };
        stateRef.current = next;
        setState(next);
      }
      try {
        await saveSettings(settings);
        notification.success({ title: "Settings saved" });
        await refresh();
      } catch (err) {
        if (previous) setState(previous);
        notification.error({ title: "Failed to save settings", description: getErrorMessage(err) });
      }
    },
    [refresh]
  );

  const setPaused = useCallback(
    async (paused: boolean) => {
      const previous = stateRef.current;
      if (previous) {
        const next = { ...previous, lending_paused: paused };
        stateRef.current = next;
        setState(next);
      }
      try {
        if (paused) {
          await pauseLending();
        } else {
          await resumeLending();
        }
        await refresh();
      } catch (err) {
        if (previous) setState(previous);
        notification.error({ title: "Failed to update lending state", description: getErrorMessage(err) });
      }
    },
    [refresh]
  );

  return { state, loading, error, refresh, updateSettings, setPaused };
}

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
