"""
Tests for Poloniex module core logic.
"""

import urllib.request
from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.modules.Poloniex import ApiError, Poloniex


@pytest.fixture
def poloniex_api():
    mock_config = Mock()
    mock_config.get.side_effect = (
        lambda _s, _k, d=None, _min=None, _max=None: d if d is not None else "key"
    )
    mock_config.getboolean.return_value = False
    mock_log = MagicMock()
    return Poloniex(mock_config, mock_log)


class TestPoloniexCore:
    def test_api_query_public(self, poloniex_api):
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"BTC_ETH": {"last": "0.05"}}'
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            res = poloniex_api.return_ticker()
            assert res["BTC_ETH"]["last"] == "0.05"
            mock_url.assert_called()

    def test_api_query_private(self, poloniex_api):
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"result": "success"}'
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            # private query (not in public list)
            res = poloniex_api.return_balances()
            assert res["result"] == "success"

            # Verify it was called with headers (Sign/Key)
            args, _kwargs = mock_url.call_args
            req = args[0]
            assert "Key" in req.headers
            assert "Sign" in req.headers

    def test_api_error_handling(self, poloniex_api):
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"error": "Invalid API Key"}'
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            with pytest.raises(ApiError, match="Invalid API Key"):
                poloniex_api.return_ticker()

    def test_http_error_handling(self, poloniex_api):
        with patch("urllib.request.urlopen") as mock_url:
            mock_error = urllib.request.HTTPError("url", 429, "Too Many Requests", {}, MagicMock())
            mock_error.read = lambda: b'{"error": "Rate limit exceeded"}'
            mock_url.side_effect = mock_error

            with pytest.raises(ApiError, match="Rate limit exceeded"):
                poloniex_api.return_ticker()

    def test_post_process(self):
        from lendingbot.modules.Poloniex import post_process

        data = {"return": [{"datetime": "2025-12-30 21:43:00"}]}
        res = post_process(data)
        assert "timestamp" in res["return"][0]
        assert isinstance(res["return"][0]["timestamp"], float)
