import sched
import threading
import time
from decimal import Decimal
from typing import Any

from . import Configuration as Config
from . import Data, MaxToLend
from .Logger import Logger


SATOSHI = Decimal(10) ** -8

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
coin_cfg: dict[str, Any] = {}
dry_run: bool = False
transferable_currencies: list[str] = []
currencies_to_analyse: list[str] = []
keep_stuck_orders: bool = True
hide_coins: bool = True
coin_cfg_alerted: dict[str, bool] = {}
max_active_alerted: dict[str, bool] = {}
notify_conf: dict[str, Any] = {}
loans_provided: list[dict[str, Any]] = []
gap_mode_default: str = ""
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
    gap_mode_default = str(Config.get_gap_mode("BOT", "gapMode"))
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
    frrdelta_min = Decimal(Config.get("BOT", "frrdelta_min", 0.0000))
    frrdelta_max = Decimal(Config.get("BOT", "frrdelta_max", 0.00008))
    analysis_method = str(Config.get("Daily_min", "method", "percentile"))
    if analysis_method not in ["percentile", "MACD"]:
        raise ValueError(
            f'analysis_method: "{analysis_method}" is not valid, must be percentile or MACD'
        )

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
    return sleep_time


def set_sleep_time(usable: int) -> None:
    global sleep_time
    sleep_time = sleep_time_inactive if usable == 0 else sleep_time_active


def notify_summary(sleep_time_val: float) -> None:
    try:
        if log:
            log.notify(Data.stringify_total_lent(*Data.get_total_lent()), notify_conf)
    except Exception as ex:
        print(f"Error during summary notification: {ex}")
    if scheduler:
        scheduler.enter(sleep_time_val, 1, notify_summary, (sleep_time_val,))


def notify_new_loans(sleep_time_val: float) -> None:
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
                text = f"{amount} {loan['currency']} loan filled for {loan['duration']} days at a rate of {float(loan['rate']) * 100:.4f}%"
                if log:
                    log.notify(text, notify_conf)
        loans_provided = new_provided
    except Exception as ex:
        print(f"Error during new loans notification: {ex}")
    if scheduler:
        scheduler.enter(sleep_time_val, 1, notify_new_loans, (sleep_time_val,))


def get_min_loan_size(currency: str) -> Decimal:
    if currency not in min_loan_sizes:
        return min_loan_size
    return Decimal(min_loan_sizes[currency])


# parse config like "0.050:25,0.058:30,0.060:45,0.064:60,0.070:120", i.e. rate:days pairs,
# and return the rates, days list
def parse_xday_threshold(xday_threshold_str: str) -> tuple[list[float], list[str]]:
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
    rate_f = float(rate)
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
        print(f"Using xday threshold: rate={rate_f}, days={days}")

    if Config.has_option("BOT", "endDate") and end_date:
        days_remaining = int(Data.get_max_duration(end_date, "order"))
        if days_remaining <= 2:
            print("endDate reached. Bot can no longer lend.\nExiting...")
            if log:
                log.log(
                    "The end date has almost been reached and the bot can no longer lend. Exiting."
                )
                log.refreshStatus(
                    Data.stringify_total_lent(*Data.get_total_lent()),
                    str(Data.get_max_duration(end_date, "status")),
                )
                log.persistStatus()
            exit(0)
        if int(days) > days_remaining:
            days = str(days_remaining)
    if not dry_run:
        msg = api.create_loan_offer(currency, amt_s, days, 0, rate_f)
        if len(xdays) > 0 and days == xdays[-1] and notify_conf["notify_xday_threshold"]:
            text = (
                f"{amt_s} {currency} loan placed for {days} days at a rate of {rate_f * 100:.4f}%"
            )
            if log:
                log.notify(text, notify_conf)
        if log:
            log.offer(amt_s, currency, rate_f, days, msg)


def cancel_all() -> None:
    loan_offers = api.return_open_loan_offers()
    available_balances = api.return_available_account_balances("lending")
    for cur in loan_offers:
        if cur not in all_currencies:
            continue
        if cur in coin_cfg and coin_cfg[cur]["maxactive"] == 0:
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
    total_lent = Data.get_total_lent()[0]
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
            if "rawbtc" in str(coin_cfg[cur_name].get("gapmode", "")):
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


