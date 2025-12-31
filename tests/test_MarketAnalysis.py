"""
Tests for MarketAnalysis module.
"""

import time
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from lendingbot.modules.MarketAnalysis import MarketAnalysis, MarketDataException


@pytest.fixture
def ma_module(tmp_path):
    mock_config = Mock()
    mock_config.get_currencies_list.return_value = ["BTC"]
    # Sensible defaults for ma init
    mock_config.get.side_effect = (
        lambda _s, _k, d=None, _min=None, _max=None: d if d is not None else "0"
    )
    mock_config.getboolean.return_value = False
    mock_config.get_exchange.return_value = "POLONIEX"
    mock_config.get_all_currencies.return_value = ["BTC", "ETH"]

    mock_api = Mock()
    mock_api.return_loan_orders.return_value = {"offers": []}

    return MarketAnalysis(mock_config, mock_api, db_dir=tmp_path)


class TestMarketAnalysis:
    def test_init_and_db_creation(self, ma_module):
        assert ma_module.exchange == "POLONIEX"

        # Test DB connection and table creation
        db_con = ma_module.create_connection("BTC")
        assert db_con is not None
        ma_module.create_rate_table(db_con, 3)

        # Verify table exists
        cursor = db_con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='loans'")
        assert cursor.fetchone() is not None
        db_con.close()

    def test_insert_and_get_rates(self, ma_module):
        db_con = ma_module.create_connection("BTC")
        ma_module.create_rate_table(db_con, 1)

        # rate0, amnt0, percentile
        ma_module.insert_into_db(db_con, ["0.01", "1.0", "0"], levels=1)

        rates = ma_module.get_rates_from_db(db_con, price_levels=["rate0"])
        assert len(rates) == 1
        assert float(rates[0][1]) == 0.01
        db_con.close()

    def test_get_percentile(self, ma_module):
        rates = [0.01, 0.02, 0.03, 0.04, 0.05]
        # lending_style 50 -> median
        perc = ma_module.get_percentile(rates, 50)
        assert perc == 0.03

        perc_np = ma_module.get_percentile(rates, 50)
        assert perc_np == 0.03

    def test_get_rate_suggestion_percentile(self, ma_module):
        # Create a mock DataFrame
        df = pd.DataFrame(
            {
                "time": pd.to_datetime([100, 200, 300], unit="s"),
                "rate0": [0.01, 0.02, 0.03],
            }
        )

        ma_module.lending_style = 50
        with patch.object(ma_module, "get_rate_list", return_value=df):
            suggestion = ma_module.get_rate_suggestion("BTC", method="percentile")
            assert suggestion == 0.02

    def test_get_rate_suggestion_macd(self, ma_module):
        # Need enough data for MACD
        ma_module.MACD_short_win_seconds = 2
        ma_module.MACD_long_win_seconds = 3
        ma_module.data_tolerance = 0
        ma_module.daily_min_multiplier = 1.0

        df = pd.DataFrame(
            {"time": pd.to_datetime([1, 2, 3], unit="s"), "rate0": [0.01, 0.02, 0.03]}
        )

        with patch.object(ma_module, "get_rate_list", return_value=df):
            suggestion = ma_module.get_rate_suggestion("BTC", method="MACD")
            assert suggestion == 0.03

    def test_delete_old_data(self, ma_module):
        db_con = ma_module.create_connection("BTC")
        ma_module.create_rate_table(db_con, 1)

        # Insert old data manually
        old_time = int(time.time()) - 1000
        db_con.execute(
            f"INSERT INTO loans (unixtime, rate0, amnt0, percentile) VALUES ({old_time}, 0.01, 1.0, 0)"
        )
        db_con.commit()

        # Verify it's there
        res = db_con.execute("SELECT count(*) FROM loans").fetchone()
        assert res[0] == 1

        # Delete data older than 500 seconds
        ma_module.delete_old_data(db_con, 500)

        res = db_con.execute("SELECT count(*) FROM loans").fetchone()
        assert res[0] == 0
        db_con.close()

    def test_update_market_once(self, ma_module):
        db_con = ma_module.create_connection("BTC")
        ma_module.create_rate_table(db_con, 1)

        ma_module.api.return_loan_orders.return_value = {"offers": [{"rate": 0.01, "amount": 1.0}]}

        ma_module.update_market_once("BTC", 1, db_con)

        res = db_con.execute("SELECT rate0 FROM loans").fetchone()
        assert float(res[0]) == 0.01
        db_con.close()

    def test_get_rate_suggestion_error_handling(self, ma_module):
        df = pd.DataFrame({"rate0": [0.01, 0.02], "time": pd.to_datetime([1, 2], unit="s")})
        # Test MarketDataException fallback
        with patch.object(ma_module, "get_rate_list") as mock_get:
            # First call (MACD) fails, second call (percentile fallback) succeeds
            mock_get.side_effect = [MarketDataException, df]
            ma_module.lending_style = 50
            suggestion = ma_module.get_rate_suggestion("BTC", method="MACD")
            assert suggestion == 0.015  # median of 0.01 and 0.02

        # Test general exception
        with patch.object(ma_module, "get_rate_list", side_effect=Exception("Unexpected")):
            suggestion = ma_module.get_rate_suggestion("BTC")
            assert suggestion == 0.0

    def test_get_rate_list_logic(self, ma_module):
        db_con = ma_module.create_connection("BTC")
        ma_module.create_rate_table(db_con, 1)

        now = time.time()
        # Insert some points
        db_con.execute(
            f"INSERT INTO loans (unixtime, rate0, amnt0, percentile) VALUES ({now - 10}, 0.01, 1.0, 0)"
        )
        db_con.execute(
            f"INSERT INTO loans (unixtime, rate0, amnt0, percentile) VALUES ({now - 5}, 0.02, 1.0, 0)"
        )
        db_con.commit()

        ma_module.currencies_to_analyse = ["BTC"]
        df = ma_module.get_rate_list("BTC", 60)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        db_con.close()

    def test_utilities(self, ma_module):
        # test get_day_difference
        now = time.time()
        yesterday = now - 86400
        assert ma_module.get_day_difference(yesterday) == 1

        # test prints (just coverage)
        with patch("sys.stdout.write"):
            ma_module.print_traceback(Exception("test"), "msg")
            ma_module.print_exception_error(Exception("test"), "msg", debug=True)

    def test_get_rate_list_errors(self, ma_module):
        # invalid currency
        with pytest.raises(ValueError, match="is not a valid currency"):
            ma_module.get_rate_list("INVALID", 60)

        # currency not analyzed
        ma_module.currencies_to_analyse = []
        assert ma_module.get_rate_list("ETH", 60) == []
