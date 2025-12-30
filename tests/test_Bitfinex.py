import base64
import json
import re
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.ExchangeApi import ApiError


@pytest.fixture
def mock_cfg():
    cfg = MagicMock()

    def cfg_get_side_effect(cat, opt, default=None, *args, **kwargs):
        mapping = {
            ("API", "apikey"): "test_key",
            ("API", "secret"): "test_secret",
            ("BOT", "timeout"): "30",
            ("BOT", "api_debug_log"): "False",
        }
        return mapping.get((cat, opt), default)

    cfg.get.side_effect = cfg_get_side_effect
    cfg.getboolean.return_value = False
    cfg.get_all_currencies.return_value = ["BTC", "ETH", "USD"]
    return cfg


@pytest.fixture
def mock_log():
    return MagicMock()


@pytest.fixture
def bitfinex_api(mock_cfg, mock_log):
    with patch.object(Bitfinex, "return_available_account_balances", return_value={}):
        api = Bitfinex(mock_cfg, mock_log)
    return api


# --- Basic Unit Tests ---


def test_nonce(bitfinex_api):
    nonce1 = bitfinex_api._nonce
    time.sleep(0.001)
    nonce2 = bitfinex_api._nonce
    assert int(nonce2) > int(nonce1)


def test_sign_payload(bitfinex_api):
    payload = {"request": "/v1/balances", "nonce": "12345"}
    signed = bitfinex_api._sign_payload(payload)
    assert signed["X-BFX-APIKEY"] == "test_key"
    decoded_payload = json.loads(base64.b64decode(signed["X-BFX-PAYLOAD"]).decode("utf-8"))
    assert decoded_payload == payload


@patch("requests.get")
def test_request_get_success(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}
    mock_response.text = '{"key": "value"}'
    mock_get.return_value = mock_response
    result = bitfinex_api._request("get", "/v1/test")
    assert result == {"key": "value"}


@patch("requests.post")
def test_request_post_success(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}
    mock_response.text = '{"key": "value"}'
    mock_post.return_value = mock_response
    result = bitfinex_api._request("post", "/v1/test", payload={"X-BFX-APIKEY": "test"})
    assert result == {"key": "value"}


