import asyncio
import itertools
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


FRR_DELTA_MIN_LIMIT = Decimal("-30")

XDAY_RATE_MIN = Decimal("0")
XDAY_RATE_MAX = Decimal("5")
XDAY_DAYS_MIN = 2
XDAY_DAYS_MAX = 120


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
        @self.app.get("/api/dashboard/state", response_model=None)
        async def dashboard_state(include_logs: bool = True) -> dict[str, Any]:
            return self._get_dashboard_state(include_logs=include_logs)

        @self.app.get("/api/settings", response_model=None)
        async def api_get_settings() -> dict[str, Any]:
            return self.get_web_settings()

        @self.app.post("/api/settings", response_model=None)
        async def api_set_settings(request: Request) -> dict[str, Any] | JSONResponse:
            config_data = await request.json()
            return self._apply_web_settings(config_data)

        @self.app.post("/api/lending/pause", response_model=None)
        async def api_pause_lending() -> dict[str, Any]:
            self.lending_engine.lending_paused = True
            self.save_web_settings({"lending_paused": True})
            return {"success": True, "lending_paused": True}

        @self.app.post("/api/lending/resume", response_model=None)
        async def api_resume_lending() -> dict[str, Any]:
            self.lending_engine.lending_paused = False
            self.save_web_settings({"lending_paused": False})
            return {"success": True, "lending_paused": False}

        @self.app.get("/api/charts/history", response_model=None)
        async def api_chart_history() -> dict[str, Any] | JSONResponse:
            history_file = Path(self.web_server_template) / "history.json"
            if not history_file.exists():
                return {}
            try:
                with history_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})
            return {}

        @self.app.get("/get_status", response_model=None)
        async def get_status() -> dict[str, Any]:
            strategies = {cur: cfg.strategy for cur, cfg in self.lending_engine.coin_cfg.items()}
            return self._get_live_status_snapshot() | {
                "lending_paused": self.lending_engine.lending_paused,
                "lending_strategies": strategies,
            }

        @self.app.get("/bot_stats.json", response_model=None)
        async def bot_stats() -> JSONResponse:
            return JSONResponse(
                content=self._get_persisted_stats_snapshot(),
                headers={"Cache-Control": "no-store"},
            )

        @self.app.get("/get_settings", response_model=None)
        async def get_settings() -> dict[str, Any]:
            return self.get_web_settings()

        @self.app.post("/set_config", response_model=None)
        async def set_config(request: Request) -> dict[str, Any] | JSONResponse:
            config_data = await request.json()
            return self._apply_web_settings(config_data)

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

    def _get_live_status_snapshot(self) -> dict[str, Any]:
        get_snapshot = getattr(self.log, "get_stats_snapshot", None)
        if callable(get_snapshot):
            snapshot = get_snapshot()
            if isinstance(snapshot, dict) and snapshot:
                return {
                    key: snapshot[key] for key in ("last_status", "last_update") if key in snapshot
                }

        persisted = self._read_stats_file()
        return {key: persisted[key] for key in ("last_status", "last_update") if key in persisted}

    def _get_persisted_stats_snapshot(self) -> dict[str, Any]:
        persisted = self._read_stats_file()
        if persisted:
            return persisted

        get_snapshot = getattr(self.log, "get_stats_snapshot", None)
        if callable(get_snapshot):
            snapshot = get_snapshot()
            if isinstance(snapshot, dict):
                return snapshot
        return {}

    def _read_stats_file(self) -> dict[str, Any]:
        stats_file = Path(self.config.bot.stats_file)
        if stats_file.exists():
            try:
                with stats_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}

    def _get_lending_strategies(self) -> dict[str, str]:
        strategies = {}
        for cur, cfg in self.lending_engine.coin_cfg.items():
            strategy = getattr(cfg, "strategy", "")
            strategies[cur] = str(getattr(strategy, "value", strategy))
        return strategies

    def _get_dashboard_state(self, include_logs: bool = True) -> dict[str, Any]:
        stats = self._get_persisted_stats_snapshot()
        state = {
            "settings": self.get_web_settings(),
            "status": self._get_live_status_snapshot(),
            "stats": stats,
            "lending_paused": self.lending_engine.lending_paused,
            "lending_strategies": self._get_lending_strategies(),
            "recent_successful_loans": self._get_recent_successful_loans(),
            "plugins": stats.get("plugins", {}),
        }
        if include_logs:
            state["recent_logs"] = self.log.get_recent_logs()
        return state

    def _get_recent_successful_loans(self) -> dict[str, list[dict[str, str]]]:
        limit = self.config.bot.web.recent_successful_loans
        if limit <= 0:
            return {}

        get_recent = getattr(self.lending_engine, "get_recent_successful_loans", None)
        if not callable(get_recent):
            return {}
        recent = get_recent(limit)
        return recent if isinstance(recent, dict) else {}

    # Web Settings methods
    def get_web_settings(self) -> dict[str, Any]:
        default_coin_cfg = self.config.get_coin_config("default")
        default_settings = {
            "refreshRate": self.config.bot.web.refresh_rate,
            "timespanNames": ["Year", "Month", "Week", "Day", "Hour"],
            "btcDisplayUnit": "BTC",
            "outputCurrencyDisplayMode": "all",
            "frrdelta_min": float(default_coin_cfg.frr_delta_min),
            "frrdelta_max": float(default_coin_cfg.frr_delta_max),
            "xday_thresholds": [
                {"rate": float(t.rate), "days": t.days} for t in default_coin_cfg.xday_thresholds
            ],
            "recentSuccessfulLoans": self.config.bot.web.recent_successful_loans,
        }
        default_settings = sanitize_web_settings(default_settings)
        if not Path(self.web_settings_file).exists():
            return default_settings

        try:
            with Path(self.web_settings_file).open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings = default_settings | data
                    settings.pop("effRateMode", None)
                    settings["recentSuccessfulLoans"] = default_settings["recentSuccessfulLoans"]
                    if not settings.get("timespanNames"):
                        settings["timespanNames"] = default_settings["timespanNames"]
                    settings = sanitize_web_settings(settings)
                    # Re-apply the TOML default when the persisted value was malformed.
                    if "xday_thresholds" not in settings:
                        settings["xday_thresholds"] = default_settings["xday_thresholds"]
                    return settings
                return default_settings
        except Exception:
            return default_settings

    def save_web_settings(self, settings: dict[str, Any]) -> None:
        current = self.get_web_settings()
        current.update(settings)
        current.pop("effRateMode", None)
        current.pop("recentSuccessfulLoans", None)
        current = sanitize_web_settings(current)
        try:
            with Path(self.web_settings_file).open("w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)
        except Exception as e:
            print(f"Error saving web settings: {e}")

    def _apply_web_settings(self, config_data: dict[str, Any]) -> dict[str, Any] | JSONResponse:
        xday_submitted = "xday_thresholds" in config_data
        config_data = sanitize_web_settings(config_data)
        applied: dict[str, Any] = {}

        # Validate xday before mutating anything so a rejected submission
        # never leaves the engine half-updated.
        xday_thresholds: list[Configuration.XDayThreshold] | None = None
        if xday_submitted:
            # sanitize_web_settings strips values that are not a list at all,
            # so their absence here means the submitted shape was invalid.
            xday_thresholds = (
                normalize_xday_thresholds(config_data["xday_thresholds"])
                if "xday_thresholds" in config_data
                else None
            )
            if xday_thresholds is None:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "xday_thresholds must be a list of {rate, days} entries",
                    },
                )
            if any(
                later.days < earlier.days for earlier, later in itertools.pairwise(xday_thresholds)
            ):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "xday_thresholds days must not decrease as the rate increases",
                    },
                )

        if "frrdelta_min" in config_data and "frrdelta_max" in config_data:
            try:
                self.lending_engine.frrdelta_min = Decimal(str(config_data["frrdelta_min"]))
                self.lending_engine.frrdelta_max = Decimal(str(config_data["frrdelta_max"]))
                self.lending_engine.has_web_frr_override = True
                self.log.log(
                    f"Settings updated by user: FRR Delta Min={self.lending_engine.frrdelta_min}%, Max={self.lending_engine.frrdelta_max}%"
                )
                applied |= {
                    "frrdelta_min": str(self.lending_engine.frrdelta_min),
                    "frrdelta_max": str(self.lending_engine.frrdelta_max),
                }
            except (ValueError, TypeError, InvalidOperation) as e:
                return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

        if xday_thresholds is not None:
            self.lending_engine.xday_thresholds = xday_thresholds
            self.lending_engine.has_web_xday_override = True
            self.log.log(
                "Settings updated by user: xday_thresholds="
                + ",".join(f"{t.rate}%->{t.days}d" for t in xday_thresholds)
            )
            applied["xday_thresholds"] = [
                {"rate": float(t.rate), "days": t.days} for t in xday_thresholds
            ]

        try:
            self.save_web_settings(config_data)
            return {"success": True} | applied
        except Exception as e:
            return JSONResponse(status_code=400, content={"success": False, "error": str(e)})


