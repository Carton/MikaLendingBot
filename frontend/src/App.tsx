import { Spin } from "antd";
import { lazy, Suspense } from "react";
import { DashboardPage } from "./pages/DashboardPage";
import { useDashboardState } from "./hooks/useDashboardState";

const ChartsPage = lazy(() => import("./pages/ChartsPage").then((mod) => ({ default: mod.ChartsPage })));

export function App() {
  const path = window.location.pathname;
  if (path.endsWith("/charts.html")) {
    return (
      <Suspense fallback={<FullPageSpin />}>
        <ChartsPage />
      </Suspense>
    );
  }
  if (path.endsWith("/") || path.endsWith("/index.html")) {
    window.location.replace("/lendingbot.html");
    return null;
  }
  return <DashboardApp />;
}

function DashboardApp() {
  const { state, loading, error, refresh, updateSettings, setPaused } = useDashboardState();
  if (!state) {
    return <FullPageSpin />;
  }
  return (
    <DashboardPage
      state={state}
      loading={loading}
      error={error}
      onRefresh={() => void refresh()}
      onSaveSettings={updateSettings}
      onSetPaused={setPaused}
    />
  );
}

function FullPageSpin() {
  return (
    <div className="centered-loader">
      <Spin size="large" />
    </div>
  );
}
