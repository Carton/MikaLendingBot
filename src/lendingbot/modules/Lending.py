import sched
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from . import Configuration
from .ExchangeApi import ExchangeApi
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


# Global instance for backward compatibility during migration
_engine: "LendingEngine | None" = None


def init(
    cfg: Configuration.RootConfig,
    api: ExchangeApi,
    log: Logger,
    data: Any,
    maxtolend: Any,
    dry_run: bool,
    analysis: Any,
    notify_conf: dict[str, Any],
) -> None:
    """
    Backward-compatible init function that creates the global LendingEngine instance.
    """
    global _engine
    _engine = LendingEngine(cfg, api, log, data, analysis)
    _engine.initialize(dry_run=dry_run)
    _engine.start_scheduler()


def get_sleep_time() -> float:
    if _engine:
        return _engine.sleep_time
    return 60.0


def lend_all() -> None:
    if _engine:
        _engine.lend_all()


def cancel_all() -> None:
    if _engine:
        _engine.cancel_all()


def transfer_balances() -> None:
    if _engine:
        _engine.transfer_balances()


def get_sleep_time_inactive() -> float:
    if _engine:
        return _engine.config.bot.period_inactive
    return 300.0


def parse_xday_threshold(xday_threshold_str: str) -> tuple[list[float], list[str]]:
    return LendingEngine.parse_xday_threshold(xday_threshold_str)


def _reset_globals() -> None:
    """For testing support."""
    global _engine
    _engine = None


