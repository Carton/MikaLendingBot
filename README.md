# Mika Lending Bot (Python 3 Edition)

> [!NOTE]
> This project is a modern Python 3 fork of the original Mika Lending Bot, enhanced with new features and improved stability.

## Key Improvements in this Version

This project has been extensively refactored and improved from the original codebase:

-   **Python 3 Migration**: Fully ported to Python 3, establishing a more modern and secure runtime environment.
-   **Enhanced Bitfinex Strategies**:
    -   **Dynamic FRR Delta**: Instead of a fixed offset, you can now specify a range (`frrdelta_min` to `frrdelta_max`). The bot will dynamically utilize values within this range to optimize lending rates.
    -   **Advanced XDay Thresholds**: Granular control over lending duration based on rates. You can now define mappings like `0.050:20,0.058:30`, meaning "lend for 20 days if rate is 0.05%, 30 days if 0.058%".
    -   **Smart Competitor Analysis**: The bot checks the demand book to intelligently place offers just below competing rates.
-   **Web UI Upgrades**:
    -   **Pause/Resume Control**: A new button allows you to safely pause lending operations without shutting down the bot.
    -   **Live Configuration**: Update critical settings like FRR Delta ranges directly from the web interface.
-   **Quality Assurance**: Significantly increased unit test coverage for core lending logic and API interactions.

## Original Introduction

Mika Lending Bot is an automatic lending bot for **Poloniex** and **Bitfinex**. It automatically lends all cryptocurrencies found in your lending account using advanced strategies to maximize returns.

It is inspired by [MarginBot](https://github.com/HFenter/MarginBot) and [BitfinexLendingBot](https://github.com/eAndrius/BitfinexLendingBot).

## Features

-   **Automated Lending**: Lends coins 24/7 at the best possible rates.
-   **Configurable Strategies**: Choose between aggressive high-yield strategies or conservative constant-lending approaches.
-   **Spike Detection**: Spreads offers to capture momentary spikes in lending rates.
-   **Hold Back Funds**: Option to withhold coins until rates reach a certain threshold.
-   **Long-Term Locking**: Lock in high daily rates for extended periods (up to 120 days on Bitfinex).
-   **Auto-Transfer**: Automatically moves deposited funds to the lending wallet.
-   **Web Dashboard**: Monitor profits, active loans, and bot status via a local web interface.
-   **Docker Support**: Ready-to-run Docker configuration.

## Quick Start (Python 3)

We recommend using `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Run the bot
uv run python lendingbot.py
```

## Community (Original)

*Note: These links refer to the original project community.*

-   [Gitter Chat](https://gitter.im/Mikadily/poloniexlendingbot)
-   [Telegram](https://t.me/mikalendingbot)
-   [Subreddit](https://www.reddit.com/r/poloniexlendingbot/)

## Documentation

For the original documentation, visit [readthedocs.io](http://poloniexlendingbot.readthedocs.io/en/latest/index.html).
*Please note that some configuration options regarding the new Bitfinex features are documented in `default.cfg.example`.*
