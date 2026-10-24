"""Centralized helpers for outbound network access.

Every outbound HTTP(S) call the bot makes (exchange APIs, blockchain.info rate
lookups, Slack/Telegram/Pushbullet notifications) goes through requests with
the proxies mapping from here, so a proxy configured in ``[bot]`` applies
everywhere at once. Explicitly passed proxies are never bypassed by the
NO_PROXY environment variable. When no proxy is configured the mapping is
None, which keeps requests' default behavior of honoring HTTP(S)_PROXY /
ALL_PROXY environment variables.
"""

from __future__ import annotations

from . import Configuration


DEFAULT_REQUEST_TIMEOUT = 30.0


def get_proxies() -> dict[str, str] | None:
    """Returns a proxies mapping for requests calls, or None for defaults."""
    try:
        config = Configuration.get_config()
    except RuntimeError:
        # Configuration not loaded (e.g. unit tests); fall back to env vars.
        return None

    proxy = config.bot.proxy
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def request_timeout() -> float:
    """Timeout for simple outbound calls (notifications, rate lookups)."""
    try:
        config = Configuration.get_config()
    except RuntimeError:
        return DEFAULT_REQUEST_TIMEOUT
    return float(config.bot.request_timeout)
