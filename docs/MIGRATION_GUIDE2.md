# LendingBot Python 3 迁移指南

本文档详细说明如何将 Python 2.7 代码迁移到现代化的 Python 3.12+ 架构。

## 📋 迁移概览

- **源架构**: Python 2.7, 扁平项目结构
- **目标架构**: Python 3.12+, `src/` 布局, 类型提示, 现代工具链

## 🏗️ 新项目结构

```
lendingbot/
├── src/
│   └── lendingbot/          # 主包
│       ├── __init__.py          # 包初始化
│       ├── main.py              # ✅ 已创建: 主入口
│       ├── modules/             # TODO: 从 modules/ 迁移
│       │   ├── Bitfinex.py
│       │   ├── Poloniex.py
│       │   ├── WebServer.py
│       │   └── ...
│       └── plugins/             # TODO: 从 plugins/ 迁移
│           ├── Plugin.py
│           ├── AccountStats.py
│           └── ...
├── tests/                       # 现有测试目录
├── pyproject.toml               # ✅ 已创建: 现代项目配置
├── .gitignore                   # ✅ 已更新
├── main.py                      # 旧主入口 (保留)
├── lendingbot.py               # 旧主入口 (保留)
└── requirements.txt             # 旧依赖 (已迁移到 pyproject.toml)
```

## 🔄 迁移步骤

### 第 1 步: 导入语句更新

**Python 2.7 → Python 3**

```python
# 旧代码 (Python 2.7)
import SimpleHTTPServer
import SocketServer
from httplib import BadStatusLine
from urllib2 import URLError

# 新代码 (Python 3)
import http.server as SimpleHTTPServer
import socketserver as SocketServer
from http.client import BadStatusLine
from urllib.error import URLError
```

**常见导入映射表**:

| Python 2.7 | Python 3 |
|-----------|----------|
| `httplib` | `http.client` |
| `urllib2` | `urllib.request`, `urllib.error` |
| `SimpleHTTPServer` | `http.server` |
| `SocketServer` | `socketserver` |
| `ConfigParser` | `configparser` |

### 第 2 步: 语法更新

#### 2.1 print 语句 → print 函数

```python
# 旧代码
print 'Hello, world!'
print 'Status:', status

# 新代码
print('Hello, world!')
print('Status:', status)
```

#### 2.2 整数除法

```python
# 旧代码
result = 5 / 2  # = 2

# 新代码 (如果需要整数除法)
result = 5 // 2  # = 2
result = 5 / 2   # = 2.5
```

#### 2.3 字符串处理

```python
# 旧代码
# 字符串默认为 bytes

# 新代码
# 字符串默认为 Unicode
text = "Hello"
bytes_data = b"Hello"
text = bytes_data.decode('utf-8')
```

### 第 3 步: 添加类型提示

```python
# 旧代码
def calculate_rate(amount, rate):
    return amount * rate

# 新代码
from decimal import Decimal
from typing import Union

def calculate_rate(amount: Decimal, rate: Decimal) -> Decimal:
    """
    计算利率
    
    Args:
        amount: 金额
        rate: 利率
        
    Returns:
        计算后的金额
    """
    return amount * rate
```

### 第 4 步: 更新 WebServer 模块

**关键变更** (modules/WebServer.py:48-54):

```python
# 旧代码
import SimpleHTTPServer
import SocketServer

class QuietHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    # ...

# 新代码
import http.server
import socketserver

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    # ...

# 服务器启动
socketserver.TCPServer.allow_reuse_address = True
server = socketserver.TCPServer((host, port), QuietHandler)
```

### 第 5 步: 异常处理更新

```python
# 旧代码
try:
    # some code
except Exception, e:
    print e.message

# 新代码
try:
    # some code
except Exception as e:
    print(str(e))
```

### 第 6 步: 迭代器更新

```python
# 旧代码
for i in xrange(100):
    print(i)

# 新代码
for i in range(100):
    print(i)
```

## 🛠️ 开发工作流

### 安装依赖

```bash
# 清空代理 (如果需要)
export https_proxy= && export http_proxy=

# 安装所有依赖
uv sync --group dev --group test
```

### 运行应用

```bash
# 方式 1: 使用 uv run
uv run python -m lendingbot.main

# 方式 2: 使用 poe 任务
uv run poe run

# 方式 3: 使用自定义配置
uv run python -m lendingbot.main --config=myconfig.cfg
```

