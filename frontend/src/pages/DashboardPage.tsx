import { PauseCircleOutlined, PlayCircleOutlined, ReloadOutlined, SettingOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Descriptions, Empty, Flex, Modal, Row, Space, Statistic, Table, Tag, Typography, Form, InputNumber, Slider, Radio, Grid } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo, useState } from "react";
import { buildDashboardView, formatNumber } from "../domain/dashboard";
import type { CoinRow, DashboardSettings, DashboardStateResponse } from "../domain/types";

interface DashboardPageProps {
  state: DashboardStateResponse;
  loading: boolean;
  error?: string | null;
  onRefresh: () => void;
  onSaveSettings?: (settings: DashboardSettings) => Promise<void> | void;
  onSetPaused?: (paused: boolean) => Promise<void> | void;
  compact?: boolean;
}

export function DashboardPage({
  state,
  loading,
  error,
  onRefresh,
  onSaveSettings,
  onSetPaused,
  compact
}: DashboardPageProps) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const screens = Grid.useBreakpoint();
  const view = useMemo(() => buildDashboardView(state), [state]);
  const useCompactLayout = compact ?? !screens.md;
  const columns = useMemo<ColumnsType<CoinRow>>(
    () => [
      { title: "Coin", dataIndex: "currency", key: "currency", render: (value) => <Typography.Text strong>{value}</Typography.Text> },
      { title: "Lent", key: "lent", render: (_, row) => `${formatNumber(row.lentSum)} / ${formatNumber(row.totalCoins)}` },
      { title: "Lent %", key: "lentPercent", render: (_, row) => `${formatNumber(row.lentPercent, 2)}%` },
      { title: "Avg. Day", key: "averageDailyRate", render: (_, row) => `${formatNumber(row.averageDailyRate, 5)}%` },
      { title: "Eff. Day", key: "effectiveDailyRate", render: (_, row) => `${formatNumber(row.effectiveDailyRate, 5)}%` },
      { title: "Comp. Year", key: "yearlyCompoundRate", render: (_, row) => `${formatNumber(row.yearlyCompoundRate, 2)}%` },
      {
        title: "Earnings",
        key: "earnings",
        render: (_, row) => (
          <Space orientation="vertical" size={0}>
            {row.earnings.map((earning) => (
              <Typography.Text key={earning.timespan} type="secondary">
                {formatNumber(earning.value, 4)} {earning.currency} / {earning.timespan}
              </Typography.Text>
            ))}
          </Space>
        )
      }
    ],
    []
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <Flex align="center" justify="space-between" gap="middle" wrap="wrap">
          <Space>
            <img className="brand-icon" src="/images/icon192.png" alt="" />
            <div>
              <Typography.Title level={3} className="page-title">
                {view.title}
              </Typography.Title>
              <Typography.Text type="secondary">{view.lastUpdate}</Typography.Text>
            </div>
          </Space>
          <Space wrap>
            <Tag color={view.paused ? "gold" : "green"}>{view.paused ? "Paused" : "Running"}</Tag>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh} />
            <Button icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>
              Settings
            </Button>
            <Button
              type="primary"
              danger={!view.paused}
              icon={view.paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={() => void onSetPaused?.(!view.paused)}
            >
              {view.paused ? "Resume" : "Pause"}
            </Button>
            <Button href="/charts.html">Charts</Button>
          </Space>
        </Flex>
      </header>

      <main className="content">
        {error ? <Alert type="error" showIcon title="Dashboard refresh failed" description={error} /> : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card>
              <Statistic title="Status" value={view.statusText} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="Strategies" value={view.strategies.join(", ") || "N/A"} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="Refresh" value={`${state.settings.refreshRate ?? 30}s`} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
        </Row>

        <Card title="Lending Positions" className="section-card">
          {view.statsReady ? (
            useCompactLayout ? (
              <CoinCardList rows={view.coinRows} />
            ) : (
              <Table
                data-testid="desktop-coin-table"
                rowKey="currency"
                columns={columns}
                dataSource={view.coinRows}
                pagination={false}
                scroll={{ x: 920 }}
                size="middle"
              />
            )
          ) : (
            <Empty description={view.emptyStatsMessage} />
          )}
        </Card>

        <Row gutter={[16, 16]} className="section-card">
          <Col xs={24} lg={10}>
            <Card title="Snapshot">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Exchange">{state.stats.exchange || "N/A"}</Descriptions.Item>
                <Descriptions.Item label="Label">{state.stats.label || "Lending Bot"}</Descriptions.Item>
                <Descriptions.Item label="Output Currency">{state.stats.outputCurrency?.currency || "N/A"}</Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col xs={24} lg={14}>
            <Card title="Recent Logs">
              <div className="log-list">
                {view.logs.length === 0 ? (
                  <Empty description="No logs yet" />
                ) : (
                  view.logs.map((item, index) => (
                    <div className="log-line" key={`${index}-${item}`}>
                      {item}
                    </div>
                  ))
                )}
              </div>
            </Card>
          </Col>
        </Row>
      </main>

      <SettingsModal
        open={settingsOpen}
        settings={state.settings}
        onCancel={() => setSettingsOpen(false)}
        onSave={async (settings) => {
          await onSaveSettings?.(settings);
          setSettingsOpen(false);
        }}
      />
    </div>
  );
}

