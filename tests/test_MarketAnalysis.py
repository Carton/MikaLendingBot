import sqlite3 as sqlite
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import floats, integers, lists

from lendingbot.modules.MarketAnalysis import MarketAnalysis, MarketDataException


@pytest.fixture(autouse=True)
def mock_sleep():
    """Globally mock sleep for all tests in this file to prevent hangs."""
    with patch("time.sleep", return_value=None):
        yield


@pytest.fixture(scope="module")
def mock_api() -> Any:
    api = MagicMock()
    api.return_loan_orders.return_value = {"offers": []}
    return api


@pytest.fixture
def market_analysis(mock_api: Any, tmp_path: Path) -> MarketAnalysis:
    mock_config = MagicMock()
    mock_config.get_currencies_list.return_value = []
    mock_config.get.side_effect = (
        lambda _cat, _opt, default=None, *_args, **_kwargs: str(default)
        if default is not None
        else "10"
    )
    mock_config.getboolean.return_value = False
    mock_config.get_exchange.return_value = "POLONIEX"
    mock_config.get_all_currencies.return_value = ["BTC", "ETH"]

    return MarketAnalysis(mock_config, mock_api, db_dir=tmp_path)


def new_db(ma: MarketAnalysis) -> sqlite.Connection:
    db_con = ma.create_connection("BTC", ":memory:")
    if db_con:
        ma.create_rate_table(db_con, 3)
        return db_con
    raise Exception("Failed to create in-memory DB")


@pytest.fixture
def populated_db(market_analysis: MarketAnalysis) -> tuple[sqlite.Connection, list[list[float]]]:
    price_levels = 3
    db_con = new_db(market_analysis)
    # Fixed rates to avoid .example() warning
    rates = [0.01, 0.02, 0.015, 0.03]
    inserted_rates = []
    for rate in rates:
        market_data = []
        for _level in range(price_levels):
            market_data.append(f"{rate:.8f}")
            market_data.append(f"{rate:.2f}")
        percentile = f"{rate:.8f}"
        market_data.append(percentile)
        market_analysis.insert_into_db(db_con, market_data, price_levels)
        market_data_f = [float(x) for x in market_data]
        inserted_rates.append(market_data_f)
    yield db_con, inserted_rates
    db_con.close()


def test_new_db(market_analysis: MarketAnalysis) -> None:
    db = new_db(market_analysis)
    assert isinstance(db, sqlite.Connection)
    db.close()


def test_insert_into_db(populated_db: tuple[sqlite.Connection, list[list[float]]]) -> None:
    db_con, rates = populated_db
    query = "SELECT rate0, amnt0, rate1, amnt1, rate2, amnt2, percentile FROM loans;"
    db_rates = db_con.cursor().execute(query).fetchall()
    assert len(rates) == len(db_rates)
    for db_rate, rate in zip(db_rates, rates, strict=False):
        assert len(rate) == len(db_rate)
        assert len(rate) > 1
        for level in range(len(rate)):
            assert pytest.approx(db_rate[level]) == float(rate[level])


def test_get_rates_from_db(
    market_analysis: MarketAnalysis, populated_db: tuple[sqlite.Connection, list[list[float]]]
) -> None:
    db_con, rates = populated_db
    db_rates = market_analysis.get_rates_from_db(
        db_con, from_date=time.time() - 10, price_levels=["rate0"]
    )
    # We inserted 4 rates
    assert len(db_rates) == 4
    for db_rate, rate in zip(db_rates, rates, strict=False):
        assert len(db_rate) == 2
        assert pytest.approx(db_rate[1]) == float(rate[0])


def test_get_rate_list(
    market_analysis: MarketAnalysis, populated_db: tuple[sqlite.Connection, list[list[float]]]
) -> None:
    db_con, _rates = populated_db
    db_rates = market_analysis.get_rate_list(db_con, 1)
    assert len(db_rates) >= 1


