from decimal import Decimal

from . import Configuration
from .Logger import Logger
from .Utils import format_amount_currency, format_rate_pct


coin_cfg: dict[str, Configuration.CoinConfig] = {}
max_to_lend_rate: Decimal = Decimal(0)
max_to_lend: Decimal = Decimal(0)
max_percent_to_lend: Decimal = Decimal(0)
min_loan_size: Decimal = Decimal("0.001")
log: Logger | None = None


def init(config: Configuration.RootConfig, log1: Logger) -> None:
    """
    Initializes the MaxToLend module with configuration settings.

    Args:
        config: The configuration object.
        log1: The logger instance.
    """
    global coin_cfg, max_to_lend_rate, max_to_lend, max_percent_to_lend, min_loan_size, log

    # Populate coin_cfg with configured coins (merged with defaults by get_coin_config)
    coin_cfg = {}
    for symbol in config.coin:
        coin_cfg[symbol] = config.get_coin_config(symbol)

    default_coin = config.get_coin_config("default")
    max_to_lend = default_coin.max_to_lend
    max_percent_to_lend = default_coin.max_percent_to_lend
    max_to_lend_rate = default_coin.max_to_lend_rate
    min_loan_size = default_coin.min_loan_size
    log = log1


def amount_to_lend(
    active_cur_test_balance: Decimal,
    active_cur: str,
    lending_balance: Decimal,
    low_rate: Decimal,
    total_lent: Decimal = Decimal(0),
) -> Decimal:
    """
    Calculates the actual amount to lend based on limits and market rates.

    Args:
        active_cur_test_balance: The total balance of the currency (lending + on-order).
        active_cur: The currency symbol.
        lending_balance: The available balance in the lending account.
        low_rate: The lowest rate currently in the order book.
        total_lent: The amount currently lent out (active loans).

    Returns:
        Decimal: The amount calculated to be offered for lending.
    """
    if log is None:
        return lending_balance

    restrict_lend = False
    active_bal = Decimal(0)
    log_data = ""
    cur_max_to_lend_rate = max_to_lend_rate
    cur_max_to_lend = max_to_lend
    cur_max_percent_to_lend = max_percent_to_lend
    cur_max_active_amount = Decimal(-1)

    if cfg := coin_cfg.get(active_cur):
        cur_max_to_lend_rate = cfg.max_to_lend_rate
        cur_max_to_lend = cfg.max_to_lend
        cur_max_percent_to_lend = cfg.max_percent_to_lend
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

    if (cur_max_to_lend_rate == 0 and low_rate > 0) or cur_max_to_lend_rate >= low_rate > 0:
        log_data = (
            f"The Lower Rate found on {active_cur} is {format_rate_pct(low_rate)} "
            f"vs conditional rate {format_rate_pct(cur_max_to_lend_rate)}. "
        )
        restrict_lend = True

    if cur_max_to_lend != 0 and restrict_lend:
        log.updateStatusValue(active_cur, "maxToLend", cur_max_to_lend)
        if lending_balance > (active_cur_test_balance - cur_max_to_lend):
            active_bal = lending_balance - (active_cur_test_balance - cur_max_to_lend)

    if cur_max_to_lend == 0 and cur_max_percent_to_lend != 0 and restrict_lend:
        log.updateStatusValue(
            active_cur, "maxToLend", (cur_max_percent_to_lend * active_cur_test_balance)
        )
        if lending_balance > (
            active_cur_test_balance - (cur_max_percent_to_lend * active_cur_test_balance)
        ):
            active_bal = lending_balance - (
                active_cur_test_balance - (cur_max_percent_to_lend * active_cur_test_balance)
            )

    if cur_max_to_lend == 0 and cur_max_percent_to_lend == 0:
        log.updateStatusValue(active_cur, "maxToLend", active_cur_test_balance)
        active_bal = lending_balance

    if not restrict_lend:
        log.updateStatusValue(active_cur, "maxToLend", active_cur_test_balance)
        active_bal = lending_balance

    if (lending_balance - active_bal) < min_loan_size:
        active_bal = lending_balance

    if active_bal < lending_balance:
        log.log(
            f"{log_data} Lending {format_amount_currency(active_bal, active_cur)} "
            f"of {format_amount_currency(lending_balance, active_cur)} Available"
        )

    return active_bal