### 代码质量检查

```bash
# 完整检查 (格式 + lint + 类型检查)
uv run poe check-full

# 自动修复
uv run poe fix-full

# 仅运行测试
uv run poe test

# 测试覆盖率
uv run poe test-coverage
```

### 添加新依赖

```bash
# 添加运行时依赖
uv add requests

# 添加开发依赖
uv add --dev pytest
```

## 📝 代码规范

### Ruff 配置

- **行长度**: 100 字符
- **目标版本**: Python 3.12+
- **导入排序**: isort 风格
- **类型检查**: mypy strict 模式

### 文档字符串规范

使用 Google 风格的文档字符串:

```python
def process_loan_request(amount: Decimal, currency: str) -> bool:
    """
    处理借贷请求
    
    Args:
        amount: 借贷金额
        currency: 货币代码 (如 'BTC', 'USD')
        
    Returns:
        是否成功处理请求
        
    Raises:
        ValueError: 当金额为负数时
        ApiError: 当 API 调用失败时
        
    Example:
        >>> process_loan_request(Decimal('1.5'), 'BTC')
        True
    """
    if amount < 0:
        raise ValueError("Amount must be positive")
    # implementation...
```

## ✅ 迁移检查清单

### 每个模块迁移时检查:

- [ ] 更新导入语句 (httplib → http.client, etc.)
- [ ] 更新 print 语句为函数
- [ ] 更新异常语法 (`except X, e` → `except X as e`)
- [ ] 替换 `xrange` 为 `range`
- [ ] 更新字符串处理 (bytes vs str)
- [ ] 添加类型提示
- [ ] 添加文档字符串
- [ ] 更新路径操作 (推荐使用 `pathlib`)
- [ ] 移除 Python 2 特定的编码声明 (`# coding=utf-8`)
- [ ] 运行 mypy 类型检查
- [ ] 运行 ruff 代码检查
- [ ] 编写/更新测试

### 推荐迁移顺序

1. **低依赖模块**: Logger.py, Data.py, RingBuffer.py
2. **工具模块**: Configuration.py, ConsoleUtils.py
3. **API 模块**: ExchangeApi.py, Bitfinex.py, Poloniex.py
4. **业务逻辑**: Lending.py, MarketAnalysis.py
5. **Web 服务**: WebServer.py (需要特别注意 HTTP 库更新)
6. **主入口**: lendingbot.py (已创建新的 main.py)
7. **插件**: plugins/ 目录下的所有文件

## 🧪 测试迁移

现有的测试需要更新:

```python
# 旧代码 (tests/test_RingBuffer.py)
# coding=utf-8  # 移除这个
import os
import sys

# 新代码
import sys
from pathlib import Path

# 使用 pathlib 而不是 os.path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
```

## 🔍 常见问题

### Q: 如何处理全角中文标点符号的警告?

A: RUFF 会警告中文全角标点 (如 `，` `：` `（` `）`)。这在中文文档中是正常的,可以:

1. 在该行添加 `# noqa: RUF001` 忽略警告
2. 或者在 `.gitignore` 中不处理 (不推荐)

### Q: 旧的 tests/ 目录有很多 Python 2 语法错误怎么办?

A: 按以下优先级处理:

1. 先迁移 src/ 中的源代码
2. 然后逐个修复 tests/ 中的文件
3. 或者重新编写测试 (推荐使用 pytest fixtures)

### Q: 如何设置 CI/CD?

A: 项目已经包含 poe 任务,可以在 GitHub Actions 中使用:

```yaml
- name: Check code
  run: uv run poe check-full

- name: Run tests
  run: uv run poe test-coverage
```

## 📚 参考资源

- [Python 3 移 porting 指南](https://docs.python.org/3/howto/pyporting.html)
- [2to3 迁移工具](https://docs.python.org/3/library/2to3.html)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [uv 文档](https://github.com/astral-sh/uv)
- [mypy 文档](https://mypy.readthedocs.io/)

## 🚀 下一步

1. 开始迁移低依赖模块
2. 逐步迁移业务逻辑
3. 更新 WebServer 以使用 http.server
4. 编新的测试覆盖核心功能
5. 性能测试和优化

---

**提示**: 使用 `uv run poe check-full` 在每次迁移后检查代码质量！
