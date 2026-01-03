# Specification: Lending Strategy Selection

## 1. Overview
引入明确的借贷策略选择配置 `lending_strategy`。该配置将替代旧的 `frrasmin` 开关。FRR 策略仅适用于 Bitfinex，因此系统需要增加交易所验证逻辑。

## 2. Functional Requirements

### 2.1 Configuration
- **新配置项**: 在 `default.cfg` 和 `Configuration.py` 中引入 `lending_strategy`。
- **可选值**:
    - `Spread`: 基础的间隔/价差借贷策略。
    - `FRR`: Flash Return Rate 借贷策略。
- **移除配置**: 弃用/移除 `frrasmin` 配置项。

### 2.2 Logic & Validation
- **策略选择与交易所匹配**:
    - **IF Strategy == FRR**:
        - 检查交易所是否为 Bitfinex。
        - 如果 **不是** Bitfinex，程序必须报错并停止启动（告知用户 FRR 仅支持 Bitfinex）。
        - 内部强制 `spread_lend = 1`。
        - 使用 `frrdelta` 等相关参数。
    - **IF Strategy == Spread**:
        - 使用 `spreadlend`, `gapMode` 等参数。
        - 禁用/忽略所有 FRR 相关逻辑。
- **默认值**: 如果未指定，默认为 `Spread`。

### 2.3 Web UI
- **API 数据**: 确保 API 返回 `lending_strategy` 的实际值。
- **动态 UI**:
    - Web UI (`lendingbot.js`) 需根据当前策略动态展示/隐藏控制面板。
    - 当策略为 `Spread` 时，隐藏 FRR 相关的滑块或控件。
    - 当策略为 `FRR` 时，显示 FRR 相关控件。

## 3. Non-Functional Requirements
- **健壮性**: 在配置读取阶段进行严格验证，确保用户明确知道为何配置无效（例如在 Poloniex 上误选 FRR）。
- **可扩展性**: 采用模块化或清晰的条件分支，以便未来添加第三种策略（如基于某种 AI 的策略）。

## 4. Acceptance Criteria
- [ ] **策略验证**: 在非 Bitfinex 环境下配置 `lending_strategy = FRR` 时，程序报错并退出。
- [ ] **强制参数**: 选择 `FRR` 策略后，系统内部正确处理 `spread_lend = 1` 且激活 FRR 逻辑。
- [ ] **参数清理**: 代码中不再依赖 `frrasmin` 配置项。
- [ ] **UI 同步**: 网页端根据后端返回的 `lending_strategy` 正确切换显示模式。
- [ ] **文档更新**: `default.cfg.example` 和 `docs/configuration.rst` 能够清晰反映这些变更。
