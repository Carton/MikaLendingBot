# Specification: Modernizing Unit Tests for DI Architecture

## 1. Overview
本 Track 的目标是修复并重写由于项目转向 **依赖注入 (DI)** 和 **类化架构** 而失效的所有单元测试。我们将废弃过时的、基于全局状态和 `unittest.mock` 样板代码的测试，统一采用现代化的 `pytest` 风格，通过 `fixtures` 注入依赖，直接对组件实例（如 `LendingEngine`）进行测试。

## 2. 需求范围

### 2.1 核心借贷逻辑 (最高优先级)
- **LendingEngine**: 重写 `test_Lending_core.py`、`test_Lending_comprehensive.py`、`test_Lending_strategy.py` 等。
    - 验证 `LendingEngine` 在各种市场配置和 API 响应下的行为。
    - 移除对模块级全局变量的修改，改为实例化独立的测试对象。

### 2.2 外围与依赖模块 (第二优先级)
- **Exchange API**: 修复 `test_Bitfinex.py` 和 `test_Poloniex_core.py`。
    - 重点解决 `SecretStr` 处理以及新的构造函数签名适配。
- **MarketAnalysis**: 重写测试以支持 `RootConfig` 和 `api` 实例的注入。
- **PluginsManager & WebServer**: 重写测试，不再依赖 `Lending` 模块的全局状态变量。

### 2.3 测试实践标准
- **Pytest Idioms**: 优先使用 `@pytest.fixture` 进行环境准备。
- **Mocking**: 使用 `pytest-mock` 或标准的 `unittest.mock`，但要确保 Mock 对象能正确模拟新的 Pydantic 配置模型。
- **Clean State**: 每个测试用例都应使用全新的实例，彻底避免测试间的状态污染。

## 3. 验收标准 (Acceptance Criteria)
- [ ] `tests/` 目录下的所有单元测试全部通过 (`uv run poe test`)。
- [ ] 核心模块（Lending, Data, ExchangeApi）的测试覆盖率恢复或超过重构前水平。
- [ ] 没有任何测试脚本依赖 `Lending.py` 中已删除的旧全局变量。
- [ ] 通过 `mypy` 和 `ruff` 的代码质量检查。

## 4. 超出范围 (Out of Scope)
- 编写新的集成测试（除非为了验证现有单元测试的重写）。
- 修改 `src/` 目录下的业务逻辑（仅限于为了提高可测试性而进行的微调）。
