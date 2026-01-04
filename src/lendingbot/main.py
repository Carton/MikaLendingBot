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

from .modules import Configuration
from .modules import Data, Lending, MaxToLend, PluginsManager, WebServer, MarketAnalysis
from .modules.ExchangeApi import ApiError
from .modules.ExchangeApiFactory import ExchangeApiFactory
from .modules.Logger import Logger


# Add type hints and docstrings
def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments

    Returns:
        argparse.Namespace: Parsed arguments object

    Command line arguments:
        -cfg, --config: Custom configuration file path
        -dry, --dryrun: Dry-run mode, does not execute actual trades
    """
    parser = argparse.ArgumentParser(
        description="LendingBot - Cryptocurrency Lending Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-cfg",
        "--config",
        help="Custom configuration file path (default: default.cfg)",
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
    config_location = args.config or "default.cfg"

    # Load configuration
    try:
        # Default to 'default.toml' if it exists
        config_path = Path("default.toml")
        if args.config:
            config_path = Path(args.config)
            if config_path.suffix == '.cfg':
                print("Warning: .cfg files are legacy. Please migrate to .toml.")
                # We could support legacy loading via a bridge, but for now we enforce TOML
                # or we just fail. User instruction says 'migrate'
        
        config = Configuration.load_config(config_path)
    except FileNotFoundError:
        print(f"Config file '{config_path}' not found. Please create one.")
        sys.exit(1)
    except Exception as ex:
        print(f"Error loading configuration: {ex}")
        sys.exit(1)

    try:
        # Data module doesn't need config init anymore based on our analysis
        pass 
    except Exception as ex:
        print("Error initializing Data module: {0}".format(ex))
        sys.exit(1)

    # ... Logger init ...
    # Initialize the logger with the new config structure
    try:
        log = Logger(
            json_file=config.bot.json_file,
            json_log_size=config.bot.json_log_size,
            exchange=config.api.exchange.value,
            label=config.bot.label,
        )
    except Exception as ex:
        print("Error initializing Logger: {0}".format(ex))
        sys.exit(1)

    try:
        api = ExchangeApiFactory.createApi(config.api.exchange.value, config, log)
    except Exception as ex:
        print("Error initializing API: {0}".format(ex))
        sys.exit(1)

    # Initialize sub-modules
    try:
        notify_conf = config.notifications.model_dump()
        # Pass the new config object
        Lending.init(config, api, log, Data, MaxToLend, args.dryrun, MarketAnalysis, notify_conf)
    except Exception as ex:
        print("Error initializing Lending: {0}".format(ex))
        sys.exit(1)

    # Log active lending strategies (must be after Lending.init where coin_cfg is populated)
    if Lending.coin_cfg:
        strategies_log = [f"{cur}: {cfg.strategy}" for cur, cfg in Lending.coin_cfg.items()]
        print(f"Active Lending Strategies: {', '.join(strategies_log)}")

    # Load plugins
    PluginsManager.init(config, api, log, notify_conf)

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

    try:
        last_summary_time = 0.0
        while True:
            try:
                dns_cache.clear()  # Flush DNS Cache
                Data.update_conversion_rates(config.bot.output_currency, config.bot.web.enabled)

                if Lending.lending_paused != Lending.last_lending_status:
                    if not Lending.lending_paused:
                        log.log("Lending running")
                    else:
                        log.log("Lending paused")
                    Lending.last_lending_status = Lending.lending_paused

                if not Lending.lending_paused:
                    PluginsManager.before_lending()
                    Lending.transfer_balances()
                    Lending.cancel_all()
                    Lending.lend_all()
                    PluginsManager.after_lending()

                lent_status_str = Data.stringify_total_lent(Data.get_total_lent())
                if time.time() - last_summary_time >= Lending.get_sleep_time_inactive():
                    log.log(lent_status_str)
                    last_summary_time = time.time()
                log.persistStatus()
                sys.stdout.flush()
                time.sleep(Lending.get_sleep_time())
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
                    print(f"Timed out, will retry in {Lending.get_sleep_time()}sec")
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
                    if notify_conf["notify_caught_exception"]:
                        log.notify(f"{ex}\n-------\n{traceback.format_exc()}", notify_conf)

                sys.stdout.flush()
                time.sleep(Lending.get_sleep_time())

    except KeyboardInterrupt:
        if config.bot.web.enabled:
            WebServer.stop_web_server()
        PluginsManager.on_bot_stop()
        log.log("bye")
        print("bye")
        os._exit(0)


if __name__ == "__main__":
    main()
