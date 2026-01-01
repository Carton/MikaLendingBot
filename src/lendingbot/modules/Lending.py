import sched
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from . import Configuration as Config
from . import Data, MaxToLend
from .Logger import Logger
from .Utils import format_amount_currency, format_rate_pct


SATOSHI = Decimal(10) ** -8


@dataclass
class RateCalcInfo:
    """Rate calculation details for generating clear log output."""

    final_rate: Decimal  # The final rate to use
    min_rate: Decimal  # Configured minimum rate
    frr_enabled: bool  # Whether FRR as min is enabled
    frr_base: Decimal | None = None  # FRR base rate (only when frr_enabled=True)
    frr_delta: Decimal | None = None  # FRR delta value (only when frr_enabled=True)
    frr_delta_step: int | None = None  # Current delta step (1-5)
    frr_used: bool = False  # Whether FRR was actually used (FRR+delta > min_rate)


sleep_time_active: float = 0
sleep_time_inactive: float = 0
sleep_time: float = 0
min_daily_rate: Decimal = Decimal(0)
max_daily_rate: Decimal = Decimal(0)
spread_lend: int = 0
gap_bottom_default: Decimal = Decimal(0)
gap_top_default: Decimal = Decimal(0)
xday_threshold: str = ""
min_loan_size: Decimal = Decimal(0)
min_loan_sizes: dict[str, Decimal] = {}
end_date: str | None = None
coin_cfg: dict[str, Config.CoinConfig] = {}
dry_run: bool = False
transferable_currencies: list[str] = []
currencies_to_analyse: list[str] = []
keep_stuck_orders: bool = True
hide_coins: bool = True
coin_cfg_alerted: dict[str, bool] = {}
max_active_alerted: dict[str, bool] = {}
notify_conf: dict[str, Any] = {}
loans_provided: list[dict[str, Any]] = []
gap_mode_default: Config.GapMode | bool | str = ""
scheduler: sched.scheduler | None = None
exchange: str = ""
frrasmin: bool = False

frrdelta_cur_step: int = 0
frrdelta_min: Decimal = Decimal(0)
frrdelta_max: Decimal = Decimal(0)
debug_on: bool = False
lending_paused: bool = False
last_lending_status: bool | None = None

# limit of orders to request
loanOrdersRequestLimit: dict[str, int] = {}
defaultLoanOrdersRequestLimit: int = 5
# FIXME: Make this configurable
compete_rate: float = 0.00064

api: Any = None
log: Logger | None = None
Analysis: Any = None
analysis_method: str = "percentile"
all_currencies: list[str] = []


def _reset_globals() -> None:
    """
    Resets all global variables to their default values.
    Primarily used for testing to ensure a clean state between test cases.
    """
    global \
        sleep_time, \
        sleep_time_active, \
        sleep_time_inactive, \
        min_daily_rate, \
        max_daily_rate, \
        spread_lend, \
        gap_bottom_default, \
        gap_top_default, \
        xday_threshold, \
        min_loan_size, \
        end_date, \
        coin_cfg, \
        min_loan_sizes, \
        dry_run, \
        transferable_currencies, \
        keep_stuck_orders, \
        hide_coins, \
        scheduler, \
        gap_mode_default, \
        exchange, \
        analysis_method, \
        currencies_to_analyse, \
        all_currencies, \
        frrasmin, \
        frrdelta_min, \
        frrdelta_max, \
        frrdelta_cur_step, \
        debug_on, \
        lending_paused, \
        last_lending_status, \
        loans_provided, \
        api, \
        log, \
        Data, \
        MaxToLend, \
        Analysis, \
        notify_conf

    sleep_time = 0
    sleep_time_active = 0
    sleep_time_inactive = 0
    min_daily_rate = Decimal(0)
    max_daily_rate = Decimal(0)
    spread_lend = 0
    gap_bottom_default = Decimal(0)
    gap_top_default = Decimal(0)
    xday_threshold = ""
    min_loan_size = Decimal(0)
    min_loan_sizes = {}
    end_date = None
    coin_cfg = {}
    dry_run = False
    transferable_currencies = []
    keep_stuck_orders = True
    hide_coins = True
    scheduler = None
    gap_mode_default = ""
    exchange = ""
    analysis_method = "percentile"
    currencies_to_analyse = []
    all_currencies = []
    frrasmin = False
    frrdelta_min = Decimal(0)
    frrdelta_max = Decimal(0)
    frrdelta_cur_step = 0
    debug_on = False
    lending_paused = False
    last_lending_status = None
    loans_provided = []
    api = None
    log = None
    Data = None  # type: ignore[assignment]
    MaxToLend = None  # type: ignore[assignment]
    Analysis = None
    notify_conf = {}


