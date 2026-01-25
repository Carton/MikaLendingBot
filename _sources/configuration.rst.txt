.. _configuration-section:

Configuration
=============

Configuring the bot can be as simple as select the exchange to use and copy-pasting your API key and Secret.

New features are generally backwards compatible with previous versions of the configuration but it is still recommended that you update your config immediately after updating to take advantage of new features.

The bot now uses TOML format for configuration. To begin, copy ``config_sample.toml`` to ``config.toml``. Now you can edit your settings.

Exchange selection, API key and Secret
--------------------------------------

Select the exchange to use in attribute ``exchange`` within the ``[api]`` section. Supported are ``Poloniex`` and ``Bitfinex``. Default is ``Bitfinex``.

.. code-block:: toml

    [api]
    exchange = "Bitfinex"
    # or
    exchange = "Poloniex"

Create a **NEW** API key and Secret from `Poloniex <https://poloniex.com/apiKeys>`_
or `Bitfinex <https://www.bitfinex.com/api>`_ and paste them into the respective slots in the config.

.. code-block:: toml

    [api]
    apikey = "XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX"
    secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx..."

.. warning:: Do not share your API key nor secret with anyone whom you do not trust with all your Poloniex funds.

.. note:: If you use an API key that has been used by any other application, it will likely fail for one application or the other. This is because the API requires a `nonce <https://en.wikipedia.org/wiki/Cryptographic_nonce>`_.

**Poloniex**

Your Poloniex API key is all capital letters and numbers in groups of 8, separated by hyphens.
Your secret is 128 lowercase letters and numbers.

HIGHLY Recommended:

    - Disable the "Enable Trading" checkbox. The bot does not need it to operate normally.
    - Enable IP filter to only the IP address the bot will be running from.

**Bitfinex**

Your Bitfinex API key and secret are both 43 letters and numbers.

HIGHLY Recommended:

    - The lending bot needs only READ permission to "Account History", "Marging Funding", "Wallets"
      and WRITE permission to "Margin Funding" and "Wallets". Deselect all other on key generation,
      especially to "Withdraw".

Exchange Sections
-----------------
The ``[api]`` section contains exchange-related configurations.

- ``all_currencies`` is a list of all supported currencies for funding. The list only needs to change when the exchange adds or removes a supported currency.

.. code-block:: toml

    [api]
    all_currencies = ["BTC", "LTC", "ETH", "XRP"]

.. note:: In the new TOML format, this is a list of strings. To disable a currency, simply remove it from the list.



Timing
---------

- ``period_active`` is how long the bot will "rest" (in seconds) between running while the bot has loan offers waiting to be filled. Found in the ``[bot]`` section.

    - Default value: 60 seconds
    - Allowed range: 1 to 3600 seconds
    - If the bot finishes a cycle and has no open lend orders left to manage, it will change to inactive mode.

.. note:: Just because 1 second is a permitted period is not necessarily a good idea for API rate limits.

- ``period_inactive`` is how long the bot will "rest" (in seconds) between running while the bot has nothing to do. Found in the ``[bot]`` section.

    - Default value: 300 seconds (5 minutes)
    - Allowed range: 1 to 3600 seconds
    - If the bot finishes a cycle and has lend orders to manage, it will change to active mode.

- ``request_timeout`` is how long the bot waits for a response of a request. Found in the ``[bot]`` section.

    - Default value: 30 seconds
    - Allowed range: 1 to 180 seconds

.. code-block:: toml

    [bot]
    period_active = 60
    period_inactive = 300
    request_timeout = 30

Min and Max Rates
-----------------

These settings are located in the ``[coin.default]`` section to apply globally, or can be overridden in specific ``[coin.SYMBOL]`` sections.

- ``min_daily_rate`` is the minimum rate (in percent) that the bot will allow offer loans at.

    - Default value: 0.005 percent
    - Allowed range: 0.0031 to 5 percent
    - 0.0031% every day for a year, works out around 1%. This is less than most bank accounts and is considered not worth while.
    - The current default value is a optimistic but very viable for the more high volume currencies. Not viable for lending DOGE, for example.

- ``max_daily_rate`` is the maximum rate (in percent) that the bot will allow lends to open.

    - Default value: 5 percent
    - Allowed range: 0.0031 to 5 percent
    - 2% is the default value offered by the exchange, but there is little reason not to set it higher if you feel optimistic.

.. code-block:: toml

    [coin.default]
    min_daily_rate = 0.005
    max_daily_rate = 5.0