@patch("requests.get")
def test_request_error_429(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_get.return_value = mock_response
    with patch.object(bitfinex_api, "increase_request_timer") as mock_increase:
        with pytest.raises(ApiError, match="API Error 429"):
            bitfinex_api._request("get", "/v1/test")
        mock_increase.assert_called_once()


@patch("requests.get")
def test_request_error_502(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_response.text = "Bad Gateway"
    mock_get.return_value = mock_response
    with pytest.raises(ApiError, match="bad gateway"):
        bitfinex_api._request("get", "/v1/test")


@patch("requests.get")
def test_get_symbols(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["btcusd", "ethusd", "ltcusd"]
    mock_response.text = json.dumps(mock_response.json.return_value)
    mock_get.return_value = mock_response
    bitfinex_api.baseCurrencies = ["USD", "BTC"]
    symbols = bitfinex_api._get_symbols()
    assert "btcusd" in symbols
    assert "ethusd" in symbols
    assert "ltcusd" not in symbols


@patch("requests.get")
def test_return_loan_orders(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"asks": [], "bids": []}
    mock_response.text = "{}"
    mock_get.return_value = mock_response
    with patch(
        "lendingbot.modules.Bitfinex2Poloniex.Bitfinex2Poloniex.convertLoanOrders"
    ) as mock_conv:
        mock_conv.return_value = {"asks": "converted"}
        res = bitfinex_api.return_loan_orders("BTC", limit=5)
        assert res == {"asks": "converted"}


@patch("requests.get")
def test_return_ticker(mock_get, bitfinex_api):
    bitfinex_api.symbols = ["btcusd", "ethusd"]
    bitfinex_api.usedCurrencies = ["BTC", "ETH"]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "last_price": "50000.0",
        "ask": "50001.0",
        "bid": "49999.0",
        "volume": "100.0",
        "mid": "50000.0",
    }
    mock_get.return_value = mock_response
    ticker = bitfinex_api.return_ticker()
    assert "USD_BTC" in ticker
    assert "BTC_USD" in ticker
    assert bitfinex_api.tickerTime > 0


@patch("requests.post")
def test_cancel_loan_offer_success(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 12345, "remaining_amount": "10.0", "rate": "365.0"}
    mock_post.return_value = mock_response
    res = bitfinex_api.cancel_loan_offer("BTC", 12345)
    assert res["success"] == 1


@patch("requests.post")
def test_cancel_loan_offer_exception(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # No "id" key
    mock_post.return_value = mock_response
    res = bitfinex_api.cancel_loan_offer("BTC", 123)
    assert res["success"] == 0
    assert "Error canceling offer" in res["message"]


@patch("requests.post")
def test_create_loan_offer_success(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 67890}
    mock_post.return_value = mock_response
    res = bitfinex_api.create_loan_offer("BTC", 10.0, 2, 0, 0.01)
    assert res["success"] == 1
    assert res["orderId"] == 67890


@patch("requests.post")
def test_create_loan_offer_min_amount_error(mock_post, bitfinex_api):
    with patch.object(
        bitfinex_api,
        "_request",
        side_effect=ApiError("Invalid offer: incorrect amount, minimum is 50"),
    ):
        bitfinex_api.ticker = {"USD_BTC": {"lowestAsk": "50000.0"}}
        bitfinex_api.tickerTime = 10000000000
        with pytest.raises(ApiError, match=re.escape("Amount must be at least 0.001 BTC")):
            bitfinex_api.create_loan_offer("BTC", 0.0001, 2, 0, 0.01)


@patch("requests.post")
def test_transfer_balance(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"status": "success", "message": "Transfer completed"}]
    mock_post.return_value = mock_response
    res = bitfinex_api.transfer_balance("BTC", 1.0, "exchange", "lending")
    assert res["status"] == 1


@patch("requests.post")
def test_return_lending_history(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"description": "Margin Funding Payment", "amount": "0.85", "timestamp": "1600000000.0"}
    ]
    mock_post.return_value = mock_response
    history = bitfinex_api.return_lending_history(1600000000, 1600000001)
    # One per currency (3 from mock cfg)
    assert len(history) == 3


# --- Concurrency Tests (from test_BitfinexAPI.py) ---


def test_multiple_calls(bitfinex_api):
    """Test fast api calls with mocks for concurrency"""
    bitfinex_api.return_open_loan_offers = MagicMock(return_value={})

    def call_get_open_loan_offers(i: int) -> None:
        bitfinex_api.return_open_loan_offers()

    threads = []
    for i in range(10):
        t = threading.Thread(target=call_get_open_loan_offers, args=(i + 1,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


# --- More edge cases ---


@patch("requests.post")
def test_return_balances(mock_post, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"type": "exchange", "currency": "btc", "amount": "1.0", "available": "1.0"}
    ]
    mock_post.return_value = mock_response
    balances = bitfinex_api.return_balances()
    assert balances["BTC"] == "1.0"


@patch("requests.get")
def test_return_ticker_error_message(mock_get, bitfinex_api):
    bitfinex_api.symbols = ["btcusd"]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Error"}
    mock_get.return_value = mock_response
    with patch.object(bitfinex_api.log, "log_error") as mock_log_err:
        bitfinex_api.return_ticker()
        mock_log_err.assert_called()


def test_debug_log(bitfinex_api):
    bitfinex_api.api_debug_log = True
    bitfinex_api.debug_log("test")
    bitfinex_api.log.log.assert_called_with("test")


@patch("requests.get")
def test_get_frr(mock_get, bitfinex_api):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [["fUSD", 0.0002]]
    mock_get.return_value = mock_response
    assert bitfinex_api.get_frr("USD") == 0.0002