_web_server: WebServer | None = None


def normalize_xday_thresholds(raw: Any) -> list[Configuration.XDayThreshold] | None:
    """
    Parses raw xday_thresholds web settings into a canonical threshold list.

    Invalid entries (non-dict items, out-of-range values) are dropped, the list
    is sorted by rate ascending and duplicate rates keep the last occurrence.
    Returns None when raw is not a list at all.
    """
    if not isinstance(raw, list):
        return None

    parsed: list[Configuration.XDayThreshold] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        rate_raw = entry.get("rate")
        days_raw = entry.get("days")
        if rate_raw is None or days_raw is None:
            continue
        try:
            rate = Decimal(str(rate_raw))
            days = int(days_raw)
        except (ValueError, TypeError, InvalidOperation):
            continue
        # A Decimal NaN parses fine, but comparing against it raises InvalidOperation.
        if rate.is_nan() or not (XDAY_RATE_MIN <= rate <= XDAY_RATE_MAX):
            continue
        if not (XDAY_DAYS_MIN <= days <= XDAY_DAYS_MAX):
            continue
        parsed.append(Configuration.XDayThreshold(rate=rate, days=days))

    parsed.sort(key=lambda t: t.rate)
    deduped: list[Configuration.XDayThreshold] = []
    for threshold in parsed:
        if deduped and deduped[-1].rate == threshold.rate:
            deduped[-1] = threshold
        else:
            deduped.append(threshold)
    return deduped