Lending Strategies
------------------

The bot supports different lending strategies. You can select the active strategy using the ``strategy`` parameter within ``[coin.default]`` or a specific ``[coin.SYMBOL]`` section.

- ``strategy`` determines the logic used for placing lend offers.

    - Allowed values: ``Spread``, ``FRR``
    - Default value: ``Spread``
    - **Spread Strategy**: Standard gap/spread based lending. Uses ``spread_lend``, ``gap_mode``, ``gap_bottom``, and ``gap_top`` to distribute offers across the order book.
    - **FRR Strategy**: Flash Return Rate based lending (Bitfinex only). It uses the exchange's FRR as a dynamic base for your ``min_daily_rate``.
        - When active, it forces ``spread_lend = 1`` internally.
        - It enables the use of ``frr_delta_min`` and ``frr_delta_max`` for rate adjustments.
        - If selected on a non-Bitfinex exchange, the bot will fail to start.

- ``frr_delta_min`` and ``frr_delta_max`` are the adjustment range (in percent) relative to the `flash return rate <https://support.bitfinex.com/hc/en-us/articles/115003284729-What-is-the-FRR-Delta->`_.

    - Default value: ``-10`` / ``10``
    - Range: -50 to +50
    - These values are relative percentages of the FRR. For example, a setting of ``-20`` means the target rate will be ``FRR * 0.80``.
    - The bot cycles through 5 steps between min and max to improve chances of being filled.
    - This option only works on Bitfinex when ``strategy = "FRR"``.
- ``xday_thresholds`` is a list of rate and days pairs that defines the lending period for different interest rates.

    - Default value: Empty (disabled)
    - Format: Array of inline tables ``{ rate = <rate>, days = <days> }``
    - Rate values are in percent (0 to 5), days are integers (2 to 120).
    - The bot uses linear interpolation between defined thresholds.
    - Poloniex max lending period: 60 days
    - Bitfinex max lending period: 120 days
    - This feature allows you to lock in a better rate for a longer period of time.

.. code-block:: toml

    [coin.default]
    strategy = "Spread"
    frr_delta_min = -10.0
    frr_delta_max = 10.0
    xday_thresholds = [
        { rate = 0.050, days = 20 },
        { rate = 0.058, days = 30 },
        { rate = 0.060, days = 45 },
        { rate = 0.063, days = 60 },
        { rate = 0.070, days = 120 },
    ]

Spreading your Lends
--------------------

If ``spread_lend = 1`` and ``gap_bottom = 0``, it will behave as simple lending bot lending at lowest possible offer.

- ``spread_lend`` is the amount (as an integer) of separate loans the bot will split your balance into across the order book.

    - Default value: 3
    - Allowed range: 1 to 20 (1 is the same as disabling)
    - The loans are distributed evenly between ``gap_bottom`` and ``gap_top``.
    - This allows the bot to benefit from spikes in lending rate but can result in loan fragmentation (not really a bad thing since the bot has to deal with it.)

- ``gap_mode`` is the "mode" you would like your gaps to be calculated in.

    - Default value: ``Relative``
    - Allowed values: ``Relative``, ``RawBTC``, ``Raw``
    - The values are case insensitive.
    - The purpose of spreading your lends is to skip dust offers in the lendbook, and also to take advantage of any spikes that occur.
    - Mode descriptions:
        - ``Relative`` - ``gap_bottom`` and ``gap_top`` will be relative to your balance for each coin individually.
            - This is relative to your total lending balance, both loaned and unloaned.
            - ``gap_bottom`` and ``gap_top`` will be in percents of your balance. (A setting of 100 will equal 100%)
            - Example: You have 1BTC. If ``gap_bottom = 100`` then you will skip 100% of your balance of dust offers, thus skipping 1BTC into the lendbook. If ``gap_top = 200`` then you will continue into the lendbook until you reach 200% of your balance, thus 2BTC. Then, if ``spread_lend = 5``, you will make 5 equal volume loans over that gap.
        - ``RawBTC`` - ``gap_bottom`` and ``gap_top`` will be in a raw BTC value, converted to each coin.
            - Recommended when using one-size-fits-all settings.
            - ``gap_bottom`` and ``gap_top`` will be in BTC. (A setting of 3 will equal 3 BTC)
            - Example: If ``gap_bottom = 1`` and you are currently lending ETH, the bot will check the current exchange rate, say 1BTC = 10ETH. Then the bot will skip 10ETH of dust offers at the bottom of the lendbook before lending. If ``gap_top = 10``, then using the same exchange rate 10BTC will be 100ETH. The bot will then continue 100ETH into the loanbook before stopping. Then, if ``spread_lend = 5``, you will make 5 equal volume loans over that gap.
        - ``Raw`` - ``gap_bottom`` and ``gap_top`` will be in a raw value of the coin being lent.
            - Recommended when used with coin-specific settings.
            - ``gap_bottom`` and ``gap_top`` will be in value of the coin. (A setting of 3 will equal 3 BTC, 3 ETH, 3 DOGE, or whatever coin is being lent.)
            - Example: If ``gap_bottom = 1`` and you are currently lending ETH, the bot will skip 1ETH of dust offers at the bottom of the lendbook before lending. If ``gap_top = 10``, the bot will then continue 10ETH into the loanbook before stopping. Then, if ``spread_lend = 5``, you will make 5 equal volume loans over that gap.

