import asyncio
import json
import threading
from collections.abc import AsyncGenerator
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import Configuration
from .Logger import Logger


class WebServer:
    def __init__(self, config: Configuration.RootConfig, lending_engine: Any, log: Logger):
        self.config = config
        self.lending_engine = lending_engine
        self.log = log
        self.web_server_ip = config.bot.web.host
        self.web_server_port = config.bot.web.port
        self.web_server_template = config.bot.web.template
        self.web_settings_file = "web_settings.json"

        self.app = FastAPI(title="LendingBot Dashboard")
        self._setup_routes()
        self._setup_static()

        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    def _setup_routes(self) -> None:
        @self.app.get("/get_status", response_model=None)
        async def get_status() -> dict[str, Any]:
            strategies = {cur: cfg.strategy for cur, cfg in self.lending_engine.coin_cfg.items()}
            return {
                "lending_paused": self.lending_engine.lending_paused,
                "lending_strategies": strategies,
            }

        @self.app.get("/get_settings", response_model=None)
        async def get_settings() -> dict[str, Any]:
            return self.get_web_settings()

        @self.app.post("/set_config", response_model=None)
        async def set_config(request: Request) -> dict[str, Any] | JSONResponse:
            config_data = await request.json()
            if "frrdelta_min" in config_data and "frrdelta_max" in config_data:
                try:
                    self.lending_engine.frrdelta_min = Decimal(str(config_data["frrdelta_min"]))
                    self.lending_engine.frrdelta_max = Decimal(str(config_data["frrdelta_max"]))
                    self.log.log(
                        f"Settings updated by user: FRR Delta Min={self.lending_engine.frrdelta_min}%, Max={self.lending_engine.frrdelta_max}%"
                    )
                    self.save_web_settings(config_data)
                    return {
                        "success": True,
                        "frrdelta_min": str(self.lending_engine.frrdelta_min),
                        "frrdelta_max": str(self.lending_engine.frrdelta_max),
                    }
                except (ValueError, TypeError, InvalidOperation) as e:
                    return JSONResponse(
                        status_code=400, content={"success": False, "error": str(e)}
                    )
            else:
                try:
                    self.save_web_settings(config_data)
                    return {"success": True}
                except Exception as e:
                    return JSONResponse(
                        status_code=400, content={"success": False, "error": str(e)}
                    )

        @self.app.get("/pause_lending", response_model=None)
        async def pause_lending() -> Response:
            self.lending_engine.lending_paused = True
            self.save_web_settings({"lending_paused": True})
            return Response(content="Lending paused")

        @self.app.get("/resume_lending", response_model=None)
        async def resume_lending() -> Response:
            self.lending_engine.lending_paused = False
            self.save_web_settings({"lending_paused": False})
            return Response(content="Lending resumed")

        @self.app.get("/recent_logs", response_model=None)
        async def recent_logs() -> dict[str, Any]:
            return {"log": self.log.get_recent_logs()}

        @self.app.get("/stream-logs", response_model=None)
        async def stream_logs(request: Request) -> StreamingResponse:
            queue: asyncio.Queue[str] = asyncio.Queue()

            def log_callback(msg: str) -> None:
                if self.loop:
                    self.loop.call_soon_threadsafe(queue.put_nowait, msg)

            self.log.callbacks.append(log_callback)

            async def event_generator() -> AsyncGenerator[str, None]:
                try:
                    while True:
                        if await request.is_disconnected():
                            break
                        try:
                            # Wait with timeout to periodically send keep-alives
                            message = await asyncio.wait_for(queue.get(), timeout=15.0)
                            yield f"data: {message}\n\n"
                        except TimeoutError:
                            # Send SSE comment as keep-alive ping to prevent proxy timeouts
                            yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    pass
                finally:
                    if log_callback in self.log.callbacks:
                        self.log.callbacks.remove(log_callback)

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable Nginx buffering
                },
            )

    def _setup_static(self) -> None:
        # Serve logs directory
        if Path("logs").exists():
            self.app.mount("/logs", StaticFiles(directory="logs"), name="logs")

        # Serve main template (www)
        self.app.mount(
            "/", StaticFiles(directory=self.web_server_template, html=True), name="static"
        )

    def start(self) -> None:
        """Start the web server in a separate daemon thread.

        This initializes the asyncio event loop and runs the Uvicorn ASGI server.
        """
        print(f"Starting WebServer at {self.web_server_ip} on port {self.web_server_port}")
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()

    def _run_server(self) -> None:
        """Internal method to run the Uvicorn server in a new event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        config = uvicorn.Config(
            app=self.app,
            host=self.web_server_ip,
            port=self.web_server_port,
            log_level="warning",
            loop="asyncio",
        )
        self.server = uvicorn.Server(config)
        self.loop.run_until_complete(self.server.serve())

    def stop(self) -> None:
        """Gracefully stop the web server.

        Signals the Uvicorn server to exit its event loop.
        """
        print("Stopping WebServer")
        if self.server:
            self.server.should_exit = True

    # Web Settings methods
    def get_web_settings(self) -> dict[str, Any]:
        default_settings = {
            "refreshRate": self.config.bot.web.refresh_rate,
            "timespanNames": ["Year", "Month", "Week", "Day", "Hour"],
            "btcDisplayUnit": "BTC",
            "outputCurrencyDisplayMode": "all",
            "effRateMode": "lentperc",
            "frrdelta_min": -10,
            "frrdelta_max": 10,
        }
        if not Path(self.web_settings_file).exists():
            return default_settings

        try:
            with Path(self.web_settings_file).open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings = default_settings | data
                    if not settings.get("timespanNames"):
                        settings["timespanNames"] = default_settings["timespanNames"]
                    return settings
                return default_settings
        except Exception:
            return default_settings

    def save_web_settings(self, settings: dict[str, Any]) -> None:
        current = self.get_web_settings()
        current.update(settings)
        try:
            with Path(self.web_settings_file).open("w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)
        except Exception as e:
            print(f"Error saving web settings: {e}")


_web_server: WebServer | None = None


def get_web_settings() -> dict[str, Any]:
    if _web_server:
        return _web_server.get_web_settings()
    return {}
