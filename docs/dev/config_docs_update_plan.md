# 文档更新计划 (Documentation Update Plan)

本计划旨在更新 `docs/` 目录下的 RST 文件，使其与最新的 [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) 配置文件结构及代码逻辑保持一致。

## User Review Required

> [!IMPORTANT]
> **配置项删除**: 以下配置项在代码中已变为自动计算或不再支持，将从文档中彻底移除：
> *   `market_analysis` Section: `keep_history_seconds`, `macd_short_window`, `delete_thread_sleep`.
> *   `configuration` legacy: `coincfg` (dictionary style).

> [!NOTE]
> **配置项名称变更**: 所文档中的配置项名称将更新为 Snake Case (例如 `sleeptimeactive` -> `period_active`)。

## Proposed Changes

### Documentation

#### [MODIFY] [configuration.rst](file:///f:/devel/gitsrc/LendingBot_py3/docs/configuration.rst)
*   **重构结构**: 按照 [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) 的 Section 顺序重写文档结构：
    *   `[api]`
    *   `[bot]` (及 `[bot.web]`)
    *   `[coin]`, `[coin.default]`, `[coin.Ignore]`
    *   `[notifications]`
    *   `[plugins]`
*   **清理过时内容**:
    *   删除 `coincfg` 字典配置说明。
    *   删除 `customWebServer*` 系列配置，替换为 `[bot.web]` 下的 `host`, `port`, `template`。
*   **内容同步**:
    *   更新 `period_active`, `min_daily_rate` 等所有重命名项。
    *   更新默认值和范围说明。
    *   添加 `max_active_amount`, `xday_thresholds`, `frr_delta_min/max` 等新特性说明。
    *   明确 `[coin.default]` 作为默认配置的作用。

#### [MODIFY] [market_analysis.rst](file:///f:/devel/gitsrc/LendingBot_py3/docs/market_analysis.rst)
*   **删除过时配置**:
    *   删除 `keep_history_seconds` (现在由 `max(long_window, percentile_window) * 1.1` 自动计算)。
    *   删除 `MACD_short_win_seconds` (现在固定为 `long_window / 12`)。
    *   删除 `delete_thread_sleep` (自动计算)。
*   **更新现有配置**:
    *   `analyseCurrencies` -> `analyse_currencies`
    *   `analyseUpdateInterval` -> `update_interval`
    *   `MACD_long_win_seconds` -> `macd_long_window`
    *   `percentile_seconds` -> `percentile_window` (注意名称变化)
    *   `daily_min_method` -> 移至 `[plugins.market_analysis.daily_min]` 说明? 或者仅作为 `market_analysis` 的一个属性 (根据 Config 类，它在 MarketAnalysisConfig 根下，但 toml sample 里好像有个 daily_min table? 经检查代码 [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py)，`daily_min_multiplier` 在根下，没有独立的 daily_min section model， sample toml 里的 `[plugins.market_analysis.daily_min]` 可能是旧习惯或误导，代码 [MarketAnalysisConfig](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#126-139) 没有嵌套 `daily_min`。**Wait**, [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) showed `[plugins.market_analysis.daily_min]`. Let me double check [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py) again. [MarketAnalysisConfig](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#126-139) has `daily_min_multiplier`. It does NOT have a `daily_min` sub-model. Step 22 Line 138: `daily_min_multiplier: float`. So TOML sample might be slightly misleading or flat. I will stick to [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py) structure: flat `daily_min_multiplier`).
    *   Correction: [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) used `[plugins.market_analysis.daily_min]`. If [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py) is flat, then TOML parsing might fail if it's a section? `tomllib.load` loads sections as nested dicts. [RootConfig(**data)](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#162-193) expects `plugins` -> `market_analysis` -> `daily_min_multiplier`. If TOML has `[plugins.market_analysis.daily_min]`, it creates `plugins['market_analysis']['daily_min']`. [MarketAnalysisConfig](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#126-139) doesn't have `daily_min` field. So [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) structure for `daily_min` might be **WRONG** vs Code. I should document based on CODE ([Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py)), which is Flat `daily_min_multiplier`.
    *   Actually, [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) line 222: `multiplier = 1.05` inside `[plugins.market_analysis.daily_min]`. Code [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py) L138: `daily_min_multiplier`. This mismatch suggests I should document `daily_min_multiplier` and maybe fix TOML sample separately (out of scope, or note it). I will make docs matches Code: `daily_min_multiplier`.

## Verification Plan

### Manual Verification
1.  **阅读检查**: 检查生成的 RST 文件，确认删除了 `keep_history_seconds` 等项。
2.  **结构对比**: 确认 RST 结构与 [config_sample.toml](file:///f:/devel/gitsrc/LendingBot_py3/config_sample.toml) (修正后的理解) 一致。
