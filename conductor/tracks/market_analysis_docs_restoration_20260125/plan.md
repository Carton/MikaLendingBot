# Implementation Plan: Market Analysis Documentation Restoration

本计划旨在恢复 `docs/market_analysis.rst` 中被误删的深度内容，并确保其与分层 TOML 结构及参数命名完全兼容。

## Phase 1: Preparation & Content Recovery
- [x] Task: 提取 `git show ca6455a:docs/market_analysis.rst` 之前的历史版本内容作为参考。
- [x] Task: 深入分析 `src/lendingbot/modules/MarketAnalysis.py` 源码，提取 `MACD_short_win_seconds` 和 `keep_history_seconds` 的具体计算公式。

## Phase 2: Content Adaptation & Updating
- [x] Task: 恢复 **Percentile** 和 **MACD** 方法的详细逻辑说明与数据示例，并将参数名更新为 snake_case。
- [x] Task: 恢复 **configuring** 章节：更新推荐配置表格，确保其中的参数名（如 `spread_lend`, `period_active`）与最新系统一致。
- [x] Task: 更新 **analyse_currencies** 子章节：明确其仅支持显式的币种列表，移除 `ALL` 和 `ACTIVE` 描述。
- [x] Task: 恢复并更新 **Analysing currencies** 下的所有详细参数说明子章节。
- [x] Task: 完善衍生参数说明：在文档中明确解释哪些参数是自动计算的，并提供公式。

## Phase 3: Verification & Quality Check
- [x] Task: 全面检查 RST 语法，确保表格和代码块（toml 格式）渲染正确。
- [x] Task: 验证所有内部引用和交叉链接是否在文档内保持有效。
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & Quality Check' (Protocol in workflow.md)
