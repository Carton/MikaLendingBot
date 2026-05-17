from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

import pytest
import uvicorn
from httpx import ASGITransport, AsyncClient

from lendingbot.modules.Configuration import RootConfig
from lendingbot.modules.WebServer import WebServer


class MockEngine:
    def __init__(self) -> None:
        self.lending_paused: bool = False
        self.coin_cfg: dict[str, Any] = {}
        self.frrdelta_min: int = -10
        self.frrdelta_max: int = 10


class MockLogger:
    def __init__(self) -> None:
        self.callbacks: list[Callable[[str], None]] = []
        self.status_snapshot: dict[str, Any] = {
            "last_status": "Live status from logger",
            "last_update": "2026-05-10 12:00:00",
            "exchange": "Bitfinex",
            "label": "Lending Bot",
            "raw_data": {},
            "outputCurrency": {},
        }

    def log(self, msg: str) -> None:
        for cb in self.callbacks:
            cb(msg)

    def get_recent_logs(self) -> list[str]:
        return ["Mocked Log 1", "Mocked Log 2"]

    def get_stats_snapshot(self) -> dict[str, Any]:
        return dict(self.status_snapshot)


@pytest.fixture
async def web_server(tmp_path: Path) -> WebServer:
    cfg = RootConfig()
    cfg.bot.stats_file = str(tmp_path / "bot_stats.json")
    engine = MockEngine()
    logger = MockLogger()
    logger.callbacks = []
    ws = WebServer(cfg, engine, logger)  # type: ignore[arg-type]
    ws.web_settings_file = str(tmp_path / "web_settings.json")
    ws.loop = asyncio.get_running_loop()
    return ws


@pytest.fixture
async def live_web_server(web_server: WebServer) -> AsyncGenerator[str, None]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    config = uvicorn.Config(
        app=web_server.app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    try:
        while not server.started:
            await asyncio.sleep(0.01)
        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=5.0)


