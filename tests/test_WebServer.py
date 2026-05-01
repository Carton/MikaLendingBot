import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from lendingbot.modules.Configuration import RootConfig
from lendingbot.modules.WebServer import WebServer


class MockEngine:
    def __init__(self):
        self.lending_paused = False
        self.coin_cfg = {}
        self.frrdelta_min = -10
        self.frrdelta_max = 10


class MockLogger:
    def __init__(self):
        self.callbacks = []

    def log(self, msg):
        for cb in self.callbacks:
            cb(msg)


@pytest.fixture
async def web_server():
    cfg = RootConfig()
    engine = MockEngine()
    logger = MockLogger()
    logger.callbacks = []
    ws = WebServer(cfg, engine, logger)
    ws.loop = asyncio.get_running_loop()
    return ws


@pytest.mark.asyncio
async def test_get_status(web_server):
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_status")
    assert response.status_code == 200
    data = response.json()
    assert data["lending_paused"] is False


@pytest.mark.asyncio
async def test_get_settings(web_server):
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        response = await ac.get("/get_settings")
    assert response.status_code == 200
    data = response.json()
    assert data["refreshRate"] == 30


@pytest.mark.asyncio
async def test_pause_resume(web_server):
    async with AsyncClient(
        transport=ASGITransport(app=web_server.app), base_url="http://test"
    ) as ac:
        await ac.get("/pause_lending")
        assert web_server.lending_engine.lending_paused is True
        await ac.get("/resume_lending")
        assert web_server.lending_engine.lending_paused is False


@pytest.mark.asyncio
async def test_sse_stream(web_server):
    async with (
        AsyncClient(transport=ASGITransport(app=web_server.app), base_url="http://test") as ac,
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

            async def read_stream():
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        return line

            line = await asyncio.wait_for(read_stream(), timeout=5.0)
            assert test_msg in line
        except TimeoutError:
            pytest.fail("SSE stream timed out")
