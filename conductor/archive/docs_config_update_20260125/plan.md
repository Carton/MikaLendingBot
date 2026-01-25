# Implementation Plan: Configuration Documentation Update

本计划旨在根据配置重构的最新状态，将 `docs/configuration.rst` 从旧格式全面更新为新的分层 TOML 格式，同时保持文档的深度和逻辑性。

## Phase 1: Preparation & Analysis
- [x] Task: 深入对比 `config_sample.toml` 与 `docs/configuration.rst`，建立完整的参数映射表（Old Name -> New TOML Path）。
- [x] Task: 检查 `src/lendingbot/modules/Configuration.py` 中的 Pydantic 模型，确保文档中的所有参数名和默认值与之完全一致。

## Phase 2: Content Migration & Formatting
- [x] Task: 更新 "Exchange selection" 章节：反映 `[api]` 节的引入及参数名变更。
- [x] Task: 更新 "Timing" 章节：将 `sleeptimeactive/inactive` 更新为 `bot.period_active/inactive`。
- [x] Task: 更新 "Lending Strategies" 章节：反映 `strategy` 参数及其在 `[coin.default]` 或特定币种下的位置。
- [x] Task: 更新 "Spreading your Lends" 章节：更新 `spread_lend`, `gap_mode`, `gap_bottom`, `gap_top` 等参数。
- [x] Task: 更新 "Variable loan Length" 章节：**重点更新** `xday_thresholds` 的数组/表格式示例。
- [x] Task: 更新 "Auto-transfer" 章节：更新 `transferable_currencies` 参数。
- [x] Task: 更新 "Max to be lent" 章节：更新 `max_to_lend`, `max_percent_to_lend`, `max_to_lend_rate` 参数。
- [x] Task: 更新 "Config per Coin" 章节：详细说明 `[coin.BTC]` 这种新的覆盖机制。
- [x] Task: 更新 "Advanced logging and Web Display" 章节：更新 `[bot.web]` 下的所有参数。
- [x] Task: 更新 "Plugins" & "Notifications" 章节：反映嵌套的 `[plugins.xxx]` 和 `[notifications.xxx]` 结构。
- [x] Task: 更新 "MarketAnalysis" 章节：基于 `config_sample.toml` 和代码，补全所有高级参数的说明。

## Phase 3: Verification & Polish
- [x] Task: 全面检查 RST 语法，特别是代码块（code-block toml） and 交叉引用。
- [x] Task: 确保所有保留的说明文字（Warning, Note）与新的参数上下文衔接自然。
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & Polish' (Protocol in workflow.md)
