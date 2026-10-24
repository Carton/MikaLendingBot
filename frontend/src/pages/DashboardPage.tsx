import { MinusCircleOutlined, PauseCircleOutlined, PlayCircleOutlined, PlusOutlined, ReloadOutlined, SettingOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, Descriptions, Empty, Flex, Modal, Row, Space, Statistic, Table, Tabs, Tag, Typography, Form, InputNumber, Slider, Radio, Grid } from "antd";
import type { ColumnsType } from "antd/es/table";
import ReactECharts from "echarts-for-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildDashboardView, buildXdayDurationCurve, formatNumber } from "../domain/dashboard";
import { LANGUAGE_OPTIONS, useLanguage } from "../i18n";
import type { CoinRow, CoinSettingsEntry, DashboardSettings, DashboardStateResponse, RecentLoan, XDayThresholdEntry } from "../domain/types";

type TranslateFn = ReturnType<typeof useLanguage>["t"];
type SetLanguageFn = ReturnType<typeof useLanguage>["setLanguage"];

const FRR_DELTA_MIN_LIMIT = -30;
const FRR_DELTA_MAX_LIMIT = 50;
const XDAY_RATE_LIMIT = 5;
const XDAY_DAYS_MIN = 2;
const XDAY_DAYS_MAX = 120;
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
  const showRecentLoans =
    (state.settings.recentSuccessfulLoans ?? 0) > 0 ||
    view.coinRows.some((row) => row.recentSuccessfulLoans.length > 0);
  const columns = useMemo<ColumnsType<CoinRow>>(
    () => {
      const baseColumns: ColumnsType<CoinRow> = [
        { title: t("table.coin"), dataIndex: "currency", key: "currency", render: (value) => <Typography.Text strong>{value}</Typography.Text> },
        { title: t("table.lent"), key: "lent", render: (_, row) => `${formatNumber(row.lentSum)} / ${formatNumber(row.totalCoins)}` },
        { title: t("table.lentPercent"), key: "lentPercent", render: (_, row) => `${formatNumber(row.lentPercent, 2)}%` },
        { title: t("table.averageDay"), key: "averageDailyRate", render: (_, row) => `${formatNumber(row.averageDailyRate, 5)}%` },
        { title: t("table.effectiveDay"), key: "effectiveDailyRate", render: (_, row) => `${formatNumber(row.effectiveDailyRate, 5)}%` },
        { title: t("table.compoundYear"), key: "yearlyCompoundRate", render: (_, row) => `${formatNumber(row.yearlyCompoundRate, 2)}%` }
      ];

      if (showRecentLoans) {
        baseColumns.push({
          title: t("table.recentLoans"),
          key: "recentSuccessfulLoans",
          render: (_, row) => <RecentLoansList currency={row.currency} loans={row.recentSuccessfulLoans} t={t} />
        });
      }

      baseColumns.push({
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
      });

      return baseColumns;
    },
    [showRecentLoans, t]
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
              <CoinCardList rows={view.coinRows} showRecentLoans={showRecentLoans} t={t} />
            ) : (
              <Table
                data-testid="desktop-coin-table"
                rowKey="currency"
                columns={columns}
                dataSource={view.coinRows}
                pagination={false}
                scroll={{ x: 1080 }}
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

function CoinCardList({ rows, showRecentLoans, t }: { rows: CoinRow[]; showRecentLoans: boolean; t: TranslateFn }) {
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
          {showRecentLoans ? (
            <div className="recent-loans-block">
              <Typography.Text strong>{t("table.recentLoans")}</Typography.Text>
              <RecentLoansList currency={row.currency} loans={row.recentSuccessfulLoans} t={t} />
            </div>
          ) : null}
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

function RecentLoansList({ currency, loans, t }: { currency: string; loans: RecentLoan[]; t: TranslateFn }) {
  if (loans.length === 0) {
    return <Typography.Text type="secondary">{t("table.noRecentLoans")}</Typography.Text>;
  }

  return (
    <Space className="recent-loans-list" orientation="vertical" size={2}>
      {loans.map((loan) => (
        <div className="recent-loan-line" key={`${loan.amount}-${loan.rate}-${loan.date}`}>
          <Typography.Text>
            {formatNumber(loan.amount, 8)} {currency}
          </Typography.Text>
          <Typography.Text type="secondary">{formatLoanRate(loan.rate)}%</Typography.Text>
          <Typography.Text type="secondary">{loan.date}</Typography.Text>
        </div>
      ))}
    </Space>
  );
}

function formatLoanRate(rate: number): string {
  return (rate * 100).toLocaleString(undefined, {
    maximumFractionDigits: 5,
    minimumFractionDigits: 5
  });
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

function normalizeSettings(settings: DashboardSettings): DashboardSettings {
  return {
    ...settings,
    frrdelta_min: Math.max(settings.frrdelta_min ?? -10, FRR_DELTA_MIN_LIMIT),
    frrdelta_max: Math.min(settings.frrdelta_max ?? 10, FRR_DELTA_MAX_LIMIT),
    xday_thresholds: (settings.xday_thresholds ?? []).map((entry) => ({
      rate: entry.rate,
      days: entry.days
    })),
    coin_settings: Object.fromEntries(
      Object.entries(settings.coin_settings ?? {}).map(([coin, entry]) => [
        coin,
        {
          frrdelta_min: Math.max(entry.frrdelta_min ?? -10, FRR_DELTA_MIN_LIMIT),
          frrdelta_max: Math.min(entry.frrdelta_max ?? 10, FRR_DELTA_MAX_LIMIT),
          xday_thresholds: (entry.xday_thresholds ?? []).map((threshold) => ({
            rate: threshold.rate,
            days: threshold.days
          }))
        }
      ])
    )
  };
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
  const [resetCoins, setResetCoins] = useState<Set<string>>(new Set());
  // Dirty-compare baseline, captured when the modal opens. The live settings
  // object changes with every background poll; comparing stale form values
  // against a moving baseline would misjudge them as edited.
  const [baseline, setBaseline] = useState<DashboardSettings>(() => normalizeSettings(settings));
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    // Run only on the closed->open transition: a refreshed settings object
    // must neither clobber the user's in-progress edits nor clear a pending
    // per-coin reset.
    if (open) {
      const snapshot = normalizeSettings(settingsRef.current);
      setBaseline(snapshot);
      form.setFieldsValue(snapshot);
      setResetCoins(new Set());
    }
  }, [form, open]);

  const existingOverrides = baseline.coin_overrides ?? {};
  const currencies = settings.currencies ?? [];

  const markReset = useCallback((coin: string) => {
    setResetCoins((prev) => new Set(prev).add(coin));
  }, []);
  const clearReset = useCallback((coin: string) => {
    setResetCoins((prev) => {
      if (!prev.has(coin)) return prev;
      const next = new Set(prev);
      next.delete(coin);
      return next;
    });
  }, []);
  const tabItems = [
    {
      key: "default",
      label: t("settings.coinTabDefault"),
      forceRender: true,
      children: (
        <>
          <Typography.Text className="coin-tab-hint" type="secondary">
            {t("settings.coinTabDefaultHint")}
          </Typography.Text>
          <CoinStrategyFields coin={null} t={t} onUserEdit={undefined} />
        </>
      )
    },
    ...currencies.map((coin) => ({
      key: coin,
      label: coin,
      forceRender: true,
      children: (
        <>
          <CoinTabToolbar
            coin={coin}
            hasOverride={Boolean(existingOverrides[coin])}
            resetPending={resetCoins.has(coin)}
            onReset={markReset}
            t={t}
          />
          <CoinStrategyFields coin={coin} t={t} onUserEdit={() => clearReset(coin)} />
        </>
      )
    }))
  ];

  return (
    <Modal
      title={t("settings.title")}
      open={open}
      okText={t("settings.ok")}
      cancelText={t("settings.cancel")}
      onCancel={onCancel}
      onOk={() => {
        void form
          .validateFields()
          .then(() => {
            // getFieldsValue(true): the full store, including fields in tabs
            // the user never opened (validateFields alone would omit them).
            const values = form.getFieldsValue(true) as DashboardSettings;
            return onSave(
              buildSettingsPayload(values, baseline, existingOverrides, resetCoins)
            );
          })
          .catch(() => undefined);
      }}
      destroyOnHidden
    >
      <Form
        className="settings-form"
        form={form}
        layout="vertical"
        initialValues={baseline}
        onValuesChange={(changed: Record<string, unknown>) => {
          const changedCoins = changed.coin_settings;
          if (changedCoins && typeof changedCoins === "object") {
            for (const coin of Object.keys(changedCoins)) {
              clearReset(coin);
            }
          }
        }}
      >
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
          label={t("settings.refreshInterval")}
        >
          <Space.Compact className="settings-number-control" data-testid="refresh-interval-control">
            <Form.Item name="refreshRate" noStyle normalize={normalizeOptionalNumber} rules={[{ type: "number", min: 30, max: 600 }]}>
              <InputNumber aria-label={t("settings.refreshInterval")} name="refreshRate" autoComplete="off" min={30} max={600} />
            </Form.Item>
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
        <Tabs
          data-testid="coin-settings-tabs"
          items={tabItems}
          size="small"
        />
      </Form>
    </Modal>
  );
}

function CoinTabToolbar({
  coin,
  hasOverride,
  resetPending,
  onReset,
  t
}: {
  coin: string;
  hasOverride: boolean;
  resetPending: boolean;
  onReset: (coin: string) => void;
  t: TranslateFn;
}) {
  if (!hasOverride && !resetPending) return null;
  return (
    <div className="coin-tab-toolbar" data-testid={`coin-tab-toolbar-${coin}`}>
      {hasOverride ? <Tag color="blue">{t("settings.coinOverridden")}</Tag> : null}
      {hasOverride ? (
        <Button size="small" onClick={() => onReset(coin)}>
          {t("settings.coinReset")}
        </Button>
      ) : null}
      {resetPending ? (
        <Typography.Text className="coin-tab-hint" type="warning">
          {t("settings.coinResetPending")}
        </Typography.Text>
      ) : null}
    </div>
  );
}

function xdayThresholdsEqual(a?: XDayThresholdEntry[], b?: XDayThresholdEntry[]): boolean {
  if ((a?.length ?? 0) !== (b?.length ?? 0)) return false;
  return (a ?? []).every(
    (entry, index) =>
      entry?.rate === b?.[index]?.rate && entry?.days === b?.[index]?.days
  );
}

function buildSettingsPayload(
  values: DashboardSettings,
  initial: DashboardSettings,
  existingOverrides: Record<string, CoinSettingsEntry>,
  resetCoins: Set<string>
): DashboardSettings {
  // Only explicitly changed fields (plus previously saved overrides) become
  // per-currency overrides; untouched coins keep inheriting the Default tab
  // and their TOML config.
  const coinSettings: Record<string, CoinSettingsEntry> = {};
  const coins = new Set([
    ...Object.keys(values.coin_settings ?? {}),
    ...Object.keys(existingOverrides)
  ]);
  for (const coin of coins) {
    if (resetCoins.has(coin)) continue;
    const current = values.coin_settings?.[coin] ?? {};
    const init = initial.coin_settings?.[coin];
    const existing = existingOverrides[coin];
    const entry: CoinSettingsEntry = {};
    const frrDirty =
      current.frrdelta_min !== init?.frrdelta_min ||
      current.frrdelta_max !== init?.frrdelta_max;
    if (frrDirty || (existing && "frrdelta_min" in existing && "frrdelta_max" in existing)) {
      // Unedited overrides keep their original values: the form display
      // clamps to the slider range, which would silently truncate a saved
      // override that exceeds it.
      entry.frrdelta_min = frrDirty ? current.frrdelta_min : existing?.frrdelta_min;
      entry.frrdelta_max = frrDirty ? current.frrdelta_max : existing?.frrdelta_max;
    }
    const xdayDirty = !xdayThresholdsEqual(current.xday_thresholds, init?.xday_thresholds);
    if (xdayDirty || (existing && "xday_thresholds" in existing)) {
      entry.xday_thresholds = xdayDirty
        ? (current.xday_thresholds ?? [])
        : (existing?.xday_thresholds ?? []);
    }
    if (Object.keys(entry).length > 0) {
      coinSettings[coin] = entry;
    }
  }
  const { coin_settings: _display, ...rest } = values;
  // Unchanged global strategy values are not resubmitted: resubmitting the
  // pre-filled (possibly TOML-derived) value would create a web override that
  // shadows per-coin TOML config.
  if (
    values.frrdelta_min === initial.frrdelta_min &&
    values.frrdelta_max === initial.frrdelta_max
  ) {
    delete rest.frrdelta_min;
    delete rest.frrdelta_max;
  }
  if (xdayThresholdsEqual(values.xday_thresholds, initial.xday_thresholds)) {
    delete rest.xday_thresholds;
  }
  return { ...rest, coin_settings: coinSettings };
}

function CoinStrategyFields({
  coin,
  t,
  onUserEdit
}: {
  /** null = the global/default tab; otherwise a per-currency override. */
  coin: string | null;
  t: TranslateFn;
  /** Called on slider/list edits: setFieldValue bypasses onValuesChange, so a
   *  pending per-coin reset must be cleared explicitly. */
  onUserEdit?: () => void;
}) {
  const form = Form.useFormInstance<DashboardSettings>();
  const frrMinName: "frrdelta_min" | ["coin_settings", string, "frrdelta_min"] =
    coin === null ? "frrdelta_min" : ["coin_settings", coin, "frrdelta_min"];
  const frrMaxName: "frrdelta_max" | ["coin_settings", string, "frrdelta_max"] =
    coin === null ? "frrdelta_max" : ["coin_settings", coin, "frrdelta_max"];
  const xdayName: "xday_thresholds" | ["coin_settings", string, "xday_thresholds"] =
    coin === null ? "xday_thresholds" : ["coin_settings", coin, "xday_thresholds"];
  const watchedFrrMin = Form.useWatch(frrMinName, form);
  const watchedFrrMax = Form.useWatch(frrMaxName, form);
  const watchedXday = Form.useWatch(xdayName, form);
  const frrMin =
    typeof watchedFrrMin === "number"
      ? watchedFrrMin
      : Number(form.getFieldValue(frrMinName) ?? -10);
  const frrMax =
    typeof watchedFrrMax === "number"
      ? watchedFrrMax
      : Number(form.getFieldValue(frrMaxName) ?? 10);
  const xdayCurve = useMemo(
    () => buildXdayDurationCurve(watchedXday, XDAY_RATE_LIMIT),
    [watchedXday]
  );

  function updateFrrRange(value: number | number[]) {
    if (!Array.isArray(value)) return;
    const [nextMin, nextMax] = value;
    form.setFieldValue(frrMinName, nextMin);
    form.setFieldValue(frrMaxName, nextMax);
    onUserEdit?.();
  }

  return (
    <>
      <Form.Item label={t("settings.frrAdjustment")}>
        <Form.Item name={frrMinName} hidden normalize={normalizeOptionalNumber}>
          <input type="hidden" />
        </Form.Item>
        <Form.Item name={frrMaxName} hidden normalize={normalizeOptionalNumber}>
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
      <Form.Item label={t("settings.xdayTitle")}>
        <Form.List
          name={xdayName}
          rules={[
            {
              validator: async (_rule, value: XDayThresholdEntry[] | undefined) => {
                const sorted = [...(value ?? [])].sort(
                  (left, right) => (left?.rate ?? 0) - (right?.rate ?? 0)
                );
                const decreasing = sorted.some(
                  (entry, index) =>
                    index > 0 && (entry?.days ?? 0) < (sorted[index - 1]?.days ?? 0)
                );
                if (decreasing) {
                  throw new Error(t("settings.xdayDaysOrderError"));
                }
              }
            }
          ]}
        >
          {(fields, { add, remove }, { errors }) => (
            <div className="xday-threshold-list" data-testid="xday-threshold-list">
              {fields.map((field) => (
                <Space key={field.key} align="center" className="xday-threshold-row">
                  <Form.Item
                    name={[field.name, "rate"]}
                    noStyle
                    normalize={normalizeOptionalNumber}
                    rules={[
                      { required: true, message: t("settings.xdayRateRequired") },
                      { type: "number", min: 0, max: XDAY_RATE_LIMIT }
                    ]}
                  >
                    <InputNumber
                      aria-label={t("settings.xdayRateLabel")}
                      min={0}
                      max={XDAY_RATE_LIMIT}
                      step={0.001}
                    />
                  </Form.Item>
                  <span className="input-addon">%</span>
                  <Form.Item
                    name={[field.name, "days"]}
                    noStyle
                    normalize={normalizeOptionalNumber}
                    rules={[
                      { required: true, message: t("settings.xdayDaysRequired") },
                      { type: "number", min: XDAY_DAYS_MIN, max: XDAY_DAYS_MAX }
                    ]}
                  >
                    <InputNumber
                      aria-label={t("settings.xdayDaysLabel")}
                      min={XDAY_DAYS_MIN}
                      max={XDAY_DAYS_MAX}
                      step={1}
                      precision={0}
                    />
                  </Form.Item>
                  <span className="input-addon">{t("settings.xdayAxisDays")}</span>
                  <Button
                    aria-label={t("settings.xdayRemove")}
                    icon={<MinusCircleOutlined />}
                    onClick={() => {
                      remove(field.name);
                      onUserEdit?.();
                    }}
                    type="text"
                    danger
                  />
                </Space>
              ))}
              <Button
                block
                icon={<PlusOutlined />}
                onClick={() => {
                  add({ rate: undefined, days: undefined });
                  onUserEdit?.();
                }}
                type="dashed"
              >
                {t("settings.xdayAdd")}
              </Button>
              <Form.ErrorList errors={errors} />
            </div>
          )}
        </Form.List>
        {xdayCurve.length > 0 ? (
          <div className="xday-preview">
            <Typography.Text className="xday-preview-title" strong>
              {t("settings.xdayPreview")}
            </Typography.Text>
            <XdayPreviewChart points={xdayCurve} t={t} />
            <Typography.Text type="secondary">{t("settings.xdayPreviewHint")}</Typography.Text>
          </div>
        ) : (
          <Typography.Text type="secondary">{t("settings.xdayEmpty")}</Typography.Text>
        )}
      </Form.Item>
    </>
  );
}

function XdayPreviewChart({ points, t }: { points: Array<[number, number]>; t: TranslateFn }) {
  const option = {
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      min: 0,
      name: t("settings.xdayAxisRate"),
      axisLabel: { formatter: (value: number) => `${value}` }
    },
    yAxis: {
      type: "value",
      min: 0,
      minInterval: 1,
      name: t("settings.xdayAxisDays")
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: unknown) => `${value} ${t("settings.xdayAxisDays")}`
    },
    series: [
      {
        type: "line",
        showSymbol: true,
        symbolSize: 7,
        data: points,
        areaStyle: { opacity: 0.08 },
        lineStyle: { width: 2 }
      }
    ]
  };

  return (
    <div data-testid="xday-preview-chart">
      <ReactECharts option={option} style={{ height: 200 }} notMerge />
    </div>
  );
}

function normalizeOptionalNumber(value: unknown): number | undefined {
  if (value === "" || value === null || value === undefined) return undefined;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}
