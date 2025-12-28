"""
Tests for Poloniex module core logic.
"""

import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from lendingbot.modules.Poloniex import Poloniex
from lendingbot.modules.ExchangeApi import ApiError

@pytest.fixture
def poloniex_api():
    mock_config = MagicMock()
    mock_config.get.return_value = "key"
    mock_config.getboolean.return_value = False
    mock_log = MagicMock()
    return Poloniex(mock_config, mock_log)

class TestPoloniexCore:
    @patch('urllib.request.urlopen')
    def test_api_query_public(self, mock_urlopen, poloniex_api):
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"BTC_USD": {"last": "100"}}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        ret = poloniex_api.api_query("returnTicker")
        
        assert ret["BTC_USD"]["last"] == "100"
        mock_urlopen.assert_called_once()
        args, _ = mock_urlopen.call_args
        assert "https://poloniex.com/public?command=returnTicker" in args[0].full_url

    @patch('urllib.request.urlopen')
    def test_api_query_private(self, mock_urlopen, poloniex_api):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"success": 1}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Private command
        poloniex_api.api_query("returnOpenOrders", {"currencyPair": "BTC_USD"})
        
        mock_urlopen.assert_called_once()
        args, _ = mock_urlopen.call_args
        assert "https://poloniex.com/tradingApi" in args[0].full_url
        assert "Sign" in args[0].headers
        assert "Key" in args[0].headers

    @patch('urllib.request.urlopen')
    def test_api_query_error_429(self, mock_urlopen, poloniex_api):
        # Mock HTTPError 429
        error = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, None
        )
        error.read = MagicMock(return_value=b'{"error":"Rate limit"}') # Mock read method on error
        mock_urlopen.side_effect = error

        with pytest.raises(ApiError) as excinfo:
            poloniex_api.api_query("returnTicker")
        
        # The error message from JSON response is used if valid JSON
        assert "Rate limit" in str(excinfo.value)

    @patch('urllib.request.urlopen')
    def test_api_query_error_502(self, mock_urlopen, poloniex_api):
        error = urllib.error.HTTPError(
            "url", 502, "Bad Gateway", {}, None
        )
        error.read = MagicMock(return_value=b'<html>...</html>')
        mock_urlopen.side_effect = error

        with pytest.raises(ApiError) as excinfo:
            poloniex_api.api_query("returnTicker")
        
        assert "bad gateway" in str(excinfo.value)