def debug_log(msg: str) -> None:
    if debug_on:
        print(f"DEBUG: {msg}")


def init(
    cfg: Any,
    api1: Any,
    log1: Logger,
    data: Any,
    maxtolend: Any,
    dry_run1: bool,
    analysis: Any,
    notify_conf1: dict[str, Any],
) -> None:
    """
    Initialize the Lending module with configuration, API, logger, and other dependencies.

    Args:
        cfg: The configuration object.
        api1: The exchange API instance.
        log1: The logger instance.
        data: The Data module instance.
        maxtolend: The MaxToLend module instance.
        dry_run1: Boolean flag for dry run mode.
        analysis: The MarketAnalysis module instance.
        notify_conf1: Configuration dictionary for notifications.
    """
    global Config, api, log, Data, MaxToLend, Analysis, notify_conf
    Config = cfg
    api = api1
    log = log1
    Data = data
    MaxToLend = maxtolend
    Analysis = analysis
    notify_conf = notify_conf1

    global \
        sleep_time, \
        sleep_time_active, \
        sleep_time_inactive, \
        min_daily_rate, \
        max_daily_rate, \
        spread_lend, \
        gap_bottom_default, \
        gap_top_default, \
        xday_threshold, \
        min_loan_size, \
        end_date, \
        coin_cfg, \
        min_loan_sizes, \
        dry_run, \
        transferable_currencies, \
        keep_stuck_orders, \
        hide_coins, \
        scheduler, \
        gap_mode_default, \
        exchange, \
        analysis_method, \
        currencies_to_analyse, \
        all_currencies, \
        frrasmin, \
        frrdelta_min, \
        frrdelta_max

    exchange = Config.get_exchange()

    sleep_time_active = float(Config.get("BOT", "sleeptimeactive", None, 1, 3600))
    sleep_time_inactive = float(Config.get("BOT", "sleeptimeinactive", None, 1, 3600))
    exchange_max = 7 if exchange == "BITFINEX" else 5
    min_daily_rate = Decimal(Config.get("BOT", "mindailyrate", None, 0.003, exchange_max)) / 100
    max_daily_rate = Decimal(Config.get("BOT", "maxdailyrate", None, 0.003, exchange_max)) / 100
    spread_lend = int(Config.get("BOT", "spreadlend", None, 1, 20))
    gap_mode_default = Config.get_gap_mode("BOT", "gapMode")
    gap_bottom_default = Decimal(Config.get("BOT", "gapbottom", None, 0))
    gap_top_default = Decimal(Config.get("BOT", "gaptop", None, float(gap_bottom_default)))
    xday_threshold = str(Config.get("BOT", "xdaythreshold"))
    # maxPeriod = 120 if exchange == 'BITFINEX' else 60
    min_loan_size = Decimal(Config.get("BOT", "minloansize", None, 0.01))
    end_date = Config.get("BOT", "endDate")
    coin_cfg = Config.get_coin_cfg()
    min_loan_sizes = Config.get_min_loan_sizes()
    dry_run = dry_run1
    transferable_currencies = Config.get_currencies_list("transferableCurrencies")
    all_currencies = Config.get_all_currencies()
    currencies_to_analyse = Config.get_currencies_list("analyseCurrencies", "MarketAnalysis")
    keep_stuck_orders = Config.getboolean("BOT", "keepstuckorders", True)
    hide_coins = Config.getboolean("BOT", "hideCoins", True)
    frrasmin = Config.getboolean("BOT", "frrasmin", False)
    frrdelta_min = Decimal(Config.get("BOT", "frrdelta_min", -10))
    frrdelta_max = Decimal(Config.get("BOT", "frrdelta_max", 10))
    try:
        analysis_method = Config.AnalysisMethod(Config.get("Daily_min", "method", "percentile"))
    except ValueError:
        allowed = ", ".join([m.value for m in Config.AnalysisMethod])
        raise ValueError(
            f'analysis_method: "{Config.get("Daily_min", "method")}" is not valid, must be {allowed}'
        ) from None

    sleep_time = sleep_time_active  # Start with active mode

    # create the scheduler thread
    scheduler = sched.scheduler(time.time, time.sleep)
    if notify_conf["notify_summary_minutes"]:
        # Wait 10 seconds before firing the first summary notification, then use the config time value for future updates
        scheduler.enter(10, 1, notify_summary, (notify_conf["notify_summary_minutes"] * 60,))
    if notify_conf["notify_new_loans"]:
        scheduler.enter(20, 1, notify_new_loans, (60,))
    if not scheduler.empty():
        t = threading.Thread(target=scheduler.run)
        t.daemon = True
        t.start()


