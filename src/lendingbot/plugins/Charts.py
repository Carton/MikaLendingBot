import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .Plugin import Plugin


DB_PATH = "market_data/loan_history.sqlite3"


class Charts(Plugin):
    def __init__(self, cfg1: Any, api1: Any, log1: Any, notify_config1: Any) -> None:
        super().__init__(cfg1, api1, log1, notify_config1)
        self.db: sqlite3.Connection | None = None
        self.last_dump: float = 0
        self.dump_interval: int = 21600
        self.history_file: str = "logs/history.json"
        self.activeCurrencies: list[str] = []

    def on_bot_init(self) -> None:
        super().on_bot_init()

        # If there's no history database, can't use this
        if not Path(DB_PATH).is_file():
            self.log.log_error("DB Doesn't Exist. 'AccountStats' plugin must be enabled.")
            return

        self.log.addSectionLog("plugins", "charts", {"navbar": True})

        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.last_dump = 0
        self.dump_interval = int(self.config.get("CHARTS", "DumpInterval", 21600))
        # Note: history_file is hardcoded because frontend expects it at logs/history.json
        self.activeCurrencies = self.config.get_all_currencies()

    def before_lending(self) -> None:
        return

    def after_lending(self) -> None:
        if self.get_db_version() > 0 and self.last_dump + self.dump_interval < time.time():
            self.log.log("Dumping Charts Data")
            self.dump_history()
            self.last_dump = time.time()

    def get_db_version(self) -> int:
        if self.db:
            row = self.db.execute("PRAGMA user_version").fetchone()
            return int(row[0]) if row else 0
        return 0

    def dump_history(self) -> None:
        if not self.db:
            return

        cursor = self.db.cursor()

        data: dict[str, list[list[Any]]] = {}
        placeholder = "?"
        placeholders = ", ".join(placeholder for _ in self.activeCurrencies)

        # Get distinct coins
        query = f"SELECT DISTINCT currency FROM history WHERE currency IN ({placeholders}) ORDER BY currency DESC"
        cursor.execute(query, self.activeCurrencies)
        for i in cursor:
            data[i[0]] = []

        # Loop over the coins and get data for each
        for coin in data:
            running_total = 0.0

            cursor.execute(
                "SELECT strftime('%s', strftime('%Y-%m-%d 00:00:00', close)) ts, round(SUM(earned), 8) i "
                f"FROM history WHERE currency = '{coin}' GROUP BY ts ORDER BY ts"
            )
            for row in cursor:
                running_total += float(row[1])
                data[coin].append([int(row[0]), float(row[1]), float(running_total)])

        # Dump data to file
        with Path(self.history_file).open("w", encoding="utf-8") as hist:
            hist.write(json.dumps(data))

        self.log.log("Charts Plugin: History dumped. You can open charts.html.")
        cursor.close()
