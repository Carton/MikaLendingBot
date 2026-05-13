from pathlib import Path


def test_built_pages_use_local_vite_assets_only() -> None:
    html = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in ("www/lendingbot.html", "www/charts.html", "www/index.html")
    )

    assert "https://maxcdn.bootstrapcdn.com" not in html
    assert "https://code.jquery.com" not in html
    assert "https://cdnjs.cloudflare.com" not in html
    assert "https://www.gstatic.com/charts" not in html
    assert "/assets/main.js" in html
    assert "/assets/main.css" in html


def test_legacy_dashboard_script_is_removed() -> None:
    assert not Path("www/lendingbot.js").exists()


def test_react_dashboard_uses_aggregated_state_endpoint() -> None:
    client = Path("frontend/src/api/client.ts").read_text(encoding="utf-8")
    hook = Path("frontend/src/hooks/useDashboardState.ts").read_text(encoding="utf-8")

    assert '"/api/dashboard/state"' in client
    assert '"/get_status"' not in client
    assert '"/bot_stats.json"' not in client
    assert "INITIAL_RETRY_MS" in hook
    assert "stream-logs" in hook


def test_mobile_portrait_layout_is_explicitly_supported() -> None:
    page = Path("frontend/src/pages/DashboardPage.tsx").read_text(encoding="utf-8")
    styles = Path("frontend/src/styles.css").read_text(encoding="utf-8")
    tests = Path("frontend/src/pages/DashboardPage.test.tsx").read_text(encoding="utf-8")

    assert "CoinCardList" in page
    assert 'data-testid="mobile-coin-list"' in page
    assert "@media (max-width: 640px)" in styles
    assert "renders mobile-friendly coin cards" in tests
