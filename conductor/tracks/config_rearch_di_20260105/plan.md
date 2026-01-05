# Implementation Plan: Config Rearch & DI Refactoring

## 阶段 1: 基础设施与测试先行 (TDD Start) [checkpoint: 074f074]
本阶段的目标是为新的 `LendingEngine` 类建立测试环境。

- [x] Task 1.1: 在 `tests/` 下创建一个新的测试文件 `tests/test_LendingEngine_new.py`。
- [x] Task 1.2: 在新测试中定义针对 `LendingEngine` 构造函数和基本属性的测试用例（使用 Mock 的 `RootConfig`）。
- [x] Task 1.3: 更新 `src/lendingbot/modules/Lending.py`，初步定义 `LendingEngine` 类骨架，以使测试能够导入。
- [x] Task: Conductor - User Manual Verification '阶段 1' (Protocol in workflow.md) [074f074]

## 阶段 2: LendingEngine 核心重构
本阶段是将 `Lending.py` 的逻辑从全局函数迁移到类方法中。

- [ ] Task 2.1: 实现 `LendingEngine.__init__`，将 `RootConfig`, `Data`, `Logger`, `ExchangeApi` 等注入并保存为实例属性。
- [ ] Task 2.2: 迁移核心状态变量。将原本分散的全局变量（如 `coin_cfg`, `loans_provided`）转化为 `LendingEngine` 的实例属性。
- [ ] Task 2.3: 迁移核心方法（如 `create_lend_offer`, `get_rate_for_currency`）。
    - **TDD 步骤**: 为每个方法编写测试 -> 迁移逻辑 -> 修复测试。
- [ ] Task 2.4: 移除 `Lending.py` 中所有的 `global` 声明和模块级变量复制逻辑。
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## 阶段 3: 外围模块重构 (DI Conversion)
将其他模块也改为接收注入的 `config` 对象。

- [ ] Task 3.1: **ExchangeApi**: 修改 `Bitfinex.py` 和 `Poloniex.py` 的 `__init__`，接受 `RootConfig`。
- [ ] Task 3.2: **MarketAnalysis**: 将其封装为类并接受 `RootConfig` 注入，移除对 `Configuration_old` 的调用。
- [ ] Task 3.3: **PluginsManager**: 重构初始化逻辑，确保注入 `config` 给所有插件。
- [ ] Task 3.4: **WebServer**: 封装为 `WebServer` 类，接收 `config` 和 `lending_engine` 实例作为参数。
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

## 阶段 4: 集成与清理 (Wiring & Cleanup)
在 `main.py` 中完成所有组件的组装，并彻底废弃旧代码。

- [ ] Task 4.1: 修改 `src/lendingbot/main.py`。
    - 实例化 `RootConfig` -> `Logger` -> `Data` -> `ExchangeApi` -> `LendingEngine`。
    - 移除所有旧的 `Configuration.init()` 等调用。
- [ ] Task 4.2: 运行集成测试或冒烟测试，确保整个流程跑通。
- [ ] Task 4.3: **清理**: 删除 `Configuration_old.py` 和 `Lending.py` 中遗留的死代码。
- [ ] Task 4.4: 最终质量检查：运行 `uv run poe fix-full` 修复所有类型检查和风格问题。
- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)
