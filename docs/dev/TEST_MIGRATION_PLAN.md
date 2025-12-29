# 测试迁移与分类实施计划

## 📋 概述

本计划旨在将 `old/tests/` 目录下的 Python 2.7 测试代码完整迁移到 Python 3 测试套件中，并建立清晰的测试分类体系（单元测试 vs 集成测试）。

## 🎯 目标

1. **完整性**: 确保所有 old/tests/ 的测试用例都已迁移到 Python 3
2. **分类清晰**: 使用 pytest markers 区分单元测试和集成测试
3. **独立集成测试**: 创建 `tests/integration/` 目录存放真实 API 测试
4. **CI 友好**: 集成测试默认跳过，通过环境变量控制运行

## 📊 当前状态分析

### old/tests/ 测试清单

| 测试文件 | 测试数量 | 类型 | 状态 |
|---------|---------|------|------|
| test_Data.py | 11 | 单元测试 | ✅ 已迁移 |
| test_Lending.py | 6 | 单元测试 | ✅ 已迁移 |
| test_RingBuffer.py | 7 | 单元测试 | ✅ 已迁移 |
| test_MarketAnalysis.py | 6 | 数据库集成测试 | ✅ 已扩展到 28 个测试 |
| **test_BitfinexAPI.py** | **1** | **真实 API 集成测试** | ❌ **缺失** |
| **test_PoloniexAPI.py** | **1** | **真实 API 集成测试** | ❌ **缺失** |

**关键发现**: 缺少 2 个真实 API 集成测试

### tests/ 当前状态

- ✅ 单元测试完整（84 个测试）
- ✅ 测试覆盖率良好（15.94%）
- ❌ 无真实 API 集成测试
- ❌ 无 pytest markers 配置
- ❌ 无 conftest.py

## 🔧 实施计划

### 阶段 1: 创建集成测试目录结构

#### 1.1 创建目录

```
tests/
├── integration/          # 新增：集成测试目录
│   ├── __init__.py
│   ├── conftest.py       # 集成测试专用 fixtures
│   ├── test_bitfinex_api.py
│   └── test_poloniex_api.py
├── conftest.py           # 全局测试配置
└── [现有测试文件...]
```

### 阶段 2: 迁移和更新真实 API 测试

#### 2.1 创建 `tests/integration/test_bitfinex_api.py`

**源文件**: `old/tests/test_BitfinexAPI.py`

**迁移要点**:
1. Python 3 语法转换
   - `xrange()` → `range()`
   - `print '...'` → `print(... )`
   - `e.message` → `str(e)`

2. 添加 pytest markers
   ```python
   @pytest.mark.integration
   @pytest.mark.slow
   ```

3. 添加环境变量检查
   ```python
   pytest.importorskip("integration_tests_enabled")
   ```

4. 使用现代 API 对象导入
   ```python
   from lendingbot.modules.Bitfinex import Bitfinex
   from lendingbot.modules import Configuration
   ```

**测试用例**:
- `test_multiple_calls()` - 10 个并发线程调用 `return_open_loan_offers()`

#### 2.2 创建 `tests/integration/test_poloniex_api.py`

**源文件**: `old/tests/test_PoloniexAPI.py`

**迁移要点**:
1. 同上 Python 3 语法转换
2. 添加 pytest markers
3. 添加环境变量检查
4. 使用现代导入

**测试用例**:
- `test_rate_limiter()` - 20 个线程测试速率限制器

### 阶段 3: 配置 pytest markers

#### 3.1 更新 `pyproject.toml`

**当前配置**:
```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src/lendingbot",
    "--cov-report=term-missing",
    "--cov-report=html",
]
```

**需要添加**:
```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast, isolated, no external dependencies)",
    "integration: Integration tests (slow, real API calls, require API keys)",
    "slow: Slow-running tests (take > 1 second)",
]
```

### 阶段 4: 创建 conftest.py 文件

#### 4.1 创建 `tests/conftest.py` (全局)

