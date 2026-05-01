from __future__ import annotations

import asyncio
import json
import socket
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from pathlib import Path

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

    def log(self, msg: str) -> None:
        for cb in self.callbacks:
            cb(msg)

    def get_recent_logs(self) -> list[str]:
        return ["Mocked Log 1", "Mocked Log 2"]


@pytest.fixture
async def web_server() -> WebServer:
    cfg = RootConfig()
    engine = MockEngine()
    logger = MockLogger()
    logger.callbacks = []
    ws = WebServer(cfg, engine, logger)  # type: ignore[arg-type]
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


@pytest.mark.asyncio
async def test_get_settings(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_settings")
    assert response.status_code == 200
    data = response.json()
    assert data["refreshRate"] == 30


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
async def test_pause_resume(web_server: WebServer) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        await ac.get("/pause_lending")
        assert web_server.lending_engine.lending_paused is True
        await ac.get("/resume_lending")
        assert web_server.lending_engine.lending_paused is False


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