- ``gap_bottom`` is the lower setting for your ``gap_mode`` values, and will be where you start to lend.

    - Default value: 10 percent
    - Allowed range: 0 to <arbitrary large number>
    - 10% ``gap_bottom`` is recommended to skip past dust at the bottom of the lending book, but if you have a VERY high volume this will cause issues as you stray to far away from the most competitive bid.

- ``gap_top`` is the upper setting for your ``gap_mode`` values, and will be where you finish spreading your lends.

    - Default value: 200 percent
    - Allowed range: 0 to <arbitrary large number>
    - This value should be adjusted based on your coin volume to avoid going astronomically far away from a realistic rate.

.. code-block:: toml

    [coin.default]
    spread_lend = 3
    gap_mode = "RawBTC"
    gap_bottom = 40
    gap_top = 200

Auto-transfer from Exchange Balance
-----------------------------------

If you regularly transfer funds into your account but don't enjoy having to log in yourself and transfer them to the lending balance, this feature is for you.

- ``transferable_currencies`` is a list of currencies you would like to be transferred from your exchange balance to your lending balance. Found in the ``[bot]`` section.

    - Default value: Empty list (disabled)
    - Format: A list of currency tickers, e.g., ``["BTC", "ETH", "USD"]``
    - Commenting it out or leaving it as an empty list will disable the feature.
    - Coins will be transferred every time the bot runs, so if you intend to trade or withdraw it is recommended to turn off the bot or disable this feature.

.. code-block:: toml

    [bot]
    transferable_currencies = ["BTC", "ETH", "USD"]

Unimportant settings
--------------------

Very few situations require you to change these settings.

- ``min_loan_size`` is the minimum size that a bot will make a loan at. Found in the ``[coin.default]`` or specific ``[coin.SYMBOL]`` section.

    - Default value: 0.01 of a coin
    - Allowed range: 0.01 and up.
    - If you dislike loan fragmentation, then this will make the minimum for each loan larger.
    - Automatically adjusts to at least meet the minimum of each coin.

- ``keep_stuck_orders`` If True, keeps orders that are "stuck" in the market instead of canceling them. Found in the ``[bot]`` section.

    - Default value: True
    - Allowed values: True or False
    - A "Stuck" order occurs when it partially fills and leaves the coins balance total (total = open orders + let in balance) below your ``min_loan_size`` and so the bot would not be able to lend it again if it was canceled.
    - When disabled, stuck orders will be canceled and held in balance until enough orders expire to allow it to lend again.

- ``hide_coins`` If True, will not lend any of a coin if its market low is below the set ``min_daily_rate``. Found in the ``[bot]`` section.

    - Default value: True
    - Allowed values: True or False. Commented defaults to True
    - This hides your coins from appearing in walls.
    - Allows you to catch a higher rate if it spikes past your ``min_daily_rate``.
    - Not necessarily recommended if used with ``MarketAnalysis`` with an aggressive ``lending_style``, as the bot may miss short-lived rate spikes. This is not the case if using ``MACD`` with ``analysis_method``. In that case it is recommended to set ``hide_coins`` to True.
    - If you are using the ``MarketAnalysis`` plugin, you will likely see a lot of ``Not lending BTC due to rate below 0.9631%`` type messages in the logs. This is normal.

- ``end_date`` Bot will try to make sure all your loans are done by this date so you can withdraw or do whatever you need. Found in the ``[bot]`` section.

    - Default value: Disabled
    - Uncomment to enable.
    - Format: ``YEAR-MONTH-DAY``

Max to be lent
--------------