@pytest.mark.asyncio
async def test_get_status(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_status")
    assert response.status_code == 200
    data = response.json()
    assert data["lending_paused"] is False
    assert data["last_status"] == "Live status from logger"
    assert data["last_update"] == "2026-05-10 12:00:00"
    assert "raw_data" not in data
    assert "outputCurrency" not in data


@pytest.mark.asyncio
async def test_bot_stats_json_prefers_persisted_stats_file(
    web_server: WebServer,
) -> None:
    stats_file = Path(web_server.config.bot.stats_file)
    stats_file.write_text(
        json.dumps(
            {
                "last_status": "Persisted complete status",
                "raw_data": {"USD": {"totalCoins": "139176.70496700"}},
                "outputCurrency": {
                    "currency": "USD",
                    "highestBid": "80775.44426494346",
                },
            }
        ),
        encoding="utf-8",
    )

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/bot_stats.json")

    assert response.status_code == 200
    data = response.json()
    assert data["last_status"] == "Persisted complete status"
    assert data["raw_data"]["USD"]["totalCoins"] == "139176.70496700"
    assert data["outputCurrency"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_get_settings(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_settings")
    assert response.status_code == 200
    data = response.json()
    assert data["refreshRate"] == web_server.config.bot.web.refresh_rate
    assert "effRateMode" not in data


@pytest.mark.asyncio
async def test_recent_logs(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/recent_logs")
    assert response.status_code == 200
    data = response.json()
    assert data["log"] == ["Mocked Log 1", "Mocked Log 2"]


@pytest.mark.asyncio
async def test_dashboard_state_returns_live_status_when_stats_file_missing(
    web_server: WebServer,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/dashboard/state")

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["last_status"] == "Live status from logger"
    assert data["status"]["last_update"] == "2026-05-10 12:00:00"
    assert data["stats"]["raw_data"] == {}
    assert data["recent_logs"] == ["Mocked Log 1", "Mocked Log 2"]
    assert data["lending_paused"] is False
    assert data["settings"]["refreshRate"] == web_server.config.bot.web.refresh_rate


@pytest.mark.asyncio
async def test_dashboard_state_prefers_persisted_full_stats(
    web_server: WebServer,
) -> None:
    stats_file = Path(web_server.config.bot.stats_file)
    stats_file.write_text(
        json.dumps(
            {
                "last_status": "Persisted complete status",
                "last_update": "2026-05-10 13:00:00",
                "raw_data": {"USD": {"totalCoins": "139176.70496700"}},
                "outputCurrency": {
                    "currency": "USD",
                    "highestBid": "80775.44426494346",
                },
                "plugins": {"charts": {"navbar": True}},
            }
        ),
        encoding="utf-8",
    )

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/dashboard/state")

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["last_status"] == "Live status from logger"
    assert data["stats"]["last_status"] == "Persisted complete status"
    assert data["stats"]["raw_data"]["USD"]["totalCoins"] == "139176.70496700"
    assert data["plugins"]["charts"]["navbar"] is True


@pytest.mark.asyncio
async def test_get_settings_restores_default_timespans(
    web_server: WebServer, tmp_path: Path
) -> None:
    settings_file = tmp_path / "web_settings.json"
    settings_file.write_text(
        json.dumps({"refreshRate": 15, "timespanNames": []}),
        encoding="utf-8",
    )
    web_server.web_settings_file = str(settings_file)

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_settings")

    assert response.status_code == 200
    data = response.json()
    assert data["refreshRate"] == 15
    assert data["timespanNames"] == ["Year", "Month", "Week", "Day", "Hour"]


@pytest.mark.asyncio
async def test_get_settings_ignores_legacy_effective_rate_mode(
    web_server: WebServer, tmp_path: Path
) -> None:
    settings_file = tmp_path / "web_settings.json"
    settings_file.write_text(
        json.dumps({"refreshRate": 60, "effRateMode": "onlyfee"}),
        encoding="utf-8",
    )
    web_server.web_settings_file = str(settings_file)

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_settings")

    assert response.status_code == 200
    assert "effRateMode" not in response.json()


@pytest.mark.asyncio
async def test_pause_resume(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        await ac.get("/pause_lending")
        assert web_server.lending_engine.lending_paused is True
        await ac.get("/resume_lending")
        assert web_server.lending_engine.lending_paused is False


@pytest.mark.asyncio
async def test_api_pause_resume(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        pause_response = await ac.post("/api/lending/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["lending_paused"] is True
        assert web_server.lending_engine.lending_paused is True

        resume_response = await ac.post("/api/lending/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["lending_paused"] is False
        assert web_server.lending_engine.lending_paused is False


@pytest.mark.asyncio
async def test_api_settings_round_trip(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        save_response = await ac.post("/api/settings", json={"refreshRate": 45})
        assert save_response.status_code == 200

        get_response = await ac.get("/api/settings")
        assert get_response.status_code == 200
        assert get_response.json()["refreshRate"] == 45


@pytest.mark.asyncio
async def test_api_settings_clamps_frr_minimum(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        save_response = await ac.post(
            "/api/settings", json={"frrdelta_min": -80, "frrdelta_max": 9}
        )
        assert save_response.status_code == 200

        data = save_response.json()
        assert data["frrdelta_min"] == "-30.0"
        assert web_server.lending_engine.frrdelta_min == -30

        get_response = await ac.get("/api/settings")
        assert get_response.status_code == 200
        assert get_response.json()["frrdelta_min"] == -30.0


@pytest.mark.asyncio
async def test_get_settings_clamps_persisted_frr_minimum(
    web_server: WebServer, tmp_path: Path
) -> None:
    settings_file = tmp_path / "web_settings.json"
    settings_file.write_text(
        json.dumps({"frrdelta_min": -80, "frrdelta_max": 9}),
        encoding="utf-8",
    )
    web_server.web_settings_file = str(settings_file)

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/settings")

    assert response.status_code == 200
    assert response.json()["frrdelta_min"] == -30.0


@pytest.mark.asyncio
async def test_api_charts_history_reads_history_file(
    web_server: WebServer, tmp_path: Path
) -> None:
    history_dir = tmp_path / "www"
    history_dir.mkdir()
    (history_dir / "history.json").write_text(
        json.dumps({"USD": [[100, "1.5", "10.5"]]}),
        encoding="utf-8",
    )
    web_server.web_server_template = str(history_dir)

    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/charts/history")

    assert response.status_code == 200
    assert response.json()["USD"] == [[100, "1.5", "10.5"]]


@pytest.mark.asyncio
async def test_sse_stream(web_server: WebServer, live_web_server: str) -> None:
    async with (
        AsyncClient(base_url=live_web_server, timeout=5.0) as ac,
        ac.stream("GET", "/stream-logs") as response,
    ):
        assert response.status_code == 200

        test_msg = "SSE Test Message"
        # Give a moment for the subscriber to be registered
        await asyncio.sleep(0.1)

        web_server.log.log(test_msg)
        # Give loop a chance to process the scheduled put_nowait
        await asyncio.sleep(0.1)

        # Use wait_for to prevent hanging
        try:

            async def read_stream() -> str:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        return line
                return ""

            line = await asyncio.wait_for(read_stream(), timeout=5.0)
            assert test_msg in line
        except TimeoutError:
            pytest.fail("SSE stream timed out")
