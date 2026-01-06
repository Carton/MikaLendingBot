# Implementation Plan: Coverage Boost & Strategic Refactor

## 阶段 1: LendingEngine 逻辑重构与单元测试增强 [checkpoint: 9424449]
本阶段重点是拆解 `Lending.py` 中的复杂方法，并大幅提升其测试覆盖率。

- [x] Task 1.1: 重构 `LendingEngine.create_lend_offer`。将其中的天数计算、汇率调整逻辑剥离为独立的纯函数。 7d2e472
- [x] Task 1.2: 重构 `LendingEngine.refresh_order_books` 及相关订单簿处理逻辑，增强其模块化程度。 4cbf3c3
- [x] Task 1.3: 在 `tests/test_LendingEngine.py` 中增加针对重构后私有逻辑的精细化单元测试（覆盖极值、精度误差）。 4cbf3c3
- [x] Task 1.4: 增加 API 失败、超时及异常数据响应的 Mock 测试用例。 ea41dd5
- [ ] Task: Conductor - User Manual Verification '阶段 1' (Protocol in workflow.md)

## 阶段 2: WebServer 健壮性提升
针对 Web 服务层增加异常处理和对应的测试用例。

- [x] Task 2.1: 为 `WebServer` 增加对文件系统操作（如 `web_settings.json` 读写失败）的异常捕获。 8f34209
- [ ] Task 2.2: 在 `tests/test_WebServer.py` 中增加模拟网络端口占用、非法 JSON 负载等异常路径的测试。
- [ ] Task: Conductor - User Manual Verification '阶段 2' (Protocol in workflow.md)

## 阶段 3: main.py 逻辑剥离与编排层测试
将入口点逻辑迁移到类中，并实现基本覆盖。

- [ ] Task 3.1: 创建 `src/lendingbot/modules/Orchestrator.py` 并定义 `BotOrchestrator` 类。
- [ ] Task 3.2: 将 `main.py` 中的初始化、依赖注入组装逻辑和主循环迁移至 `BotOrchestrator`。
- [ ] Task 3.3: 编写 `tests/test_Orchestrator.py` 验证机器人启动序列、插件加载和退出流程。
- [ ] Task 3.4: 编写 `tests/test_Orchestrator.py` 验证机器人启动序列、插件加载和退出流程。
- [ ] Task 3.5: 更新 `main.py` 使其仅作为 `BotOrchestrator` 的实例化和启动入口。
- [ ] Task: Conductor - User Manual Verification '阶段 3' (Protocol in workflow.md)

## 阶段 4: 全量验证与集成测试跟进
最后进行系统级验证并恢复总体覆盖率达标。

- [ ] Task 4.1: 创建新的集成测试文件 `tests/integration/test_full_cycle.py`，模拟完整的借贷心跳循环。
- [ ] Task 4.2: 运行全量覆盖率报告 `uv run poe test-coverage`，确保核心模块覆盖率 > 70%。
- [ ] Task 4.3: 最终质量检查 `uv run poe fix-full`。
- [ ] Task: Conductor - User Manual Verification '阶段 4' (Protocol in workflow.md)
