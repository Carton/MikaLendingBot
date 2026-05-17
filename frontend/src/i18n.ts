import { useCallback, useEffect, useState } from "react";

export type Language = "en" | "zh-CN";

export const LANGUAGE_STORAGE_KEY = "lendingbot-language";

export const LANGUAGE_OPTIONS: Array<{ label: string; value: Language }> = [
  { label: "English", value: "en" },
  { label: "简体中文", value: "zh-CN" }
];

const translations: Record<Language, Record<string, string>> = {
  en: {
    "actions.charts": "Charts",
    "actions.dashboard": "Dashboard",
    "actions.pause": "Pause",
    "actions.refreshCharts": "Refresh Charts",
    "actions.refreshDashboard": "Refresh Dashboard",
    "actions.resume": "Resume",
    "actions.settings": "Settings",
    "charts.empty": "No chart history available",
    "charts.errorTitle": "Failed to load chart history",
    "charts.series.daily": "Daily Earnings",
    "charts.series.total": "Total Earnings",
    "charts.title": "{coin} Daily Lending Earnings",
    "charts.titleSuffix": "Profit Charts",
    "dashboard.emptyStats": "Waiting for the first statistics snapshot",
    "dashboard.errorTitle": "Dashboard refresh failed",
    "dashboard.lendingPositions": "Lending Positions",
    "dashboard.noLogs": "No logs yet",
    "dashboard.newLogs": "New Logs",
    "dashboard.emptyPositions": "Waiting for lending position data",
    "dashboard.recentLogs": "Recent Logs",
    "dashboard.refresh": "Refresh",
    "dashboard.status": "Status",
    "dashboard.strategies": "Strategies",
    "language.label": "Language",
    "settings.allCoins": "All Coins",
    "settings.cancel": "Cancel",
    "settings.frrAdjustment": "FRR rate adjustment",
    "settings.frrMaxHandle": "Maximum FRR adjustment",
    "settings.frrMinHandle": "Minimum FRR adjustment",
    "settings.language": "Language",
    "settings.max": "Max",
    "settings.min": "Min",
    "settings.ok": "OK",
    "settings.onlySummary": "Only Summary",
    "settings.outputCurrencyDisplay": "Output currency display",
    "settings.refreshInterval": "Refresh interval",
    "settings.seconds": "seconds",
    "settings.title": "Settings",
    "status.lendingRunning": "Lending running",
    "status.lentPrefix": "Lent:",
    "status.paused": "Paused",
    "status.running": "Running",
    "table.averageDay": "Avg. Day",
    "table.coin": "Coin",
    "table.compoundYear": "Comp. Year",
    "table.earnings": "Earnings",
    "table.effectiveDay": "Eff. Day",
    "table.lent": "Lent",
    "table.lentPercent": "Lent %",
    "timespan.Day": "Day",
    "timespan.Hour": "Hour",
    "timespan.Month": "Month",
    "timespan.Week": "Week",
    "timespan.Year": "Year"
  },
  "zh-CN": {
    "actions.charts": "图表",
    "actions.dashboard": "仪表盘",
    "actions.pause": "暂停",
    "actions.refreshCharts": "刷新图表",
    "actions.refreshDashboard": "刷新仪表盘",
    "actions.resume": "恢复",
    "actions.settings": "设置",
    "charts.empty": "暂无图表历史",
    "charts.errorTitle": "图表历史加载失败",
    "charts.series.daily": "每日收益",
    "charts.series.total": "累计收益",
    "charts.title": "{coin} 每日借贷收益",
    "charts.titleSuffix": "收益图表",
    "dashboard.emptyStats": "等待第一份统计快照",
    "dashboard.errorTitle": "仪表盘刷新失败",
    "dashboard.lendingPositions": "借出仓位",
    "dashboard.noLogs": "暂无日志",
    "dashboard.newLogs": "最新日志",
    "dashboard.emptyPositions": "等待借出仓位数据",
    "dashboard.recentLogs": "最近日志",
    "dashboard.refresh": "刷新",
    "dashboard.status": "状态",
    "dashboard.strategies": "策略",
    "language.label": "语言",
    "settings.allCoins": "全部币种",
    "settings.cancel": "取消",
    "settings.frrAdjustment": "FRR 利率调整",
    "settings.frrMaxHandle": "最大 FRR 调整",
    "settings.frrMinHandle": "最小 FRR 调整",
    "settings.language": "语言",
    "settings.max": "最大",
    "settings.min": "最小",
    "settings.ok": "确定",
    "settings.onlySummary": "仅汇总",
    "settings.outputCurrencyDisplay": "输出币种显示",
    "settings.refreshInterval": "刷新间隔",
    "settings.seconds": "秒",
    "settings.title": "设置",
    "status.lendingRunning": "借贷运行中",
    "status.lentPrefix": "已借出:",
    "status.paused": "已暂停",
    "status.running": "运行中",
    "table.averageDay": "平均日息",
    "table.coin": "币种",
    "table.compoundYear": "复利年化",
    "table.earnings": "收益",
    "table.effectiveDay": "有效日息",
    "table.lent": "已借出",
    "table.lentPercent": "借出比例",
    "timespan.Day": "天",
    "timespan.Hour": "小时",
    "timespan.Month": "月",
    "timespan.Week": "周",
    "timespan.Year": "年"
  }
};

export function useLanguage() {
  const [language, setLanguageState] = useState<Language>(readStoredLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((nextLanguage: Language) => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    setLanguageState(nextLanguage);
  }, []);

  const t = useCallback(
    (key: string, values?: Record<string, string | number>) => {
      const template = translations[language][key] ?? translations.en[key] ?? key;
      return Object.entries(values ?? {}).reduce(
        (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
        template
      );
    },
    [language]
  );

  return { language, setLanguage, t };
}

function readStoredLanguage(): Language {
  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored === "zh-CN" || stored === "en") {
    return stored;
  }
  return readBrowserLanguage();
}

function readBrowserLanguage(): Language {
  const browserLanguages = navigator.languages.length > 0 ? navigator.languages : [navigator.language];
  const normalizedLanguages = browserLanguages.map((language) => language.toLowerCase());

  if (normalizedLanguages.some((language) => language === "zh" || language === "zh-cn" || language === "zh-hans" || language === "zh-sg")) {
    return "zh-CN";
  }

  return "en";
}
