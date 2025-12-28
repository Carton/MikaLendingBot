"""
Factory to instantiate right API class
"""

from typing import Any

from .Bitfinex import Bitfinex
from .ExchangeApi import ExchangeApi
from .Poloniex import Poloniex


EXCHANGE: dict[str, type[ExchangeApi]] = {"POLONIEX": Poloniex, "BITFINEX": Bitfinex}


class ExchangeApiFactory:
    @staticmethod
    def createApi(exchange: str, cfg: Any, log: Any) -> ExchangeApi:
        if exchange not in EXCHANGE:
            raise Exception(f"Invalid exchange: {exchange}")
        return EXCHANGE[exchange](cfg, log)
