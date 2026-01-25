.. _market_analysis-section:

Market Analysis
---------------

Overview
``````````
This feature records a currency's market and allows the bot to see trends. With this data, we can compute a recommended minimum lending rate per currency to avoid lending at times when the rate dips.

When this module is enabled, it will start recording the lending rates for the market in an SQLite database. This data is stored in the ``market_data`` folder.

A separate database is created for each currency you wish to record. These are enabled in the ``analyse_currencies`` configuration option within the ``[plugins.market_analysis]`` section.

 .. warning:: The more currencies you record, the more data is stored on disk and more CPU processing time is used. You may also experience API rate limit issues (429 errors) if you record too many currencies with a low update interval.

A quick list of each config option and what they do:

========================== =============================================================================================
Parameter                  Description
========================== =============================================================================================
``analyse_currencies``     A list of each currency you wish to record and analyse.
``update_interval``        The frequency (in seconds) between rates requested and stored in the DB.
``lending_style``          The percentile used for the percentile calculation (1-99).
``percentile_window``      The number of seconds to analyse when working out the percentile.
``macd_long_window``       The number of seconds used for the long moving average.
``recorded_levels``        The depth of the lending book to record in the DB (number of unfilled loans).
``data_tolerance``         The percentage of data that can be ignored as missing.
``analysis_method``        Which method (MACD or Percentile) to use for the daily min calculation.
``daily_min_multiplier``   Multiplier for the MACD method to scale up the returned rate value.
``ma_debug_log``           Print extra debug info regarding rate calculations.
========================== =============================================================================================

.. note::
    In the latest version, some parameters are now automatically derived from others:
    - ``MACD_short_win_seconds`` is now derived as ``macd_long_window / 12``.
    - ``keep_history_seconds`` is now derived as ``max(macd_long_window, percentile_window) * 1.1``.

The module has two main methods to calculate the minimum rate:

Percentile
``````````
This method takes all the data for the given time period (``percentile_window``) and works out the Xth percentile (``lending_style``) for that set of data. For example, if you are using a ``lending_style`` of 85, it means 85% of recorded rates were below this value.

MACD
````
Moving Average Convergence Divergence. This method uses moving averages to work out if it's a good time to lend. It looks at the best rate available for two windows: a long window (``macd_long_window``) and a short window (derived). If the short average is higher than the long average, the market trend is going up, and it will return a suggested loan rate.

If the short average is higher than the long average, it suggests a minimum lending rate of ``long_average * daily_min_multiplier`` (default 1.05).

suggested loan rate
'''''''''''''''''''
If the average of the short window is greater than the average of the long window, we return the calculated rate.

configuring
'''''''''''

The Market Analysis plugin can be configured in the ``[plugins.market_analysis]`` section of your ``config.toml``.

.. code-block:: toml

    [plugins.market_analysis]
    analyse_currencies = ["BTC", "ETH"]
    lending_style = 75
    macd_long_window = 1800
    percentile_window = 86400
    daily_min_multiplier = 1.05
    analysis_method = "Percentile"

Recording currencies
````````````````````

All the data is stored in an SQLite database per currency.

analyse_currencies
''''''''''''''''''

``analyse_currencies`` is the list of currencies to record and analyse.

.. code-block:: toml

    [plugins.market_analysis]
    analyse_currencies = ["BTC", "ETH", "LTC"]

update_interval
'''''''''''''''

``update_interval`` is how long the bot will sleep between requests for rate data. Default is 10 seconds.

recorded_levels
'''''''''''''''

``recorded_levels`` is the number of rates found in the current offers that will be recorded in the DB. Default is 10.

Analysing currencies
````````````````````

lending_style
'''''''''''''

``lending_style`` lets you choose the percentile of each currency's market to lend at.
- Conservative: 50
- Moderate: 75
- Aggressive: 90
- Very Aggressive: 99

percentile_window
'''''''''''''''''

The number of seconds worth of data to use for the percentile calculation. Default is 86400 (1 day).

macd_long_window
''''''''''''''''

The number of seconds used for the long window average in the MACD method. Default is 1800 (30 minutes).

data_tolerance
''''''''''''''

The percentage of data that can be missed and still considered valid. Default is 15.

analysis_method
'''''''''''''''

The method used to calculate the daily minimum: ``MACD`` or ``Percentile``.

daily_min_multiplier
''''''''''''''''''''

Used by the MACD method to scale up the returned average. Default is 1.05.

ma_debug_log
''''''''''''

When enabled, prints internal information around calculations. Default is ``false``.