This feature group allows you to only lend a certain percentage of your total holding in a coin, until the lending rate surpasses a certain threshold. Then it will lend at max capacity. These settings are found in the ``[coin.default]`` section or specific ``[coin.SYMBOL]`` sections.

- ``max_to_lend`` is a raw number of how much you will lend of each coin whose lending rate is below ``max_to_lend_rate``.

    - Default value: 0 (disabled)
    - Allowed range: 0 (disabled) or ``min_loan_size`` and up
    - If set to 0, it is disabled.
    - If disabled, the bot will check if ``max_percent_to_lend`` is enabled and use that instead.
    - Setting this overrides ``max_percent_to_lend``.
    - This is a setting for the raw value of coin that will be lent if the coin's lending rate is under ``max_to_lend_rate``.
    - Has no effect if current rate is higher than ``max_to_lend_rate``.
    - If the remainder (after subtracting ``max_to_lend``) in a coin's balance is less than ``min_loan_size``, then the remainder will be lent anyway. Otherwise, the coins would go to waste since you can't lend under ``min_loan_size``.

- ``max_percent_to_lend`` is a percentage of how much you will lend of each coin whose lending rate is below ``max_to_lend_rate``.

    - Default value: 0 (disabled)
    - Allowed range: 0 (disabled) to 100 percent
    - If set to 0, it is disabled.
    - If disabled in addition to ``max_to_lend``, the entire feature will be disabled (100% of balance will be lent).
    - This percentage is calculated per-coin, and is the percentage of the balance that will be lent if the coin's current rate is less than ``max_to_lend_rate``.
    - Has no effect if current rate is higher than ``max_to_lend_rate``.
    - If the remainder in a coin's balance is less than ``min_loan_size``, then the remainder will be lent anyway.


- ``max_to_lend_rate`` is the rate threshold (in percent) when all coins are lent.

    - Default value: 0 (disabled)
    - Allowed range: 0 (disabled) or ``min_daily_rate`` to 5 percent
    - Setting this to 0 with a limit in place causes the limit to always be active.
    - When an individual coin's lending rate passes this threshold, all of the coin will be lent instead of applying the limits from ``max_to_lend`` or ``max_percent_to_lend``.

.. code-block:: toml

    [coin.default]
    max_to_lend = 0
    max_percent_to_lend = 0
    max_to_lend_rate = 0


Config per Coin
---------------

You can define specific configurations for each currency by creating a section named ``[coin.SYMBOL]`` (e.g., ``[coin.BTC]``, ``[coin.USD]``). Any settings defined in a coin-specific section will override the defaults set in ``[coin.default]``.

Configuration should look like this (using TOML format):

.. code-block:: toml

    [coin.BTC]
    min_loan_size = 0.01
    min_daily_rate = 0.1
    max_active_amount = 1.0
    gap_mode = "Raw"
    gap_bottom = 10
    gap_top = 20
    strategy = "Spread"
    spread_lend = 5
    xday_thresholds = [
        { rate = 0.05, days = 30 }
    ]

Max Active Amount (Limit Total Lending)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``max_active_amount`` limits the total amount that can be lent out for a currency. Found in the ``[coin.default]`` or specific ``[coin.SYMBOL]`` section.

    - Default value: -1 (unlimited)
    - Allowed values:
        - ``-1`` = Unlimited (no restriction on total lending)
        - ``0`` = Disabled (skip this coin entirely, equivalent to not listing it in ``all_currencies``)
        - ``> 0`` = Limit (cap total lending to this amount in coin units)
    - This is useful when you want to maintain a reserve or limit exposure for a specific currency.
    - The limit applies to the total amount currently lent out (active loans). If you have 10000 USD and set ``max_active_amount = 5000``, the bot will only lend up to 5000 USD total.
    - Example: If you have ``max_active_amount = 1000`` for USD and currently have 800 USD lent out, the bot will only offer up to 200 USD more in new loans.

    Example configuration:

    .. code-block:: toml

        [coin.USD]
        min_loan_size = 150
        max_active_amount = 5000.0  # Only lend up to 5000 USD total


Advanced logging and Web Display
--------------------------------

- ``enabled`` (within the ``[bot.web]`` section) if true, this enables a webserver on the ``www/`` folder.

    - Default value: ``true``
    - The server page can be accessed locally, at ``http://localhost:8000/lendingbot.html`` by default.
    - When enabled, JSON logging is automatically enabled with output to ``www/botlog.json``.
    - You must close bot with a keyboard interrupt (CTRL-C on Windows) to properly shutdown the server and release the socket, otherwise you may have to wait several minutes for it to release itself.

