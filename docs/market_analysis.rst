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
`analyse_currencies`       A list of each currency you wish to record and analyse.
`update_interval`          The frequency (in seconds) between rates requested and stored in the DB.
`lending_style`            The percentile used for the percentile calculation (1-99).
`percentile_window`        The number of seconds to analyse when working out the percentile.
`macd_long_window`         The number of seconds used for the long moving average.
`recorded_levels`          The depth of the lending book to record in the DB (number of unfilled loans).
`data_tolerance`           The percentage of data that can be ignored as missing.
`analysis_method`          Which method (MACD or Percentile) to use for the daily min calculation.
`daily_min_multiplier`     Multiplier for the MACD method to scale up the returned rate value.
`ma_debug_log`             Print extra debug info regarding rate calculations.
========================== =============================================================================================

.. note::
    In the latest version, some parameters are now automatically derived from others:
    - ``MACD_short_win_seconds`` is now derived as ``macd_long_window / 12``.
    - ``keep_history_seconds`` is now derived as ``max(macd_long_window, percentile_window) * 1.1``.

The module has two main methods to calculate the minimum rate:

Percentile
``````````
This method takes all the data for the given time period (``percentile_window``) and works out the Xth percentile (``lending_style``) for that set of data. For example, if you are using a ``lending_style`` of 85 and you had a list of rates like so:

  :Example: 0.04, 0.04, 0.05, 0.05, 0.05, 0.05, 0.06, 0.06, 0.06, 0.07, 0.07, 0.07, 0.08, 0.08, 0.09, 0.09, 0.09, 0.10, 0.10, 0.10

The 85th percentile would be 0.0985 because 85% of rates are below this.

The following configuration options should be considered when using the percentile calculation method:
- `percentile_window`
- `lending_style`

MACD
````
Moving Average Convergence Divergence. This method uses moving averages to work out if it's a good time to lend. It looks at the best rate available for two windows: a long window (``macd_long_window``) and a short window (derived). If the short average is higher than the long average, the market trend is going up, and it will return a suggested loan rate.

If the long window is greater than the short window, then we will not lend as trend for rates is below what it should be.
So for example:

===== ===== ==== =========
Time  Short Long Suggested
===== ===== ==== =========
12:00 0.08  0.1  0.1
12:01 0.09  0.1  0.1
12:02 0.1   0.1  0.105
12:03 0.11  0.1  0.1155
12:04 0.12  0.1  0.126
===== ===== ==== =========

In this example, the bot would start to lend at 12:02 and it would suggest a minimum lending rate of ``long_average * daily_min_multiplier`` (default 1.05). Giving a rate of 0.105. This is then passed back to the main lendingbot where it will use your ``gap_top`` and ``gap_bottom``, along with spreads and all the other smarts to place loan offers.

Currently using this method gives the best results with well configured ``gap_top`` and ``gap_bottom``. This allows you to catch spikes in the market as see above.

The short window and long window are configured by a number of seconds, the data is then taken from the DB requesting ``macd_long_window * 1.1``. This is to get an extra 10% of data as there is usually some lost in the recording.
You can also use the `data_tolerance` to help with the amount of data required by the bot for this calculation, that is the percentage of data that can be missing for the data to still be valid.

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

The number of config options and combinations for this can be quite daunting. We have put in sensible defaults into the config. Change the currency to whatever you want, though best not use more than 3 really, as it slows down the API calls considerably.

The most important is probably setting `hide_coins` to ``false``. This means that it will always place loans so you don't need to have as low a resolution on the sleep timers. You also want to make sure the ``gap_top`` and ``gap_bottom`` are high so you can get a large spread.

Recommended Bot Settings for Market Analysis:

======================= =========
Config                  Value
======================= =========
period_active           10
period_inactive         10
spread_lend             3
gap_mode                RawBTC
gap_bottom              40
gap_top                 200
hide_coins              false
analyse_currencies      ETH,BTC
======================= =========

notes
'''''
- `analysis_method` will default back to the percentile method if it can't function. This will happen at start up for a while when it's collecting data and can also happen if something goes wrong with the Database or other failures.
- You can turn on `ma_debug_log` to get some more information if things aren't working.
- When it's starting up you will see ``Need more data for analysis, still collecting. I have Y/X records``, so long as it's still increasing then this is fine. If it always prints that message then you should change your `data_tolerance`.


Recording currencies
````````````````````

All the data is stored in an SQLite database per currency. You can see the database files in the ``market_data`` folder of the bot.
There are a number of things to consider before configuring this section. The most important being that you can only make a limited number of API calls to exchanges per second.

.. warning:: If you start to see the error message: ``HTTP Error 429: Too Many Requests`` then you need to review the settings in this file. Increase your timer or decrease the number of recorded currencies.

analyse_currencies
''''''''''''''''''

``analyse_currencies`` is the list of currencies to record and analyse.

None of the points below need be considered problematic unless you are planning to run with low (single digit seconds) timers on the bot.

With that said, every currency you add to this will:
- Increase the number of db files (and therefore disk usage).
- Increase I/O and CPU usage (each currency will be writing to disk).
- Reduce the number of requests you can make to the API per second for other tasks.

.. code-block:: toml

    [plugins.market_analysis]
    analyse_currencies = ["BTC", "ETH", "LTC"]

update_interval
'''''''''''''''

``update_interval`` is how long the bot will sleep between requests for rate data. Default is 10 seconds.
You are not guaranteed to get data at exactly the update interval if you have many currencies or if the API is slow.

recorded_levels
'''''''''''''''

``recorded_levels`` is the number of rates found in the current offers that will be recorded in the DB. Default is 10.

Analysing currencies
````````````````````
Everything in this section relates to how the analysis is carried out.

lending_style
'''''''''''''

``lending_style`` lets you choose the percentile of each currency's market to lend at.
- Conservative: 50
- Moderate: 75
- Aggressive: 90
- Very Aggressive: 99

This is a percentile, so choosing 75 would mean that your minimum will be the value that the market is above 25% of the recorded time.

percentile_window
'''''''''''''''''

The number of seconds worth of data to use for the percentile calculation. Default is 86400 (1 day).

macd_long_window
''''''''''''''''

The number of seconds used for the long window average in the MACD method. Default is 1800 (30 minutes).

data_tolerance
''''''''''''''

The percentage of data that can be missed and still considered valid. Default is 15.
If you keep seeing messages saying ``Need more data for analysis, still collecting. I have Y/X records``, then you need to increase this or reduce the number of currencies you are analysing.

analysis_method
'''''''''''''''

The method used to calculate the daily minimum: ``MACD`` or ``Percentile``.
This will not change the ``min_daily_rate`` that you have set for coins in the main config. So you will never lend below what you have statically configured.

daily_min_multiplier
''''''''''''''''''''

Used by the MACD method to scale up the returned average. Default is 1.05.

ma_debug_log
''''''''''''

When enabled, prints internal information around calculations. Default is ``false``.