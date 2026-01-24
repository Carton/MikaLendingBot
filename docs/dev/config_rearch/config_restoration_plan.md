# 配置恢复计划 (Config Restoration Plan)

本报告详细说明了原始 `default.cfg` 与新配置系统（`config_sample.toml` / `Configuration.py`）之间缺失项的调查结果及恢复计划。

## 1. 差异研究报告 (Research Report)

通过对旧版 `default.cfg.example` 与新配置架构的系统对比，发现以下差异：

### 1.1 关键缺失项（导致功能损坏）

* **`transferableCurrencies` (自动划转)**
    * **状态**: `Configuration.py` 和 `config_sample.toml` 中均**缺失**。
    * **影响**: 自动划转功能（将资金从交易钱包移至借贷钱包）目前处于断开状态。`Lending.py` 将此列表初始化为空，实际上禁用了该功能。
    * **建议**: 在 `Configuration.py` 的 `BotConfig` 中添加 `transferable_currencies` 字段，并同步更新 `config_sample.toml`。

* **`all_currencies` (币种白名单)**
    * **状态**: 代码中已存在（`ApiConfig` 模型），但 `config_sample.toml` 中**缺失**。
    * **影响**: `ApiConfig` 模型默认将其设为空列表 `[]`。`Lending.py` 中的代码（如 `cancel_all`）会跳过不在该列表中的币种。
    * **结果**: 机器人可能无法管理或取消任何币种的订单，因为白名单默认为空。
    * **建议**: 在 `config_sample.toml` 中添加 `all_currencies`，并包含支持交易所（Bitfinex/Poloniex）的标准默认列表。

### 1.2 次要/外观缺失项

* **`notify_prefix` (通知标签)**
    * **状态**: `Configuration.py` 中**缺失**。
    * **影响**: 用户无法自定义通知前缀（例如 `[Polo]`）。虽然 `Notify.py` 能妥善处理缺失情况，但配置选项已丢失。
    * **建议**: 在 `NotificationConfig` 中添加 `notify_prefix`。

* **`method` (市场分析策略：MACD vs Percentile)**
    * **状态**: **缺失**。目前在 `LendingEngine.py` 中硬编码为 `"percentile"`。
    * **影响**: 用户无法通过配置切换到 MACD 分析方法。
    * **建议**: 在 `MarketAnalysisConfig` 中以 `analysis_method` 的名称恢复此选项。

### 1.3 有意更改/派生项（无需操作）

以下项不再显式配置，而是根据 `MarketAnalysis.py` 动态计算或硬编码：
* `MACD_short_win_seconds`: 现在计算为 `MACD_long_win_seconds / 12`。
* `keep_history_seconds`: 现在根据最长窗口 + 10% 计算。
* `delete_thread_sleep`: 现在计算为 `keep_history_seconds` 的一半。

---

## 2. 拟议恢复计划

### 步骤 1: 更新配置 Schema (`Configuration.py`)
1. 在 `BotConfig` 中添加 `transferable_currencies`。
2. 在 `NotificationConfig` 中添加 `notify_prefix`。
3. 在 `MarketAnalysisConfig` 中添加 `analysis_method` (枚举: `Percentile`, `MACD`)。

### 步骤 2: 更新默认配置 (`config_sample.toml`)
1. 添加 `transferable_currencies` 示例（注释掉）。
2. 添加 `all_currencies` 并填入默认值（如 `["USD", "BTC", "ETH", ...]`）。
3. 添加 `notify_prefix` 示例。
4. 添加 `analysis_method` 示例。

### 步骤 3: 更新代码调用
1. 确保 `LendingEngine.py` 正确从配置中读取 `transferable_currencies`。
2. 确保 `LendingEngine.py` 读取 `analysis_method` 而非使用硬编码的 `"percentile"`。

### 步骤 4: 验证
1. 验证生成的配置读取结果是否符合预期。
2. 运行测试确保无回归。