def sanitize_web_settings(settings: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(settings)
    if "xday_thresholds" in sanitized:
        thresholds = normalize_xday_thresholds(sanitized["xday_thresholds"])
        if thresholds is None:
            # Drop malformed values so the TOML defaults apply instead.
            sanitized.pop("xday_thresholds")
        else:
            sanitized["xday_thresholds"] = [
                {"rate": float(t.rate), "days": t.days} for t in thresholds
            ]
    if "frrdelta_min" not in sanitized:
        return sanitized

    try:
        frrdelta_min = Decimal(str(sanitized["frrdelta_min"]))
    except (ValueError, TypeError, InvalidOperation):
        return sanitized

    if frrdelta_min < FRR_DELTA_MIN_LIMIT:
        sanitized["frrdelta_min"] = float(FRR_DELTA_MIN_LIMIT)
    return sanitized


def read_web_settings() -> dict[str, Any]:
    """Statically read web settings from file without needing WebServer instance."""
    web_settings_file = Path("web_settings.json")
    if web_settings_file.exists():
        try:
            with web_settings_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return sanitize_web_settings(data)
        except Exception:
            pass
    return {}


def get_web_settings() -> dict[str, Any]:
    if _web_server:
        return _web_server.get_web_settings()
    return read_web_settings()