def get_sleep_time() -> float:
    """
    Returns the current sleep time based on the bot's activity.

    Returns:
        float: The sleep time in seconds.
    """
    return sleep_time


def set_sleep_time(usable: int) -> None:
    """
    Updates the global sleep time based on whether any currency was lendable.

    Args:
        usable: The number of currencies that had enough balance to lend.
    """
    global sleep_time
    sleep_time = sleep_time_inactive if usable == 0 else sleep_time_active


def notify_summary(sleep_time_val: float) -> None:
    """
    Sends a summary notification of total lent assets and schedules the next one.

    Args:
        sleep_time_val: Interval in seconds for the next notification.
    """
    try:
        if log:
            log.notify(Data.stringify_total_lent(Data.get_total_lent()), notify_conf)
    except Exception as ex:
        print(f"Error during summary notification: {ex}")
    if scheduler:
        scheduler.enter(sleep_time_val, 1, notify_summary, (sleep_time_val,))


def notify_new_loans(sleep_time_val: float) -> None:
    """
    Checks for newly filled loans and sends notifications if found.

    Args:
        sleep_time_val: Interval in seconds for the next check.
    """
    global loans_provided
    try:
        new_provided = api.return_active_loans()["provided"]
        if loans_provided:
            # function to return a set of ids from the api result
            # get_id_set = lambda loans: set([x['id'] for x in loans])
            def get_id_set(loans: list[dict[str, Any]]) -> set[Any]:
                return {x["id"] for x in loans}

            loans_amount: dict[str, float] = {}
            loans_info: dict[str, dict[str, Any]] = {}
            for loan_id in get_id_set(new_provided) - get_id_set(loans_provided):
                loan = next(x for x in new_provided if x["id"] == loan_id)
                # combine loans with the same rate
                k = f"c{loan['currency']}r{loan['rate']}d{loan['duration']}"
                loans_amount[k] = float(loan["amount"]) + loans_amount.get(k, 0.0)
                loans_info[k] = loan
            # send notifications with the grouped info
            for k, amount in loans_amount.items():
                loan = loans_info[k]
                text = f"{format_amount_currency(amount, loan['currency'])} loan filled for {loan['duration']} days at a rate of {format_rate_pct(loan['rate'])}"
                if log:
                    log.notify(text, notify_conf)
        loans_provided = new_provided
    except Exception as ex:
        print(f"Error during new loans notification: {ex}")
    if scheduler:
        scheduler.enter(sleep_time_val, 1, notify_new_loans, (sleep_time_val,))


def get_min_loan_size(currency: str) -> Decimal:
    """
    Gets the minimum loan size for a specific currency.

    Args:
        currency: The currency symbol (e.g., 'BTC').

    Returns:
        Decimal: The minimum allowed amount for a lending offer.
    """
    if currency not in min_loan_sizes:
        return min_loan_size
    return Decimal(min_loan_sizes[currency])


# parse config like "0.050:25,0.058:30,0.060:45,0.064:60,0.070:120", i.e. rate:days pairs,
# and return the rates, days list
def parse_xday_threshold(xday_threshold_str: str) -> tuple[list[float], list[str]]:
    """
    Parses the xdaythreshold config string into rates and days lists.

    Args:
        xday_threshold_str: A comma-separated string of 'rate:days' pairs.

    Returns:
        tuple: (list of rates as floats, list of days as strings).
    """
    rates: list[float] = []
    xdays: list[str] = []
    if xday_threshold_str:
        for pair in xday_threshold_str.split(","):
            rate, day = pair.split(":")
            rates.append(float(rate) / 100)
            xdays.append(day)
    return rates, xdays