- ``json_log_size`` (within the ``[bot]`` section) is the amount of lines the botlog will keep before deleting the oldest event.

    - Default value: 200
    - Reasons to lower this include: you are conscious of bandwidth when hosting your webserver, you prefer (slightly) faster loading times and less RAM usage of bot.

- ``host`` (within the ``[bot.web]`` section) is the IP address that the webserver can be found at.

    - Advanced users only.
    - Default value: ``127.0.0.1``
    - Format: ``IP``
    - Setting the ip to ``127.0.0.1`` will ONLY allow the webpage to be accessed at localhost (``127.0.0.1``)
    - Setting the ip to ``0.0.0.0`` will allow the webpage to be accessed at localhost (``127.0.0.1``) as well as at the computer's LAN IP address within the local network.
    - You must know what you are doing when changing the IP address to anything other than the suggested configurations above.

- ``port`` (within the ``[bot.web]`` section) is the IP port that the webserver can be found at.

    - Advanced users only.
    - Default value: 8000
    - Format: ``PORT``

- ``template`` (within the ``[bot.web]`` section) is the location the bot will use for WebServer HTML GUI template.

    - Default value: ``www``
    - Format: ``PATH``

- ``output_currency`` (within the ``[bot]`` section) this is the ticker of the coin which you would like the website to report your summary earnings in.

    - Default value: BTC
    - Acceptable values: BTC, USDT, Any coin with a direct BTC trading pair (ex. DOGE, MAID, ETH), Currencies that have a BTC exchange rate on blockchain.info (i.e. EUR, USD)
    - Will be a close estimate, due to unexpected market fluctuations, trade fees, and other unforseeable factors.

- ``label`` (within the ``[bot]`` section) is a custom name of the bot, that will be displayed in html page.

    - Default value: Lending Bot
    - Allowed values: Any literal string

.. code-block:: toml

    [bot]
    label = "Lending Bot"
    output_currency = "BTC"
    json_log_size = 200

    [bot.web]
    enabled = true
    host = "127.0.0.1"
    port = 8000
    template = "www"


Plugins
-------

Plugins allow extending Bot functionality with extra features.
To enable/disable a plugin add/remove it to the ``plugins`` list config option under the ``[bot]`` section, example:

.. code-block:: toml

    [bot]
    plugins = ["AccountStats", "Charts"]

Plugins can add their own HTML pages by calling ``self.log.addSectionlog('plugins', '<pluginName>', 'navbar', True);`` within their init code.
This will add a navbar element on the main lendingbot.html page linking to <pluginName>.html

AccountStats Plugin
~~~~~~~~~~~~~~~~~~~

The AccountStats plugin fetches all your loan history and provides statistics based on it.
Current implementation sends a earnings summary Notification (see Notifications sections) every 24hr.

To enable the plugin add ``AccountStats`` to the ``plugins`` list, example:

.. code-block:: toml

    [bot]
    plugins = ["AccountStats"]

There is an optional setting to change how frequently this plugin reports. By default, once per day. Example:

.. code-block:: toml

    [plugins.account_stats]
    report_interval = 86400

Be aware that first initialization might take longer as the bot will fetch all the history.

Profit Charts Plugin
~~~~~~~~~~~~~~~~~~~~

The Charts plugin dumps out the historical lending data to a JSON structure which is read by the new charts.html page.
This page reads this dump data and constructs a Google Chart showing daily profit over time.

The AccountStats plugin must be enabled for the Charts plugin to function correctly.

To enable the plugin add ``Charts`` to the ``plugins`` list, example:

.. code-block:: toml

    [bot]
    plugins = ["AccountStats", "Charts"]

There is an optional setting to change how frequently this plugin dumps data. By default, four times per day. Example:

.. code-block:: toml

    [plugins.charts]
    dump_interval = 21600

The history data is automatically saved to ``logs/history.json``.

On a new installation, the AccountStats database may not be up to date on first iteration of the Charts plugin and no data will get dumped. Simply wait for the next interval or restart the bot after the AccountStats plugin is finished.


lendingbot.html options
-----------------------

You can pass options to statistics page by adding them to URL. Eg, ``http://localhost:8000/lendingbot.html?option1=value&option2=0``