def get_frr_or_min_daily_rate(cur: str) -> Decimal:
    """
    Checks the Flash Return Rate of cur against the min daily rate and returns the better of the two. If not using
    bitfinex then it will always return the min daily rate for the currency.

    :param cur: The currency which to check
    :return: The better of the two rates (FRR and min daily rate)
    """
    global frrdelta_cur_step, frrdelta_min, frrdelta_max
    if cur in coin_cfg:
        min_rate = Decimal(coin_cfg[cur]["minrate"])
        frr_as_min = coin_cfg[cur]["frrasmin"]
        frr_d_min = Decimal(coin_cfg[cur]["frrdelta_min"]) / 100
        frr_d_max = Decimal(coin_cfg[cur]["frrdelta_max"]) / 100
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
    frrdelta_val = frr_d_min + (frrdelta_step * frrdelta_cur_step)
    frrdelta_cur_step += 1

    if log:
        log.log(f"Using frrasmin {frr_as_min} for {cur}")
        log.log(
            f"Using frrdelta {frr_d_min * 100}% + {(frrdelta_val - frr_d_min) * 100}% = {frrdelta_val * 100}% for {cur}"
        )

    if exchange == "BITFINEX" and frr_as_min:
        frr_rate = Decimal(api.get_frr(cur)) + frrdelta_val
        if frr_rate > min_rate:
            if log:
                log.log(f"Using FRR as mindailyrate {frr_rate * 100:.6f}% for {cur}")
            return frr_rate

    if log:
        log.log(f"Using min_daily_rate {min_rate * 100:.6f}% for {cur}")
    return min_rate


def get_min_daily_rate(cur: str) -> Decimal | bool:
    cur_min_daily_rate = get_frr_or_min_daily_rate(cur)
    if cur in coin_cfg:
        if coin_cfg[cur]["maxactive"] == 0:
            if cur not in max_active_alerted:  # Only alert once per coin.
                max_active_alerted[cur] = True
                if log:
                    log.log(f"maxactive amount for {cur} set to 0, won't lend.")
            return False
        if cur not in coin_cfg_alerted:  # Only alert once per coin.
            coin_cfg_alerted[cur] = True
            if log:
                log.log(f"Using custom mindailyrate {cur_min_daily_rate * 100}% for {cur}")
    if Analysis and cur in currencies_to_analyse:
        # TODO: Check how the suggested rate is calculated here.
        recommended_min = Analysis.get_rate_suggestion(cur, method=analysis_method)
        if cur_min_daily_rate < Decimal(str(recommended_min)) and log:
            log.log(
                f"Suggest to use {analysis_method} as mindailyrate {recommended_min * 100}% for {cur}"
            )
            # cur_min_daily_rate = recommended_min
    return Decimal(cur_min_daily_rate)


def construct_order_books(active_cur: str) -> bool | list[dict[str, Any]]:
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
    Calculates the gap rate for a given active currency.

    Args:
        active_cur (str): The active currency.
        gap (float): The gap value.
        order_book (dict): The order book containing volumes and rates.
        cur_total_balance (Decimal): The current total balance.
        raw (bool, optional): Whether to use the raw gap value. Defaults to False.

    Returns:
        float: The calculated gap rate.

    Raises:
        StopIteration: If there are not enough offers in the response.

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
        A dictionary containing lists of 'amounts' and 'rates' for the orders.
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
    global gap_mode_default, gap_bottom_default, gap_top_default  # To be able to change them later if needed.
    gap_mode, gap_bottom, gap_top = gap_mode_default, gap_bottom_default, gap_top_default
    use_gap_cfg = False

    books = construct_order_books(cur)
    if not books or not isinstance(books, list) or len(books) < 2:
        return [max_daily_rate, max_daily_rate]

    order_book = books[1]

    if cur in coin_cfg:  # Get custom values specific to coin
        cfg = coin_cfg[cur]
        if (
            cfg.get("gapmode")
            and cfg.get("gapbottom") is not None
            and cfg.get("gaptop") is not None
        ):
            # Only overwrite default if all three are set
            use_gap_cfg = True
            gap_mode = cfg["gapmode"]
            gap_bottom = Decimal(str(cfg["gapbottom"]))
            gap_top = Decimal(str(cfg["gaptop"]))

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
            coin_cfg[cur]["gapmode"] = "rawbtc"
            coin_cfg[cur]["gapbottom"] = 10
            coin_cfg[cur]["gaptop"] = 100
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
                    f"Not lending {active_cur} due to rate below {Decimal(str(cur_min_daily_rate)) * 100:.4f}% (actual: {Decimal(str(orders['rates'][i])) * 100:.4f}%)"
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
                    f"Competing offer found for {active_cur} at {float(rate) * 100:.4f}% for {days} days."
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