def create_lend_offer(
    currency: str, amt: str | Decimal, rate: str | float | Decimal, days: str = "2"
) -> None:
    """
    Creates a new lending offer on the exchange.

    Args:
        currency: The currency to lend.
        amt: The amount to lend.
        rate: The daily interest rate (as a float or decimal).
        days: The duration of the loan in days.
    """
    original_rate = float(rate)
    rate_f = original_rate
    if rate_f > 0.0001:
        rate_f = rate_f - 0.000001  # lend offer just below the competing one
    amt_s = f"{Decimal(amt):.8f}"
    rates, xdays = parse_xday_threshold(xday_threshold)
    if days == "2" and len(rates) > 0:
        # map rate to xdays, use interpolation if rate is not in the list
        if rate_f < rates[0]:
            days = xdays[0]
        else:
            for i in range(len(rates)):
                if rate_f <= rates[i]:
                    # linear interpolation
                    days = str(
                        int(xdays[i - 1])
                        + int(
                            (int(xdays[i]) - int(xdays[i - 1]))
                            * (rate_f - rates[i - 1])
                            / (rates[i] - rates[i - 1])
                        )
                    )
                    break
            else:
                # If rate is greater than the last rate, use the last xdays
                days = xdays[-1]
        print(
            f"Lending {format_amount_currency(amt_s, currency)} by rate {format_rate_pct(rate_f)} for {days} days"
        )

    if Config.has_option("BOT", "endDate") and end_date:
        days_remaining = int(Data.get_max_duration(end_date, "order"))
        if days_remaining <= 2:
            print("endDate reached. Bot can no longer lend.\nExiting...")
            if log:
                log.log(
                    "The end date has almost been reached and the bot can no longer lend. Exiting."
                )
                log.log(Data.stringify_total_lent(Data.get_total_lent()))
                log.persistStatus()
            exit(0)
        if int(days) > days_remaining:
            days = str(days_remaining)
    if not dry_run:
        msg = api.create_loan_offer(currency, amt_s, days, 0, rate_f)
        if len(xdays) > 0 and days == xdays[-1] and notify_conf["notify_xday_threshold"]:
            text = f"{format_amount_currency(amt_s, currency)} loan placed for {days} days at a rate of {format_rate_pct(rate_f)}"
            if log:
                log.notify(text, notify_conf)
        if log:
            # Pass original_rate to show compete adjustment info
            log.offer(amt_s, currency, rate_f, days, msg, original_rate)


def cancel_all() -> None:
    """
    Cancels all open lending offers for active currencies.
    """
    loan_offers = api.return_open_loan_offers()
    available_balances = api.return_available_account_balances("lending")
    for cur in loan_offers:
        if cur not in all_currencies:
            continue
        if (cfg := coin_cfg.get(cur)) and cfg.maxactive == 0:
            # don't cancel disabled coin
            continue
        if keep_stuck_orders:
            lending_balances = available_balances["lending"]
            if isinstance(lending_balances, dict) and cur in lending_balances:
                cur_sum = float(available_balances["lending"][cur])
            else:
                cur_sum = 0.0
            for offer in loan_offers[cur]:
                cur_sum += float(offer["amount"])
        else:
            cur_sum = float(get_min_loan_size(cur)) + 1.0
        if cur_sum >= float(get_min_loan_size(cur)):
            for offer in loan_offers[cur]:
                if not dry_run:
                    try:
                        msg = api.cancel_loan_offer(cur, offer["id"])
                        if log:
                            log.cancelOrder(cur, msg)
                    except Exception as ex:
                        if log:
                            log.log(f"Error canceling loan offer: {ex}")
        else:
            print(f"Not enough {cur} to lend if bot canceled open orders. Not cancelling.")


def lend_all() -> None:
    """
    Main loop to attempt lending for all currencies with available balance.
    """
    total_lent = Data.get_total_lent().total_lent
    lending_balances = api.return_available_account_balances("lending")["lending"]
    if dry_run:  # just fake some numbers, if dryrun (testing)
        lending_balances = Data.get_on_order_balances()

    # Fill the (maxToLend) balances on the botlog.json for display it on the web
    for cur in sorted(total_lent):
        if not lending_balances or cur not in lending_balances:
            MaxToLend.amount_to_lend(total_lent[cur], cur, Decimal(0), Decimal(0))

    usable_currencies = 0
    # global sleep_time  # We need global var to edit sleeptime
    ticker = False
    if gap_mode_default == "rawbtc":
        ticker = api.return_ticker()  # Only call ticker once for all orders
    else:
        for cur_name in coin_cfg:
            if coin_cfg[cur_name].gapmode == "rawbtc":
                ticker = api.return_ticker()
                break

    if log:
        log.log(f"Lending balances: {lending_balances}")
        log.log(f"All currencies: {all_currencies}")

    try:
        if lending_balances:
            for cur in lending_balances:
                if cur in all_currencies:
                    usable_currencies += lend_cur(cur, total_lent, lending_balances, ticker)
    except StopIteration:  # Restart lending if we stop to raise the request limit.
        lend_all()
        return
    set_sleep_time(usable_currencies)