- ``effrate`` controls how effective loan rate is calculated. Yearly rates are calculated based on effective rate, so this option affects them as well. Last used mode remembered by browser, so you do not have to specify this option every time. By default, effective loan rate is calculated considering lent precentage (from total available coins) and exchange fee.

    - Allowed values: ``lentperc``, ``onlyfee``.
    - Default value: ``lentperc``.
    - ``onlyfee`` calculates effective rate without considering lent coin percentage.

- ``displayUnit`` controls BTC's unit output.

    - Allowed values: ``BTC``, ``mBTC``, ``Bits``, ``Satoshi``
    - Default value: ``BTC``
    - This setting will change all display of Bitcoin to that unit. Ex. 1 BTC -> 1000 mBTC.

- ``earningsInOutputCurrency`` define which earnings are shown in the output currency.

    - Allowed values: ``all``, ``summary``
    - Default value: ``all``


Notifications
-------------
The bot supports sending notifications for several different events on several different platforms. To enable notifications, you must set ``enabled = true`` in the ``[notifications]`` section, enable at least one of the following events and also at least one notification platform. The list of events you can notify about are:

Global Notification Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``notify_new_loans``

    - Sends a notification each time a loan offer is filled.

- ``notify_tx_coins``

    - This will send a notification if any coins are transferred from your exchange account, to your lending account. You must have ``transferable_currencies`` enabled for this to work.  Then you should set ``notify_tx_coins = true``.

- ``notify_xday_threshold``

    - This will send a notification every time a loan is created that is above your ``xday_thresholds`` config value. To enable you should set ``notify_xday_threshold = true``.

- ``notify_summary_minutes``

    - This will send a summary of the current loans you have every X minutes. To enable this add ``notify_summary_minutes = 120``. This will send you a notification every 2 hours (120 minutes).

- ``notify_caught_exception``

    - This is more useful for developers. This will send a notification every time there is an exception thrown in the bot that we don't handle. To enable add ``notify_caught_exception = true``.

- ``notify_prefix``

    - This string, if set, will be prepended to any notifications. Useful if you are running multiple bots and need to differentiate the source.

Once you have decided which notifications you want to receive, you can then go about configuring platforms to send them on. Currently the bot supports:

Email notifications
~~~~~~~~~~~~~~~~~~~

To enable email you should configure the following in the ``[notifications.email]`` section:

.. code-block:: toml

    [notifications.email]
    enabled = true
    login_address = "me@gmail.com"
    login_password = "secretPassword"
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    smtp_starttls = false
    to_addresses = ["me@gmail.com", "you@gmail.com"]

Slack notifications
~~~~~~~~~~~~~~~~~~~

Before you can post to slack you need to create an API token. Once you have a token you can then configure the bot as so:

.. code-block:: toml

    [notifications.slack]
    enabled = true
    token = "xoxp-..."
    channels = ["#cryptocurrency", "@someUser"]

Telegram notifications
~~~~~~~~~~~~~~~~~~~~~~

To have telegram notifications you need to get a bot id from the BotFather. Once you have a bot id you need to get your Chat ID or create a channel and invite the bot. Once you have all this in place you configure it like so:

.. code-block:: toml

    [notifications.telegram]
    enabled = true
    bot_id = "281421543:..."
    chat_ids = ["123456789", "@cryptocurrency"]

Pushbullet notifications
~~~~~~~~~~~~~~~~~~~~~~~~

To enable Pushbullet notifications, you first need to create an API key and then discover your device ID.

.. code-block:: toml

    [notifications.pushbullet]
    enabled = true
    token = "l.2mDDvy..."
    deviceid = "ujpah7..."

IRC notifications
~~~~~~~~~~~~~~~~~

IRC is very easy to configure, if you are already interested in using it you'll understand what each of the options are.

.. code-block:: toml

    [notifications.irc]
    enabled = true
    host = "irc.freenode.net"
    port = 6667
    nick = "LendingBot"
    ident = "lendingbot"
    realname = "Poloniex lending bot"
    target = "#bitbotfactory"


Market Analysis Plugin
~~~~~~~~~~~~~~~~~~~~~~

The Market Analysis plugin records currency market data and allows the bot to see trends. This data can be used to compute a recommended minimum lending rate.

To enable the plugin, add ``MarketAnalysis`` to the ``plugins`` list and configure the ``[plugins.market_analysis]`` section.

For more detailed information on all available parameters, please refer to the :ref:`market_analysis-section` documentation.

Example configuration:

.. code-block:: toml

    [plugins.market_analysis]
    analyse_currencies = ["BTC", "ETH"]
    lending_style = 75
    analysis_method = "Percentile"
