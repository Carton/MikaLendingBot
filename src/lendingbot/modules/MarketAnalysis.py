import datetime
import math
import sqlite3 as sqlite
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

import pandas as pd

from . import Configuration as Config
from .Data import truncate
from .ExchangeApi import ApiError


# Improvements
# [ ] Provide something that takes into account dust offers. (The golden cross works well on BTC, not slower markets)
# [ ] RE: above. Weighted rate.
# [ ] Add docstring to everything
# [ ] Unit tests

# NOTES
# * A possible solution for the dust problem is take the top 10 offers and if the offer amount is less than X% of the
#   total available, ignore it as dust.


try:
    import numpy as np

    use_numpy = True
except ImportError as ex:
    print(
        f"WARN: Module Numpy not found, using manual percentile method instead. It is recommended to install Numpy. Error: {ex}"
    )
    use_numpy = False


class MarketDataException(Exception):
    pass


class MarketAnalysis:
    def __init__(self, config: Any, api: Any) -> None:
        self.currencies_to_analyse = config.get_currencies_list(
            "analyseCurrencies", "MarketAnalysis"
        )
        self.update_interval = int(
            config.get("MarketAnalysis", "analyseUpdateInterval", 10, 1, 3600)
        )
        self.api = api
        self.lending_style = int(config.get("MarketAnalysis", "lendingStyle", 75, 1, 99))
        self.recorded_levels = 10

        self.modules_dir = Path(__file__).resolve().parent
        self.top_dir = self.modules_dir.parent
        self.db_dir = self.top_dir / "market_data"
        self.recorded_levels = int(config.get("MarketAnalysis", "recorded_levels", 3, 1, 100))
        self.data_tolerance = float(config.get("MarketAnalysis", "data_tolerance", 15, 10, 90))
        self.ma_debug_log = config.getboolean("MarketAnalysis", "ma_debug_log")
        self.MACD_long_win_seconds = int(
            config.get("MarketAnalysis", "MACD_long_win_seconds", 60 * 30, 60, 60 * 60 * 24 * 7)
        )
        self.percentile_seconds = int(
            config.get(
                "MarketAnalysis", "percentile_seconds", 60 * 60 * 24, 60 * 60, 60 * 60 * 24 * 14
            )
        )
        keep_sec = max(self.MACD_long_win_seconds, self.percentile_seconds)
        self.keep_history_seconds = int(
            config.get(
                "MarketAnalysis",
                "keep_history_seconds",
                int(keep_sec * 1.1),
                int(keep_sec * 1.1),
                60 * 60 * 24 * 14,
            )
        )
        self.MACD_short_win_seconds = int(
            config.get(
                "MarketAnalysis",
                "MACD_short_win_seconds",
                int(self.MACD_long_win_seconds / 12),
                1,
                self.MACD_long_win_seconds / 2,
            )
        )
        self.daily_min_multiplier = float(config.get("Daily_min", "multiplier", 1.05, 1))
        self.delete_thread_sleep = float(
            config.get(
                "MarketAnalysis",
                "delete_thread_sleep",
                self.keep_history_seconds / 2,
                60,
                60 * 60 * 2,
            )
        )
        self.exchange = config.get_exchange()

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
            try:
                db_con = self.create_connection(cur)
                if db_con:
                    self.delete_old_data(db_con, seconds)
                    db_con.close()
            except Exception as ex:
                print(f"Error in MarketAnalysis: {ex}")
                traceback.print_exc()
            time.sleep(self.delete_thread_sleep)

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
                continue
            except Exception as ex:
                if self.ma_debug_log:
                    self.print_traceback(ex, "Error in returning data from exchange")
                else:
                    print("Error in returning data from exchange, ignoring")
                time.sleep(5)
                continue

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
            time.sleep(5)

    def insert_into_db(
        self, db_con: sqlite.Connection, market_data: list[str], levels: int | None = None
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

    def delete_old_data(self, db_con: sqlite.Connection, seconds: int) -> None:
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

    def get_rate_list(self, cur: str | sqlite.Connection, seconds: int) -> list[Any] | pd.DataFrame:
        """
        Query the database (cur) for rates that are within the supplied number of seconds and now.
        """
        request_seconds = int(seconds * 1.1)
        full_list = Config.get_all_currencies()
        if isinstance(cur, sqlite.Connection):
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
            if not isinstance(cur, sqlite.Connection):
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
            if not isinstance(cur, sqlite.Connection):
                db_con.close()
            raise

        df.time = pd.to_datetime(df.time, unit="s")
        if len(df) < seconds * (self.data_tolerance / 100):
            if not isinstance(cur, sqlite.Connection):
                db_con.close()
            return df

        df = df.resample("1s", on="time").mean().ffill()
        if not isinstance(cur, sqlite.Connection):
            db_con.close()
        return df

    def get_analysis_seconds(self, method: str) -> int:
        if method == "percentile":
            return self.percentile_seconds
        elif method == "MACD":
            return self.MACD_long_win_seconds
        return 0

    def get_rate_suggestion(
        self, cur: str, rates: pd.DataFrame | None = None, method: str = "percentile"
    ) -> float:
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

    @staticmethod
    def percentile(N: list[float], percent: float, key: Any = lambda x: x) -> float:
        if not N:
            return 0.0
        k = (len(N) - 1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(key(N[int(k)]))
        d0 = key(N[int(f)]) * (c - k)
        d1 = key(N[int(c)]) * (k - f)
        return float(d0 + d1)

    def get_percentile(
        self, rates: list[float], lending_style: float, use_numpy_val: bool = use_numpy
    ) -> float:
        if use_numpy_val:
            result = float(np.percentile(rates, int(lending_style)))
        else:
            result = self.percentile(sorted(rates), lending_style / 100.0)
        return float(truncate(result, 6))

    def get_MACD_rate(self, cur: str, rates_df: pd.DataFrame) -> float:
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

    def create_connection(self, cur: str, db_path: str | None = None) -> sqlite.Connection | None:
        if db_path is None:
            prefix = Config.get_exchange()

            db_path_obj = self.db_dir / f"{prefix}-{cur}.db"
            db_path = str(db_path_obj)
        try:
            con = sqlite.connect(db_path)
            return con
        except sqlite.Error as ex:
            print(ex)
            return None

    def create_rate_table(self, db_con: sqlite.Connection, levels: int) -> None:
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
        db_con: sqlite.Connection,
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
