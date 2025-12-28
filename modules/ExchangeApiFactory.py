'''
Factory to instanciate right API class
'''

from modules.Bitfinex import Bitfinex
from modules.Poloniex import Poloniex


EXCHANGE = {'POLONIEX': Poloniex, 'BITFINEX': Bitfinex}


class ExchangeApiFactory:
    @staticmethod
    def createApi(exchange, cfg, log):
        if exchange not in EXCHANGE:
            raise Exception("Invalid exchange: " + exchange)
        return EXCHANGE[exchange](cfg, log)
