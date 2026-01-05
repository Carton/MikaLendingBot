"""
Factory to instantiate right API class
"""

from typing import Any

from . import Configuration
from .Bitfinex import Bitfinex
from .ExchangeApi import ExchangeApi
from .Poloniex import Poloniex


EXCHANGE: dict[str, type[ExchangeApi]] = {"POLONIEX": Poloniex, "BITFINEX": Bitfinex}


class ExchangeApiFactory:
    @staticmethod
    def createApi(exchange: str, cfg: Configuration.RootConfig, log: Any) -> ExchangeApi:
        exchange = exchange.upper()
        if exchange not in EXCHANGE:
            raise Exception(f"Invalid exchange: {exchange}")
        return EXCHANGE[exchange](cfg, log)
