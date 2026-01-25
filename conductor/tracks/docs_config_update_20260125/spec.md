# Specification: Configuration Documentation Update

## 1. Overview
本 Track 的目标是根据最新的配置文件重构（Config Rearch）改动，全面更新 `docs/configuration.rst` 文档。更新将反映从旧的 `.cfg` 风格（及扁平化 TOML）到现代分层 TOML 结构（基于 Pydantic 模型）的转变，同时确保文档内容的完整性和逻辑连贯性。

## 2. 功能需求

### 2.1 结构与风格
- **保持逻辑流**: 维持现有的以功能特征为导向的文档结构（如：Exchange selection, Timing, Lending Strategies 等），而不是简单的按照 TOML 节名排列。
- **更新代码示例**: 将所有配置示例更新为 `config_sample.toml` 中使用的分层 TOML 格式（例如：使用 `[bot]`, `[coin.default]`, `[notifications.email]` 等）。
- **参数更名**: 准确映射更名后的参数（例如：`sleeptimeactive` 变为 `period_active`，`minloansize` 变为 `min_loan_size`，`spreadlend` 变为 `spread_lend`）。

### 2.2 内容更新
- **全面性**: 文档必须包含所有可用的配置项，包括 `config_sample.toml` 中被注释掉的项。
- **高级设置**: 将 `config_sample.toml` 中未默认启用的项或 `MarketAnalysis` 相关的复杂参数标注为 "Advanced" 或 "Optional"。
- **xday_thresholds**: 更新该项的配置说明，反映其从逗号分隔字符串到 TOML 数组/内联表（Array of inline tables）格式的变化。
- **策略说明**: 明确 `Spread` 和 `FRR` 策略的配置方式及其互斥性，参考最新的 `strategy` 参数。

### 2.3 内容保留
- **保留说明文案**: 尽可能保留原有文档中关于各配置项背景、建议值和警告信息的有效描述。
- **避免过度简化**: 不要为了简洁而删除有价值的解释内容。

## 3. 非功能需求
- **准确性**: 配置参数名和格式必须与 `src/lendingbot/modules/Configuration.py` 中的 Pydantic 模型定义完全一致。
- **可读性**: 确保转换后的 RST 文档在 ReadTheDocs 上渲染正确。

## 4. 验收标准 (Acceptance Criteria)
- [ ] `docs/configuration.rst` 中的所有配置示例均采用 TOML 格式且与 `config_sample.toml` 一致。
- [ ] 所有更名后的参数（如 `period_active`）在文档中均已正确更新。
- [ ] 文档包含 `xday_thresholds` 的新格式说明。
- [ ] 文档保留了原有的“警告”、“提示”和详细的功能背景说明。
- [ ] 所有的高级插件配置（AccountStats, Charts, MarketAnalysis）均有相应说明。

## 5. 超出范围 (Out of Scope)
- 更改程序的实际配置逻辑或代码实现。
- 更新除 `configuration.rst` 之外的其他文档（除非涉及交叉引用失效）。
