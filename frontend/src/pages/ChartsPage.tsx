import { ReloadOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Flex, Spin, Typography } from "antd";
import ReactECharts from "echarts-for-react";
import { useEffect, useMemo, useState } from "react";
import { fetchChartHistory, fetchDashboardState } from "../api/client";
import { buildDashboardView, normalizeChartHistory } from "../domain/dashboard";
import type { ChartSeries, RawChartPoint } from "../domain/types";

export function ChartsPage() {
  const [history, setHistory] = useState<Record<string, RawChartPoint[]> | null>(null);
  const [title, setTitle] = useState("Lending Bot - Profit Charts");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const series = useMemo(() => normalizeChartHistory(history), [history]);

  async function load() {
    setLoading(true);
    try {
      const [nextState, nextHistory] = await Promise.all([fetchDashboardState(), fetchChartHistory()]);
      setTitle(`${buildDashboardView(nextState).title} - Profit Charts`);
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
            {title}
          </Typography.Title>
          <Flex gap="small">
            <Button href="/lendingbot.html">Dashboard</Button>
            <Button aria-label="Refresh Charts" icon={<ReloadOutlined />} loading={loading} onClick={() => void load()} />
          </Flex>
        </Flex>
      </header>
      <main className="content">
        {error ? <Alert type="error" showIcon title="Failed to load chart history" description={error} /> : null}
        <Spin spinning={loading}>
          {series.length === 0 ? (
            <Card>
              <Empty description="No chart history available" />
            </Card>
          ) : (
            series.map((coinSeries) => <CoinChart key={coinSeries.coin} series={coinSeries} />)
          )}
        </Spin>
      </main>
    </div>
  );
}

function CoinChart({ series }: { series: ChartSeries }) {
  const option = {
    title: { text: `${series.coin} Daily Lending Earnings` },
    tooltip: { trigger: "axis" },
    legend: { data: ["Daily", "Total"] },
    grid: { left: 48, right: 48, bottom: 48, containLabel: true },
    xAxis: { type: "time" },
    yAxis: [
      { type: "value", name: "Daily" },
      { type: "value", name: "Total" }
    ],
    series: [
      {
        name: "Daily",
        type: "line",
        yAxisIndex: 0,
        data: series.points.map((point) => [point.timestamp * 1000, point.daily])
      },
      {
        name: "Total",
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