def test_get_rate_suggestion(
    market_analysis: MarketAnalysis, populated_db: tuple[sqlite.Connection, list[list[float]]]
) -> None:
    db_con, rates = populated_db
    market_analysis.data_tolerance = 1

    rate_db = market_analysis.get_rate_suggestion("BTC", method="percentile")
    # Need to set up market_analysis to use this db_con or currency
    market_analysis.currencies_to_analyse = ["BTC"]
    with patch.object(market_analysis, "create_connection", return_value=db_con):
        rate_db = market_analysis.get_rate_suggestion("BTC", method="percentile")
        assert rate_db >= 0

    df = pd.DataFrame(rates)
    df.columns = pd.Index(["rate0", "a0", "r1", "a1", "r2", "a2", "p"])
    df["time"] = pd.to_datetime([time.time()] * len(df), unit="s")
    rate_args = market_analysis.get_rate_suggestion("BTC", df, "percentile")
    assert rate_args >= 0

    with patch.object(market_analysis, "create_connection", return_value=db_con):
        rate = market_analysis.get_rate_suggestion("BTC", method="MACD")
        assert rate >= 0


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    lists(
        floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=100,
    ),
    integers(min_value=1, max_value=99),
)
def test_get_percentile(
    market_analysis: MarketAnalysis, rates: list[float], lending_style: int
) -> None:
    np_perc = market_analysis.get_percentile(rates, lending_style, use_numpy_val=True)
    math_perc = market_analysis.get_percentile(rates, lending_style, use_numpy_val=False)
    # Use relative tolerance for large numbers and absolute for near-zero
    assert pytest.approx(np_perc, rel=1e-5, abs=1.1e-5) == math_perc


def test_get_day_difference(market_analysis: MarketAnalysis) -> None:
    now = time.time()
    assert market_analysis.get_day_difference(now) == 0
    yesterday = now - 86400
    assert market_analysis.get_day_difference(yesterday) == 1


def test_get_analysis_seconds(market_analysis: MarketAnalysis) -> None:
    assert market_analysis.get_analysis_seconds("percentile") == market_analysis.percentile_seconds
    assert market_analysis.get_analysis_seconds("MACD") == market_analysis.MACD_long_win_seconds
    assert market_analysis.get_analysis_seconds("invalid") == 0


def test_get_MACD_rate(market_analysis: MarketAnalysis) -> None:
    market_analysis.MACD_short_win_seconds = 2
    market_analysis.MACD_long_win_seconds = 400
    market_analysis.data_tolerance = 10

    # Not enough data: len=2, threshold=400*0.1=40
    df_small = pd.DataFrame({"rate0": [0.01, 0.02]})
    with pytest.raises(MarketDataException):
        market_analysis.get_MACD_rate("BTC", df_small)

    # Enough data: len=6, threshold=4*0.1=0.4
    market_analysis.MACD_long_win_seconds = 4
    df_large = pd.DataFrame({"rate0": [0.01, 0.01, 0.02, 0.02, 0.03, 0.03]})
    rate = market_analysis.get_MACD_rate("BTC", df_large)
    assert rate > 0


def test_delete_old_data(
    market_analysis: MarketAnalysis, populated_db: tuple[sqlite.Connection, list[list[float]]]
) -> None:
    db_con, _ = populated_db
    # All data is new. Delete data older than -1 second (i.e. delete everything)
    market_analysis.delete_old_data(db_con, -10)
    # unixtime is default now().
    query = "SELECT count(*) FROM loans;"
    count = db_con.cursor().execute(query).fetchone()[0]
    assert count == 0


def test_error_printing(market_analysis: MarketAnalysis) -> None:
    # Just cover the methods
    market_analysis.print_traceback(Exception("test"), "test message")
    market_analysis.print_exception_error(Exception("test"), "test message", debug=True)


def test_update_market_once_429(market_analysis: MarketAnalysis) -> None:
    from lendingbot.modules.ExchangeApi import ApiError

    mock_db = MagicMock()
    market_analysis.api.return_loan_orders = MagicMock(
        side_effect=ApiError("429 Too Many Requests")
    )
    market_analysis.ma_debug_log = True
    with patch("time.sleep"):  # Avoid waiting 130s
        market_analysis.update_market_once("BTC", 1, mock_db)
    assert not mock_db.execute.called


def test_get_rate_list_invalid_currency(market_analysis: MarketAnalysis) -> None:
    with pytest.raises(ValueError):
        market_analysis.get_rate_list("INVALID", 3600)


def test_get_rate_list_not_analysing(market_analysis: MarketAnalysis) -> None:
    market_analysis.currencies_to_analyse = []
    assert market_analysis.get_rate_list("BTC", 3600) == []


