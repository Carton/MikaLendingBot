# Specification: Market Analysis Documentation Restoration

## 1. Overview
本 Track 的目标是修复在之前提交（`ca6455a`）中对 `docs/market_analysis.rst` 进行的过度删减。我们将恢复所有关于算法逻辑、配置建议和详细参数说明的有价值内容，并确保这些内容与新的 TOML 配置结构和参数命名完全同步。

## 2. 功能需求

### 2.1 内容恢复
- **算法细节**: 恢复 `Percentile` 和 `MACD` 方法的详细解释，包括计算过程中的示例数据和推导逻辑。
- **配置建议**: 恢复使用 MACD 时推荐的 bot 配置表格（如 `spread_lend`, `gap_bottom`, `gap_top` 的推荐值）。
- **参数子章节**: 为每一个配置项恢复独立的子章节，详细说明其影响、范围和默认值。
- **提示与警告**: 恢复关于数据容错（`data_tolerance`）、API 频率限制以及 DB 清理逻辑的提示。

### 2.2 适配与更新
- **参数命名同步**: 确保所有恢复的内容使用最新的参数名（例如：`analyseUpdateInterval` -> `update_interval`）。
- **衍生参数说明**: 将 `MACD_short_win_seconds` 和 `keep_history_seconds` 标记为“衍生/内部参数”，并给出计算公式（公式参考 `MarketAnalysis.py` 源码），不再将其列为用户可直接配置的项。
- **精简 `analyse_currencies`**: 在恢复该参数说明时，移除对不再支持的 `ALL` 和 `ACTIVE` 关键字的描述。

## 3. 非功能需求
- **RST 格式一致性**: 确保恢复后的内容在 ReadTheDocs 上渲染正常，包括表格、代码块和内部链接。
- **准确性**: 所有关于计算公式的描述必须与 `src/lendingbot/modules/MarketAnalysis.py` 中的实现逻辑保持一致。

## 4. 验收标准 (Acceptance Criteria)
- [ ] `docs/market_analysis.rst` 恢复了关于算法的详细图表和示例。
- [ ] 文档包含衍生参数（`MACD_short_win_seconds`, `keep_history_seconds`）的自动计算公式说明。
- [ ] 所有参数名已更新为 snake_case 风格且对应正确的 TOML 路径。
- [ ] 移除了所有关于 `ALL` 和 `ACTIVE` 关键字的陈旧引用。
- [ ] 文档保留了原有的“高级配置建议”部分。

## 5. 超出范围 (Out of Scope)
- 更改程序的实际配置逻辑或代码实现。
- 更新除 `market_analysis.rst` 之外的其他文档。