def get_frr_or_min_daily_rate(cur: str) -> RateCalcInfo:
    """
    Checks the Flash Return Rate of cur against the min daily rate and returns
    detailed rate calculation info.

    :param cur: The currency which to check
    :return: RateCalcInfo containing the rate and calculation details
    """
    global frrdelta_cur_step, frrdelta_min, frrdelta_max
    if cfg := coin_cfg.get(cur):
        min_rate = cfg.minrate
        frr_as_min = cfg.frrasmin
        # Config values are now percentages (e.g., -10 means -10%)
        frr_d_min = cfg.frrdelta_min
        frr_d_max = cfg.frrdelta_max
    else:
        min_rate = Decimal(Config.get("BOT", "mindailyrate", None, 0.003, 5)) / 100
        frr_as_min = Config.getboolean("BOT", "frrasmin", False)
        frr_d_min = frrdelta_min
        frr_d_max = frrdelta_max

    if frr_d_min > frr_d_max:
        frr_d_min, frr_d_max = frr_d_max, frr_d_min

    # Let's use hard coded steps for now
    frrdelta_steps = 5
    frrdelta_step = (frr_d_max - frr_d_min) / frrdelta_steps

    if frrdelta_cur_step > frrdelta_steps:
        frrdelta_cur_step = 0
    frrdelta_pct = frr_d_min + (frrdelta_step * frrdelta_cur_step)
    current_step = frrdelta_cur_step + 1  # 1-indexed for display
    frrdelta_cur_step += 1

    if exchange == "BITFINEX" and frr_as_min:
        frr_base = Decimal(api.get_frr(cur))
        # Apply relative percentage: rate = FRR * (1 + pct/100)
        frr_rate = frr_base * (1 + frrdelta_pct / 100)
        if frr_rate > min_rate:
            return RateCalcInfo(
                final_rate=frr_rate,
                min_rate=min_rate,
                frr_enabled=True,
                frr_base=frr_base,
                frr_delta=frrdelta_pct,
                frr_delta_step=current_step,
                frr_used=True,
            )
        else:
            # FRR enabled but rate too low, use min_rate
            return RateCalcInfo(
                final_rate=min_rate,
                min_rate=min_rate,
                frr_enabled=True,
                frr_base=frr_base,
                frr_delta=frrdelta_pct,
                frr_delta_step=current_step,
                frr_used=False,
            )

    # FRR not enabled or not on Bitfinex
    return RateCalcInfo(
        final_rate=min_rate,
        min_rate=min_rate,
        frr_enabled=False,
    )


def get_min_daily_rate(cur: str) -> Decimal | bool:
    """
    Determines the minimum daily lending rate for a currency, considering
    user config, market analysis suggestions, and exchange-specific FRR.

    Args:
        cur: The currency symbol.

    Returns:
        Decimal: The minimum daily rate to use.
        bool: False if the currency is disabled (maxactive == 0).
    """
    rate_info = get_frr_or_min_daily_rate(cur)

    # Check if currency is disabled
    if (cfg := coin_cfg.get(cur)) and cfg.maxactive == 0:
        if cur not in max_active_alerted:  # Only alert once per coin.
            max_active_alerted[cur] = True
            if log:
                log.log(f"[{cur}] Disabled: maxactive=0, skipping")
        return False

    # Generate rate calculation log
    if log:
        _log_rate_calculation(cur, rate_info)

    # Check for Market Analysis suggestion
    if Analysis and cur in currencies_to_analyse:
        recommended_min = Analysis.get_rate_suggestion(cur, method=analysis_method)
        if rate_info.final_rate < Decimal(str(recommended_min)) and log:
            log.log(f"[{cur}] Tip: {analysis_method} suggests {format_rate_pct(recommended_min)}")

    return rate_info.final_rate