**内容**:
```python
"""
Global pytest configuration and fixtures for LendingBot tests.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


def pytest_collection_modifyitems(config, items):
    """Modify collected test items.

    - Automatically mark tests in tests/integration/ as 'integration'
    - Skip integration tests unless RUN_INTEGRATION_TESTS is set
    """
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"

    for item in items:
        # Mark integration tests based on directory
        if "integration" in str(item.fspath):
            item.add_marker("integration")
            item.add_marker("slow")

        # Skip integration tests by default
        if item.get_closest_marker("integration") and not run_integration:
            item.add_marker(
                pytest.mark.skipif(
                    not run_integration,
                    reason="Integration tests skipped. Set RUN_INTEGRATION_TESTS=true to run.",
                )
            )
```

#### 4.2 创建 `tests/integration/conftest.py` (集成测试专用)

**内容**:
```python
"""
Pytest configuration and fixtures for integration tests.
"""

import os
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lendingbot.modules import Configuration, Data
from lendingbot.modules.Logger import Logger
from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.Poloniex import Poloniex


def pytest_configure(config):
    """Skip all integration tests if not enabled."""
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"
    if not run_integration:
        pytest.skip("Integration tests disabled. Set RUN_INTEGRATION_TESTS=true")


@pytest.fixture(scope="module")
def config():
    """Load configuration for integration tests."""
    config_path = Path(__file__).parent.parent.parent / "default.cfg"
    Data.init(None, None)  # Initialize Data module
    config = Configuration
    config.init(str(config_path), Data)
    return config


@pytest.fixture(scope="module")
def logger():
    """Create logger instance for integration tests."""
    return Logger()


@pytest.fixture(scope="module")
def bitfinex_api(config, logger):
    """Create Bitfinex API instance for integration tests."""
    return Bitfinex(config, logger)


@pytest.fixture(scope="module")
def poloniex_api(config, logger):
    """Create Poloniex API instance for integration tests."""
    return Poloniex(config, logger)
```

### 阶段 5: 更新现有测试文件

#### 5.1 为现有单元测试添加 markers

**需要更新的文件**:
- `tests/test_*.py` (所有单元测试文件)

**操作**:
在每个测试函数或类上添加 `@pytest.mark.unit` 装饰器

**示例**:
```python
# tests/test_Data.py
@pytest.mark.unit
class TestTruncate:
    @pytest.mark.unit
    def test_truncate_normal_float(self):
        ...
```

**注意**: 这个步骤可以逐步进行，不是阻塞项

### 阶段 6: 文档和脚本更新

#### 6.1 更新 `README.md` 或测试文档

**添加章节**:
```markdown
## 运行测试

### 单元测试（快速，无外部依赖）
```bash
# 运行所有单元测试
pytest tests/ -m "not integration"

# 或使用 uv
uv run poe test
```

### 集成测试（慢速，需要 API 密钥）
```bash
# 运行集成测试（需要有效的 API 密钥）
RUN_INTEGRATION_TESTS=true pytest tests/integration/

# 运行所有测试（单元 + 集成）
RUN_INTEGRATION_TESTS=true pytest tests/
```

### 仅运行慢速测试
```bash
pytest tests/ -m "slow"
```
```

#### 6.2 更新 `pyproject.toml` 的 Poe 任务

**添加任务**:
```toml
[tool.poe.tasks]
test = "pytest tests/ -m 'not integration'"
test-integration = "bash -c 'RUN_INTEGRATION_TESTS=true pytest tests/integration/'"
test-all = "bash -c 'RUN_INTEGRATION_TESTS=true pytest tests/'"
test-cov = "pytest tests/ -m 'not integration' --cov=src/lendingbot --cov-report=html"
```

## 📝 详细文件清单

### 需要创建的文件

1. **`tests/integration/__init__.py`**
   - 空文件，标记为 Python 包

2. **`tests/integration/conftest.py`**
   - 集成测试专用 fixtures
   - 配置文件加载
   - API 对象创建

3. **`tests/integration/test_bitfinex_api.py`**
   - 从 `old/tests/test_BitfinexAPI.py` 迁移
   - Python 3 语法更新
   - 添加 pytest markers

