import { useCallback, useEffect, useRef, useState } from "react";
import { notification } from "antd";
import { fetchDashboardState, pauseLending, resumeLending, saveSettings } from "../api/client";
import type { DashboardSettings, DashboardStateResponse } from "../domain/types";

const INITIAL_RETRY_MS = 5000;
type DashboardState = DashboardStateResponse & { recent_logs: string[] };

export function useDashboardState() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const stateRef = useRef<DashboardState | null>(null);

  const loadState = useCallback(async (includeLogs: boolean) => {
    try {
      const response = await fetchDashboardState({ includeLogs });
      const next = normalizeDashboardState(response, stateRef.current);
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

  const refresh = useCallback(async () => {
    await loadState(true);
  }, [loadState]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const refreshMs = Math.max((state?.settings.refreshRate ?? 30) * 1000, 30000);
    const statsReady = Boolean(state?.stats.raw_data && Object.keys(state.stats.raw_data).length > 0);
    const interval = statsReady ? refreshMs : INITIAL_RETRY_MS;
    const timer = window.setTimeout(() => void loadState(false), interval);
    return () => window.clearTimeout(timer);
  }, [loadState, state]);

  useEffect(() => {
    const source = new EventSource("/stream-logs");
    source.onmessage = (event) => {
      setState((current) => {
        if (!current) return current;
        const recent_logs = [...current.recent_logs, event.data].slice(-500);
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
        await loadState(false);
      } catch (err) {
        if (previous) setState(previous);
        notification.error({ title: "Failed to save settings", description: getErrorMessage(err) });
      }
    },
    [loadState]
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
        await loadState(false);
      } catch (err) {
        if (previous) setState(previous);
        notification.error({ title: "Failed to update lending state", description: getErrorMessage(err) });
      }
    },
    [loadState]
  );

  return { state, loading, error, refresh, updateSettings, setPaused };
}

function normalizeDashboardState(
  response: DashboardStateResponse,
  previous: DashboardState | null
): DashboardState {
  return {
    ...response,
    recent_logs: response.recent_logs ?? previous?.recent_logs ?? []
  };
}

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
