import datetime
import sqlite3
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .Data import truncate
from .ExchangeApi import ApiError


class MarketDataException(Exception):
    pass


class MarketAnalysis:
    def __init__(self, config: Any, api: Any, db_dir: Path | None = None) -> None:
        self.config = config
        self.api = api
        self.currencies_to_analyse = self.config.get_currencies_list(
            "analyseCurrencies", "MarketAnalysis"
        )
        self.update_interval = int(
            self.config.get("MarketAnalysis", "analyseUpdateInterval", 10, 1, 3600)
        )
        self.lending_style = int(self.config.get("MarketAnalysis", "lendingStyle", 75, 1, 99))
        self.recorded_levels = 10

        self.modules_dir = Path(__file__).resolve().parent
        self.top_dir = self.modules_dir.parent
        if db_dir:
            self.db_dir = db_dir
        else:
            self.db_dir = self.top_dir / "market_data"

        self.recorded_levels = int(self.config.get("MarketAnalysis", "recorded_levels", 3, 1, 100))
        self.data_tolerance = float(self.config.get("MarketAnalysis", "data_tolerance", 15, 10, 90))
        self.ma_debug_log = self.config.getboolean("MarketAnalysis", "ma_debug_log")
        self.MACD_long_win_seconds = int(
            self.config.get(
                "MarketAnalysis", "MACD_long_win_seconds", 60 * 30, 60, 60 * 60 * 24 * 7
            )
        )
        self.percentile_seconds = int(
            self.config.get(
                "MarketAnalysis", "percentile_seconds", 60 * 60 * 24, 60 * 60, 60 * 60 * 24 * 14
            )
        )
        keep_sec = max(self.MACD_long_win_seconds, self.percentile_seconds)
        self.keep_history_seconds = int(
            self.config.get(
                "MarketAnalysis",
                "keep_history_seconds",
                int(keep_sec * 1.1),
                int(keep_sec * 1.1),
                60 * 60 * 24 * 14,
            )
        )
        self.MACD_short_win_seconds = int(
            self.config.get(
                "MarketAnalysis",
                "MACD_short_win_seconds",
                int(self.MACD_long_win_seconds / 12),
                1,
                self.MACD_long_win_seconds / 2,
            )
        )
        self.daily_min_multiplier = float(self.config.get("Daily_min", "multiplier", 1.05, 1))
        self.delete_thread_sleep = float(
            self.config.get(
                "MarketAnalysis",
                "delete_thread_sleep",
                self.keep_history_seconds / 2,
                60,
                60 * 60 * 2,
            )
        )
        self.exchange = self.config.get_exchange()

        if len(self.currencies_to_analyse) != 0:
            for currency in self.currencies_to_analyse:
                try:
                    self.api.return_loan_orders(currency, 5)
                except Exception as cur_ex:
                    raise Exception(
                        f"ERROR: You entered an incorrect currency: '{currency}' to analyse the market of, please "
                        f"check your settings. Error message: {cur_ex}"
                    ) from cur_ex
                time.sleep(2)

    def run(self) -> None:
        """
        Main entry point to start recording data. This starts all the other threads.
        """
        for cur in self.currencies_to_analyse:
            db_con = self.create_connection(cur)
            if db_con:
                self.create_rate_table(db_con, self.recorded_levels)
                db_con.close()
        self.run_threads()
        self.run_del_threads()

    def run_threads(self) -> None:
        """
        Start threads for each currency we want to record.
        """
        for cur in self.currencies_to_analyse:
            thread = threading.Thread(target=self.update_market_thread, args=(cur,))
            thread.daemon = True
            thread.start()

    def run_del_threads(self) -> None:
        """
        Start thread to start the DB cleaning threads.
        """
        for cur in self.currencies_to_analyse:
            del_thread = threading.Thread(
                target=self.delete_old_data_thread, args=(cur, self.keep_history_seconds)
            )
            del_thread.daemon = True
            del_thread.start()

    def delete_old_data_thread(self, cur: str, seconds: int) -> None:
        """
        Thread to clean the DB.
        """
        while True:
            self.delete_old_data_once(cur, seconds)
            time.sleep(self.delete_thread_sleep)

    def delete_old_data_once(self, cur: str, seconds: int) -> None:
        """
        Perform a single cleanup of old data for a currency.
        """
        try:
            db_con = self.create_connection(cur)
            if db_con:
                self.delete_old_data(db_con, seconds)
                db_con.close()
        except Exception as ex:
            print(f"Error in MarketAnalysis cleanup: {ex}")
            traceback.print_exc()

    @staticmethod
    def print_traceback(ex: Exception, log_message: str) -> None:
        print(f"{log_message}: {ex}")
        traceback.print_exc()

    @staticmethod
    def print_exception_error(ex: Exception, log_message: str, debug: bool = False) -> None:
        print(f"{log_message}: {ex}")
        if debug:
            ex_type, value, tb = sys.exc_info()
            print(f"DEBUG: Class:{ex.__class__} Args:{ex.args}")
            print(f"DEBUG: Type:{ex_type} Value:{value} LineNo:{tb.tb_lineno if tb else 'N/A'}")
            traceback.print_exc()

    def update_market_thread(self, cur: str, levels: int | None = None) -> None:
        """
        This is where the main work is done for recording the market data.
        """
        if levels is None:
            levels = self.recorded_levels
        db_con = self.create_connection(cur)
        if not db_con:
            return
        while True:
            self.update_market_once(cur, levels, db_con)
            time.sleep(5)

    def update_market_once(self, cur: str, levels: int, db_con: sqlite3.Connection) -> None:
        """
        Perform a single market data update for a currency.
        """
        try:
            raw_data = self.api.return_loan_orders(cur, levels)["offers"]
        except ApiError as ex:
            if "429" in str(ex):
                if self.ma_debug_log:
                    print(
                        "Caught ERR_RATE_LIMIT, sleeping capture and increasing request delay. "
                        f"Current {self.api.req_period}ms"
                    )
                time.sleep(130)
            return
        except Exception as ex:
            if self.ma_debug_log:
                self.print_traceback(ex, "Error in returning data from exchange")
            else:
                print("Error in returning data from exchange, ignoring")
            time.sleep(5)
            return

        market_data = []
        for i in range(levels):
            try:
                market_data.append(str(raw_data[i]["rate"]))
                market_data.append(str(raw_data[i]["amount"]))
            except IndexError:
                market_data.append("5")
                market_data.append("0.1")
        market_data.append("0")  # Percentile field not being filled yet.
        self.insert_into_db(db_con, market_data, levels)

    def insert_into_db(
        self, db_con: sqlite3.Connection, market_data: list[str], levels: int | None = None
    ) -> None:
        if levels is None:
            levels = self.recorded_levels
        insert_sql = "INSERT INTO loans ("
        for level in range(levels):
            insert_sql += f"rate{level}, amnt{level}, "
        insert_sql += "percentile) VALUES ({});".format(",".join(market_data))
        with db_con:
            try:
                db_con.execute(insert_sql)
            except Exception as ex:
                self.print_traceback(ex, "Error inserting market data into DB")

    def delete_old_data(self, db_con: sqlite3.Connection, seconds: int) -> None:
        """
        Delete old data from the database
        """
        del_time = int(time.time()) - seconds
        with db_con:
            query = f"DELETE FROM loans WHERE unixtime < {del_time};"
            cursor = db_con.cursor()
            cursor.execute(query)

    @staticmethod
    def get_day_difference(date_time: str | float) -> int:
        """
        Get the difference in days between the supplied date_time and now.
        """
        date1 = datetime.datetime.fromtimestamp(float(date_time))
        now = datetime.datetime.now()
        diff_days = (now - date1).days
        return diff_days

    def get_rate_list(
        self, cur: str | sqlite3.Connection, seconds: int
    ) -> list[Any] | pd.DataFrame:
        """
        Query the database (cur) for rates that are within the supplied number of seconds and now.
        """
        request_seconds = int(seconds * 1.1)
        full_list = self.config.get_all_currencies()
        if isinstance(cur, sqlite3.Connection):
            db_con = cur
        else:
            if cur not in full_list:
                raise ValueError(f"{cur} is not a valid currency, must be one of {full_list}")
            if cur not in self.currencies_to_analyse:
                return []
            db_con = self.create_connection(cur)  # type: ignore

        if not db_con:
            return []

        price_levels = ["rate0"]
        rates = self.get_rates_from_db(
            db_con, from_date=time.time() - request_seconds, price_levels=price_levels
        )
        if len(rates) == 0:
            if not isinstance(cur, sqlite3.Connection):
                db_con.close()
            return []

        df = pd.DataFrame(rates)

        columns = ["time"]
        columns.extend(price_levels)
        try:
            df.columns = pd.Index(columns)
        except Exception:
            if self.ma_debug_log:
                print(f"DEBUG:get_rate_list: cols: {columns} rates:{rates} db:{db_con}")
            if not isinstance(cur, sqlite3.Connection):
                db_con.close()
            raise

        df.time = pd.to_datetime(df.time, unit="s")
        if len(df) < seconds * (self.data_tolerance / 100):
            if not isinstance(cur, sqlite3.Connection):
                db_con.close()
            return df

        df = df.resample("1s", on="time").mean().ffill()
        if not isinstance(cur, sqlite3.Connection):
            db_con.close()
        return df

    def get_analysis_seconds(self, method: str) -> int:
        if method == "percentile":
            return self.percentile_seconds
        elif method == "MACD":
            return self.MACD_long_win_seconds
        return 0

    def get_rate_suggestion(
        self, cur: str, method: str = "percentile", rates: pd.DataFrame | None = None
    ) -> float:
        """
        Analyses the market data and suggests a lending rate.

        Args:
            cur: The currency to analyse.
            rates: Optional pre-fetched market data.
            method: The analysis method ('percentile' or 'MACD').

        Returns:
            The suggested daily lending rate as a float.
        """
        error_msg = (
            "WARN: Exception found when analysing markets, if this happens for more than a couple minutes "
            "please create a Github issue so we can fix it. Otherwise, you can ignore it. Error"
        )

        try:
            analysis_seconds = self.get_analysis_seconds(method)
            rates_df = self.get_rate_list(cur, analysis_seconds) if rates is None else rates
            if not isinstance(rates_df, pd.DataFrame):
                return 0.0
            if len(rates_df) == 0:
                if self.ma_debug_log:
                    print(f"DEBUG:get_analysis_seconds: cur: {cur} method:{method} rates empty")
                return 0.0
            if method == "percentile":
                return self.get_percentile(
                    rates_df.rate0.values.tolist(), float(self.lending_style)
                )
            if method == "MACD":
                macd_rate = truncate(self.get_MACD_rate(cur, rates_df), 6)
                if self.ma_debug_log:
                    print(
                        f"Cur:{cur}, MACD:{macd_rate:.6f}, Perc:{self.get_percentile(rates_df.rate0.values.tolist(), float(self.lending_style)):.6f}, Best:{rates_df.rate0.iloc[-1]:.6f}"
                    )
                return float(macd_rate)
        except MarketDataException:
            if method != "percentile":
                print(f"Caught exception during {method} analysis, using percentile for now")
                # Need to re-fetch or use existing rates_df if available
                rates_df = (
                    self.get_rate_list(cur, self.get_analysis_seconds("percentile"))
                    if rates is None
                    else rates
                )
                if isinstance(rates_df, pd.DataFrame) and len(rates_df) > 0:
                    return self.get_percentile(
                        rates_df.rate0.values.tolist(), float(self.lending_style)
                    )
            return 0.0
        except Exception as ex:
            self.print_exception_error(ex, error_msg, debug=self.ma_debug_log)
            return 0.0
        return 0.0

    def get_percentile(self, rates: list[float], lending_style: float) -> float:
        """
        Calculates the percentile suggested rate using Numpy.

        Args:
            rates: List of daily rates.
            lending_style: The percentile to target (1-99).

        Returns:
            The calculated percentile rate, truncated to 6 decimals.
        """
        result = float(np.percentile(rates, int(lending_style)))
        return float(truncate(result, 6))

    def get_MACD_rate(self, cur: str, rates_df: pd.DataFrame) -> float:
        """
        Calculates a suggested rate using a simplified MACD (Moving Average Convergence Divergence) strategy.

        Args:
            cur: The currency symbol.
            rates_df: DataFrame containing market data.

        Returns:
            The suggested rate based on short and long moving average comparison.

        Raises:
            MarketDataException: If there isn't enough data to perform analysis.
        """
        analysis_seconds = self.get_analysis_seconds("MACD")
        if len(rates_df) < analysis_seconds * (self.data_tolerance / 100):
            print(
                f"{cur} : Need more data for analysis, still collecting. I have {len(rates_df)}/{int(analysis_seconds * (self.data_tolerance / 100))} records"
            )
            raise MarketDataException

        # tail() returns a Series, mean() returns a scalar
        short_rate = float(rates_df.rate0.tail(self.MACD_short_win_seconds).mean())
        long_rate = float(rates_df.rate0.tail(self.MACD_long_win_seconds).mean())

        if self.ma_debug_log:
            sys.stdout.write("Short higher: ") if short_rate > long_rate else sys.stdout.write(
                "Long  higher: "
            )

        if short_rate > long_rate:
            if rates_df.rate0.iloc[-1] < short_rate:
                return float(short_rate * self.daily_min_multiplier)
            else:
                return float(rates_df.rate0.iloc[-1] * self.daily_min_multiplier)
        else:
            return float(long_rate * self.daily_min_multiplier)

    def create_connection(self, cur: str, db_path: str | None = None) -> sqlite3.Connection | None:
        if db_path is None:
            prefix = self.config.get_exchange()

            db_path_obj = self.db_dir / f"{prefix}-{cur}.db"
            db_path = str(db_path_obj)
        try:
            con = sqlite3.connect(db_path)
            return con
        except sqlite3.Error as ex:
            print(ex)
            return None

    def create_rate_table(self, db_con: sqlite3.Connection, levels: int) -> None:
        with db_con:
            cursor = db_con.cursor()
            create_table_sql = (
                "CREATE TABLE IF NOT EXISTS loans (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                + "unixtime integer(4) not null default (strftime('%s','now')),"
            )
            for level in range(levels):
                create_table_sql += f"rate{level} FLOAT, "
                create_table_sql += f"amnt{level} FLOAT, "
            create_table_sql += "percentile FLOAT);"
            cursor.execute("PRAGMA journal_mode=wal")
            cursor.execute(create_table_sql)

    def get_rates_from_db(
        self,
        db_con: sqlite3.Connection,
        from_date: float | None = None,
        price_levels: list[str] | None = None,
    ) -> list[Any]:
        if price_levels is None:
            price_levels = ["rate0"]
        with db_con:
            cursor = db_con.cursor()
            query = "SELECT unixtime, {} FROM loans ".format(",".join(price_levels))
            if from_date is not None:
                query += f"WHERE unixtime > {from_date}"
            query += ";"
            cursor.execute(query)
            return cursor.fetchall()
