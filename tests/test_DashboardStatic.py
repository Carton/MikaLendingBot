from pathlib import Path


def test_status_poll_interval_uses_configured_refresh_rate() -> None:
    script = Path("www/lendingbot.js").read_text(encoding="utf-8")

    assert "statusRefreshRate = 5" not in script
    assert "scheduleStatusRefresh(refreshRate * 1000)" in script
