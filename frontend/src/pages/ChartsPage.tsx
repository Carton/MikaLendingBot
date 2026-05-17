import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Flex, Spin, Typography } from "antd";
import ReactECharts from "echarts-for-react";
import { useEffect, useMemo, useState } from "react";
import { fetchChartHistory, fetchDashboardState } from "../api/client";
import { buildDashboardView, normalizeChartHistory } from "../domain/dashboard";
import { useLanguage } from "../i18n";
import type { ChartSeries, RawChartPoint } from "../domain/types";

export function ChartsPage() {
  const [history, setHistory] = useState<Record<string, RawChartPoint[]> | null>(null);
  const [dashboardTitle, setDashboardTitle] = useState("Lending Bot");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();
  const series = useMemo(() => normalizeChartHistory(history), [history]);

  async function load() {
    setLoading(true);
    try {
      const [nextState, nextHistory] = await Promise.all([fetchDashboardState(), fetchChartHistory()]);
      setDashboardTitle(buildDashboardView(nextState).title);
      setHistory(nextHistory);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <Flex className="topbar-inner" align="center" justify="space-between" gap="middle" wrap="wrap">
          <Typography.Title level={3} className="page-title">
            {dashboardTitle} - {t("charts.titleSuffix")}
          </Typography.Title>
          <Flex gap="small">
            <Button href="/lendingbot.html">{t("actions.dashboard")}</Button>
            <Button aria-label={t("actions.refreshCharts")} icon={<ReloadOutlined />} loading={loading} onClick={() => void load()} />
          </Flex>
        </Flex>
      </header>
      <main className="content">
        {error ? <Alert type="error" showIcon title={t("charts.errorTitle")} description={error} /> : null}
        <Spin spinning={loading}>
          {series.length === 0 ? (
            <Card>
              <Empty description={t("charts.empty")} />
            </Card>
          ) : (
            series.map((coinSeries) => <CoinChart key={coinSeries.coin} series={coinSeries} t={t} />)
          )}
        </Spin>
      </main>
    </div>
  );
}

function CoinChart({ series, t }: { series: ChartSeries; t: (key: string, values?: Record<string, string | number>) => string }) {
  const dailySeriesName = t("charts.series.daily");
  const totalSeriesName = t("charts.series.total");
  const option = {
    title: { text: t("charts.title", { coin: series.coin }) },
    tooltip: { trigger: "axis" },
    legend: { data: [dailySeriesName, totalSeriesName] },
    grid: { left: 48, right: 48, bottom: 76, containLabel: true },
    xAxis: { type: "time" },
    yAxis: [
      { type: "value", name: dailySeriesName },
      { type: "value", name: totalSeriesName }
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: 0 },
      { type: "slider", xAxisIndex: 0, bottom: 24 }
    ],
    series: [
      {
        name: dailySeriesName,
        type: "line",
        yAxisIndex: 0,
        data: series.points.map((point) => [point.timestamp * 1000, point.daily])
      },
      {
        name: totalSeriesName,
        type: "line",
        yAxisIndex: 1,
        data: series.points.map((point) => [point.timestamp * 1000, point.total])
      }
    ]
  };

  return (
    <Card className="section-card">
      <ReactECharts option={option} style={{ height: 420 }} />
    </Card>
  );
}
