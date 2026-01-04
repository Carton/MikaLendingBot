
from __future__ import annotations

import sys
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib  # type: ignore[import-not-found]
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

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
    apikey: Optional[SecretStr] = None
    secret: Optional[SecretStr] = None

class WebServerConfig(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(8000, ge=1, le=65535)
    template: str = "www"
    json_log_size: int = 200

class BotConfig(BaseModel):
    label: str = "Lending Bot"
    period_active: float = Field(60.0, ge=1, le=3600)
    period_inactive: float = Field(300.0, ge=1, le=3600)
    request_timeout: int = Field(30, ge=1, le=180)
    api_debug_log: bool = False
    output_currency: str = "BTC"
    keep_stuck_orders: bool = True
    hide_coins: bool = True
    end_date: Optional[str] = None
    plugins: List[str] = Field(default_factory=list)
    web: WebServerConfig = Field(default_factory=WebServerConfig)

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
    min_loan_size: Decimal = Field(Decimal("0.01"), ge=Decimal("0.005"))
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
    gap_top: Optional[Decimal] = None # Defaults to gap_bottom if None

    # FRR Strategy
    frr_delta_min: Decimal = Decimal("-10.0")
    frr_delta_max: Decimal = Decimal("10.0")

    # XDay
    xday_thresholds: List[XDayThreshold] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_gap_top(self) -> CoinConfig:
        if self.gap_top is None:
            self.gap_top = self.gap_bottom
        return self

# --- Top Model ---

class MarketAnalysisConfig(BaseModel):
    analyse_currencies: List[str] = Field(default_factory=list)
    update_interval: int = Field(10, ge=1, le=3600)
    lending_style: int = Field(75, ge=1, le=99)
    recorded_levels: int = Field(3, ge=1, le=100)
    data_tolerance: float = Field(15.0, ge=10.0, le=90.0)
    ma_debug_log: bool = False
    macd_long_window: int = Field(1800, ge=60, le=604800)
    percentile_window: int = Field(86400, ge=3600, le=1209600)
    daily_min_multiplier: float = Field(1.05, ge=1.0)

    # Derived/Hidden fields managed via property or init logic in original code
    # We keep them simple here.

class PluginsConfig(BaseModel):
    account_stats: Dict[str, Any] = Field(default_factory=dict)
    charts: Dict[str, Any] = Field(default_factory=dict)
    market_analysis: MarketAnalysisConfig = Field(default_factory=MarketAnalysisConfig)

class NotificationConfig(BaseModel):
    enabled: bool = False
    # ... add other fields as mapping existing structure ...
    # For now utilizing generic dict to catch all for notification plugins
    # pending detailed improved struct
    email: Dict[str, Any] = Field(default_factory=dict, alias="email")
    slack: Dict[str, Any] = Field(default_factory=dict)
    telegram: Dict[str, Any] = Field(default_factory=dict)
    pushbullet: Dict[str, Any] = Field(default_factory=dict)
    irc: Dict[str, Any] = Field(default_factory=dict)
    
    # Common settings
    notify_new_loans: bool = False
    notify_tx_coins: bool = False
    notify_xday_threshold: bool = False
    notify_summary_minutes: int = 0
    notify_caught_exception: bool = False

class RootConfig(BaseModel):
    api: ApiConfig = Field(default_factory=ApiConfig)
    bot: BotConfig = Field(default_factory=BotConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    coin: Dict[str, CoinConfig] = Field(default_factory=dict)

    def get_coin_config(self, symbol: str) -> CoinConfig:
        """
        Returns the merged configuration for a specific coin.
        Priority:
        1. [coin.SYMBOL] settings
        2. [coin.default] settings
        3. Pydantic Model defaults
        """
        # Start with defaults
        defaults = self.coin.get("default", CoinConfig())
        default_dict = defaults.model_dump(exclude_unset=True)
        
        # Get specific overrides
        specific = self.coin.get(symbol)
        
        if not specific:
            return defaults
            
        specific_dict = specific.model_dump(exclude_unset=True)
        
        # Merge: Default updated by Specific
        # Note: We must re-validate to ensure consistency if needed, 
        # but CoinConfig is flat enough that simple dict merge usually works.
        # However, for deep merging (like lists), standard update is replace.
        # TOML behavior for re-definition is usually 'replace'.
        
        merged_dict = default_dict.copy()
        merged_dict.update(specific_dict)
        
        return CoinConfig(**merged_dict)

# --- Global Instance & accessors ---

_current_config: Optional[RootConfig] = None

def load_config(file_path: Path) -> RootConfig:
    global _current_config
    
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")
        
    with open(file_path, "rb") as f:
        data = tomllib.load(f)
        
    config = RootConfig(**data)
    _current_config = config
    return config

def get_config() -> RootConfig:
    if _current_config is None:
        raise RuntimeError("Configuration not initialized. Call load_config() first.")
    return _current_config