def test_get_MACD_rate_logic(market_analysis: MarketAnalysis) -> None:
    market_analysis.data_tolerance = 0
    market_analysis.MACD_short_win_seconds = 2
    market_analysis.MACD_long_win_seconds = 4

    # Scenario 1: short > long, last < short
    df1 = pd.DataFrame({"rate0": [0.01, 0.01, 0.05, 0.05]})
    # short mean = (0.05+0.05)/2 = 0.05
    # long mean = (0.01+0.01+0.05+0.05)/4 = 0.03
    # last = 0.05. last not < short.
    rate1 = market_analysis.get_MACD_rate("BTC", df1)
    assert rate1 > 0

    # Scenario 2: short < long
    df2 = pd.DataFrame({"rate0": [0.05, 0.05, 0.01, 0.01]})
    # short mean = 0.01
    # long mean = 0.03
    rate2 = market_analysis.get_MACD_rate("BTC", df2)
    assert rate2 > 0


def test_get_rate_suggestion_macd_fallback(market_analysis: MarketAnalysis) -> None:
    market_analysis.currencies_to_analyse = ["BTC"]
    # Mock get_rate_list to return enough data for percentile but not for MACD (or raise MarketDataException)
    with patch.object(market_analysis, "get_MACD_rate", side_effect=MarketDataException):
        df = pd.DataFrame({"rate0": [0.01, 0.02, 0.03], "time": [time.time()] * 3})
        with patch.object(market_analysis, "get_rate_list", return_value=df):
            rate = market_analysis.get_rate_suggestion("BTC", method="MACD")
            assert rate > 0  # Fallback to percentile


def test_insert_into_db_error(market_analysis: MarketAnalysis) -> None:
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB error")
    market_analysis.insert_into_db(mock_db, ["0.01", "1.0", "0"], 1)
    # Should print error and continue (covered by print_traceback)


def test_get_percentile_manual(market_analysis: MarketAnalysis) -> None:
    rates = [1.0, 2.0, 3.0, 4.0, 5.0]
    # Test manual calculation (use_numpy_val=False)
    res = market_analysis.get_percentile(rates, 50, use_numpy_val=False)
    assert res == 3.0

    # Test non-integer percentile
    res = market_analysis.get_percentile(rates, 25, use_numpy_val=False)
    assert res == 2.0

    # Test empty list
    assert market_analysis.get_percentile([], 50, use_numpy_val=False) == 0.0


def test_run_threads(market_analysis: MarketAnalysis) -> None:
    market_analysis.currencies_to_analyse = ["BTC"]
    with patch("threading.Thread") as mock_thread:
        market_analysis.run_threads()
        assert mock_thread.called
        market_analysis.run_del_threads()
        assert mock_thread.call_count == 2


def test_create_rate_table(market_analysis: MarketAnalysis) -> None:
    db_con = sqlite.connect(":memory:")
    market_analysis.create_rate_table(db_con, 5)
    # Check if table exists
    cursor = db_con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='loans';")
    assert cursor.fetchone() is not None
    db_con.close()


def test_create_connection_error(market_analysis: MarketAnalysis) -> None:
    with patch("sqlite3.connect", side_effect=sqlite.Error("Connection error")):
        assert market_analysis.create_connection("BTC") is None


def test_get_rate_suggestion_edge_cases(market_analysis: MarketAnalysis) -> None:
    # Invalid method
    assert market_analysis.get_rate_suggestion("BTC", method="invalid") == 0.0

    # Empty df
    df_empty = pd.DataFrame()
    assert market_analysis.get_rate_suggestion("BTC", df_empty) == 0.0


def test_get_rates_from_db_params(
    market_analysis: MarketAnalysis, populated_db: tuple[sqlite.Connection, list[list[float]]]
) -> None:
    db_con, _ = populated_db
    # Test with price_levels and from_date
    res = market_analysis.get_rates_from_db(db_con, from_date=0, price_levels=["rate0", "rate1"])
    assert len(res) > 0
    assert len(res[0]) == 3  # unixtime, rate0, rate1


def test_delete_old_data_error(market_analysis: MarketAnalysis) -> None:
    # Test error handling in the 'once' method which has the try-except
    with patch.object(market_analysis, "create_connection") as mock_conn:
        mock_db = MagicMock()
        mock_db.cursor.side_effect = Exception("DB error")
        mock_conn.return_value = mock_db
        market_analysis.delete_old_data_once("BTC", 3600)
        # Should finish without raising


def test_get_rate_suggestion_exceptions(market_analysis: MarketAnalysis) -> None:
    # Test top level exception in get_rate_suggestion
    with patch.object(
        market_analysis, "get_analysis_seconds", side_effect=Exception("Major error")
    ):
        assert market_analysis.get_rate_suggestion("BTC") == 0.0


