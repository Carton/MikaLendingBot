import { PauseCircleOutlined, PlayCircleOutlined, ReloadOutlined, SettingOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Descriptions, Empty, Flex, Modal, Row, Space, Statistic, Table, Tag, Typography, Form, InputNumber, Slider, Radio, Grid } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildDashboardView, formatNumber } from "../domain/dashboard";
import { LANGUAGE_OPTIONS, useLanguage } from "../i18n";
import type { CoinRow, DashboardSettings, DashboardStateResponse } from "../domain/types";

type TranslateFn = ReturnType<typeof useLanguage>["t"];
type SetLanguageFn = ReturnType<typeof useLanguage>["setLanguage"];

const FRR_DELTA_MIN_LIMIT = -30;
const FRR_DELTA_MAX_LIMIT = 50;
const LOG_FOLLOW_THRESHOLD_PX = 32;

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
  const { language, setLanguage, t } = useLanguage();
  const screens = Grid.useBreakpoint();
  const view = useMemo(() => buildDashboardView(state), [state]);
  const useCompactLayout = compact ?? !screens.md;
  const statusText = translateStatusText(view.statusText, t);
  const columns = useMemo<ColumnsType<CoinRow>>(
    () => [
      { title: t("table.coin"), dataIndex: "currency", key: "currency", render: (value) => <Typography.Text strong>{value}</Typography.Text> },
      { title: t("table.lent"), key: "lent", render: (_, row) => `${formatNumber(row.lentSum)} / ${formatNumber(row.totalCoins)}` },
      { title: t("table.lentPercent"), key: "lentPercent", render: (_, row) => `${formatNumber(row.lentPercent, 2)}%` },
      { title: t("table.averageDay"), key: "averageDailyRate", render: (_, row) => `${formatNumber(row.averageDailyRate, 5)}%` },
      { title: t("table.effectiveDay"), key: "effectiveDailyRate", render: (_, row) => `${formatNumber(row.effectiveDailyRate, 5)}%` },
      { title: t("table.compoundYear"), key: "yearlyCompoundRate", render: (_, row) => `${formatNumber(row.yearlyCompoundRate, 2)}%` },
      {
        title: t("table.earnings"),
        key: "earnings",
        render: (_, row) => (
          <Space orientation="vertical" size={0}>
            {row.earnings.map((earning) => (
              <Typography.Text key={earning.timespan} type="secondary">
                {formatNumber(earning.value, 4)} {earning.currency} / {t(`timespan.${earning.timespan}`)}
              </Typography.Text>
            ))}
          </Space>
        )
      }
    ],
    [t]
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <Flex className="topbar-inner" align="center" justify="space-between" gap="middle" wrap="wrap">
          <Space>
            <img className="brand-icon" src="/images/icon192.png" alt="" width={40} height={40} />
            <div>
              <Typography.Title level={3} className="page-title">
                <span translate="no">{view.title}</span>
              </Typography.Title>
              <Space size="small" className="topbar-meta" wrap>
                <Tag color={view.paused ? "gold" : "green"}>{view.paused ? t("status.paused") : t("status.running")}</Tag>
                <Typography.Text type="secondary">{view.lastUpdate}</Typography.Text>
              </Space>
            </div>
          </Space>
          <Space wrap>
            <Button href="/charts.html">{t("actions.charts")}</Button>
            <Button aria-label={t("actions.refreshDashboard")} icon={<ReloadOutlined />} loading={loading} onClick={onRefresh} />
            <Button icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>
              {t("actions.settings")}
            </Button>
            <Button
              type="primary"
              danger={!view.paused}
              icon={view.paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={() => void onSetPaused?.(!view.paused)}
            >
              {view.paused ? t("actions.resume") : t("actions.pause")}
            </Button>
          </Space>
        </Flex>
      </header>

      <main className="content">
        {error ? <Alert type="error" showIcon title={t("dashboard.errorTitle")} description={error} /> : null}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card>
              <Statistic title={t("dashboard.status")} value={statusText} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title={t("dashboard.strategies")} value={view.strategies.join(", ") || "N/A"} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title={t("dashboard.refresh")} value={`${state.settings.refreshRate ?? 30}s`} styles={{ content: { fontSize: 20 } }} />
            </Card>
          </Col>
        </Row>

        <Card title={t("dashboard.lendingPositions")} className="section-card">
          {view.coinRows.length > 0 ? (
            useCompactLayout ? (
              <CoinCardList rows={view.coinRows} t={t} />
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
            <div className="empty-state">{t("dashboard.emptyPositions")}</div>
          )}
        </Card>

        <Row gutter={[16, 16]} className="section-card">
          <Col xs={24}>
            <RecentLogsCard logs={view.logs} t={t} />
          </Col>
        </Row>
      </main>

      <SettingsModal
        open={settingsOpen}
        language={language}
        settings={state.settings}
        setLanguage={setLanguage}
        t={t}
        onCancel={() => setSettingsOpen(false)}
        onSave={async (settings) => {
          await onSaveSettings?.(settings);
          setSettingsOpen(false);
        }}
      />
    </div>
  );
}

function translateStatusText(statusText: string, t: TranslateFn) {
  if (statusText === "Lending running") {
    return t("status.lendingRunning");
  }
  if (statusText.startsWith("Lent:")) {
    return statusText.replace(/^Lent:/, t("status.lentPrefix"));
  }
  return statusText;
}

function CoinCardList({ rows, t }: { rows: CoinRow[]; t: TranslateFn }) {
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
            <Descriptions.Item label={t("table.lent")}>
              {formatNumber(row.lentSum)} / {formatNumber(row.totalCoins)}
            </Descriptions.Item>
            <Descriptions.Item label={t("table.averageDay")}>{formatNumber(row.averageDailyRate, 5)}%</Descriptions.Item>
            <Descriptions.Item label={t("table.effectiveDay")}>{formatNumber(row.effectiveDailyRate, 5)}%</Descriptions.Item>
            <Descriptions.Item label={t("table.compoundYear")}>{formatNumber(row.yearlyCompoundRate, 2)}%</Descriptions.Item>
          </Descriptions>
          <div className="earnings-list">
            {row.earnings.map((earning) => (
              <Typography.Text key={earning.timespan} type="secondary">
                {formatNumber(earning.value, 4)} {earning.currency} / {t(`timespan.${earning.timespan}`)}
              </Typography.Text>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}

function RecentLogsCard({ logs, t }: { logs: string[]; t: TranslateFn }) {
  const logListRef = useRef<HTMLDivElement>(null);
  const previousLogCountRef = useRef(0);
  const [isFollowingTail, setIsFollowingTail] = useState(true);
  const [hasUnreadLogs, setHasUnreadLogs] = useState(false);

  const scrollToTail = useCallback(() => {
    const element = logListRef.current;
    if (!element) return;
    element.scrollTop = element.scrollHeight;
  }, []);

  const followTail = useCallback(() => {
    setIsFollowingTail(true);
    setHasUnreadLogs(false);
    scrollToTail();
  }, [scrollToTail]);

  useEffect(() => {
    const nextLogCount = logs.length;
    if (isFollowingTail) {
      scrollToTail();
      setHasUnreadLogs(false);
    } else if (nextLogCount > previousLogCountRef.current) {
      setHasUnreadLogs(true);
    }
    previousLogCountRef.current = nextLogCount;
  }, [isFollowingTail, logs, scrollToTail]);

  function handleLogScroll() {
    const element = logListRef.current;
    if (!element) return;
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const isNearBottom = distanceFromBottom <= LOG_FOLLOW_THRESHOLD_PX;
    setIsFollowingTail(isNearBottom);
    if (isNearBottom) {
      setHasUnreadLogs(false);
    }
  }

  return (
    <Card
      title={t("dashboard.recentLogs")}
      extra={
        hasUnreadLogs ? (
          <Button size="small" onClick={followTail}>
            {t("dashboard.newLogs")}
          </Button>
        ) : null
      }
    >
      <div
        aria-live={isFollowingTail ? "polite" : "off"}
        className="log-list"
        data-testid="recent-log-list"
        onScroll={handleLogScroll}
        ref={logListRef}
      >
        {logs.length === 0 ? (
          <Empty description={t("dashboard.noLogs")} />
        ) : (
          logs.map((item, index) => (
            <div className="log-line" key={`${index}-${item}`}>
              {item}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function SettingsModal({
  open,
  language,
  settings,
  setLanguage,
  t,
  onCancel,
  onSave
}: {
  open: boolean;
  language: string;
  settings: DashboardSettings;
  setLanguage: SetLanguageFn;
  t: TranslateFn;
  onCancel: () => void;
  onSave: (settings: DashboardSettings) => Promise<void>;
}) {
  const [form] = Form.useForm<DashboardSettings>();
  const initialSettings = {
    ...settings,
    frrdelta_min: Math.max(settings.frrdelta_min ?? -10, FRR_DELTA_MIN_LIMIT),
    frrdelta_max: Math.min(settings.frrdelta_max ?? 10, FRR_DELTA_MAX_LIMIT)
  };
  const watchedFrrMin = Form.useWatch("frrdelta_min", form);
  const watchedFrrMax = Form.useWatch("frrdelta_max", form);
  const frrMin = typeof watchedFrrMin === "number" ? watchedFrrMin : initialSettings.frrdelta_min;
  const frrMax = typeof watchedFrrMax === "number" ? watchedFrrMax : initialSettings.frrdelta_max;

  function updateFrrRange(value: number | number[]) {
    if (!Array.isArray(value)) return;
    const [nextMin, nextMax] = value;
    form.setFieldsValue({ frrdelta_min: nextMin, frrdelta_max: nextMax });
  }

  return (
    <Modal
      title={t("settings.title")}
      open={open}
      okText={t("settings.ok")}
      cancelText={t("settings.cancel")}
      onCancel={onCancel}
      onOk={() => {
        void form.validateFields().then(onSave).catch(() => undefined);
      }}
      destroyOnHidden
    >
      <Form className="settings-form" form={form} layout="vertical" initialValues={initialSettings}>
        <Form.Item label={t("settings.language")}>
          <Radio.Group
            aria-label={t("language.label")}
            optionType="button"
            options={LANGUAGE_OPTIONS}
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          />
        </Form.Item>
        <Form.Item
          name="refreshRate"
          label={t("settings.refreshInterval")}
          normalize={normalizeOptionalNumber}
          rules={[{ type: "number", min: 30, max: 600 }]}
        >
          <Space.Compact className="settings-number-control" data-testid="refresh-interval-control">
            <InputNumber aria-label={t("settings.refreshInterval")} name="refreshRate" autoComplete="off" min={30} max={600} />
            <span className="input-addon">{t("settings.seconds")}</span>
          </Space.Compact>
        </Form.Item>
        <Form.Item name="outputCurrencyDisplayMode" label={t("settings.outputCurrencyDisplay")}>
          <Radio.Group
            optionType="button"
            buttonStyle="solid"
            options={[
              { label: t("settings.allCoins"), value: "all" },
              { label: t("settings.onlySummary"), value: "summary" }
            ]}
          />
        </Form.Item>
        <Form.Item label={t("settings.frrAdjustment")}>
          <Form.Item name="frrdelta_min" hidden normalize={normalizeOptionalNumber}>
            <input type="hidden" />
          </Form.Item>
          <Form.Item name="frrdelta_max" hidden normalize={normalizeOptionalNumber}>
            <input type="hidden" />
          </Form.Item>
          <div className="frr-range-summary">
            <span className="frr-value-chip">{t("settings.min")} {frrMin}%</span>
            <span className="frr-value-chip">{t("settings.max")} {frrMax}%</span>
          </div>
          <Slider
            range
            min={FRR_DELTA_MIN_LIMIT}
            max={FRR_DELTA_MAX_LIMIT}
            marks={{ [FRR_DELTA_MIN_LIMIT]: `${FRR_DELTA_MIN_LIMIT}%`, 0: "0%", [FRR_DELTA_MAX_LIMIT]: `${FRR_DELTA_MAX_LIMIT}%` }}
            ariaLabelForHandle={[t("settings.frrMinHandle"), t("settings.frrMaxHandle")]}
            ariaValueTextFormatterForHandle={(value) => `${value}%`}
            tooltip={{ formatter: (value) => `${value}%` }}
            value={[frrMin, frrMax]}
            onChange={updateFrrRange}
          />
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