4. **`tests/integration/test_poloniex_api.py`**
   - 从 `old/tests/test_PoloniexAPI.py` 迁移
   - Python 3 语法更新
   - 添加 pytest markers

5. **`tests/conftest.py`**
   - 全局 pytest 配置
   - marker 定义
   - 集成测试自动跳过逻辑

### 需要修改的文件

1. **`pyproject.toml`**
   - 添加 `[tool.pytest.ini_options.markers]` 配置
   - 可选：添加 Poe 任务

2. **`README.md`** 或 `tests/README.md`**
   - 添加测试运行说明

### 可选改进

1. **为所有单元测试添加 `@pytest.mark.unit`**
   - 逐步进行，可以使用脚本批量添加

2. **添加 `.gitignore` 规则**
   ```gitignore
   # Test artifacts
   .pytest_cache/
   htmlcov/
   .coverage
   ```

3. **创建 `tests/integration/README.md`**
   - 说明集成测试的用途
   - 列出前置条件（API 密钥等）
   - 提供故障排查指南

## 🚀 实施步骤（按优先级）

### 第 1 步：基础结构（必须）
1. ✅ 创建 `tests/integration/` 目录
2. ✅ 创建 `tests/integration/__init__.py`
3. ✅ 创建 `tests/integration/conftest.py`

### 第 2 步：迁移测试（必须）
4. ✅ 创建 `tests/integration/test_bitfinex_api.py`
5. ✅ 创建 `tests/integration/test_poloniex_api.py`

### 第 3 步：配置（必须）
6. ✅ 更新 `pyproject.toml` 添加 markers
7. ✅ 创建 `tests/conftest.py`

### 第 4 步：文档和工具（推荐）
8. ⚠️ 更新 README.md 添加测试说明
9. ⚠️ 添加 Poe 任务（可选）
10. ⚠️ 更新 CI 配置跳过集成测试

### 第 5 步：优化（可选）
11. 📝 为现有单元测试添加 markers
12. 📝 添加更多集成测试
13. 📝 性能基准测试

## ⚠️ 注意事项

### API 密钥安全
- 集成测试需要真实的 API 密钥
- 不要在代码中硬编码密钥
- 使用 `default.cfg` 或环境变量
- 在 CI 中跳过集成测试

### 测试隔离
- 集成测试可能会触及真实 API
- 注意速率限制（Rate Limits）
- 考虑使用测试环境的 API 端点

### 性能考虑
- 集成测试较慢（网络延迟）
- 标记为 `@pytest.mark.slow`
- 在 CI 中单独运行或跳过

## ✅ 验证清单

完成实施后，验证以下功能：

- [ ] `pytest tests/ -m "not integration"` 仅运行单元测试
- [ ] `pytest tests/ -m "integration"` 无 `RUN_INTEGRATION_TESTS` 时跳过
- [ ] `RUN_INTEGRATION_TESTS=true pytest tests/integration/` 运行集成测试
- [ ] `pytest tests/ --collect-only` 显示正确的 markers
- [ ] `pytest tests/ -v` 显示跳过的集成测试
- [ ] `pytest tests/ -m "not integration" --cov` 生成覆盖率报告

## 📚 参考资源

- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Skipping Tests](https://docs.pytest.org/en/stable/how-to/skipping.html)
- [Test Organization](https://docs.pytest.org/en/stable/explanation/goodpractices.html#test-discovery)

## 🔗 相关文件

- `pyproject.toml` - 项目配置和 pytest 配置
- `old/tests/test_BitfinexAPI.py` - 源集成测试（Python 2.7）
- `old/tests/test_PoloniexAPI.py` - 源集成测试（Python 2.7）
- `tests/test_*.py` - 现有单元测试
- `default.cfg` - 配置文件（集成测试需要）

---

**计划创建时间**: 2025-12-28
**预计实施时间**: 1-2 小时
**优先级**: 中（完成测试迁移的收尾工作）
