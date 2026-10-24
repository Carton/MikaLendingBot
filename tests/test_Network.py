"""
Tests for the Network proxy helpers and the proxy wiring of outbound clients.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from lendingbot.modules import Configuration, Network, Notify
from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.Configuration import ApiConfig, BotConfig, RootConfig
from lendingbot.modules.Poloniex import Poloniex


PROXY_URL = "http://127.0.0.1:7777"
PROXY_MAP = {"http": PROXY_URL, "https": PROXY_URL}


@pytest.fixture(autouse=True)
def restore_global_config():
    """Saves and restores the module-global configuration around every test."""
    saved = Configuration._current_config
    yield
    Configuration._current_config = saved


def set_global_config(proxy: str | None, request_timeout: int = 30) -> None:
    Configuration._current_config = RootConfig(
        bot=BotConfig(proxy=proxy, request_timeout=request_timeout)
    )


# --- get_proxies / request_timeout ---


class TestNetworkHelpers:
    def test_get_proxies_returns_none_when_config_not_loaded(self):
        Configuration._current_config = None
        assert Network.get_proxies() is None

    def test_get_proxies_returns_none_without_proxy_configured(self):
        set_global_config(None)
        assert Network.get_proxies() is None

    def test_get_proxies_returns_proxy_map_when_configured(self):
        set_global_config(PROXY_URL)
        assert Network.get_proxies() == PROXY_MAP

    def test_request_timeout_falls_back_without_config(self):
        Configuration._current_config = None
        assert Network.request_timeout() == Network.DEFAULT_REQUEST_TIMEOUT

    def test_request_timeout_reads_config(self):
        set_global_config(None, request_timeout=17)
        assert Network.request_timeout() == 17.0


# --- proxy config validation ---


class TestProxyValidation:
    def test_default_is_none(self):
        assert BotConfig().proxy is None

    def test_empty_string_normalized_to_none(self):
        assert BotConfig(proxy="").proxy is None

    @pytest.mark.parametrize("proxy", ["http://127.0.0.1:7777", "https://proxy.example.com:8443"])
    def test_accepts_http_and_https(self, proxy):
        assert BotConfig(proxy=proxy).proxy == proxy

    @pytest.mark.parametrize(
        "proxy",
        [
            "socks5://127.0.0.1:1080",
            "127.0.0.1:7777",
            "http://",
            "http://:7890",
            "ftp://proxy.example.com",
        ],
    )
    def test_rejects_other_schemes_or_missing_host(self, proxy):
        with pytest.raises(ValidationError, match="http:// or https://"):
            BotConfig(proxy=proxy)

    @pytest.mark.parametrize("proxy", ["http://proxy:abc", "http://proxy:70000"])
    def test_rejects_invalid_ports(self, proxy):
        with pytest.raises(ValidationError):
            BotConfig(proxy=proxy)

    @pytest.mark.parametrize(
        "proxy",
        [
            "socks5://user:secret@127.0.0.1:1080",
            "http://user:secret@h\uff1a80",  # full-width colon trips urlparse's netloc check
        ],
    )
    def test_validation_errors_do_not_leak_credentials(self, proxy):
        with pytest.raises(ValidationError) as excinfo:
            BotConfig(proxy=proxy)
        assert "secret" not in str(excinfo.value)
        # The real load path validates through RootConfig, which renders the
        # error (and would echo the raw input) unless it hides inputs too.
        with pytest.raises(ValidationError) as excinfo:
            RootConfig.model_validate({"bot": {"proxy": proxy}})
        assert "secret" not in str(excinfo.value)


# --- wiring: exchange clients pass the proxy map to requests ---


@pytest.fixture
def mock_200_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.text = '{"key": "value"}'
    resp.json.return_value = {"key": "value"}
    return resp


class TestExchangeWiring:
    @patch("requests.get")
    def test_bitfinex_get_uses_proxy(self, mock_get, mock_200_response):
        set_global_config(PROXY_URL)
        cfg = RootConfig(
            api=ApiConfig(apikey="k", secret="s", all_currencies=["USD"]),
            bot=BotConfig(request_timeout=30),
        )
        with patch.object(Bitfinex, "return_available_account_balances", return_value={}):
            api = Bitfinex(cfg, MagicMock())
        mock_get.return_value = mock_200_response
        api._request("get", "/v1/symbols")
        assert mock_get.call_args.kwargs["proxies"] == PROXY_MAP

    @patch("requests.post")
    def test_bitfinex_post_uses_proxy(self, mock_post, mock_200_response):
        set_global_config(PROXY_URL)
        cfg = RootConfig(
            api=ApiConfig(apikey="k", secret="s", all_currencies=["USD"]),
            bot=BotConfig(request_timeout=30),
        )
        with patch.object(Bitfinex, "return_available_account_balances", return_value={}):
            api = Bitfinex(cfg, MagicMock())
        mock_post.return_value = mock_200_response
        api._request("post", "/v1/balances", payload={"X-BFX-APIKEY": "k"})
        assert mock_post.call_args.kwargs["proxies"] == PROXY_MAP

    @patch("requests.get")
    def test_poloniex_public_get_uses_proxy(self, mock_get, mock_200_response):
        set_global_config(PROXY_URL)
        cfg = RootConfig(
            api=ApiConfig(apikey="k", secret="s", all_currencies=["BTC"]),
            bot=BotConfig(request_timeout=30),
        )
        api = Poloniex(cfg, MagicMock())
        mock_get.return_value = mock_200_response
        api.api_query("returnTicker")
        assert mock_get.call_args.kwargs["proxies"] == PROXY_MAP

    @patch("requests.post")
    def test_poloniex_trading_post_uses_proxy(self, mock_post, mock_200_response):
        set_global_config(PROXY_URL)
        cfg = RootConfig(
            api=ApiConfig(apikey="k", secret="s", all_currencies=["BTC"]),
            bot=BotConfig(request_timeout=30),
        )
        api = Poloniex(cfg, MagicMock())
        mock_post.return_value = mock_200_response
        api.api_query("returnBalances")
        assert mock_post.call_args.kwargs["proxies"] == PROXY_MAP

    @patch("requests.get")
    def test_bitfinex_without_proxy_passes_none(self, mock_get, mock_200_response):
        set_global_config(None)
        cfg = RootConfig(
            api=ApiConfig(apikey="k", secret="s", all_currencies=["USD"]),
            bot=BotConfig(request_timeout=30),
        )
        with patch.object(Bitfinex, "return_available_account_balances", return_value={}):
            api = Bitfinex(cfg, MagicMock())
        mock_get.return_value = mock_200_response
        api._request("get", "/v1/symbols")
        assert mock_get.call_args.kwargs["proxies"] is None


# --- wiring: notifications go through requests with the proxy map ---


class TestNotifyWiring:
    @patch("lendingbot.modules.Notify.requests.post")
    def test_telegram_uses_proxy_and_configured_timeout(self, mock_post):
        set_global_config(PROXY_URL, request_timeout=17)
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        Notify.post_to_telegram("msg", ["123"], "botid")

        kwargs = mock_post.call_args.kwargs
        assert kwargs["proxies"] == PROXY_MAP
        assert kwargs["timeout"] == 17.0

    @patch("lendingbot.modules.Notify.requests.post")
    def test_pushbullet_uses_proxy(self, mock_post):
        set_global_config(PROXY_URL)
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        Notify.post_to_pushbullet("msg", "token", "devid")

        assert mock_post.call_args.kwargs["proxies"] == PROXY_MAP
