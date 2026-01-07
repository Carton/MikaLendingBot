
import http.client
import os
import socket
import sys
import time
import traceback
import urllib.error
from pathlib import Path
from typing import Any, Optional

from lendingbot.modules import (
    Configuration,
    Data,
    Lending,
    MarketAnalysis,
    PluginsManager,
    WebServer,
)
from lendingbot.modules.ExchangeApi import ApiError
from lendingbot.modules.ExchangeApiFactory import ExchangeApiFactory
from lendingbot.modules.Logger import Logger

class BotOrchestrator:
    def __init__(self, config_path: str | Path, dry_run: bool = False):
        self.config_path = Path(config_path) if isinstance(config_path, str) else config_path
        self.dry_run = dry_run
        
        # Components
        self.config = None
        self.log = None
        self.api = None
        self.analysis = None
        self.engine = None
        self.plugins_manager = None
        self.web_server = None
        
        # Runtime state
        self.dns_cache: dict[Any, Any] = {}
        self.last_summary_time = 0.0

    def initialize(self) -> None:
        """
        Initializes all the bot components.
        """
        # Load configuration
        try:
            if self.config_path.suffix == ".cfg":
                print("Warning: .cfg files are legacy. Please migrate to .toml.")
                
            self.config = Configuration.load_config(self.config_path)
        except FileNotFoundError:
            print(f"Config file '{self.config_path}' not found. Please create one.")
            sys.exit(1)
        except Exception as ex:
            print(f"Error loading configuration: {ex}")
            sys.exit(1)
        
        # Initialize Logger
        try:
            self.log = Logger(
                json_file=self.config.bot.json_file,
                json_log_size=self.config.bot.json_log_size,
                exchange=self.config.api.exchange.value,
                label=self.config.bot.label,
            )
        except Exception as ex:
            print(f"Error initializing Logger: {ex}")
            sys.exit(1)

        # Initialize API
        try:
            self.api = ExchangeApiFactory.createApi(
                self.config.api.exchange.value, 
                self.config, 
                self.log
            )
        except Exception as ex:
            print(f"Error initializing API: {ex}")
            sys.exit(1)

        # Initialize Market Analysis
        if self.config.plugins.market_analysis.analyse_currencies:
            try:
                self.analysis = MarketAnalysis.MarketAnalysis(self.config, self.api)
                self.analysis.run()
            except Exception as ex:
                print(f"Error initializing Market Analysis: {ex}")
                sys.exit(1)

        # Initialize Lending Engine
        try:
            self.engine = Lending.LendingEngine(
                self.config, 
                self.api, 
                self.log, 
                Data, 
                self.analysis
            )
            self.engine.initialize(dry_run=self.dry_run)
        except Exception as ex:
            print(f"Error initializing Lending Engine: {ex}")
            sys.exit(1)
        
        # Initialize Plugins
        try:
            self.plugins_manager = PluginsManager.PluginsManager(
                self.config, 
                self.api, 
                self.log
            )
            # Backward compatibility globals (to be phased out ideally)
            PluginsManager._manager = self.plugins_manager
        except Exception as ex:
            print(f"Error initializing Plugins: {ex}")
            sys.exit(1)

        # Initialize Web Server
        if self.config.bot.web.enabled:
            self.web_server = WebServer.WebServer(self.config, self.engine)
            # Global for backward compatibility
            WebServer._web_server = self.web_server

    def _setup_dns_cache(self):
        """Monkeys patches socket.getaddrinfo to cache DNS results."""
        prv_getaddrinfo = socket.getaddrinfo
        self.dns_cache = {}

        def new_getaddrinfo(*urlargs: Any) -> Any:
            try:
                return self.dns_cache[urlargs]
            except KeyError:
                res = prv_getaddrinfo(*urlargs)
                self.dns_cache[urlargs] = res
                return res

        socket.getaddrinfo = new_getaddrinfo  # type: ignore[assignment]

    def step(self) -> None:
        """
        Executes a single iteration of the bot loop.
        """
        self.dns_cache.clear()  # Flush DNS Cache
        Data.update_conversion_rates(self.config.bot.output_currency, self.config.bot.web.enabled)

        if self.engine.lending_paused != self.engine.last_lending_status:
            if not self.engine.lending_paused:
                self.log.log("Lending running")
            else:
                self.log.log("Lending paused")
            self.engine.last_lending_status = self.engine.lending_paused

        if not self.engine.lending_paused:
            self.plugins_manager.before_lending()
            self.engine.transfer_balances()
            self.engine.cancel_all()
            self.engine.lend_all()
            self.plugins_manager.after_lending()

        lent_status_str = Data.stringify_total_lent(Data.get_total_lent())
        if time.time() - self.last_summary_time >= self.config.bot.period_inactive:
            self.log.log(lent_status_str)
            self.last_summary_time = time.time()

        self.log.persistStatus()
        sys.stdout.flush()

    def run(self) -> None:
        """
        Starts the main loop of the bot.
        """
        if self.web_server:
            self.web_server.start()
        
        self._setup_dns_cache()
        
        self.log.log(f"Welcome to {self.config.bot.label} on {self.config.api.exchange.value}")
        self.engine.start_scheduler()
        
        if self.engine.coin_cfg:
            strategies_log = [f"{cur}: {cfg.strategy}" for cur, cfg in self.engine.coin_cfg.items()]
            print(f"Active Lending Strategies: {', '.join(strategies_log)}")

        try:
            self.last_summary_time = 0.0
            while True:
                try:
                    self.step()
                    time.sleep(self.engine.sleep_time)
                except KeyboardInterrupt:
                    raise
                except Exception as ex:
                    self._handle_exception(ex)
                    sys.stdout.flush()
                    time.sleep(self.engine.sleep_time)

        except KeyboardInterrupt:
            self.stop()

    def _handle_exception(self, ex: Exception) -> None:
        msg = str(ex)
        self.log.log_error(msg)
        self.log.persistStatus()

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
            print(f"Timed out, will retry in {self.engine.sleep_time}sec")
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
            if self.config.notifications.notify_caught_exception:
                self.log.notify(
                    f"{ex}\n-------\n{traceback.format_exc()}",
                    self.config.notifications.model_dump(),
                )

    def stop(self):
        if self.web_server:
            self.web_server.stop()
        if self.plugins_manager:
            self.plugins_manager.on_bot_stop()
        if self.log:
            self.log.log("bye")
        print("bye")
        os._exit(0)

