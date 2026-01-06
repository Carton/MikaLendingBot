"""
LendingBot main entry point

This is the main entry point for the application, responsible for:
- Parsing command line arguments
- Loading configuration
- Initializing various modules
- Starting the main loop and Web server
"""

from __future__ import annotations

import argparse
import http.client
import os
import socket
import sys
import time
import traceback
import urllib.error
from pathlib import Path
from typing import Any, NoReturn

from .modules import (
    Configuration,
    Data,
    Lending,
    MarketAnalysis,
    PluginsManager,
    WebServer,
)
from .modules.ExchangeApi import ApiError
from .modules.ExchangeApiFactory import ExchangeApiFactory
from .modules.Logger import Logger


# Add type hints and docstrings
def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments

    Returns:
        argparse.Namespace: Parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description="LendingBot - Cryptocurrency Lending Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-cfg",
        "--config",
        help="Custom configuration file path (default: default.toml)",
        type=str,
        default=None,
    )

    parser.add_argument(
        "-dry",
        "--dryrun",
        help="Dry-run mode, does not execute actual trades",
        action="store_true",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose output mode",
        action="store_true",
    )

    return parser.parse_args()


def main() -> NoReturn:
    """
    LendingBot main entrance function
    """
    # Allow running from different directories
    if not Path("pyproject.toml").exists():
        os.chdir(Path(sys.argv[0]).resolve().parent)

    # Parse command line arguments
    args = parse_arguments()
    dry_run = bool(args.dryrun)

    # Load configuration
    try:
        config_path = Path(args.config) if args.config else Path("config.toml")
        if config_path.suffix == ".cfg":
            print("Warning: .cfg files are legacy. Please migrate to .toml.")

        config = Configuration.load_config(config_path)
    except FileNotFoundError:
        print(f"Config file '{config_path}' not found. Please create one.")
        sys.exit(1)
    except Exception as ex:
        print(f"Error loading configuration: {ex}")
        sys.exit(1)

    # Initialize Logger
    try:
        log = Logger(
            json_file=config.bot.json_file,
            json_log_size=config.bot.json_log_size,
            exchange=config.api.exchange.value,
            label=config.bot.label,
        )
    except Exception as ex:
        print(f"Error initializing Logger: {ex}")
        sys.exit(1)

    # Initialize API
    try:
        api = ExchangeApiFactory.createApi(config.api.exchange.value, config, log)
    except Exception as ex:
        print(f"Error initializing API: {ex}")
        sys.exit(1)

    # Initialize Market Analysis (Class)
    analysis = None
    if config.plugins.market_analysis.analyse_currencies:
        try:
            analysis = MarketAnalysis.MarketAnalysis(config, api)
            analysis.run()
        except Exception as ex:
            print(f"Error initializing Market Analysis: {ex}")
            sys.exit(1)

    # Initialize Lending Engine (Class)
    try:
        engine = Lending.LendingEngine(config, api, log, Data, analysis)
        engine.initialize(dry_run=dry_run)

        if engine.coin_cfg:
            strategies_log = [f"{cur}: {cfg.strategy}" for cur, cfg in engine.coin_cfg.items()]
            print(f"Active Lending Strategies: {', '.join(strategies_log)}")
    except Exception as ex:
        print(f"Error initializing Lending Engine: {ex}")
        sys.exit(1)

    # Initialize Plugins (Class)
    try:
        plugins_manager = PluginsManager.PluginsManager(config, api, log)
        # Global for backward compatibility
        PluginsManager._manager = plugins_manager
    except Exception as ex:
        print(f"Error initializing Plugins: {ex}")
        sys.exit(1)

    # Initialize Web Server (Class)
    if config.bot.web.enabled:
        web_server = WebServer.WebServer(config, engine)
        web_server.start()
        # Global for backward compatibility
        WebServer._web_server = web_server

    # Start DNS cache management
    prv_getaddrinfo = socket.getaddrinfo
    dns_cache: dict[Any, Any] = {}

    def new_getaddrinfo(*urlargs: Any) -> Any:
        try:
            return dns_cache[urlargs]
        except KeyError:
            res = prv_getaddrinfo(*urlargs)
            dns_cache[urlargs] = res
            return res

    socket.getaddrinfo = new_getaddrinfo  # type: ignore[assignment]

    log.log(f"Welcome to {config.bot.label} on {config.api.exchange.value}")
    engine.start_scheduler()

    try:
        last_summary_time = 0.0
        while True:
            try:
                dns_cache.clear()  # Flush DNS Cache
                Data.update_conversion_rates(config.bot.output_currency, config.bot.web.enabled)

                if engine.lending_paused != engine.last_lending_status:
                    if not engine.lending_paused:
                        log.log("Lending running")
                    else:
                        log.log("Lending paused")
                    engine.last_lending_status = engine.lending_paused

                if not engine.lending_paused:
                    plugins_manager.before_lending()
                    engine.transfer_balances()
                    engine.cancel_all()
                    engine.lend_all()
                    plugins_manager.after_lending()

                lent_status_str = Data.stringify_total_lent(Data.get_total_lent())
                if time.time() - last_summary_time >= config.bot.period_inactive:
                    log.log(lent_status_str)
                    last_summary_time = time.time()

                log.persistStatus()
                sys.stdout.flush()
                time.sleep(engine.sleep_time)
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                msg = str(ex)
                log.log_error(msg)
                log.persistStatus()

                if "Invalid API key" in msg:
                    print("!!! Troubleshooting !!!")
                    print("Are your API keys correct? No quotation. Just plain keys.")
                    sys.exit(1)
                elif "Nonce must be greater" in msg:
                    print("!!! Troubleshooting !!!")
                    print(
                        "Are you reusing the API key in multiple applications? Use a unique key for every application."
                    )
                    sys.exit(1)
                elif "Permission denied" in msg:
                    print("!!! Troubleshooting !!!")
                    print("Are you using IP filter on the key? Maybe your IP changed?")
                    sys.exit(1)
                elif "timed out" in msg:
                    print(f"Timed out, will retry in {engine.sleep_time}sec")
                elif isinstance(ex, http.client.BadStatusLine):
                    print("Caught BadStatusLine exception from exchange, ignoring.")
                elif isinstance(ex, urllib.error.URLError):
                    print(f"Caught {ex} from exchange, ignoring.")
                elif isinstance(ex, ApiError):
                    print(f"Caught {msg} reading from exchange API, ignoring.")
                else:
                    print(traceback.format_exc())
                    print(
                        f"v{Data.get_bot_version()} Unhandled error, please open a Github issue so we can fix it!"
                    )
                    if config.notifications.notify_caught_exception:
                        log.notify(
                            f"{ex}\n-------\n{traceback.format_exc()}",
                            config.notifications.model_dump(),
                        )

                sys.stdout.flush()
                time.sleep(engine.sleep_time)

    except KeyboardInterrupt:
        if config.bot.web.enabled:
            web_server.stop()
        plugins_manager.on_bot_stop()
        log.log("bye")
        print("bye")
        os._exit(0)


if __name__ == "__main__":
    main()
