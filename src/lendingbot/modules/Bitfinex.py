import base64
import hashlib
import hmac
import json
import threading
import time
from typing import Any

import requests

from .Bitfinex2Poloniex import Bitfinex2Poloniex
from .ExchangeApi import ApiError, ExchangeApi
from .RingBuffer import RingBuffer


class Bitfinex(ExchangeApi):
    def __init__(self, cfg: Any, log: Any) -> None:
        super().__init__(cfg, log)
        self.cfg = cfg
        self.log = log
        self.lock = threading.RLock()
        self.req_per_period = 1
        self.default_req_period = 5000.0  # milliseconds, 1000 = 60/min
        self.req_period = self.default_req_period
        self.req_time_log: Any = RingBuffer(self.req_per_period)
        self.url = "https://api.bitfinex.com"
        self.key = self.cfg.get("API", "apikey", None)
        self.secret = self.cfg.get("API", "secret", None)
        self.apiVersion = "v1"
        self.symbols: list[str] = []
        self.ticker: dict[str, dict[str, Any]] = {}
        self.tickerTime = 0
        self.baseCurrencies = ["USD", "BTC", "ETH"]
        self.all_currencies = self.cfg.get_all_currencies()
        self.usedCurrencies: list[str] = []
        self.timeout = int(self.cfg.get("BOT", "timeout", 30, 1, 180))
        self.api_debug_log = self.cfg.getboolean("BOT", "api_debug_log")
        # Initialize usedCurrencies
        _ = self.return_available_account_balances("lending")

    @property
    def _nonce(self) -> str:
        """
        Returns a nonce
        Used in authentication
        """
        return str(int(time.time() * 100000))

    def limit_request_rate(self) -> None:
        super().limit_request_rate()

    def increase_request_timer(self) -> None:
        super().increase_request_timer()

    def decrease_request_timer(self) -> None:
        super().decrease_request_timer()

    def reset_request_timer(self) -> None:
        super().reset_request_timer()

    def _sign_payload(self, payload: dict[str, Any]) -> dict[str, str]:
        j = json.dumps(payload)
        data = base64.standard_b64encode(j.encode("utf8"))

        h = hmac.new(self.secret.encode("utf8"), data, hashlib.sha384)
        signature = h.hexdigest()
        return {
            "X-BFX-APIKEY": self.key,
            "X-BFX-SIGNATURE": signature,
            "X-BFX-PAYLOAD": data.decode("utf-8"),
            "Connection": "close",
        }

    def debug_log(self, msg: str) -> None:
        if self.api_debug_log:
            self.log.log(msg)

    def _request(
        self,
        method: str,
        request_path: str,
        payload: dict[str, str] | None = None,
        verify: bool = True,
    ) -> Any:
        try:
            url = f"{self.url}{request_path}"
            if method == "get":
                r = requests.get(url, timeout=self.timeout, headers={"Connection": "close"})
                self.debug_log(f"GET: {url}")
            else:
                r = requests.post(url, headers=payload, verify=verify, timeout=self.timeout)
                self.debug_log(f"POST: {url} headers={payload}")

            if r.status_code != 200:
                if r.status_code == 502 or r.status_code in range(520, 527):
                    raise ApiError(
                        f"API Error {r.status_code}: The web server reported a bad gateway or gateway timeout error."
                    )
                elif r.status_code == 429:
                    self.increase_request_timer()
                raise ApiError(f"API Error {r.status_code}: {r.text}")

            # Check in case something has gone wrong and the timer is too big
            self.reset_request_timer()
            self.debug_log(f"Response: {r.text}")
            return r.json()

        except Exception as ex:
            msg = getattr(ex, "message", str(ex))
            ex_msg = f"{msg} Requesting {self.url + request_path}"
            raise ApiError(ex_msg) from ex

    @ExchangeApi.synchronized
    def _post(
        self, command: str, payload: dict[str, Any] | None = None, verify: bool = True
    ) -> Any:
        # keep the request per minute limit
        self.limit_request_rate()

        payload = payload or {}
        payload["request"] = f"/{self.apiVersion}/{command}"
        payload["nonce"] = self._nonce
        signed_payload = self._sign_payload(payload)
        return self._request("post", str(payload["request"]), signed_payload, verify)

    @ExchangeApi.synchronized
    def _get(self, command: str, api_version: str | None = None) -> Any:
        # keep the request per minute limit
        self.limit_request_rate()

        if api_version is None:
            api_version = self.apiVersion
        request_path = f"/{api_version}/{command}"
        return self._request("get", request_path)

    def _get_symbols(self) -> list[str]:
        """
        A list of symbol names. Currently "btcusd", "ltcusd", "ltcbtc", ...
        https://bitfinex.readme.io/v1/reference#rest-public-symbols
        """
        if len(self.symbols) == 0:
            bfx_resp = self._get("symbols")
            for symbol in bfx_resp:
                base = symbol[3:].upper()
                curr = symbol[:3].upper()
                if (base in self.baseCurrencies) and (curr in self.all_currencies):
                    self.symbols.append(symbol)

        return self.symbols

    def return_open_loan_offers(self) -> dict[str, list[dict[str, Any]]]:
        """
        Returns active loan offers
        https://bitfinex.readme.io/v1/reference#rest-auth-offers
        """
        bfx_resp = self._post("offers")
        resp = Bitfinex2Poloniex.convertOpenLoanOffers(bfx_resp)

        return resp

    def return_loan_orders(self, currency: str, limit: int = 0) -> dict[str, list[dict[str, Any]]]:
        command = f"lendbook/{currency}?limit_asks={limit}&limit_bids={limit}"
        bfx_resp = self._get(command)
        resp = Bitfinex2Poloniex.convertLoanOrders(bfx_resp)

        return resp

    def return_active_loans(self) -> dict[str, list[dict[str, Any]]]:
        """
        Returns own active loan offers
        https://bitfinex.readme.io/v1/reference#rest-auth-offers
        """
        bfx_resp = self._post("credits")
        resp = Bitfinex2Poloniex.convertActiveLoans(bfx_resp)

        return resp

    def return_ticker(self) -> dict[str, dict[str, str]]:
        """
        The ticker is a high level overview of the state of the market
        https://bitfinex.readme.io/v1/reference#rest-public-ticker
        """
        t = int(time.time())
        if t - self.tickerTime < 60:
            return self.ticker

        set_ticker_time = True

        for symbol in self._get_symbols():
            base = symbol[3:].upper()
            curr = symbol[:3].upper()
            if (base in self.baseCurrencies) and (curr == "BTC" or curr in self.usedCurrencies):
                couple = f"{base}_{curr}"
                couple_reverse = f"{curr}_{base}"

                try:
                    ticker = self._get(f"pubticker/{symbol}")

                    if isinstance(ticker, dict) and "message" in ticker:
                        raise ApiError(f"Error: {ticker['message']} ({symbol})")

                    self.ticker[couple] = {
                        "last": ticker["last_price"],
                        "lowestAsk": ticker["ask"],
                        "highestBid": ticker["bid"],
                        "percentChange": "",
                        "baseVolume": str(float(ticker["volume"]) * float(ticker["mid"])),
                        "quoteVolume": ticker["volume"],
                    }
                    self.ticker[couple_reverse] = {
                        "last": str(1 / float(self.ticker[couple]["last"])),
                        "lowestAsk": str(1 / float(self.ticker[couple]["lowestAsk"])),
                        "highestBid": str(1 / float(self.ticker[couple]["highestBid"])),
                    }

                except Exception as ex:
                    msg = getattr(ex, "message", str(ex))
                    self.log.log_error(
                        f"Error retrieving ticker for {symbol}: {msg}. Continue with next currency."
                    )
                    set_ticker_time = False
                    continue

        if set_ticker_time and len(self.ticker) > 2:  # USD_BTC and BTC_USD are always in
            self.tickerTime = t

        return self.ticker

    def return_available_account_balances(self, account: str) -> dict[str, dict[str, str]]:
        """
        Returns own balances sorted by account
        https://bitfinex.readme.io/v1/reference#rest-auth-wallet-balances
        """
        bfx_resp = self._post("balances")
        balances = Bitfinex2Poloniex.convertAccountBalances(bfx_resp, account)

        if "lending" in balances:
            for curr in balances["lending"]:
                if curr not in self.usedCurrencies:
                    self.usedCurrencies.append(curr)

        return balances

    def cancel_loan_offer(self, _currency: str, order_number: int) -> dict[str, Any]:
        """
        Cancels an offer
        https://bitfinex.readme.io/v1/reference#rest-auth-cancel-offer
        """
        payload = {
            "offer_id": order_number,
        }

        bfx_resp = self._post("offer/cancel", payload)

        success = 0
        message = ""
        try:
            if bfx_resp["id"] == order_number:
                success = 1
                message = "Loan offer canceled ({:.4f} @ {:.4f}%).".format(
                    float(bfx_resp["remaining_amount"]), float(bfx_resp["rate"]) / 365
                )
        except Exception as e:
            message = f"Error canceling offer: {e}"
            success = 0

        return {"success": success, "message": message}

    def create_loan_offer(
        self,
        currency: str,
        amount: float,
        duration: int,
        _auto_renew: int,
        lending_rate: float,
    ) -> dict[str, Any]:
        """
        Creates a loan offer for a given currency.
        https://bitfinex.readme.io/v1/reference#rest-auth-new-offer
        """

        payload = {
            "currency": currency,
            "amount": str(amount),
            "rate": str(round(float(lending_rate), 10) * 36500),
            "period": int(duration),
            "direction": "lend",
        }

        try:
            bfx_resp = self._post("offer/new", payload)
            plx_resp = {"success": 0, "message": "Error", "orderId": 0}
            if bfx_resp.get("id"):
                plx_resp["orderId"] = bfx_resp["id"]
                plx_resp["success"] = 1
                plx_resp["message"] = "Loan order placed."
            return plx_resp

        except Exception as e:
            msg = str(e)
            if "Invalid offer: incorrect amount, minimum is 50" in msg:
                usd_min = 50.0
                cur_min = float(usd_min)
                if currency != "USD":
                    ticker = self.return_ticker()
                    if currency == "EUR":
                        cur_min = (
                            usd_min
                            / float(ticker["USD_BTC"]["lowestAsk"])
                            * float(ticker["EUR_BTC"]["lowestAsk"])
                        )
                    else:
                        cur_min = usd_min / float(ticker["USD_" + currency]["lowestAsk"])

                raise ApiError(
                    f"Error create_loan_offer: Amount must be at least {cur_min} {currency}"
                ) from e
            else:
                raise e

    def return_balances(self) -> dict[str, str]:
        """
        Returns balances of exchange wallet
        https://bitfinex.readme.io/v1/reference#rest-auth-wallet-balances
        """
        balances = self.return_available_account_balances("exchange")
        return_dict = dict.fromkeys(self.cfg.get_all_currencies(), "0.00000000")
        if "exchange" in balances:
            return_dict.update(balances["exchange"])
        return return_dict

    def transfer_balance(
        self, currency: str, amount: float, from_account: str, to_account: str
    ) -> dict[str, Any]:
        """
        Transfers values from one account/wallet to another
        https://bitfinex.readme.io/v1/reference#rest-auth-transfer-between-wallets
        """
        account_map = {"margin": "trading", "lending": "deposit", "exchange": "exchange"}
        payload = {
            "currency": currency,
            "amount": amount,
            "walletfrom": account_map[from_account],
            "walletto": account_map[to_account],
        }

        bfx_resp = self._post("transfer", payload)
        plx_resp = {
            "status": 1 if bfx_resp[0]["status"] == "success" else 0,
            "message": bfx_resp[0]["message"],
        }

        return plx_resp

    def return_lending_history(
        self, start: int, stop: int, limit: int = 500
    ) -> list[dict[str, Any]]:
        """
        Retrieves balance ledger entries. Search funding payments in it and returns
        it as history.
        https://bitfinex.readme.io/v1/reference#rest-auth-balance-history
        """
        history = []
        all_currencies = self.cfg.get_all_currencies()
        for curr in all_currencies:
            payload = {
                "currency": curr,
                "since": str(start),
                "until": str(stop),
                "limit": limit,
                "wallet": "deposit",
            }
            bfx_resp = self._post("history", payload)
            for entry in bfx_resp:
                if "Margin Funding Payment" in entry["description"]:
                    amount = float(entry["amount"])
                    history.append(
                        {
                            "id": int(float(entry["timestamp"])),
                            "currency": curr,
                            "rate": "0.0",
                            "amount": "0.0",
                            "duration": "0.0",
                            "interest": str(amount / 0.85),
                            "fee": str(amount - amount / 0.85),
                            "earned": str(amount),
                            "open": Bitfinex2Poloniex.convertTimestamp(entry["timestamp"]),
                            "close": Bitfinex2Poloniex.convertTimestamp(entry["timestamp"]),
                        }
                    )

        return history

    def get_frr(self, currency: str) -> float:
        """
        Retrieves the flash return rate for the given currency
        https://bitfinex.readme.io/v2/reference#rest-public-platform-status
        """
        command = f"tickers?symbols=f{currency}"
        resp = self._get(command, "v2")
        return float(resp[0][1])
