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

from .modules import Configuration as Config
from .modules import Data, Lending, MaxToLend, PluginsManager, WebServer
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

    # 1. Load config
    Config.init(config_location)

    if args.verbose:
        Lending.debug_on = True
        if not Config.config.has_section("BOT"):
            Config.config.add_section("BOT")
        Config.config.set("BOT", "api_debug_log", "True")

    output_currency = str(Config.get("BOT", "outputCurrency", "BTC"))
    exchange = Config.get_exchange()

    # Configure web server and JSON logging
    # Note: When webserver is enabled, json logging is always enabled with hardcoded paths
    # because the frontend expects files at specific locations (logs/botlog.json)
    web_server_enabled = Config.getboolean("BOT", "startWebServer")
    json_file = "logs/botlog.json" if web_server_enabled else ""
    json_log_size = int(Config.get("BOT", "jsonlogsize", 200))

    if web_server_enabled:
        WebServer.initialize_web_server(Config)

    # Configure logging
    log = Logger(json_file, json_log_size, exchange)

    # Initialize the remaining stuff
    api = ExchangeApiFactory.createApi(exchange, Config, log)
    MaxToLend.init(Config, log)
    Data.init(api, log)
    Config.init(config_location, Data)
    notify_conf = Config.get_notification_config()

    analysis = None
    if Config.has_option("MarketAnalysis", "analyseCurrencies"):
        from .modules.MarketAnalysis import MarketAnalysis

        analysis = MarketAnalysis(Config, api)
        analysis.run()

    Lending.init(Config, api, log, Data, MaxToLend, dry_run, analysis, notify_conf)

    # Load plugins
    PluginsManager.init(Config, api, log, notify_conf)

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

    log.log(f"Welcome to {Config.get('BOT', 'label', 'Lending Bot')} on {exchange}")

    try:
        last_summary_time = 0.0
        while True:
            try:
                dns_cache.clear()  # Flush DNS Cache
                Data.update_conversion_rates(output_currency, web_server_enabled)

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
        if web_server_enabled:
            WebServer.stop_web_server()
        PluginsManager.on_bot_stop()
        log.log("bye")
        print("bye")
        os._exit(0)


if __name__ == "__main__":
    main()