def _log_rate_calculation(cur: str, info: RateCalcInfo) -> None:
    """
    Log rate calculation details in a unified format.

    Args:
        cur: Currency symbol
        info: Rate calculation details
    """
    if not log:
        return

    if info.frr_enabled:
        # FRR mode
        assert info.frr_base is not None
        assert info.frr_delta is not None
        assert info.frr_delta_step is not None

        # frr_delta is now a relative percentage (e.g., -10 means -10%)
        frr_multiplier = 1 + info.frr_delta / 100
        if info.frr_used:
            # FRR*multiplier > min_rate, use FRR
            log.log(
                f"[{cur}] Rate: FRR {format_rate_pct(info.frr_base)} × "
                f"{frr_multiplier:.2f} (step {info.frr_delta_step}/5) = "
                f"{format_rate_pct(info.final_rate)} (> min {format_rate_pct(info.min_rate)}) ✓"
            )
        else:
            # FRR*multiplier <= min_rate, use min_rate
            log.log(
                f"[{cur}] Rate: FRR {format_rate_pct(info.frr_base)} × "
                f"{frr_multiplier:.2f} (step {info.frr_delta_step}/5) = "
                f"{format_rate_pct(info.frr_base * frr_multiplier)} (< min {format_rate_pct(info.min_rate)}, using min)"
            )
    else:
        # Non-FRR mode
        log.log(f"[{cur}] Rate: min_rate {format_rate_pct(info.min_rate)}")


def construct_order_books(active_cur: str) -> bool | list[dict[str, Any]]:
    """
    Fetches the loan order book from the exchange and structures it.

    Args:
        active_cur: The currency to fetch orders for.

    Returns:
        list: [demand_book, offer_book] each containing 'rates', 'volumes', 'rangeMax'.
        bool: False if no orders found.
    """
    # make sure we have a request limit for this currency
    if active_cur not in loanOrdersRequestLimit:
        loanOrdersRequestLimit[active_cur] = defaultLoanOrdersRequestLimit

    loans = api.return_loan_orders(active_cur, loanOrdersRequestLimit[active_cur])
    if not loans or len(loans) == 0:
        return False

    resps = []
    for load_type in ("demands", "offers"):
        rate_book = []
        volume_book = []
        range_max_book = []
        for load in loans.get(load_type, []):
            rate_book.append(load["rate"])
            volume_book.append(load["amount"])
            range_max_book.append(load["rangeMax"])
        resp = {"rates": rate_book, "volumes": volume_book, "rangeMax": range_max_book}
        debug_log(f"construct {load_type}: {resp}")
        resps.append(resp)

    return resps


def get_gap_rate(
    active_cur: str,
    gap: Decimal,
    order_book: dict[str, Any],
    cur_total_balance: Decimal,
    raw: bool = False,
) -> Decimal:
    """
    Calculates the lending rate at a specific depth (gap) in the order book.

    Args:
        active_cur: The currency symbol.
        gap: The depth to look for.
        order_book: The processed offer book.
        cur_total_balance: Total balance of the currency.
        raw: If True, gap is treated as absolute amount instead of percentage.

    Returns:
        Decimal: The rate found at the specified depth.

    Raises:
        StopIteration: If the gap depth exceeds the current fetched order book size.
    """
    gap_expected = gap if raw else gap * cur_total_balance / Decimal("100.0")
    gap_sum = Decimal(0)
    i = 0
    while gap_sum < gap_expected:
        if (
            i == len(order_book["volumes"]) - 1
            and len(order_book["volumes"]) == loanOrdersRequestLimit[active_cur]
        ):
            # loanOrdersRequestLimit[active_cur] += defaultLoanOrdersRequestLimit
            if log:
                log.log(
                    f"{active_cur}: Not enough offers in response, adjusting request limit to {loanOrdersRequestLimit[active_cur]}"
                )
            raise StopIteration
        elif i == len(order_book["volumes"]) - 1:
            return max_daily_rate
        gap_sum += Decimal(str(order_book["volumes"][i]))
        i += 1
    return Decimal(str(order_book["rates"][i]))


def get_cur_spread(spread: int, cur_active_bal: Decimal, active_cur: str) -> int:
    """
    Calculates the actual spread (number of orders) possible for a currency.

    Args:
        spread: The configured desired spread.
        cur_active_bal: Available balance to lend.
        active_cur: The currency symbol.

    Returns:
        int: The number of orders to split the balance into.
    """
    cur_spread_lend = int(
        spread
    )  # Checks if active_bal can't be spread that many times, and may go down to 1.
    cur_min_loan_size = get_min_loan_size(active_cur)
    while cur_active_bal < (cur_spread_lend * cur_min_loan_size):
        cur_spread_lend -= 1
    return max(1, int(cur_spread_lend))


