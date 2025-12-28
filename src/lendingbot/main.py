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
import os
import socket
import sys
import time
import traceback
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
    # Parse command line arguments
    args = parse_arguments()
    dry_run = bool(args.dryrun)
    config_location = args.config or "default.cfg"

    # 1. Load config
    Config.init(config_location)

    output_currency = str(Config.get("BOT", "outputCurrency", "BTC"))
    end_date = Config.get("BOT", "endDate")
    exchange = Config.get_exchange()

    json_output_enabled = Config.has_option("BOT", "jsonfile") and Config.has_option(
        "BOT", "jsonlogsize"
    )
    json_file = str(Config.get("BOT", "jsonfile", ""))

    # Configure web server
    web_server_enabled = Config.getboolean("BOT", "startWebServer")
    if web_server_enabled:
        if not json_output_enabled:
            # User wants webserver enabled. Must have JSON enabled. Force logging with defaults.
            json_output_enabled = True
            json_file = str(Config.get("BOT", "jsonfile", "www/botlog.json"))

        WebServer.initialize_web_server(Config)

    # Configure logging
    log = Logger(json_file, int(Config.get("BOT", "jsonlogsize", 200)), exchange)

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
        while True:
            try:
                dns_cache.clear()  # Flush DNS Cache
                Data.update_conversion_rates(output_currency, json_output_enabled)

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

                log.refreshStatus(
                    Data.stringify_total_lent(*Data.get_total_lent()),
                    str(Data.get_max_duration(end_date, "status")),
                )
                log.persistStatus()
                sys.stdout.flush()
                time.sleep(Lending.get_sleep_time())
            except KeyboardInterrupt:
                raise
            except Exception as ex:
                msg = getattr(ex, "message", str(ex))
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
                elif "Error 429" in msg:
                    add_sleep = max(130.0 - Lending.get_sleep_time(), 0)
                    sum_sleep = add_sleep + Lending.get_sleep_time()
                    log.log_error(
                        f"IP has been banned due to many requests. Sleeping for {sum_sleep} seconds"
                    )
                    if Config.has_option("MarketAnalysis", "analyseCurrencies"):
                        if api.req_period <= api.default_req_period * 1.5:
                            api.req_period += 1000
                        # Check debug log setting
                        if Config.getboolean("MarketAnalysis", "ma_debug_log"):
                            print(
                                f"Caught ERR_RATE_LIMIT, sleeping capture and increasing request delay. Current {api.req_period}ms"
                            )
                            log.log_error(
                                "Expect this 130s ban periodically when using MarketAnalysis, it will fix itself"
                            )
                    time.sleep(add_sleep)
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