class LendingEngine:
    """
    The core lending logic engine.
    Refactored from module-level functions to a class for Dependency Injection.
    """

    def __init__(
        self,
        config: Configuration.RootConfig,
        api: ExchangeApi,
        log: Logger,
        data: Any,
        analysis: Any = None,
    ):
        self.config = config
        self.api = api
        self.log = log
        self.data = data
        self.analysis = analysis

        # Core state (mirrors of old globals)
        self.sleep_time: float = 0
        self.min_daily_rate: Decimal = Decimal(0)
        self.max_daily_rate: Decimal = Decimal(0)
        self.spread_lend: int = 0
        self.gap_bottom_default: Decimal = Decimal(0)
        self.gap_top_default: Decimal = Decimal(0)
        self.gap_mode_default: Configuration.GapMode | bool | str = ""
        self.xday_threshold: str = ""
        self.min_loan_size: Decimal = Decimal(0)
        self.min_loan_sizes: dict[str, Decimal] = {}

        self.coin_cfg: dict[str, Configuration.CoinConfig] = {}
        self.default_coin_cfg: Configuration.CoinConfig = Configuration.CoinConfig()

        self.dry_run: bool = False
        self.transferable_currencies: list[str] = []
        self.coin_cfg_alerted: dict[str, bool] = {}
        self.max_active_alerted: dict[str, bool] = {}
        self.notify_conf: dict[str, Any] = {}
        self.loans_provided: list[dict[str, Any]] = []

        self.frrdelta_cur_step: int = 0
        self.frrdelta_min: Decimal = Decimal(0)
        self.frrdelta_max: Decimal = Decimal(0)
        self.debug_on: bool = False
        self.lending_paused: bool = False
        self.last_lending_status: bool | None = None

        self.loan_orders_request_limit: dict[str, int] = {}
        self.default_loan_orders_request_limit: int = 5
        self.compete_rate: float = 0.00064
        self.analysis_method: str = "percentile"

        self.scheduler: sched.scheduler | None = None

    def initialize(self, dry_run: bool = False) -> None:
        """
        Initialize the LendingEngine state from the injected configuration.
        """
        self.dry_run = dry_run

        # Take defaults from 'default' coin config
        self.default_coin_cfg = self.config.get_coin_config("default")

        self.min_daily_rate = self.default_coin_cfg.min_daily_rate
        self.max_daily_rate = self.default_coin_cfg.max_daily_rate
        self.spread_lend = self.default_coin_cfg.spread_lend
        self.gap_mode_default = self.default_coin_cfg.gap_mode
        self.gap_bottom_default = self.default_coin_cfg.gap_bottom
        self.gap_top_default = (
            self.default_coin_cfg.gap_top
            if self.default_coin_cfg.gap_top is not None
            else self.default_coin_cfg.gap_bottom
        )

        # xday string reconstruction
        xdays = self.default_coin_cfg.xday_thresholds
        if xdays:
            self.xday_threshold = ",".join([f"{x.rate}:{x.days}" for x in xdays])
        else:
            self.xday_threshold = ""

        self.min_loan_size = self.default_coin_cfg.min_loan_size

        # Populate coin_cfg and min_loan_sizes
        self.coin_cfg = {}
        self.min_loan_sizes = {}
        for symbol in self.config.coin:
            cc = self.config.get_coin_config(symbol)
            self.coin_cfg[symbol] = cc
            self.min_loan_sizes[symbol] = cc.min_loan_size

        self.transferable_currencies = []

        self.frrdelta_min = self.default_coin_cfg.frr_delta_min
        self.frrdelta_max = self.default_coin_cfg.frr_delta_max

        self.analysis_method = "percentile"
        self.sleep_time = self.config.bot.period_active

        # Web Settings Precedence (Porting logic)
        try:
            from . import WebServer

            web_settings = WebServer.get_web_settings()
            if "frrdelta_min" in web_settings and "frrdelta_max" in web_settings:
                self.frrdelta_min = Decimal(str(web_settings["frrdelta_min"]))
                self.frrdelta_max = Decimal(str(web_settings["frrdelta_max"]))

            if "lending_paused" in web_settings:
                self.lending_paused = bool(web_settings["lending_paused"])
                if self.log:
                    self.log.log(
                        f"Loaded lending_paused={self.lending_paused} from Web Configuration."
                    )
        except Exception as e:
            if self.log:
                self.log.log(f"Failed to load web settings: {e}")

        # Initialize scheduler
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def get_min_loan_size(self, currency: str) -> Decimal:
        """
        Gets the minimum loan size for a specific currency.
        """
        if currency in self.min_loan_sizes:
            return Decimal(self.min_loan_sizes[currency])
        return self.min_loan_size

    @staticmethod
    def parse_xday_threshold(xday_threshold_str: str) -> tuple[list[float], list[str]]:
        """
        Parses the xdaythreshold config string into rates and days lists.
        """
        rates: list[float] = []
        xdays: list[str] = []
        if xday_threshold_str:
            for pair in xday_threshold_str.split(","):
                try:
                    rate, day = pair.split(":")
                    rates.append(float(rate) / 100)
                    xdays.append(day)
                except (ValueError, TypeError):
                    continue
        return rates, xdays

    def create_lend_offer(
        self, currency: str, amt: str | Decimal, rate: str | float | Decimal, days: str = "2"
    ) -> None:
        """
        Creates a new lending offer on the exchange.
        """
        original_rate = float(rate)
        rate_f = original_rate
        if rate_f > 0.0001:
            rate_f = rate_f - 0.000001  # lend offer just below the competing one
        amt_s = f"{Decimal(amt):.8f}"
        rates, xdays = self.parse_xday_threshold(self.xday_threshold)
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

        if self.config.bot.end_date:
            days_remaining = int(self.data.get_max_duration(self.config.bot.end_date, "order"))
            if days_remaining <= 2:
                print("endDate reached. Bot can no longer lend.\nExiting...")
                if self.log:
                    self.log.log(
                        "The end date has almost been reached and the bot can no longer lend. Exiting."
                    )
                    self.log.log(self.data.stringify_total_lent(self.data.get_total_lent()))
                    self.log.persistStatus()
                exit(0)
            if int(days) > days_remaining:
                days = str(days_remaining)

        if not self.dry_run:
            msg = self.api.create_loan_offer(currency, float(amt_s), int(days), 0, float(rate_f))
            if (
                len(xdays) > 0
                and int(days) == int(xdays[-1])
                and self.config.notifications.notify_xday_threshold
            ):
                text = f"{format_amount_currency(amt_s, currency)} loan placed for {days} days at a rate of {format_rate_pct(rate_f)}"
                if self.log:
                    self.log.notify(text, self.config.notifications.model_dump())  # Adjusted for DI
            if self.log:
                # Pass original_rate to show compete adjustment info
                self.log.offer(amt_s, currency, float(rate_f), days, msg, original_rate)

    def get_frr_or_min_daily_rate(self, cur: str) -> RateCalcInfo:
        """
        Checks the Flash Return Rate of cur against the min daily rate and returns
        detailed rate calculation info.
        """
        if cfg := self.coin_cfg.get(cur):
            min_rate = cfg.min_daily_rate
            frr_as_min = cfg.strategy == Configuration.LendingStrategy.FRR
            # Config values are now percentages (e.g., -10 means -10%)
            frr_d_min = cfg.frr_delta_min
            frr_d_max = cfg.frr_delta_max
        else:
            min_rate = self.default_coin_cfg.min_daily_rate
            frr_as_min = self.default_coin_cfg.strategy == Configuration.LendingStrategy.FRR
            frr_d_min = self.frrdelta_min
            frr_d_max = self.frrdelta_max

        if frr_d_min > frr_d_max:
            frr_d_min, frr_d_max = frr_d_max, frr_d_min

        # Let's use hard coded steps for now
        frr_delta_steps = 5
        frr_delta_step = (frr_d_max - frr_d_min) / frr_delta_steps

        if self.frrdelta_cur_step > frr_delta_steps:
            self.frrdelta_cur_step = 0
        frr_delta_pct = frr_d_min + (frr_delta_step * self.frrdelta_cur_step)
        current_step = self.frrdelta_cur_step + 1  # 1-indexed for display
        self.frrdelta_cur_step += 1

        exchange = self.config.api.exchange
        if hasattr(exchange, "value"):
            exchange = exchange.value
        exchange = str(exchange).upper()

        if exchange == "BITFINEX" and frr_as_min:
            frr_base = Decimal(self.api.get_frr(cur))
            # Apply relative percentage: rate = FRR * (1 + pct/100)
            frr_rate = frr_base * (1 + frr_delta_pct / 100)
            if frr_rate > min_rate:
                return RateCalcInfo(
                    final_rate=frr_rate,
                    min_rate=min_rate,
                    frr_enabled=True,
                    frr_base=frr_base,
                    frr_delta=frr_delta_pct,
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
                    frr_delta=frr_delta_pct,
                    frr_delta_step=current_step,
                    frr_used=False,
                )

        # FRR not enabled or not on Bitfinex
        return RateCalcInfo(
            final_rate=min_rate,
            min_rate=min_rate,
            frr_enabled=False,
        )

    def get_min_daily_rate(self, cur: str) -> Decimal | bool:
        """
        Determines the minimum daily lending rate for a currency.
        """
        rate_info = self.get_frr_or_min_daily_rate(cur)

        # Check if currency is disabled
        if (cfg := self.coin_cfg.get(cur)) and cfg.max_active_amount == 0:
            if cur not in self.max_active_alerted:  # Only alert once per coin.
                self.max_active_alerted[cur] = True
                if self.log:
                    self.log.log(f"[{cur}] Disabled: maxactive=0, skipping")
            return False

        # Generate rate calculation log
        if self.log:
            self._log_rate_calculation(cur, rate_info)

        # Check for Market Analysis suggestion
        if self.analysis and cur in self.config.plugins.market_analysis.analyse_currencies:
            recommended_min = self.analysis.get_rate_suggestion(cur, method=self.analysis_method)
            if rate_info.final_rate < Decimal(str(recommended_min)) and self.log:
                self.log.log(
                    f"[{cur}] Tip: {self.analysis_method} suggests {format_rate_pct(recommended_min)}"
                )

        return rate_info.final_rate

    def _log_rate_calculation(self, cur: str, info: RateCalcInfo) -> None:
        """
        Log rate calculation details in a unified format.
        """
        if not self.log:
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
                self.log.log(
                    f"[{cur}] Rate: FRR {format_rate_pct(info.frr_base)} × "
                    f"{frr_multiplier:.2f} (step {info.frr_delta_step}/5) = "
                    f"{format_rate_pct(info.final_rate)} (> min {format_rate_pct(info.min_rate)}) ✓"
                )
            else:
                # FRR*multiplier <= min_rate, use min_rate
                self.log.log(
                    f"[{cur}] Rate: FRR {format_rate_pct(info.frr_base)} × "
                    f"{frr_multiplier:.2f} (step {info.frr_delta_step}/5) = "
                    f"{format_rate_pct(info.frr_base * frr_multiplier)} (< min {format_rate_pct(info.min_rate)}, using min)"
                )
        else:
            # Non-FRR mode
            self.log.log(f"[{cur}] Rate: min_rate {format_rate_pct(info.min_rate)}")

    def construct_order_books(self, active_cur: str) -> bool | list[dict[str, Any]]:
        """
        Fetches the loan order book from the exchange and structures it.
        """
        # make sure we have a request limit for this currency
        if active_cur not in self.loan_orders_request_limit:
            self.loan_orders_request_limit[active_cur] = self.default_loan_orders_request_limit

        loans = self.api.return_loan_orders(active_cur, self.loan_orders_request_limit[active_cur])
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
            resps.append(resp)

        return resps

    def get_gap_rate(self, active_cur: str, gap: Decimal, order_book: dict[str, Any], cur_total_balance: Decimal, raw: bool = False) -> Decimal:
        """
        Calculates the lending rate at a specific depth (gap) in the order book.
        """
        if active_cur not in self.loan_orders_request_limit:
            self.loan_orders_request_limit[active_cur] = self.default_loan_orders_request_limit

        gap_expected = gap if raw else gap * cur_total_balance / Decimal("100.0")
        gap_sum = Decimal(0)
        i = 0
        while gap_sum < gap_expected:
            if (
                i == len(order_book["volumes"]) - 1
                and len(order_book["volumes"]) == self.loan_orders_request_limit[active_cur]
            ):
                if self.log:
                    self.log.log(
                        f"{active_cur}: Not enough offers in response, adjusting request limit to {self.loan_orders_request_limit[active_cur]}"
                    )
                raise StopIteration
            elif i == len(order_book["volumes"]) - 1:
                return self.max_daily_rate
            gap_sum += Decimal(str(order_book["volumes"][i]))
            i += 1
        return Decimal(str(order_book["rates"][i]))

    def get_cur_spread(self, spread: int, cur_active_bal: Decimal, active_cur: str) -> int:
        """
        Calculates the actual spread (number of orders) possible for a currency.
        """
        cur_spread_lend = int(spread)
        cur_min_loan_size = self.get_min_loan_size(active_cur)
        while cur_active_bal < (cur_spread_lend * cur_min_loan_size):
            cur_spread_lend -= 1
        return max(1, int(cur_spread_lend))

    def construct_orders(
        self, cur: str, cur_active_bal: Decimal, cur_total_balance: Decimal, ticker: Any
    ) -> dict[str, Any]:
        """
        Constructs a list of lend orders based on the configured spread and gap settings.
        """
        if (cfg := self.coin_cfg.get(cur)) and cfg.strategy == Configuration.LendingStrategy.FRR:
            cur_spread = 1
        else:
            cur_spread = self.get_cur_spread(self.spread_lend, cur_active_bal, cur)

        if cur_spread == 1:
            rate_step = Decimal(0)
            bottom_rate = Decimal(0)
        else:
            top_rate, bottom_rate = self.get_gap_mode_rates(
                cur, cur_active_bal, cur_total_balance, ticker
            )
            gap_diff = top_rate - bottom_rate
            rate_step = gap_diff / (cur_spread - 1)

        order_rates = []
        for i in range(cur_spread):
            new_rate = bottom_rate + (rate_step * i)
            order_rates.append(new_rate)

        # Condensing and logic'ing time
        for i, rate in enumerate(order_rates):
            if rate > self.max_daily_rate:
                order_rates[i] = self.max_daily_rate

        new_order_rates = sorted(set(order_rates))
        new_order_amounts = []
        for _ in range(len(new_order_rates)):
            new_amount = self.data.truncate(cur_active_bal / len(new_order_rates), 8)
            new_order_amounts.append(Decimal(str(new_amount)))

        remainder = cur_active_bal - sum(new_order_amounts)
        if remainder > 0:  # If truncating causes remainder, add that to first order.
            new_order_amounts[0] += remainder

        resp = {"amounts": new_order_amounts, "rates": new_order_rates}
        return resp

    def get_gap_mode_rates(
        self, cur: str, cur_active_bal: Decimal, cur_total_balance: Decimal, ticker: Any
    ) -> list[Decimal]:
        """
        Calculates the top and bottom rates based on the configured gap mode.
        """
        gap_mode, gap_bottom, gap_top = (
            self.gap_mode_default,
            self.gap_bottom_default,
            self.gap_top_default,
        )
        use_gap_cfg = False

        books = self.construct_order_books(cur)
        if not books or not isinstance(books, list) or len(books) < 2:
            return [self.max_daily_rate, self.max_daily_rate]

        order_book = books[1]

        if (
            (cfg := self.coin_cfg.get(cur))
            and cfg.gap_mode
            and cfg.gap_bottom is not None
            and cfg.gap_top is not None
        ):
            # Only overwrite default if all three are set
            use_gap_cfg = True
            gap_mode = cfg.gap_mode.value if hasattr(cfg.gap_mode, "value") else str(cfg.gap_mode)
            gap_bottom = cfg.gap_bottom
            gap_top = cfg.gap_top

        gap_mode_lower = str(gap_mode).lower()

        if gap_mode_lower == "rawbtc":
            btc_value = Decimal(1)
            if cur != "BTC":
                for coin in ticker:
                    if coin == f"BTC_{cur.upper()}":
                        btc_value = Decimal(str(ticker[coin]["last"]))
                        break
            bottom_depth = gap_bottom / btc_value  # Converts from BTC to altcoin's value
            bottom_rate = self.get_gap_rate(cur, bottom_depth, order_book, cur_total_balance, True)
            top_depth = gap_top / btc_value
            top_rate = self.get_gap_rate(cur, top_depth, order_book, cur_total_balance, True)
        elif gap_mode_lower == "raw":  # Value stays in altcoin
            bottom_rate = self.get_gap_rate(cur, gap_bottom, order_book, cur_total_balance, True)
            top_rate = self.get_gap_rate(cur, gap_top, order_book, cur_total_balance, True)
        elif gap_mode_lower == "relative":
            bottom_rate = self.get_gap_rate(cur, gap_bottom, order_book, cur_total_balance)
            top_rate = self.get_gap_rate(cur, gap_top, order_book, cur_total_balance)
        else:
            if use_gap_cfg:
                print(f"WARN: Invalid setting for gapMode for [{cur}], using defaults...")
                self.coin_cfg[cur].gap_mode = Configuration.GapMode.RAW_BTC
                self.coin_cfg[cur].gap_bottom = Decimal(10)
                self.coin_cfg[cur].gap_top = Decimal(100)
            else:
                print("WARN: Invalid setting for gapMode, using defaults...")
                self.gap_mode_default = "relative"
                self.gap_bottom_default = Decimal(10)
                self.gap_top_default = Decimal(200)
            return self.get_gap_mode_rates(cur, cur_active_bal, cur_total_balance, ticker)

        return [Decimal(str(top_rate)), Decimal(str(bottom_rate))]

    def cancel_all(self) -> None:
        """
        Cancels all open lending offers for active currencies.
        """
        loan_offers = self.api.return_open_loan_offers()
        available_balances = self.api.return_available_account_balances("lending")
        for cur in loan_offers:
            if cur not in self.config.api.all_currencies:
                continue
            if (cfg := self.coin_cfg.get(cur)) and cfg.max_active_amount == 0:
                # don't cancel disabled coin
                continue
            if self.config.bot.keep_stuck_orders:
                lending_balances = available_balances["lending"]
                if isinstance(lending_balances, dict) and cur in lending_balances:
                    cur_sum = float(available_balances["lending"][cur])
                else:
                    cur_sum = 0.0
                for offer in loan_offers[cur]:
                    cur_sum += float(offer["amount"])
            else:
                cur_sum = float(self.get_min_loan_size(cur)) + 1.0
            if cur_sum >= float(self.get_min_loan_size(cur)):
                for offer in loan_offers[cur]:
                    if not self.dry_run:
                        try:
                            msg = self.api.cancel_loan_offer(cur, offer["id"])
                            if self.log:
                                self.log.cancelOrder(cur, msg)
                        except Exception as ex:
                            if self.log:
                                self.log.log(f"Error canceling loan offer: {ex}")
            else:
                print(f"Not enough {cur} to lend if bot canceled open orders. Not cancelling.")

    def lend_cur(
        self, active_cur: str, total_lent_info: Any, lending_balances: dict[str, str], ticker: Any
    ) -> int:
        """
        Analyzes the market and places lend orders for a specific currency.
        """
        active_cur_total_balance = Decimal(str(lending_balances[active_cur]))
        total_lent = total_lent_info.total_lent
        if active_cur in total_lent:
            active_cur_total_balance += total_lent[active_cur]

        cur_min_daily_rate = self.get_min_daily_rate(active_cur)

        if self.log:
            self.log.updateStatusValue(active_cur, "totalCoins", active_cur_total_balance)

        books = self.construct_order_books(active_cur)
        if not books or not isinstance(books, list) or len(books) < 2 or not cur_min_daily_rate:
            return 0

        demand_book, order_book = books[0], books[1]

        from . import MaxToLend

        active_bal = MaxToLend.amount_to_lend(
            active_cur_total_balance,
            active_cur,
            Decimal(str(lending_balances[active_cur])),
            Decimal(str(order_book["rates"][0])),
        )

        if float(active_bal) >= float(self.get_min_loan_size(active_cur)):
            currency_usable = 1
        else:
            return 0

        orders = self.construct_orders(active_cur, active_bal, active_cur_total_balance, ticker)
        for i in range(len(orders["amounts"])):
            below_min = Decimal(str(orders["rates"][i])) < Decimal(str(cur_min_daily_rate))

            if self.config.bot.hide_coins and below_min:
                if self.log:
                    self.log.log(
                        f"Not lending {active_cur} due to rate below {format_rate_pct(cur_min_daily_rate)} (actual: {format_rate_pct(orders['rates'][i])})"
                    )
                return 0
            elif below_min:
                rate = str(cur_min_daily_rate)
            else:
                rate = orders["rates"][i]

            days = "2"
            if demand_book and float(demand_book["rates"][0]) > self.compete_rate:
                rate = demand_book["rates"][0]
                days = str(demand_book["rangeMax"][0])
                if self.log:
                    self.log.log(
                        f"Competing offer found for {active_cur} at {format_rate_pct(rate)} for {days} days."
                    )

            try:
                self.create_lend_offer(active_cur, orders["amounts"][i], rate, days)
            except Exception as msg:
                if "Amount must be at least " in str(msg):
                    import re

                    results = re.findall(r"[-+]?([0-9]*\.[0-9]+|[0-9]+)", str(msg))
                    for result in results:
                        if result:
                            self.min_loan_sizes[active_cur] = Decimal(result)
                            if self.log:
                                self.log.log(
                                    f"{active_cur}'s min_loan_size has been increased to the detected min: {result}"
                                )
                    return self.lend_cur(active_cur, total_lent_info, lending_balances, ticker)
                else:
                    raise msg

        return currency_usable

    def lend_all(self) -> None:
        """
        Main loop to attempt lending for all currencies with available balance.
        """
        total_lent_info = self.data.get_total_lent()
        total_lent = total_lent_info.total_lent
        lending_balances_data = self.api.return_available_account_balances("lending")
        lending_balances = lending_balances_data.get("lending", {})

        if self.dry_run:
            lending_balances = self.data.get_on_order_balances()

        from . import MaxToLend

        for cur in sorted(total_lent):
            if not lending_balances or cur not in lending_balances:
                MaxToLend.amount_to_lend(total_lent[cur], cur, Decimal(0), Decimal(0))

        usable_currencies = 0
        ticker: dict[str, dict[str, str]] | None = None
        if self.gap_mode_default == "rawbtc":
            ticker = self.api.return_ticker()
        else:
            for cur_name in self.coin_cfg:
                if self.coin_cfg[cur_name].gap_mode == "rawbtc":
                    ticker = self.api.return_ticker()
                    break

        if self.log:
            self.log.log(f"Lending balances: {lending_balances}")

        try:
            if lending_balances:
                for cur in lending_balances:
                    if cur in self.config.api.all_currencies:
                        usable_currencies += self.lend_cur(
                            cur, total_lent_info, lending_balances, ticker
                        )
        except StopIteration:
            self.lend_all()
            return

        self.sleep_time = (
            self.config.bot.period_inactive
            if usable_currencies == 0
            else self.config.bot.period_active
        )

    def transfer_balances(self) -> None:
        """
        Transfers all balances on the included list to Lending.
        """
        if len(self.transferable_currencies) > 0:
            exchange_balances = self.api.return_balances()
            for coin in list(self.transferable_currencies):
                if coin in exchange_balances and Decimal(str(exchange_balances[coin])) > 0:
                    msg = self.api.transfer_balance(
                        coin, float(exchange_balances[coin]), "exchange", "lending"
                    )
                    if self.log:
                        self.log.log(self.log.digestApiMsg(msg))
                        self.log.notify(
                            self.log.digestApiMsg(msg), self.config.notifications.model_dump()
                        )
                if coin not in exchange_balances:
                    print(f"WARN: Incorrect coin entered for transferCurrencies: {coin}")
                    self.transferable_currencies.remove(coin)

    def notify_summary(self, sleep_time_val: float) -> None:
        """
        Sends a summary notification.
        """
        try:
            if self.log:
                self.log.notify(
                    self.data.stringify_total_lent(self.data.get_total_lent()),
                    self.config.notifications.model_dump(),
                )
        except Exception as ex:
            print(f"Error during summary notification: {ex}")
        if self.scheduler:
            self.scheduler.enter(sleep_time_val, 1, self.notify_summary, (sleep_time_val,))

    def notify_new_loans(self, sleep_time_val: float) -> None:
        """
        Checks for newly filled loans and sends notifications.
        """
        try:
            new_provided = self.api.return_active_loans()["provided"]
            if self.loans_provided:

                def get_id_set(loans: list[dict[str, Any]]) -> set[Any]:
                    return {x["id"] for x in loans}

                loans_amount: dict[str, float] = {}
                loans_info: dict[str, dict[str, Any]] = {}
                for loan_id in get_id_set(new_provided) - get_id_set(self.loans_provided):
                    loan = next(x for x in new_provided if x["id"] == loan_id)
                    k = f"c{loan['currency']}r{loan['rate']}d{loan['duration']}"
                    loans_amount[k] = float(loan["amount"]) + loans_amount.get(k, 0.0)
                    loans_info[k] = loan
                for k, amount in loans_amount.items():
                    loan = loans_info[k]
                    text = f"{format_amount_currency(amount, loan['currency'])} loan filled for {loan['duration']} days at a rate of {format_rate_pct(loan['rate'])}"
                    if self.log:
                        self.log.notify(text, self.config.notifications.model_dump())
            self.loans_provided = new_provided
        except Exception as ex:
            print(f"Error during new loans notification: {ex}")
        if self.scheduler:
            self.scheduler.enter(sleep_time_val, 1, self.notify_new_loans, (sleep_time_val,))

    def start_scheduler(self) -> None:
        """
        Starts the scheduler thread for notifications.
        """
        if self.scheduler:
            if self.config.notifications.notify_summary_minutes:
                self.scheduler.enter(
                    10,
                    1,
                    self.notify_summary,
                    (self.config.notifications.notify_summary_minutes * 60,),
                )
            if self.config.notifications.notify_new_loans:
                self.scheduler.enter(20, 1, self.notify_new_loans, (60,))
            if not self.scheduler.empty():
                t = threading.Thread(target=self.scheduler.run)
                t.daemon = True
                t.start()
