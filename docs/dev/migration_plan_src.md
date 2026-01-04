# Configuration Migration Plan (Source Code)

This document outlines the step-by-step plan to migrate the `src` directory to the new `Configuration.py` module (Pydantic + TOML).

## Overview
The goal is to replace the usage of `Configuration_old` (and its `.get()` API) with the new `Configuration.RootConfig` object and its typed attributes.

**Strategy**: "Initialize Once, Pass Around (or Single Singleton Check)".
We will utilize the `Configuration.load_config()` in `main.py` and modify consumers to use the typed config object.

## Phase 1: Preparation & Interfaces

### 1.1 Update `main.py`
- Change import from `lendingbot.modules.Configuration` (which acts as old/mixed) to new `Configuration`.
- Replace `Configuration.init()` with `Configuration.load_config("default.toml")`.
- Update `Lending.init()` call to pass the new `RootConfig` object.

### 1.2 Update `Lending.py` Init
- Update `Lending.init` type hint for `cfg` argument to `Configuration.RootConfig`.
- **CRITICAL**: Rewrite the global variable initialization block in `Lending.init`.
    - Map `cfg.bot.period_active` -> `sleep_time_active`
    - Map `cfg.api.exchange` -> `exchange` (and others)
- **Coin Configuration**:
    - `Lending.py` relies on `coin_cfg` dictionary.
    - **Change**: `coin_cfg` type should be `dict[str, Configuration.CoinConfig]`.
    - **Logic**: Instead of calling `Config.get_coin_cfg()`, we should define a helper or Populate it by iterating known currencies.
    - *Better Approach*: Change `coin_cfg` to just be a reference to `cfg` or use `cfg.get_coin_config(cur)` on demand?
        - Current code uses `coin_cfg.get(cur).minrate`.
        - We should likely preload `coin_cfg` for all relevant currencies using `cfg.get_coin_config(cur)` to maintain performance and `Lending.py` structure.

## Phase 2: Refactoring Consumers (Field Name Changes)
The new Pydantic models use snake_case (e.g., `min_daily_rate`) whereas old code expected `minrate`. This requires a find-and-replace in consumers.

### 2.1 Refactor `Lending.py` Logic
- Replace `cfg.minrate` with `cfg.min_daily_rate`.
- Replace `cfg.lending_strategy` (enum) usage (Ensure Enum access matches).
- Replace `cfg.gapbottom` -> `cfg.gap_bottom`.
- ...and so on for all `CoinConfig` fields.
- **Global Config variable**: Use `Config.get_config()` if `cfg` is not available in local scope, OR pass `cfg` around. Since `Lending.py` is largely global state based, using `Config.get_config()` inside functions is acceptable if `init` has run.

### 2.2 Refactor `MarketAnalysis.py`
- Update `__init__` to accept `RootConfig`.
- Replace `self.config.get("MarketAnalysis", ...)` with `self.config.plugins.market_analysis.update_interval`.

### 2.3 Refactor `WebServer.py`
- Update `initialize_web_server(config: RootConfig)`.
- Replace `config.get(...)` with `config.bot.web.host`, `config.bot.web.port`.

### 2.4 Refactor Exchange Modules (`Poloniex.py`, `Bitfinex.py`)
- Update `__init__` to accept `RootConfig`.
- Access API keys via `config.api.apikey` / `config.api.secret`.

## Phase 3: Cleanup
- Remove `import Configuration as Config` from `Lending.py` (it should rely on the passed `cfg` or `Configuration.get_config()`).
- Verify no calls to `Configuration_old` remain.

## Implementation Order
1.  **Stop reusing `Configuration.py` for old imports**: Ensure `Lending.py` imports types from the new module but doesn't try to call old functions on it.
2.  **Modify `Lending.py`**: This is the largest task.
    - Update type hints.
    - Update `init()`.
    - Update all attribute accesses.
3.  **Modify `main.py`**: Switch the loader.
4.  **Modify Plugins/Exchanges**: Update their access patterns.

## Risks & mitigation
- **Runtime Errors**: Attribute naming mismatches are likely.
- **Mitigation**: We will rely on `mypy` (which we just fixed) to catch these mismatches after updating the code! Running `poe fix-full` after each file edit will be crucial.