def construct_orders(
    cur: str, cur_active_bal: Decimal, cur_total_balance: Decimal, ticker: Any
) -> dict[str, Any]:
    """
    Constructs a list of lend orders based on the configured spread and gap settings.

    Args:
        cur: The currency symbol.
        cur_active_bal: The active balance available to lend.
        cur_total_balance: The total balance of the currency.
        ticker: The ticker data (used for rawbtc gap mode).

    Returns:
        dict: A dictionary containing lists of 'amounts' and 'rates' for the orders.
    """
    cur_spread = get_cur_spread(spread_lend, cur_active_bal, cur)
    if cur_spread == 1:
        # print('skip get_gap_mode_rates ...')
        rate_step = Decimal(0)
        bottom_rate = Decimal(0)
    else:
        # print('call get_gap_mode_rates ...')
        top_rate, bottom_rate = get_gap_mode_rates(cur, cur_active_bal, cur_total_balance, ticker)
        gap_diff = top_rate - bottom_rate
        rate_step = gap_diff / (cur_spread - 1)

    order_rates = []
    for i in range(cur_spread):
        new_rate = bottom_rate + (rate_step * i)
        order_rates.append(new_rate)

    # Condensing and logic'ing time
    for i, rate in enumerate(order_rates):
        if rate > max_daily_rate:
            order_rates[i] = max_daily_rate

    new_order_rates = sorted(set(order_rates))
    new_order_amounts = []
    for _ in range(len(new_order_rates)):
        new_amount = Data.truncate(cur_active_bal / len(new_order_rates), 8)
        new_order_amounts.append(Decimal(str(new_amount)))

    remainder = cur_active_bal - sum(new_order_amounts)
    if remainder > 0:  # If truncating causes remainder, add that to first order.
        new_order_amounts[0] += remainder

    resp = {"amounts": new_order_amounts, "rates": new_order_rates}
    debug_log(f"Constructing orders: {resp}")
    return resp


def get_gap_mode_rates(
    cur: str, cur_active_bal: Decimal, cur_total_balance: Decimal, ticker: Any
) -> list[Decimal]:
    """
    Calculates the top and bottom rates based on the configured gap mode.

    Args:
        cur: The currency symbol.
        cur_active_bal: Current balance to lend.
        cur_total_balance: Total balance of the currency.
        ticker: Ticker data for price conversions.

    Returns:
        list: [top_rate, bottom_rate] as Decimals.
    """
    global gap_mode_default, gap_bottom_default, gap_top_default  # To be able to change them later if needed.
    gap_mode, gap_bottom, gap_top = gap_mode_default, gap_bottom_default, gap_top_default
    use_gap_cfg = False

    books = construct_order_books(cur)
    if not books or not isinstance(books, list) or len(books) < 2:
        return [max_daily_rate, max_daily_rate]

    order_book = books[1]

    if (
        (cfg := coin_cfg.get(cur))
        and cfg.gapmode
        and cfg.gapbottom is not None
        and cfg.gaptop is not None
    ):
        # Only overwrite default if all three are set
        use_gap_cfg = True
        gap_mode = str(cfg.gapmode)
        gap_bottom = cfg.gapbottom
        gap_top = cfg.gaptop

    if gap_mode == "rawbtc":
        btc_value = Decimal(1)
        if cur != "BTC":
            for coin in ticker:
                if coin == f"BTC_{cur.upper()}":
                    btc_value = Decimal(str(ticker[coin]["last"]))
                    break
        bottom_depth = gap_bottom / btc_value  # Converts from BTC to altcoin's value
        bottom_rate = get_gap_rate(cur, bottom_depth, order_book, cur_total_balance, True)
        top_depth = gap_top / btc_value
        top_rate = get_gap_rate(cur, top_depth, order_book, cur_total_balance, True)
    elif gap_mode == "raw":  # Value stays in altcoin
        bottom_rate = get_gap_rate(cur, gap_bottom, order_book, cur_total_balance, True)
        top_rate = get_gap_rate(cur, gap_top, order_book, cur_total_balance, True)
    elif gap_mode == "relative":
        bottom_rate = get_gap_rate(cur, gap_bottom, order_book, cur_total_balance)
        top_rate = get_gap_rate(cur, gap_top, order_book, cur_total_balance)
    else:
        if use_gap_cfg:
            print(f"WARN: Invalid setting for gapMode for [{cur}], using defaults...")
            coin_cfg[cur].gapmode = Config.GapMode.RAWBTC
            coin_cfg[cur].gapbottom = Decimal(10)
            coin_cfg[cur].gaptop = Decimal(100)
        else:
            print("WARN: Invalid setting for gapMode, using defaults...")
            gap_mode_default = "relative"
            gap_bottom_default = Decimal(10)
            gap_top_default = Decimal(200)
        return get_gap_mode_rates(
            cur, cur_active_bal, cur_total_balance, ticker
        )  # Start over with new defaults

    debug_log(f"gap_mode: {gap_mode}, top_rate: {top_rate}, bottom_rate: {bottom_rate}")
    return [Decimal(str(top_rate)), Decimal(str(bottom_rate))]


