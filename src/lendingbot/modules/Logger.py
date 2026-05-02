from __future__ import annotations

import atexit
import contextlib
import datetime
import json
import logging
import logging.handlers
import shutil
import sys
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable

from .Notify import send_notification
from .Utils import format_amount_currency, format_rate_pct


class ConsoleOutput:
    def __init__(self) -> None:
        self._status: str = ""
        atexit.register(self._exit)

    def _exit(self) -> None:
        self._status += "  "  # In case the shell added a ^C
        self.status("")

    def status(self, msg: Any, _time_str: str = "", _days_remaining_msg: str = "") -> None:
        status = str(msg)
        cols = shutil.get_terminal_size().columns
        if msg != "" and len(status) > cols:
            # truncate status, try preventing console bloating
            status = str(msg)[: cols - 4] + "..."
        update = "\r"
        update += status
        update += " " * (len(self._status) - len(status))
        update += "\b" * (len(self._status) - len(status))
        sys.stderr.write(update)
        self._status = status

    def printline(self, line: str) -> None:
        update = "\r"
        update += line + " " * (len(self._status) - len(line)) + "\n"
        update += self._status
        sys.stderr.write(update)


class StatsOutput:
    def __init__(
        self, file_path: str, log_limit: int, exchange: str = "", label: str = "Lending Bot"
    ) -> None:
        self.stats_file: str = file_path
        self.stats_output: dict[str, Any] = {}
        self.stats_coins: dict[str, Any] = {}
        self.stats_currency: dict[str, Any] = {}
        self.clearStatusValues()
        self.recent_logs: deque[str] = deque(maxlen=log_limit)
        self.stats_output["exchange"] = exchange
        self.stats_output["label"] = label

        # Write initial stats file on startup
        self.status("Starting...", "", "")
        self.writeStatsFile()

    def status(self, status: str, time_str: str, days_remaining_msg: str) -> None:
        self.stats_output["last_update"] = time_str + days_remaining_msg
        self.stats_output["last_status"] = status

    def printline(self, line: str) -> None:
        line = line.replace("\n", " | ")
        self.recent_logs.append(line)

    def writeStatsFile(self) -> None:
        from pathlib import Path

        path = Path(self.stats_file)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps(self.stats_output, ensure_ascii=True, sort_keys=True))

    def get_recent_logs(self) -> list[str]:
        return list(self.recent_logs)

    def addSectionLog(self, section: str, key: str, value: Any) -> None:
        if section not in self.stats_output:
            self.stats_output[section] = {}
        if key not in self.stats_output[section]:
            self.stats_output[section][key] = {}
        self.stats_output[section][key] = value

    def statusValue(self, coin: str, key: str, value: Any) -> None:
        if coin not in self.stats_coins:
            self.stats_coins[coin] = {}
        self.stats_coins[coin][key] = str(value)

    def clearStatusValues(self) -> None:
        self.stats_coins = {}
        self.stats_output["raw_data"] = self.stats_coins
        self.stats_currency = {}
        self.stats_output["outputCurrency"] = self.stats_currency

    def outputCurrency(self, key: str, value: Any) -> None:
        self.stats_currency[key] = str(value)


