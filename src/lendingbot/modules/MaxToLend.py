from decimal import Decimal
from typing import Any

from . import Configuration
from .Logger import Logger


coin_cfg: dict[str, Configuration.CoinConfig] = {}
max_to_lend_rate: Decimal = Decimal(0)
max_to_lend: Decimal = Decimal(0)
max_percent_to_lend: Decimal = Decimal(0)
min_loan_size: Decimal = Decimal("0.001")
log: Logger | None = None


def init(config: Any, log1: Logger) -> None:
    """
    Initializes the MaxToLend module with configuration settings.

    Args:
        config: The configuration object.
        log1: The logger instance.
    """
    global coin_cfg, max_to_lend_rate, max_to_lend, max_percent_to_lend, min_loan_size, log
    coin_cfg = config.get_coin_cfg()
    max_to_lend = Decimal(config.get("BOT", "maxtolend", False, 0))
    max_percent_to_lend = Decimal(config.get("BOT", "maxpercenttolend", False, 0, 100)) / 100
    max_to_lend_rate = Decimal(config.get("BOT", "maxtolendrate", False, 0.003, 5)) / 100
    min_loan_size = Decimal(config.get("BOT", "minloansize", None, 0.001))
    log = log1


def amount_to_lend(
    active_cur_test_balance: Decimal,
    active_cur: str,
    lending_balance: Decimal,
    low_rate: Decimal,
) -> Decimal:
    """
    Calculates the actual amount to lend based on limits and market rates.

    Args:
        active_cur_test_balance: The total balance of the currency (lending + on-order).
        active_cur: The currency symbol.
        lending_balance: The available balance in the lending account.
        low_rate: The lowest rate currently in the order book.

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

    if active_cur in coin_cfg:
        cur_max_to_lend_rate = coin_cfg[active_cur].maxtolendrate
        cur_max_to_lend = coin_cfg[active_cur].maxtolend
        cur_max_percent_to_lend = coin_cfg[active_cur].maxpercenttolend

    if (cur_max_to_lend_rate == 0 and low_rate > 0) or cur_max_to_lend_rate >= low_rate > 0:
        log_data = (
            f"The Lower Rate found on {active_cur} is {Decimal(low_rate) * 100:.4f}% "
            f"vs conditional rate {Decimal(cur_max_to_lend_rate) * 100:.4f}%. "
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
        log.log(f"{log_data} Lending {active_bal:.8f} of {lending_balance:.8f} Available")

    return active_bal
