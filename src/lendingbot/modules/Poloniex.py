import hashlib
import hmac
import socket
import threading
import time
import urllib.parse
from collections import deque
from typing import Any, cast

import requests

from . import Configuration as Config
from .ExchangeApi import ApiError, ExchangeApi


def post_process(before: dict[str, Any]) -> dict[str, Any]:
    after = before

    # Add timestamps if there isn't one but is a datetime
    if "return" in after and isinstance(after["return"], list):
        for x in range(len(after["return"])):
            item = after["return"][x]
            if isinstance(item, dict) and "datetime" in item and "timestamp" not in item:
                item["timestamp"] = float(ExchangeApi.create_time_stamp(item["datetime"]))

    return after


class Poloniex(ExchangeApi):
    def __init__(self, cfg: Any, log: Any) -> None:
        super().__init__(cfg, log)
        self.cfg = cfg
        self.log = log
        self.APIKey = self.cfg.get("API", "apikey", None)
        self.Secret = self.cfg.get("API", "secret", None)
        self.req_per_period = 6
        self.default_req_period = 1000  # milliseconds
        self.req_period = float(self.default_req_period)
        self.req_time_log: deque[float] = deque(maxlen=self.req_per_period)
        self.lock = threading.RLock()
        socket.setdefaulttimeout(int(Config.get("BOT", "timeout", 30, 1, 180)))
        self.api_debug_log = self.cfg.getboolean("BOT", "api_debug_log")

    def limit_request_rate(self) -> None:
        super().limit_request_rate()

    def increase_request_timer(self) -> None:
        super().increase_request_timer()

    def decrease_request_timer(self) -> None:
        super().decrease_request_timer()

    def reset_request_timer(self) -> None:
        super().reset_request_timer()

    @ExchangeApi.synchronized
    def api_query(self, command: str, req: dict[str, Any] | None = None) -> Any:
        # keep the 6 request per sec limit
        self.limit_request_rate()

        if req is None:
            req = {}

        def _handle_response(r: requests.Response) -> Any:
            try:
                resp_data = r.json()
            except ValueError:
                raise ApiError(f"Failed to decode JSON response: {r.text}") from None

            if isinstance(resp_data, dict) and "error" in resp_data:
                raise ApiError(resp_data["error"])
            return resp_data

        try:
            headers = {"Connection": "close"}
            timeout = int(Config.get("BOT", "timeout", 30, 1, 180))

            if command in ("returnTicker", "return24hVolume"):
                url = f"https://poloniex.com/public?command={command}"
                r = requests.get(url, headers=headers, timeout=timeout)
                return _handle_response(r)
            elif command == "returnOrderBook":
                url = f"https://poloniex.com/public?command={command}&currencyPair={req['currencyPair']}"
                r = requests.get(url, headers=headers, timeout=timeout)
                return _handle_response(r)
            elif command == "returnMarketTradeHistory":
                url = f"https://poloniex.com/public?command=returnTradeHistory&currencyPair={req['currencyPair']}"
                r = requests.get(url, headers=headers, timeout=timeout)
                return _handle_response(r)
            elif command == "returnLoanOrders":
                url = f"https://poloniex.com/public?command=returnLoanOrders&currency={req['currency']}"
                if req.get("limit", 0) > 0:
                    url += f"&limit={req['limit']}"
                r = requests.get(url, headers=headers, timeout=timeout)
                return _handle_response(r)
            else:
                req["command"] = command
                req["nonce"] = int(time.time() * 1000)
                post_data_str = urllib.parse.urlencode(req)
                sign = hmac.new(
                    self.Secret.encode("utf-8"), post_data_str.encode("utf-8"), hashlib.sha512
                ).hexdigest()

                headers.update({"Sign": sign, "Key": self.APIKey})
                r = requests.post(
                    "https://poloniex.com/tradingApi", data=req, headers=headers, timeout=timeout
                )
                json_ret = _handle_response(r)
                return post_process(json_ret)

            # Check in case something has gone wrong and the timer is too big
            self.reset_request_timer()

        except requests.HTTPError as ex:
            raw_polo_response = ex.response.text
            try:
                data = ex.response.json()
                polo_error_msg = data["error"]
            except Exception:
                code = ex.response.status_code
                if code == 502 or code in range(520, 527):
                    polo_error_msg = f"API Error {code}: The web server reported a bad gateway or gateway timeout error."
                elif code == 429:
                    self.increase_request_timer()
                    polo_error_msg = "Rate limit exceeded (429)"
                else:
                    polo_error_msg = raw_polo_response

            ex_msg = f"{ex} Requesting {command}. Poloniex reports: '{polo_error_msg}'"
            raise ApiError(ex_msg) from ex
        except Exception as ex:
            ex_msg = f"{ex} Requesting {command}"
            raise ApiError(ex_msg) from ex

    def return_ticker(self) -> dict[str, dict[str, str]]:
        return cast("dict[str, dict[str, str]]", self.api_query("returnTicker"))

    def return24h_volume(self) -> dict[str, Any]:
        return cast("dict[str, Any]", self.api_query("return24hVolume"))

    def return_order_book(self, currency_pair: str) -> dict[str, Any]:
        return cast(
            "dict[str, Any]", self.api_query("returnOrderBook", {"currencyPair": currency_pair})
        )

    def return_market_trade_history(self, currency_pair: str) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.api_query("returnMarketTradeHistory", {"currencyPair": currency_pair}),
        )

    def transfer_balance(
        self, currency: str, amount: float, from_account: str, to_account: str
    ) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query(
                "transferBalance",
                {
                    "currency": currency,
                    "amount": amount,
                    "fromAccount": from_account,
                    "toAccount": to_account,
                },
            ),
        )

    def return_balances(self) -> dict[str, str]:
        return cast("dict[str, str]", self.api_query("returnBalances"))

    def return_available_account_balances(self, account: str) -> dict[str, dict[str, str]]:
        balances = self.api_query("returnAvailableAccountBalances", {"account": account})
        if isinstance(balances, list):  # empty dict returns a list
            balances = {}
        return cast("dict[str, dict[str, str]]", balances)

    def return_open_orders(self, currency_pair: str) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.api_query("returnOpenOrders", {"currencyPair": currency_pair}),
        )

    def return_open_loan_offers(self) -> dict[str, list[dict[str, Any]]]:
        loan_offers = self.api_query("returnOpenLoanOffers")
        if isinstance(loan_offers, list):  # empty dict returns a list
            loan_offers = {}
        return cast("dict[str, list[dict[str, Any]]]", loan_offers)

    def return_active_loans(self) -> dict[str, list[dict[str, Any]]]:
        return cast("dict[str, list[dict[str, Any]]]", self.api_query("returnActiveLoans"))

    def return_lending_history(
        self, start: int, stop: int, limit: int = 500
    ) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.api_query("returnLendingHistory", {"start": start, "end": stop, "limit": limit}),
        )

    def return_trade_history(self, currency_pair: str) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self.api_query("returnTradeHistory", {"currencyPair": currency_pair}),
        )

    def buy(self, currency_pair: str, rate: float, amount: float) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query("buy", {"currencyPair": currency_pair, "rate": rate, "amount": amount}),
        )

    def sell(self, currency_pair: str, rate: float, amount: float) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query("sell", {"currencyPair": currency_pair, "rate": rate, "amount": amount}),
        )

    def create_loan_offer(
        self, currency: str, amount: float, duration: int, auto_renew: int, lending_rate: float
    ) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query(
                "createLoanOffer",
                {
                    "currency": currency,
                    "amount": amount,
                    "duration": duration,
                    "autoRenew": auto_renew,
                    "lendingRate": lending_rate,
                },
            ),
        )

    def cancel(self, currency_pair: str, order_number: int) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query(
                "cancelOrder", {"currencyPair": currency_pair, "orderNumber": order_number}
            ),
        )

    def cancel_loan_offer(self, currency: str, order_number: int) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query("cancelLoanOffer", {"currency": currency, "orderNumber": order_number}),
        )

    def withdraw(self, currency: str, amount: float, address: str) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            self.api_query(
                "withdraw", {"currency": currency, "amount": amount, "address": address}
            ),
        )

    def return_loan_orders(self, currency: str, limit: int = 0) -> dict[str, list[dict[str, Any]]]:
        return cast(
            "dict[str, list[dict[str, Any]]]",
            self.api_query("returnLoanOrders", {"currency": currency, "limit": limit}),
        )

    def toggle_auto_renew(self, order_number: int) -> dict[str, Any]:
        return cast(
            "dict[str, Any]", self.api_query("toggleAutoRenew", {"orderNumber": order_number})
        )
