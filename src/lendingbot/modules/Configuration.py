from __future__ import annotations

import tomllib
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator


if TYPE_CHECKING:
    from pathlib import Path


# --- Enums ---


class Exchange(str, Enum):
    POLONIEX = "Poloniex"
    BITFINEX = "Bitfinex"


class LendingStrategy(str, Enum):
    SPREAD = "Spread"
    FRR = "FRR"


class GapMode(str, Enum):
    RAW = "Raw"
    RAW_BTC = "RawBTC"
    RELATIVE = "Relative"


# --- Sub-Models ---


class ApiConfig(BaseModel):
    exchange: Exchange = Exchange.BITFINEX
    apikey: SecretStr | None = None
    secret: SecretStr | None = None
    all_currencies: list[str] = Field(default_factory=list)


class WebServerConfig(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(8000, ge=1, le=65535)
    template: str = "www"


class BotConfig(BaseModel):
    label: str = "Lending Bot"
    period_active: float = Field(60.0, ge=1, le=3600)
    period_inactive: float = Field(300.0, ge=1, le=3600)
    request_timeout: int = Field(30, ge=1, le=180)
    api_debug_log: bool = False
    json_file: str = "www/botlog.json"
    json_log_size: int = 200
    output_currency: str = "BTC"
    keep_stuck_orders: bool = True
    hide_coins: bool = True
    end_date: str | None = None
    plugins: list[str] = Field(default_factory=list)
    transferable_currencies: list[str] = Field(default_factory=list)
    web: WebServerConfig = Field(default_factory=lambda: WebServerConfig())

    @field_validator("exchange", mode="before", check_fields=False)
    @classmethod
    def case_insensitive_exchange(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.capitalize()
        return v


class XDayThreshold(BaseModel):
    rate: Decimal
    days: int


class CoinConfig(BaseModel):
    # Core Lending Settings
    min_daily_rate: Decimal = Field(Decimal("0.005"), ge=0, le=5)
    max_daily_rate: Decimal = Field(Decimal("5.0"), ge=0, le=5)

    @field_validator("min_daily_rate", "max_daily_rate", "max_to_lend_rate", mode="after")
    @classmethod
    def convert_percent_to_decimal(cls, v: Decimal) -> Decimal:
        return v / 100

    min_loan_size: Decimal = Field(Decimal("0.01"), ge=Decimal("0.005"))
    # max_active_amount: Limits total lending for this currency.
    #   -1 = unlimited (no limit on total lending)
    #    0 = disabled (skip this coin entirely, equivalent to not including in all_currencies)
    #   >0 = limit (cap total lending to this amount in coin units, e.g., 1000 USD)
    max_active_amount: Decimal = Decimal("-1")
    max_to_lend: Decimal = Decimal("0")
    max_percent_to_lend: Decimal = Field(Decimal("0"), ge=0, le=100)
    max_to_lend_rate: Decimal = Decimal("0")

    # Strategy
    strategy: LendingStrategy = LendingStrategy.SPREAD

    # Spread Strategy
    spread_lend: int = Field(3, ge=1, le=20)
    gap_mode: GapMode = GapMode.RAW_BTC
    gap_bottom: Decimal = Decimal("0")
    gap_top: Decimal | None = None  # Defaults to gap_bottom if None

    # FRR Strategy
    frr_delta_min: Decimal = Decimal("-10.0")
    frr_delta_max: Decimal = Decimal("10.0")

    # XDay
    xday_thresholds: list[XDayThreshold] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_gap_top(self) -> CoinConfig:
        if self.gap_top is None:
            self.gap_top = self.gap_bottom
        return self


# --- Top Model ---


class MarketAnalysisConfig(BaseModel):
    analyse_currencies: list[str] = Field(default_factory=list)
    # Default matches original code MarketAnalysis.py L29
    update_interval: int = Field(10, ge=1, le=3600)
    lending_style: int = Field(75, ge=1, le=99)
    # Default matches MarketAnalysis.py L41
    recorded_levels: int = Field(3, ge=1, le=100)
    # Default matches MarketAnalysis.py L42
    data_tolerance: float = Field(15.0, ge=10.0, le=90.0)
    ma_debug_log: bool = False
    macd_long_window: int = Field(1800, ge=60, le=604800)
    percentile_window: int = Field(86400, ge=3600, le=1209600)
    daily_min_multiplier: float = Field(1.05, ge=1.0)


class PluginsConfig(BaseModel):
    account_stats: dict[str, Any] = Field(default_factory=dict)
    charts: dict[str, Any] = Field(default_factory=dict)
    market_analysis: MarketAnalysisConfig = Field(default_factory=lambda: MarketAnalysisConfig())


class NotificationConfig(BaseModel):
    enabled: bool = False
    email: dict[str, Any] = Field(default_factory=dict, alias="email")
    slack: dict[str, Any] = Field(default_factory=dict)
    telegram: dict[str, Any] = Field(default_factory=dict)
    pushbullet: dict[str, Any] = Field(default_factory=dict)
    irc: dict[str, Any] = Field(default_factory=dict)

    notify_new_loans: bool = False
    notify_tx_coins: bool = False
    notify_xday_threshold: bool = False
    notify_summary_minutes: int = 0
    notify_caught_exception: bool = False


class RootConfig(BaseModel):
    api: ApiConfig = Field(default_factory=lambda: ApiConfig())
    bot: BotConfig = Field(default_factory=lambda: BotConfig())
    notifications: NotificationConfig = Field(default_factory=lambda: NotificationConfig())
    plugins: PluginsConfig = Field(default_factory=lambda: PluginsConfig())
    coin: dict[str, CoinConfig] = Field(default_factory=dict)

    def get_coin_config(self, symbol: str) -> CoinConfig:
        """
        Returns the merged configuration for a specific coin.
        Priority:
        1. [coin.SYMBOL] settings
        2. [coin.default] settings
        3. Pydantic Model defaults
        """
        defaults = self.coin.get("default", CoinConfig())

        specific = self.coin.get(symbol)

        if not specific:
            return defaults

        # Merge specific into defaults
        # We use model_copy() to avoid re-running validators (which would divide percentages again)
        # and to preserve nested objects (avoiding 'dict' vs 'model' issues).
        merged = defaults.model_copy()

        for field_name in specific.model_fields_set:
            setattr(merged, field_name, getattr(specific, field_name))

        return merged


# --- Global Instance & accessors ---

_current_config: RootConfig | None = None


def load_config(file_path: Path) -> RootConfig:
    global _current_config

    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with file_path.open("rb") as f:
        data = tomllib.load(f)

    config = RootConfig(**data)
    _current_config = config
    return config


def get_config() -> RootConfig:
    if _current_config is None:
        raise RuntimeError("Configuration not initialized. Call load_config() first.")
    return _current_config
