import atexit
import datetime
import json
import shutil
import sys
import time
from collections import deque
from typing import Any

from . import Configuration as Config
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


class JsonOutput:
    def __init__(self, file_path: str, log_limit: int, exchange: str = "") -> None:
        self.jsonOutputFile: str = file_path
        self.jsonOutput: dict[str, Any] = {}
        self.jsonOutputCoins: dict[str, Any] = {}
        self.jsonOutputCurrency: dict[str, Any] = {}
        self.clearStatusValues()
        self.jsonOutputLog: deque[str] = deque(maxlen=log_limit)
        self.jsonOutput["exchange"] = exchange
        self.jsonOutput["label"] = Config.get("BOT", "label", "Lending Bot")

    def status(self, status: str, time_str: str, days_remaining_msg: str) -> None:
        self.jsonOutput["last_update"] = time_str + days_remaining_msg
        self.jsonOutput["last_status"] = status

    def printline(self, line: str) -> None:
        line = line.replace("\n", " | ")
        self.jsonOutputLog.append(line)

    def writeJsonFile(self) -> None:
        from pathlib import Path

        with Path(self.jsonOutputFile).open("w", encoding="utf-8") as f:
            self.jsonOutput["log"] = list(self.jsonOutputLog)
            f.write(json.dumps(self.jsonOutput, ensure_ascii=True, sort_keys=True))

    def addSectionLog(self, section: str, key: str, value: Any) -> None:
        if section not in self.jsonOutput:
            self.jsonOutput[section] = {}
        if key not in self.jsonOutput[section]:
            self.jsonOutput[section][key] = {}
        self.jsonOutput[section][key] = value

    def statusValue(self, coin: str, key: str, value: Any) -> None:
        if coin not in self.jsonOutputCoins:
            self.jsonOutputCoins[coin] = {}
        self.jsonOutputCoins[coin][key] = str(value)

    def clearStatusValues(self) -> None:
        self.jsonOutputCoins = {}
        self.jsonOutput["raw_data"] = self.jsonOutputCoins
        self.jsonOutputCurrency = {}
        self.jsonOutput["outputCurrency"] = self.jsonOutputCurrency

    def outputCurrency(self, key: str, value: Any) -> None:
        self.jsonOutputCurrency[key] = str(value)


class Logger:
    def __init__(
        self,
        json_file: str = "",
        json_log_size: int = -1,
        exchange: str = "",
    ) -> None:
        self._lent: str = ""
        self._daysRemaining: str = ""
        self.output: JsonOutput | ConsoleOutput
        if json_file != "" and json_log_size != -1:
            self.output = JsonOutput(json_file, json_log_size, exchange)
        else:
            self.output = ConsoleOutput()
        self.refreshStatus()

    @staticmethod
    def timestamp() -> str:
        ts = time.time()
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    def log(self, msg: str) -> None:
        log_message = f"{self.timestamp()} {msg}"
        self.output.printline(log_message)
        self.refreshStatus()

    def log_error(self, msg: str) -> None:
        log_message = f"{self.timestamp()} Error {msg}"
        self.output.printline(log_message)
        if isinstance(self.output, JsonOutput):
            print(log_message)
        self.refreshStatus()

    def offer(self, amt: Any, cur: str, rate: Any, days: str, msg: Any) -> None:
        line = (
            f"{self.timestamp()} Placing {format_amount_currency(amt, cur)} at {format_rate_pct(rate)} for "
            f"{days} days... {self.digestApiMsg(msg)}"
        )
        self.output.printline(line)
        self.refreshStatus()

    def cancelOrder(self, cur: str, msg: Any) -> None:
        line = f"{self.timestamp()} Canceling {cur} order... {self.digestApiMsg(msg)}"
        self.output.printline(line)
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

    def persistStatus(self) -> None:
        if hasattr(self.output, "writeJsonFile"):
            self.output.writeJsonFile()
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
