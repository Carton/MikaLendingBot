# Configuration Architecture Design

This document outlines the design for the new configuration access interface, leveraging Pydantic models and TOML configuration.

## 1. Core Principles

*   **Single Source of Truth**: The Pydantic `BotConfiguration` (Root Model) instance is the sole source of truth.
*   **Typed Access**: Code should access configuration via typed properties (e.g., `conf.bot.label`) rather than string keys (`conf.get("BOT", "label")`).
*   **Immutability**: Configuration should generally be immutable after loading, preventing runtime side effects.

## 2. Pydantic Model Hierarchy

```python
# Conceptual Structure
class BotConfiguration(BaseModel):
    api: ApiConfig
    bot: GlobalBotConfig
    notifications: NotificationConfig
    plugins: PluginConfig
    coin: dict[str, CoinConfig] # Keyed by currency symbol (e.g., 'BTC', 'default')

    def get_coin(self, symbol: str) -> CoinConfig:
        """
        Returns the specific config for a coin, properly merged with defaults.
        This replaces the old `Configuration.For(currency)`
        """
        # Logic to merge coin.BTC with coin.default
        ...
```

## 3. Access Patterns

We will transition from the "Global Variable Middleman" pattern to a "Singleton / Dependency Injection" pattern.

### Phase 1: Hybrid / Compatibility (Current Refactor)

To avoid breaking the entire codebase immediately, [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/tests/test_Configuration.py) will expose a global instance but wrapped in a helper that maintains backward compatibility.

```python
# src/lendingbot/modules/Configuration.py

_config: BotConfiguration | None = None

def init(path: str) -> BotConfiguration:
    global _config
    # Load TOML, parse into Pydantic
    _config = BotConfiguration.model_validate(toml_data)
    return _config

# New Preferred Accessor
def model() -> BotConfiguration:
    if _config is None: raise RuntimeError("Config not initialized")
    return _config

# Unified Accessor for Coin Config
def get_coin_config(symbol: str) -> CoinConfig:
    return model().get_coin(symbol)

# Deprecated Compatibility Layer (to be removed later)
def get(category: str, option: str, default=None, ...) -> Any:
    # Map old (Category, Option) -> New Model Attribute
    # e.g. ("BOT", "label") -> model().bot.label
    ...
```

### Phase 2: Direct Access (Future)

Modules should import the `model()` accessor or accept configuration in their [__init__](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/MarketAnalysis.py#22-95).

```python
# Example Usage in Lending.py
from lendingbot.modules import Configuration

def check_lending():
    # Old: sleep_time = float(Configuration.get("BOT", "sleeptimeactive"))
    # New:
    conf = Configuration.model()
    sleep_time = conf.bot.period_active
    
    coin_conf = Configuration.get_coin_config("BTC")
    if coin_conf.strategy == LendingStrategy.SPREAD:
        ...
```

## 4. Solving the "Duplicate Global Variables" Problem

The current code (e.g., in [Lending.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Lending.py)) often does this:

```python
# Lending.py (Old)
def init():
    global sleep_time
    sleep_time = Config.get(...) # Copies value to local global
```

**Solution**: Stop copying.
The Pydantic model instance is already cached/global in [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/tests/test_Configuration.py). Other modules should **always** reference the configuration object directly when they need a value, rather than copying values at startup. This ensures:
1.  **Consistency**: No stale copies of config values.
2.  **Testability**: Mocking `Configuration.model()` affects all consumers immediately.
3.  **Hot Reload Potential**: If we reload the config file and update the Pydantic model, the app naturally sees new values (if we don't cache them in local variables).

## 5. Implementation Strategy

1.  **Define Models**: Create the Pydantic models in [Configuration.py](file:///f:/devel/gitsrc/LendingBot_py3/tests/test_Configuration.py).
2.  **Load Logic**: Implement TOML loading and mapping in [init()](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#47-73).
3.  **Compat Layer**: Rewrite [get()](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#92-129), [getboolean()](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#82-90), [has_option()](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#75-80) to query the Pydantic model mapping.
    *   This is crucial for [MarketAnalysis](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/MarketAnalysis.py#21-458) and `WebServer` which rely heavily on [get()](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Configuration.py#92-129).
4.  **Refactor Main Consumers**:
    *   Update `lendingbot.py` to use `Configuration.init()` with TOML.
    *   Update [Lending.py](file:///f:/devel/gitsrc/LendingBot_py3/src/lendingbot/modules/Lending.py) to remove `GlobalConfig` class alias and use `Configuration.get_coin_config()`.