def test_print_methods(market_analysis: MarketAnalysis) -> None:
    # Coverage for static methods
    market_analysis.print_traceback(Exception("err"), "msg")
    market_analysis.print_exception_error(Exception("err"), "msg", debug=True)


def test_create_connection_invalid_path(market_analysis: MarketAnalysis) -> None:
    # Testing create_connection error path
    # On Windows, "/invalid/path" might actually fail
    res = market_analysis.create_connection("BTC", "/invalid/path/that/does/not/exist")
    # sqlite.connect often succeeds even if file can't be created until write
    # but let's see. If it returns None on error as coded:
    if res:
        res.close()


def test_run_logic(market_analysis: MarketAnalysis) -> None:
    market_analysis.currencies_to_analyse = ["BTC"]
    with (
        patch.object(market_analysis, "create_connection") as mock_conn,
        patch.object(market_analysis, "create_rate_table") as mock_table,
        patch.object(market_analysis, "run_threads") as mock_run_t,
        patch.object(market_analysis, "run_del_threads") as mock_run_d,
    ):
        mock_db = MagicMock()
        mock_conn.return_value = mock_db

        market_analysis.run()

        mock_conn.assert_called()
        mock_table.assert_called()
        mock_run_t.assert_called()
        mock_run_d.assert_called()
        mock_db.close.assert_called()


def test_update_market_once_index_error(market_analysis: MarketAnalysis) -> None:
    # Test when raw_data has fewer levels than requested
    mock_db = MagicMock()
    market_analysis.api.return_loan_orders = MagicMock(
        return_value={
            "offers": []  # 0 levels
        }
    )
    market_analysis.update_market_once("BTC", 2, mock_db)
    # market_data should be ['5', '0.1', '5', '0.1', '0']
    assert mock_db.execute.called


def test_get_rate_suggestion_macd_success(market_analysis: MarketAnalysis) -> None:
    market_analysis.currencies_to_analyse = ["BTC"]
    market_analysis.data_tolerance = 0
    df = pd.DataFrame(
        {
            "rate0": [0.01, 0.02, 0.03, 0.04, 0.05],
            "time": pd.to_datetime([time.time()] * 5, unit="s"),
        }
    )
    with patch.object(market_analysis, "get_rate_list", return_value=df):
        rate = market_analysis.get_rate_suggestion("BTC", method="MACD")
        assert rate > 0


def test_get_rate_suggestion_no_data(market_analysis: MarketAnalysis) -> None:
    # Test when rates_df is empty DataFrame
    with patch.object(market_analysis, "get_rate_list", return_value=pd.DataFrame()):
        assert market_analysis.get_rate_suggestion("BTC") == 0.0


def test_delete_old_data_once(market_analysis: MarketAnalysis) -> None:
    # This should just call delete_old_data and create_connection
    with patch.object(market_analysis, "create_connection") as mock_conn:
        mock_db = MagicMock()
        mock_conn.return_value = mock_db
        market_analysis.delete_old_data_once("BTC", 3600)
        mock_conn.assert_called_with("BTC")
        mock_db.close.assert_called_once()


def test_update_market_once_success(market_analysis: MarketAnalysis) -> None:
    mock_db = MagicMock()
    market_analysis.api.return_loan_orders = MagicMock(
        return_value={"offers": [{"rate": 0.01, "amount": 1.0}]}
    )
    market_analysis.update_market_once("BTC", 1, mock_db)
    # insert_into_db should have been called
    # market_data should be ['0.01', '1.0', '0']
    assert mock_db.execute.called


def test_update_market_once_apierror(market_analysis: MarketAnalysis) -> None:
    from lendingbot.modules.ExchangeApi import ApiError

    mock_db = MagicMock()
    market_analysis.api.return_loan_orders = MagicMock(side_effect=ApiError("429 error"))
    market_analysis.update_market_once("BTC", 1, mock_db)
    # Should not call insert_into_db
    assert not mock_db.execute.called


def test_update_market_once_exception(market_analysis: MarketAnalysis) -> None:
    mock_db = MagicMock()
    market_analysis.api.return_loan_orders = MagicMock(side_effect=Exception("Other error"))
    market_analysis.update_market_once("BTC", 1, mock_db)
    # Should not call insert_into_db
    assert not mock_db.execute.called
