"""
Exchange API Base class
"""

import abc
import calendar
import time
from collections.abc import Callable
from typing import Any, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


class ExchangeApi(abc.ABC):
    def __str__(self) -> str:
        return self.__class__.__name__.upper()

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def create_time_stamp(datestr: str, formatting: str = "%Y-%m-%d %H:%M:%S") -> int:
        return calendar.timegm(time.strptime(datestr, formatting))

    @staticmethod
    def synchronized(method: F) -> F:
        """Work with instance method only !!!"""

        def new_method(self: Any, *arg: Any, **kws: Any) -> Any:
            with self.lock:
                return method(self, *arg, **kws)

        return new_method  # type: ignore[return-value]

    @abc.abstractmethod
    def __init__(self, cfg: Any, log: Any) -> None:
        """
        Constructor
        """
        self.req_time_log: Any = []
        self.req_per_period: int = 0
        self.req_period: float = 0
        self.default_req_period: float = 0

    @abc.abstractmethod
    def limit_request_rate(self) -> None:
        now = time.time() * 1000  # milliseconds
        # Start throttling only when the queue is full
        if len(self.req_time_log) == self.req_per_period:
            time_since_oldest_req = now - self.req_time_log[0]
            if time_since_oldest_req < self.req_period:
                sleep_time = (self.req_period - time_since_oldest_req) / 1000
                self.req_time_log.append(now + self.req_period - time_since_oldest_req)
                time.sleep(sleep_time)
                return

        self.req_time_log.append(now)

    @abc.abstractmethod
    def increase_request_timer(self) -> None:
        if self.req_period <= self.default_req_period * 3.0:
            self.req_period += 500

    @abc.abstractmethod
    def decrease_request_timer(self) -> None:
        if self.req_period > self.default_req_period:
            self.req_period -= 1

    @abc.abstractmethod
    def reset_request_timer(self) -> None:
        if self.req_period >= self.default_req_period * 1.5:
            self.req_period = self.default_req_period

    @abc.abstractmethod
    def return_ticker(self) -> dict[str, dict[str, str]]:
        """
        Returns the ticker for all markets.
        """

    @abc.abstractmethod
    def return_balances(self) -> dict[str, str]:
        """
        Returns available exchange balances.
        Sample output:
        {"BTC":"0.59098578","LTC":"3.31117268", ... }
        """

    @abc.abstractmethod
    def return_available_account_balances(self, account: str) -> dict[str, dict[str, str]]:
        """
        Returns balances sorted by account. You may optionally specify the
        "account" POST parameter if you wish to fetch only the balances of one
        account.

        Sample output:
        {"exchange":{"BTC":"1.19042859","BTM":"386.52379392","CHA":"0.50000000",
        "DASH":"120.00000000","STR":"3205.32958001", "VNL":"9673.22570147"},
        "margin":{"BTC":"3.90015637","DASH":"250.00238240",
        "XMR":"497.12028113"},
        "lending":{"DASH":"0.01174765","LTC":"11.99936230"}}
        """

    @abc.abstractmethod
    def return_lending_history(
        self, start: int, stop: int, limit: int = 500
    ) -> list[dict[str, Any]]:
        """
        Returns lending history within a time range specified by the "start" and
        "end" POST parameters as UNIX timestamps. "limit" may also be specified
        to limit the number of rows returned. Sample output:

        [{ "id": 175589553, "currency": "BTC", "rate": "0.00057400", "amount": "0.04374404",
         "duration": "0.47610000", "interest": "0.00001196",
         "fee": "-0.00000179", "earned": "0.00001017", "open": "2016-09-28 06:47:26",
         "close": "2016-09-28 18:13:03" }]
        """

    @abc.abstractmethod
    def return_loan_orders(self, currency: str, limit: int = 0) -> dict[str, list[dict[str, Any]]]:
        """
        Returns the list of loan offers and demands for a given currency,
        specified by the "currency". Sample output:

        {"offers":[{"rate":"0.00200000","amount":"64.66305732","rangeMin":2,"rangeMax":8}, ... ],
         "demands":[{"rate":"0.00170000","amount":"26.54848841","rangeMin":2,"rangeMax":2}, ... ]}
        """

    @abc.abstractmethod
    def return_open_loan_offers(self) -> dict[str, list[dict[str, Any]]]:
        """
        Returns own open loan offers for each currency
        """

    @abc.abstractmethod
    def return_active_loans(self) -> dict[str, list[dict[str, Any]]]:
        """
        Returns your active loans for each currency. Sample output:

        {"provided":[{"id":75073,"currency":"LTC","rate":"0.00020000","amount":"0.72234880","range":2,
        "autoRenew":0,"date":"2015-05-10 23:45:05","fees":"0.00006000"},
        {"id":74961,"currency":"LTC","rate":"0.00002000","amount":"4.43860711","range":2,
        "autoRenew":0,"date":"2015-05-10 23:45:05","fees":"0.00006000"}],
        "used":[{"id":75238,"currency":"BTC","rate":"0.00020000","amount":"0.04843834","range":2,
        "date":"2015-05-10 23:51:12","fees":"-0.00000001"}]}
        """

    @abc.abstractmethod
    def cancel_loan_offer(self, currency: str, order_number: int) -> dict[str, Any]:
        """
        Cancels a loan offer specified by the "orderNumber"
        """

    @abc.abstractmethod
    def create_loan_offer(
        self, currency: str, amount: float, duration: int, auto_renew: int, lending_rate: float
    ) -> dict[str, Any]:
        """
        Creates a loan offer for a given currency.
        """

    @abc.abstractmethod
    def transfer_balance(
        self, currency: str, amount: float, from_account: str, to_account: str
    ) -> dict[str, Any]:
        """
        Transfers values from one account/wallet to another
        """


class ApiError(Exception):
    pass
