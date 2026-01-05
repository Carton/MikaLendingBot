# Configuration Module Refactor Plan

## Goal Description
重构配置模块 [src/lendingbot/modules/Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py)，引入 **Pydantic** 进行数据定义和验证，将配置结构梳理为 **Global (系统级)** 和 **Coin (币种级)** 两大类。同时建立明确的配置继承机制：`[CUR]` > `[ALL_CUR]` > `Default Values`。

## User Review Required

## User Review Required

> [!IMPORTANT]
> **关于 TOML 格式的设计**
> 已确认切换到 TOML。我们将利用 TOML 的结构化特性进行深度优化：
> 1.  **列表优化**：[all_currencies](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#294-327), `transferableCurrencies` 等改为 TOML 数组 `["BTC", "ETH"]`。
> 2.  **复杂结构优化**：`xdaythreshold` 改为对象数组 `[{rate=0.05, days=30}, ...]`。
> 3.  **层级分组**：
>     *   `[bot]`：全局设置
>     *   `[api]`：交易所 API 设置
>     *   `[notifications]`：通知设置
>     *   `[coin.default]`：所有币种的默认策略 (原 `[ALL_CUR]` 概念)
>     *   `[coin.BTC]`：特定币种覆盖

## Proposed Configuration Structure (TOML)

### 1. TOML File Structure

```toml
[api]
exchange = "POLONIEX"
key = "YourAPIKey"
secret = "YourSecret"

[bot]
label = "Lending Bot"
period_active = 60
period_inactive = 300
output_currency = "USD"
end_date = "2026-12-25"  # Optional
keep_stuck_orders = true
hide_coins = true
request_timeout = 30
api_debug_log = false

# Web Server Settings merged into [bot.web]
[bot.web]
enabled = true
host = "127.0.0.1"
port = 8000
template = "www"

# Plugins list
plugins = ["AccountStats", "Charts"]

# Plugins configuration
[plugins.account_stats]
report_interval = 86400

[plugins.charts]
dump_interval = 21600

[plugins.market_analysis]
currencies = ["BTC", "ETH"] # List instead of csv string
lending_style = 75
macd_long_window = 1800
percentile_window = 259200
daily_min_multiplier = 1.05

# Notification Settings
[notifications]
enabled = false
# ... (simplified structure)

[notifications.telegram]
bot_id = "..."
chat_ids = ["@channel1", "@channel2"]

# Coin Configuration
# [coin.default] serves as the base for all currencies
[coin.default]
min_loan_size = 0.01
min_daily_rate = 0.005
max_daily_rate = 5.0
max_active_amount = -1    # -1 = unlimited
max_to_lend = 0           # 0 = unlimited
max_percent_to_lend = 0   # 0 = 100%
max_to_lend_rate = 0      # 0 = disabled
strategy = "Spread"       # or "FRR"

# Spread Strategy Params
spread_lend = 3
gap_mode = "RawBTC"
gap_bottom = 10
gap_top = 200

# FRR Strategy Params
frr_delta_min = -10.0
frr_delta_max = 10.0

# Advanced xday thresholds in compact array of inline tables
xday_thresholds = [
    { rate = 0.050, days = 20 },
    { rate = 0.058, days = 30 },
    { rate = 0.060, days = 45 },
    { rate = 0.063, days = 60 },
    { rate = 0.070, days = 120 }
]

# Specific overrides
[coin.BTC]
min_daily_rate = 0.18
gap_bottom = 20
gap_top = 400

[coin.CLAM]
min_loan_size = 1
min_daily_rate = 0.6
gap_mode = "raw"
gap_bottom = 10
gap_top = 20
```

## Proposed Changes

### Configuration.py

#### [MODIFY] [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py)
*   引入 `tomllib` (Python 3.11+) 或 `tomlBase`。由于是旧项目可能需要添加依赖 `tomli` (如果 py<3.11)。
*   引入 `pydantic`。
*   定义上述 Pydantic 模型。
*   重构 [init](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#47-73) 和解析逻辑以支持 TOML。

#### [NEW] [default.toml](file:///f:/devel/gitsrc/LendingBot_py3/default.toml)
*   创建新的 TOML 格式配置文件示例。

## Verification Plan

### Automated Tests
*   运行 [tests/test_Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/tests/test_Configuration.py)。需要更新测试以适应新的内部结构，或确保兼容层工作正常。
*   新增 `tests/test_Configuration_pydantic.py` 专门测试 Pydantic 模型的验证逻辑（边界值、类型转换）。

### Manual Verification
*   使用现有 `default.cfg` 启动 Bot，确保配置加载正常。
*   修改配置（如设置错误的数值），验证 Bot 是否能正确报错并提示。
