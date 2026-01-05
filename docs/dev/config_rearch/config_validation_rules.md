# Configuration Validation Rules

这份文档总结了代码中对各个配置项的格式要求、数值范围和默认值。这将作为编写 Pydantic 模型验证逻辑的基础。

## 1. API Section (`[api]`)

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `exchange` | `str` | `"Poloniex"` | Case-insensitive. Must be "POLONIEX" or "BITFINEX". | `Configuration.py:get_exchange()` |
| `apikey` | `str` | `None` | Required. | `Poloniex.py`, `Bitfinex.py` |
| `secret` | `str` | `None` | Required. | `Poloniex.py`, `Bitfinex.py` |

## 2. Bot / Global Section (`[bot]`)

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `label` | `str` | `"Lending Bot"` | None | `Logger.py:53` |
| `period_active` (old: `sleeptimeactive`) | `float` | `60.0` | `1 <= x <= 3600` | `Configuration.py:178` |
| `period_inactive` (old: `sleeptimeinactive`) | `float` | `300.0` | `1 <= x <= 3600` | `Configuration.py:183` |
| `request_timeout` (old: `timeout`) | `int` | `30` | `1 <= x <= 180` | `Poloniex.py:41`, `Bitfinex.py:37` |
| `api_debug_log` | `bool` | `False` | None | `Configuration.py` |
| `output_currency` | `str` | `"BTC"` | None | `Configuration.py:188` |
| `keep_stuck_orders` | `bool` | `True` | None | `Configuration.py:191` |
| `hide_coins` | `bool` | `True` | None | `Configuration.py:192` |
| `end_date` | `str` | `None` | Format: `YYYY-MM-DD` | `Configuration.py:190` |


### Web Server (`[bot.web]`)

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `enabled` (old: `startWebServer`) | `bool` | `True` | None | `Configuration.py:189` |
| `host` (old: `customWebServerAddress`) | `str` | `"0.0.0.0"` | Valid IP address format | `WebServer.py:27` |
| `port` (old: `customWebServerPort`) | `int` | `8000` | Valid port (1-65535) | `WebServer.py:38` |
| `template` (old: `customWebServerTemplate`) | `str` | `"www"` | None | `WebServer.py:41` |
| `json_log_size` (old: `jsonlogsize`) | `int` | `200` | Not strictly enforced in code but good to limit | `Configuration.py:187` |

## 3. Coin Configuration (`[coin.*]`)

继承链：`[coin.BTC]` > `[coin.default]` (new) > 硬编码默认值。

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `min_daily_rate` (old: `mindailyrate`) | `Decimal` | `0.003` | `0.003 <= x <= 5.0` (Exchange max limitation) | `Configuration.py:195` |
| `max_daily_rate` (old: `maxdailyrate`) | `Decimal` | `5.0` | `0.003 <= x <= 5.0` | `Configuration.py:195` |
| `min_loan_size` (old: `minloansize`) | `Decimal` | `0.01` | `>= 0.005` | `Configuration.py:244` |
| `max_active_amount` (old: `maxactiveamount`) | `Decimal` | `-1` | `-1` is special (unlimited). `0` is disabled. | `Configuration.py:178` |
| `max_to_lend` (old: `maxtolend`) | `Decimal` | `0` | `>= 0`. `0` means unlimited/check percent. | `Configuration.py:179` |
| `max_percent_to_lend` (old: `maxpercenttolend`) | `Decimal` | `0` | `0 <= x <= 100` | `Configuration.py:180` |
| `max_to_lend_rate` (old: `maxtolendrate`) | `Decimal` | `0` | `>= 0` | `Configuration.py:181` |
| `strategy` (old: `lending_strategy`) | `str` | `"Spread"` | Enum: `"Spread"`, `"FRR"` | `Configuration.py:190` |

### Spread Strategy

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `spread_lend` (old: `spreadlend`) | `int` | `3` | `1 <= x <= 20` | `Configuration.py:196` |
| `gap_mode` | `str` | `"RawBTC"` | Enum: `"Raw"`, `"RawBTC"`, `"Relative"` (Case-insensitive) | `Configuration.py:283` |
| `gap_bottom` | `Decimal` | `0` | `>= 0` | `Configuration.py:187` |
| `gap_top` | `Decimal` | `gap_bottom` | `>= gap_bottom` | `Configuration.py:188` |

### FRR Strategy

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `frr_delta_min` | `Decimal` | `-10` | None specified, typically -50 to 50 | `Configuration.py:206` |
| `frr_delta_max` | `Decimal` | `10` | None specified | `Configuration.py:207` |

### XDayThresholds

*   **Format**: Array of objects: `[{rate: Decimal, days: int}]`
*   **Constraints**:
    *   `rate`: `0 < rate <= 5.0`
    *   `days`: Poloniex max `60`, Bitfinex max `120`.

## 4. Plugins Configuration

### MarketAnalysis

Files: `MarketAnalysis.py`

| Option | Type | Default | Constraints | Source |
| :--- | :--- | :--- | :--- | :--- |
| `analyse_currencies` | `list[str]` | `[]` | Must be valid exchange currencies | `MarketAnalysis.py:25` |
| `update_interval` | `int` | `10` | `1 <= x <= 3600` | `MarketAnalysis.py:29` |
| `lending_style` | `int` | `75` | `1 <= x <= 99` | `MarketAnalysis.py:31` |
| `recorded_levels` | `int` | `3` | `1 <= x <= 100` | `MarketAnalysis.py:41` |
| `data_tolerance` | `float` | `15` | `10 <= x <= 90` | `MarketAnalysis.py:42` |
| `ma_debug_log` | `bool` | `False` | None | `MarketAnalysis.py:43` |
| `macd_long_window` | `int` | `1800` (30m) | `60 <= x <= 604800` (1w) | `MarketAnalysis.py:46` |
| `percentile_window` | `int` | `86400` (1d) | `3600 <= x <= 1209600` (2w) | `MarketAnalysis.py:51` |
| `keep_history_seconds` | `int` | > keep_sec*1.1 - 2w | calc | `MarketAnalysis.py` (L57) |
| `daily_min_multiplier` | `float` | `1.05` | `>= 1` | `MarketAnalysis.py:73` |

### AccountStats
No range constraints found in code. Only `ReportInterval`.

### Charts
No range constraints found in code. Only `DumpInterval`.
