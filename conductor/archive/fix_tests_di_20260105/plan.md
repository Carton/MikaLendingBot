# Implementation Plan: Modernizing Unit Tests for DI Architecture

## 阶段 1: 核心借贷逻辑测试重写 (Core Logic)
本阶段目标是恢复机器人最核心部分——借贷策略和引擎的测试。

- [~] Task 1.1: 合并并重写核心测试文件为 `tests/test_LendingEngine.py` (整合 core, strategy, comprehensive, precedence)。
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## 阶段 2: API 与外围组件测试修复 (Dependencies)
本阶段目标是修复底层依赖和支撑模块的测试。

- [x] Task 2.1: 修复 `tests/test_Bitfinex.py` 和 `tests/test_Poloniex_core.py`。
- [x] Task 2.2: 重写 `tests/test_MarketAnalysis.py`。
- [x] Task 2.3: 重写 `tests/test_PluginsManager.py`。
- [x] Task 2.4: 重写 `tests/test_WebServer.py` 和 `tests/test_Persistence.py`。
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## 阶段 3: 全量验证与覆盖率恢复 (Final Audit)
本阶段目标是确保所有测试回归，并达到质量标准。

- [x] Task 3.1: 执行全量单元测试 `uv run poe test`，确保 100% 通过。
- [x] Task 3.2: 检查代码覆盖率 `uv run poe test-coverage`，确保核心模块覆盖率达标。
- [x] Task 3.3: 最终清理。删除 `Lending.py` 中为了兼容性临时保留的模块级包装函数。
- [x] Task 3.4: 运行 `uv run poe fix-full` 确保测试代码也符合风格规范。
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)