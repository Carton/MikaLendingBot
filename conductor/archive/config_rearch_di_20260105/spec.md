# Specification: Config Rearch & DI Refactoring

## 1. Overview
本 Track 的目标是完成配置文件重构（Rearch）的最后阶段。我们将废弃所有旧的配置读取逻辑（`Configuration_old.py`），并彻底消除模块级别的全局变量。通过引入**依赖注入 (Dependency Injection)** 模式，将核心模块（Lending, Plugins, MarketAnalysis, WebServer）重构为类，使其职责更清晰、更易于测试。

## 2. 功能需求

### 2.1 核心类重构 (Class Transformation)
- **LendingEngine (`Lending.py`)**: 将原本基于模块函数的逻辑重构为 `LendingEngine` 类。
    - 接收 `RootConfig`, `Data`, `Logger`, `ExchangeApi` 等对象作为 `__init__` 参数。
    - 彻底删除模块级全局变量（如 `coin_cfg`, `sleep_time` 等）。
- **PluginsManager**: 重构为接受 `RootConfig` 注入，并确保所有插件（`AccountStats`, `Charts`）在初始化时都能获得对应的配置对象。
- **MarketAnalysis**: 重构为接受 `RootConfig` 注入，移除内部对全局 Config 的隐式依赖。
- **WebServer**: 封装为类或提供接受注入的启动接口，不再直接访问全局状态。
- **ExchangeApi (Poloniex/Bitfinex)**: 统一构造函数，接受 `RootConfig` 对象以获取 API Key 和相关设置。

### 2.2 配置模型应用
- 全面使用 `Configuration.py` 中的 `RootConfig` 和 `CoinConfig` Pydantic 模型。
- 消除“配置副本”：所有模块应直接访问注入的 `config` 对象或其子对象。
- 移除 `Lending.py` 中对配置项的二次定义和手动映射逻辑。

### 2.3 `main.py` 依赖组装 (Wiring)
- 在 `main.py` 中集中进行依赖对象的实例化。
- 负责将配置、日志、数据模块等正确注入到 `LendingEngine` 和各子系统中。

## 3. 非功能需求
- **代码质量**: 必须通过 `mypy` 静态类型检查和 `ruff` 代码风格检查。
- **可测试性**: 重构后的代码应允许在不加载真实配置文件的情况下，通过注入 Mock Config 进行单元测试。
- **一致性**: 统一变量命名（如统一使用 `snake_case` 以匹配 Pydantic 模型字段）。

## 4. 验收标准 (Acceptance Criteria)
- [ ] `LendingEngine` 类可以成功实例化，且不再依赖模块级全局变量。
- [ ] 应用可以通过 `default.toml` 正常启动，且各模块配置生效。
- [ ] `main.py` 中没有对 `Configuration_old` 的引用。
- [ ] **TDD 验证**: 针对 `LendingEngine` 新编写的单元测试全部通过。
- [ ] `uv run poe fix-full` 执行无误。

## 5. 超出范围 (Out of Scope)
- 修改核心借贷策略逻辑（本重构仅改变代码组织结构和配置读取方式）。
- 对 `www` 目录下的前端页面进行大规模改动。