def lend_cur(
    active_cur: str, total_lent: dict[str, Decimal], lending_balances: dict[str, str], ticker: Any
) -> int:
    """
    Analyzes the market and places lend orders for a specific currency.

    Args:
        active_cur: The currency symbol to lend.
        total_lent: Dictionary of total amounts already lent.
        lending_balances: Dictionary of available lending balances.
        ticker: The ticker data.

    Returns:
        1 if the currency was usable (orders placed or attempted), 0 otherwise.
    """
    active_cur_total_balance = Decimal(str(lending_balances[active_cur]))
    if active_cur in total_lent:
        active_cur_total_balance += total_lent[active_cur]

    # min daily rate can be changed per currency
    cur_min_daily_rate = get_min_daily_rate(active_cur)

    # log total coin
    if log:
        log.updateStatusValue(active_cur, "totalCoins", active_cur_total_balance)

    books = construct_order_books(active_cur)
    if not books or not isinstance(books, list) or len(books) < 2 or not cur_min_daily_rate:
        return 0

    demand_book, order_book = books[0], books[1]

    active_bal = MaxToLend.amount_to_lend(
        active_cur_total_balance,
        active_cur,
        Decimal(str(lending_balances[active_cur])),
        Decimal(str(order_book["rates"][0])),
    )

    if (
        float(active_bal)
        >= float(
            get_min_loan_size(active_cur)
        )  # Make sure sleeptimer is set to active if any cur can lend.
    ):
        currency_usable = 1
    else:
        return 0  # Return early to end function.

    orders = construct_orders(
        active_cur, active_bal, active_cur_total_balance, ticker
    )  # Build all potential orders
    for i in range(
        len(orders["amounts"])
    ):  # Iterate through prepped orders and create them if they work
        below_min = Decimal(str(orders["rates"][i])) < Decimal(str(cur_min_daily_rate))

        if hide_coins and below_min:
            if log:
                log.log(
                    f"Not lending {active_cur} due to rate below {format_rate_pct(cur_min_daily_rate)} (actual: {format_rate_pct(orders['rates'][i])})"
                )
            return 0
        elif below_min:
            rate = str(cur_min_daily_rate)
        else:
            rate = orders["rates"][i]

        days = "2"
        # Check demand_book for competing offers
        if demand_book and float(demand_book["rates"][0]) > compete_rate:
            rate = demand_book["rates"][0]
            days = str(demand_book["rangeMax"][0])
            if log:
                log.log(
                    f"Competing offer found for {active_cur} at {format_rate_pct(rate)} for {days} days."
                )

        try:
            create_lend_offer(active_cur, orders["amounts"][i], rate, days)
        except Exception as msg:
            if "Amount must be at least " in str(msg):
                import re

                results = re.findall(r"[-+]?([0-9]*\.[0-9]+|[0-9]+)", str(msg))
                for result in results:
                    if result:
                        min_loan_sizes[active_cur] = Decimal(result)
                        if log:
                            log.log(
                                f"{active_cur}'s min_loan_size has been increased to the detected min: {result}"
                            )
                return lend_cur(
                    active_cur, total_lent, lending_balances, ticker
                )  # Redo cur with new min.
            else:
                raise msg

    return currency_usable


def transfer_balances() -> None:
    # Transfers all balances on the included list to Lending.
    if len(transferable_currencies) > 0:
        exchange_balances = api.return_balances()  # This grabs only exchange balances.
        for coin in list(transferable_currencies):
            if coin in exchange_balances and Decimal(str(exchange_balances[coin])) > 0:
                msg = api.transfer_balance(coin, exchange_balances[coin], "exchange", "lending")
                if log:
                    log.log(log.digestApiMsg(msg))
                    log.notify(log.digestApiMsg(msg), notify_conf)
            if coin not in exchange_balances:
                print(f"WARN: Incorrect coin entered for transferCurrencies: {coin}")
                transferable_currencies.remove(coin)
