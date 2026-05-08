from decimal import Decimal

from . import Configuration
from .Logger import Logger
from .Utils import format_amount_currency


coin_cfg: dict[str, Configuration.CoinConfig] = {}
min_loan_size: Decimal = Decimal("0.001")
log: Logger | None = None


def init(config: Configuration.RootConfig, log1: Logger) -> None:
    """
    Initializes the MaxToLend module with configuration settings.

    Args:
        config: The configuration object.
        log1: The logger instance.
    """
    global coin_cfg, min_loan_size, log

    # Populate coin_cfg with configured coins (merged with defaults by get_coin_config)
    coin_cfg = {}
    for symbol in config.coin:
        coin_cfg[symbol] = config.get_coin_config(symbol)

    default_coin = config.get_coin_config("default")
    min_loan_size = default_coin.min_loan_size
    log = log1


def amount_to_lend(
    active_cur: str,
    lending_balance: Decimal,
    total_lent: Decimal = Decimal(0),
) -> Decimal:
    """
    Calculates the actual amount to lend based on absolute limits.

    Args:
        active_cur: The currency symbol.
        lending_balance: The available balance in the lending account.
        total_lent: The amount currently lent out (active loans).

    Returns:
        Decimal: The amount calculated to be offered for lending.
    """
    if log is None:
        return lending_balance

    cur_max_active_amount = Decimal("-1")

    if cfg := coin_cfg.get(active_cur):
        cur_max_active_amount = cfg.max_active_amount

    # Check max_active_amount limit first (absolute cap on total lending)
    # max_active_amount: -1 = unlimited, 0 = disabled (handled elsewhere), > 0 = limit
    if cur_max_active_amount > 0:
        # Calculate how much more we can lend without exceeding max_active_amount
        # total_lent = currently lent out (active loans)
        # lending_balance = available to lend (not yet offered)
        available_capacity = cur_max_active_amount - total_lent
        if available_capacity <= 0:
            log.log(
                f"[{active_cur}] max_active_amount limit reached: "
                f"currently lent {format_amount_currency(total_lent, active_cur)} "
                f">= limit {format_amount_currency(cur_max_active_amount, active_cur)}, skipping"
            )
            return Decimal(0)
        if lending_balance > available_capacity:
            log.log(
                f"[{active_cur}] max_active_amount limit: "
                f"reducing lending from {format_amount_currency(lending_balance, active_cur)} "
                f"to {format_amount_currency(available_capacity, active_cur)} "
                f"(currently lent: {format_amount_currency(total_lent, active_cur)}, "
                f"limit: {format_amount_currency(cur_max_active_amount, active_cur)})"
            )
            lending_balance = available_capacity

    return lending_balance
