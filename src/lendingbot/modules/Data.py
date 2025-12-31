import datetime
import json
import subprocess
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .Logger import Logger


@dataclass
class LentData:
    total_lent: dict[str, Decimal]
    rate_lent: dict[str, Decimal]

    def __iter__(self) -> Iterator[dict[str, Decimal]]:
        """Allow unpacking for legacy compatibility: total, rate = get_total_lent()"""
        yield self.total_lent
        yield self.rate_lent

    def __getitem__(self, index: int) -> dict[str, Decimal]:
        """Allow indexing for legacy compatibility: get_total_lent()[0]"""
        if index == 0:
            return self.total_lent
        if index == 1:
            return self.rate_lent
        raise IndexError("LentData index out of range")


api: Any = None
log: Logger | None = None


def init(api1: Any, log1: Logger) -> None:
    """
    Initialize the Data module.

    Args:
        api1: The exchange API instance.
        log1: The logger instance.
    """
    global api, log
    api = api1
    log = log1


def get_on_order_balances() -> dict[str, Decimal]:
    loan_offers = api.return_open_loan_offers()
    on_order_balances: dict[str, Decimal] = {}
    for cur in loan_offers:
        for offer in loan_offers[cur]:
            on_order_balances[cur] = on_order_balances.get(cur, Decimal(0)) + Decimal(
                offer["amount"]
            )
    return on_order_balances


def get_max_duration(end_date: str, context: str) -> int | str:
    if not end_date:
        return ""
    try:
        now_time = datetime.date.today()
        config_date = [int(x) for x in end_date.split(",")]
        end_time = datetime.date(*config_date)  # format YEAR,MONTH,DAY all ints
        diff_days = (end_time - now_time).days
        if context == "order":
            return diff_days  # Order needs int
        if context == "status":
            return f" - Days Remaining: {diff_days}"  # Status needs string
        return ""
    except Exception as ex:
        msg = str(ex)
        print(f"ERROR: There is something wrong with your endDate option. Error: {msg}")
        exit(1)


def get_total_lent() -> LentData:
    """
    Retrieves the total amount lent for each currency.

    Returns:
        LentData: Object containing total amount lent and total weighted rate per currency.
    """
    crypto_lent = api.return_active_loans()
    total_lent: dict[str, Decimal] = {}
    rate_lent: dict[str, Decimal] = {}
    for item in crypto_lent["provided"]:
        item_float = Decimal(str(item["amount"]))
        item_rate_float = Decimal(str(item["rate"]))
        currency = item["currency"]
        if currency in total_lent:
            total_lent[currency] += item_float
            rate_lent[currency] += item_rate_float * item_float
        else:
            total_lent[currency] = item_float
            rate_lent[currency] = item_rate_float * item_float
    return LentData(total_lent=total_lent, rate_lent=rate_lent)


def timestamp() -> str:
    """
    Returns timestamp in UTC
    """
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")


def stringify_total_lent(lent_data: LentData) -> str:
    """
    Formats the total lent data into a readable string.

    Args:
        lent_data: LentData object.

    Returns:
        A formatted string describing the lent status.
    """
    result = "Lent: "
    if log is None:
        return result
    total_lent = lent_data.total_lent
    rate_lent = lent_data.rate_lent
    for key in sorted(total_lent):
        average_lending_rate = Decimal(rate_lent[key] * 100 / total_lent[key])
        result += f"[{Decimal(total_lent[key]):.4f} {key} @ {average_lending_rate:.4f}%] "
        log.updateStatusValue(key, "lentSum", total_lent[key])
        log.updateStatusValue(key, "averageLendingRate", average_lending_rate)
    return result


def update_conversion_rates(output_currency: str, json_output_enabled: bool) -> None:
    if json_output_enabled and log:
        total_lent = get_total_lent().total_lent
        ticker_response = api.return_ticker()
        output_currency_found = False
        # Set this up now in case we get an exception later and don't have a currency to use
        log.updateOutputCurrency("highestBid", "1")
        log.updateOutputCurrency("currency", "BTC")
        # default output currency is BTC
        if output_currency == "BTC":
            output_currency_found = True

        for couple in ticker_response:
            currencies = couple.split("_")
            ref = currencies[0]
            currency = currencies[1]
            if ref == "BTC" and currency in total_lent:
                log.updateStatusValue(currency, "highestBid", ticker_response[couple]["highestBid"])
                log.updateStatusValue(currency, "couple", couple)
            if not output_currency_found:  # check for output currency
                if ref == "BTC" and currency == output_currency:
                    output_currency_found = True
                    log.updateOutputCurrency(
                        "highestBid", 1 / float(ticker_response[couple]["highestBid"])
                    )
                    log.updateOutputCurrency("currency", output_currency)
                if ref == output_currency and currency == "BTC":
                    output_currency_found = True
                    log.updateOutputCurrency("highestBid", ticker_response[couple]["highestBid"])
                    log.updateOutputCurrency("currency", output_currency)

        url = f"https://blockchain.info/tobtc?currency={output_currency}&value=1"
        if not output_currency_found:  # fetch output currency rate from blockchain.info
            try:
                with urllib.request.urlopen(url) as response:
                    data = response.read()
                    try:
                        highest_bid = json.loads(data)
                        log.updateOutputCurrency("highestBid", 1 / float(highest_bid))
                        log.updateOutputCurrency("currency", output_currency)
                    except ValueError:
                        try:
                            highest_bid_str = data.decode("utf-8")
                            log.updateOutputCurrency("highestBid", 1 / float(highest_bid_str))
                            log.updateOutputCurrency("currency", output_currency)
                        except ValueError:
                            log.log_error("Failed to decode response as plain text or JSON")
            except Exception:
                log.log_error(f"Can't connect to {url} using BTC as the output currency")


def get_lending_currencies() -> list[str]:
    currencies = []
    total_lent = get_total_lent().total_lent
    for cur in total_lent:
        currencies.append(cur)
    lending_balances = api.return_available_account_balances("lending")["lending"]
    for cur in lending_balances:
        currencies.append(cur)
    return list(set(currencies))


def truncate(f: float | Decimal, n: int) -> float:
    """Truncates/pads a float f to n decimal places without rounding"""
    # From https://stackoverflow.com/questions/783897/truncating-floats-in-python
    s = f"{f}"
    if "e" in s or "E" in s:
        return float("{0:.{1}f}".format(float(f), n))
    i, _p, d = s.partition(".")
    return float(".".join([i, (d + "0" * n)[:n]]))


def get_bot_version() -> str:
    """Gets the git commit count as version for master."""
    try:
        output = subprocess.check_output(["git", "rev-list", "--count", "HEAD"])
        return output.decode("utf-8").strip()
    except Exception:
        return "3.0.0"