function CoinCardList({ rows }: { rows: CoinRow[] }) {
  return (
    <div className="coin-card-list" data-testid="mobile-coin-list">
      {rows.map((row) => (
        <Card key={row.currency} size="small" className="coin-card">
          <Flex align="center" justify="space-between">
            <Typography.Title level={4} className="coin-title">
              {row.currency}
            </Typography.Title>
            <Tag color="blue">{formatNumber(row.lentPercent, 2)}%</Tag>
          </Flex>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Lent">
              {formatNumber(row.lentSum)} / {formatNumber(row.totalCoins)}
            </Descriptions.Item>
            <Descriptions.Item label="Avg. Day">{formatNumber(row.averageDailyRate, 5)}%</Descriptions.Item>
            <Descriptions.Item label="Eff. Day">{formatNumber(row.effectiveDailyRate, 5)}%</Descriptions.Item>
            <Descriptions.Item label="Comp. Year">{formatNumber(row.yearlyCompoundRate, 2)}%</Descriptions.Item>
          </Descriptions>
          <div className="earnings-list">
            {row.earnings.map((earning) => (
              <Typography.Text key={earning.timespan} type="secondary">
                {formatNumber(earning.value, 4)} {earning.currency} / {earning.timespan}
              </Typography.Text>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

function SettingsModal({
  open,
  settings,
  onCancel,
  onSave
}: {
  open: boolean;
  settings: DashboardSettings;
  onCancel: () => void;
  onSave: (settings: DashboardSettings) => Promise<void>;
}) {
  const [form] = Form.useForm<DashboardSettings>();
  return (
    <Modal
      title="Settings"
      open={open}
      onCancel={onCancel}
      onOk={() => {
        void form.validateFields().then(onSave).catch(() => undefined);
      }}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" initialValues={settings}>
        <Form.Item
          name="refreshRate"
          label="Refresh interval"
          normalize={normalizeOptionalNumber}
          rules={[{ type: "number", min: 30, max: 600 }]}
        >
          <Space.Compact block>
            <InputNumber aria-label="Refresh interval" min={30} max={600} style={{ width: "100%" }} />
            <span className="input-addon">seconds</span>
          </Space.Compact>
        </Form.Item>
        <Form.Item name="outputCurrencyDisplayMode" label="Output currency display">
          <Radio.Group
            options={[
              { label: "All Coins", value: "all" },
              { label: "Only Summary", value: "summary" }
            ]}
          />
        </Form.Item>
        <Form.Item label="FRR rate adjustment">
          <Space wrap>
            <Space.Compact>
              <span className="input-addon">Min</span>
              <Form.Item name="frrdelta_min" noStyle normalize={normalizeOptionalNumber}>
                <InputNumber aria-label="FRR minimum adjustment" min={-50} max={50} />
              </Form.Item>
              <span className="input-addon">%</span>
            </Space.Compact>
            <Space.Compact>
              <span className="input-addon">Max</span>
              <Form.Item name="frrdelta_max" noStyle normalize={normalizeOptionalNumber}>
                <InputNumber aria-label="FRR maximum adjustment" min={-50} max={50} />
              </Form.Item>
              <span className="input-addon">%</span>
            </Space.Compact>
          </Space>
          <Slider range min={-50} max={50} defaultValue={[settings.frrdelta_min ?? -10, settings.frrdelta_max ?? 10]} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function normalizeOptionalNumber(value: unknown): number | undefined {
  if (value === "" || value === null || value === undefined) return undefined;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}