class Logger:
    def __init__(
        self,
        stats_file: str = "",
        recent_logs_limit: int = -1,
        log_file: str = "",
        log_file_days: int = 10,
        exchange: str = "",
        label: str = "Lending Bot",
    ) -> None:
        self._lent: str = ""
        self._daysRemaining: str = ""
        self.output: StatsOutput | ConsoleOutput
        if stats_file != "" and recent_logs_limit != -1:
            self.output = StatsOutput(stats_file, recent_logs_limit, exchange, label)
        else:
            self.output = ConsoleOutput()

        # Set up text file logger
        self.file_logger: logging.Logger | None = None
        self.callbacks: list[Callable[[str], None]] = []
        if log_file:
            path = Path(log_file)
            if path.parent:
                path.parent.mkdir(parents=True, exist_ok=True)
            self.file_logger = logging.getLogger("LendingBotTextLog")
            self.file_logger.setLevel(logging.INFO)
            # Remove any existing handlers to prevent duplicate logs if re-initialized
            self.file_logger.handlers = []
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(path),
                when="midnight",
                interval=1,
                backupCount=log_file_days,
                encoding="utf-8",
            )
            # Use a simple formatter since the lines already contain timestamps
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.file_logger.addHandler(handler)

        self.refreshStatus()

    @staticmethod
    def timestamp() -> str:
        ts = time.time()
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    def _broadcast(self, msg: str) -> None:
        for callback in list(self.callbacks):
            with contextlib.suppress(Exception):
                callback(msg)

    def log(self, msg: str) -> None:
        log_message = f"{self.timestamp()} {msg}"
        self.output.printline(log_message)
        if self.file_logger:
            self.file_logger.info(log_message)
        self._broadcast(log_message)
        self.refreshStatus()

    def log_error(self, msg: str) -> None:
        log_message = f"{self.timestamp()} Error {msg}"
        self.output.printline(log_message)
        if self.file_logger:
            self.file_logger.error(log_message)
        if isinstance(self.output, StatsOutput):
            print(log_message)
        self._broadcast(log_message)
        self.refreshStatus()

    def offer(
        self,
        amt: Any,
        cur: str,
        rate: Any,
        days: str,
        msg: Any,
        original_rate: float | None = None,
    ) -> None:
        rate_info = format_rate_pct(rate)
        # If original_rate provided and compete adjustment happened, show it
        if original_rate is not None and abs(float(rate) - original_rate) > 1e-10:
            adjustment = float(rate) - original_rate
            rate_info = f"{format_rate_pct(rate)} ({adjustment * 100:+.5f}% compete)"

        result = self.digestApiMsg(msg)
        status = "✓" if result == "Loan order placed." else result

        line = f"{self.timestamp()} [{cur}] Loan: {format_amount_currency(amt, cur)} @ {rate_info} for {days} days {status}"
        self.output.printline(line)
        if self.file_logger:
            self.file_logger.info(line)
        self._broadcast(line)
        self.refreshStatus()

    def cancelOrder(self, cur: str, msg: Any) -> None:
        line = f"{self.timestamp()} Canceling {cur} order... {self.digestApiMsg(msg)}"
        self.output.printline(line)
        if self.file_logger:
            self.file_logger.info(line)
        self._broadcast(line)
        self.refreshStatus()

    def refreshStatus(self, lent: str = "", days_remaining: str = "") -> None:
        if lent != "":
            self._lent = lent
        if days_remaining != "":
            self._daysRemaining = days_remaining
        self.output.status(self._lent, self.timestamp(), self._daysRemaining)

    def addSectionLog(self, section: str, key: str, value: Any) -> None:
        if hasattr(self.output, "addSectionLog"):
            self.output.addSectionLog(section, key, value)

    def updateStatusValue(self, coin: str, key: str, value: Any) -> None:
        if hasattr(self.output, "statusValue"):
            self.output.statusValue(coin, key, value)

    def updateOutputCurrency(self, key: str, value: Any) -> None:
        if hasattr(self.output, "outputCurrency"):
            self.output.outputCurrency(key, value)

    def get_recent_logs(self) -> list[str]:
        if hasattr(self.output, "get_recent_logs"):
            return self.output.get_recent_logs()
        return []

    def persistStatus(self) -> None:
        if hasattr(self.output, "writeStatsFile"):
            self.output.writeStatsFile()
        if hasattr(self.output, "clearStatusValues"):
            self.output.clearStatusValues()

    @staticmethod
    def digestApiMsg(msg: Any) -> str:
        if isinstance(msg, dict):
            return str(msg.get("message", msg.get("error", "")))
        return str(msg) if msg is not None else ""

    @staticmethod
    def notify(msg: str, notify_conf: dict[str, Any]) -> None:
        if notify_conf.get("enable_notifications"):
            send_notification(msg, notify_conf)
