import sqlite3 as sqlite
import time
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.strategies import floats, integers, lists

from lendingbot.modules.MarketAnalysis import MarketAnalysis
from lendingbot.modules.Poloniex import Poloniex


@pytest.fixture(scope="module")
def mock_api() -> Any:
    mock_config = MagicMock()
    mock_config.get_currencies_list.return_value = []
    mock_config.get.return_value = "30"
    mock_config.getboolean.return_value = False
    mock_config.get_exchange.return_value = "POLONIEX"
    mock_config.get_all_currencies.return_value = ["BTC", "ETH"]

    api = Poloniex(mock_config, None)
    return api


@pytest.fixture
def market_analysis(mock_api: Any) -> MarketAnalysis:
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

    return MarketAnalysis(mock_config, mock_api)


def new_db(ma: MarketAnalysis) -> sqlite.Connection:
    db_con = ma.create_connection(None, ":memory:")  # type: ignore[arg-type]
    if db_con:
        ma.create_rate_table(db_con, 3)
        return db_con
    raise Exception("Failed to create in-memory DB")


def random_rates() -> list[float]:
    return [
        float(x)
        for x in lists(
            floats(min_value=0.00001, max_value=100, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=10,
        ).example()
    ]


@pytest.fixture
def populated_db(market_analysis: MarketAnalysis) -> tuple[sqlite.Connection, list[list[float]]]:
    price_levels = 3
    db_con = new_db(market_analysis)
    rates = random_rates()
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

    rate_db = market_analysis.get_rate_suggestion(db_con, method="percentile")  # type: ignore[arg-type]
    assert rate_db >= 0

    df = pd.DataFrame(rates)
    df.columns = pd.Index(["rate0", "a0", "r1", "a1", "r2", "a2", "p"])
    df["time"] = pd.to_datetime([time.time()] * len(df), unit="s")
    rate_args = market_analysis.get_rate_suggestion("BTC", df, "percentile")
    assert rate_args >= 0

    rate = market_analysis.get_rate_suggestion(db_con, method="MACD")  # type: ignore[arg-type]
    assert rate >= 0


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    lists(floats(min_value=0, allow_nan=False, allow_infinity=False), min_size=3, max_size=100),
    integers(min_value=1, max_value=99),
)
def test_get_percentile(
    market_analysis: MarketAnalysis, rates: list[float], lending_style: int
) -> None:
    np_perc = market_analysis.get_percentile(rates, lending_style, use_numpy_val=True)
    math_perc = market_analysis.get_percentile(rates, lending_style, use_numpy_val=False)
    assert pytest.approx(np_perc) == math_perc
