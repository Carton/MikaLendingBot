from typing import Any

from .. import plugins
from . import Configuration
from .Logger import Logger


class PluginsManager:
    def __init__(self, config: Configuration.RootConfig, api: Any, log: Logger):
        self.config = config
        self.api = api
        self.log = log
        self.active_plugins: list[Any] = []
        
        # Initialize plugins based on config
        plugin_names = []
        if self.config.plugins.account_stats.get("enabled"):
            plugin_names.append("AccountStats")
        if self.config.plugins.charts.get("enabled"):
            plugin_names.append("Charts")
            
        for name in plugin_names:
            try:
                plugin_class = getattr(plugins, name)
                # Ensure we pass the RootConfig and the notifications dict for compatibility
                instance = plugin_class(self.config, self.api, self.log, self.config.notifications.model_dump())
                instance.on_bot_init()
                self.active_plugins.append(instance)
            except AttributeError:
                self.log.log_error(f"Plugin {name} not found in plugins folder")
            except Exception as ex:
                self.log.log_error(f"Error initializing plugin {name}: {ex}")

    def before_lending(self) -> None:
        for plugin in self.active_plugins:
            try:
                plugin.before_lending()
            except Exception as ex:
                self.log.log_error(
                    f"Error in before_lending for plugin {plugin.__class__.__name__}: {ex}"
                )

    def after_lending(self) -> None:
        for plugin in self.active_plugins:
            try:
                plugin.after_lending()
            except Exception as ex:
                self.log.log_error(
                    f"Error in after_lending for plugin {plugin.__class__.__name__}: {ex}"
                )

    def on_bot_stop(self) -> None:
        for plugin in self.active_plugins:
            try:
                plugin.on_bot_stop()
            except Exception as ex:
                self.log.log_error(f"Error in on_bot_stop for plugin {plugin.__class__.__name__}: {ex}")


# Backward compatibility wrappers
_manager: PluginsManager | None = None

def init(cfg: Configuration.RootConfig, api: Any, log: Logger, notify_conf: dict[str, Any]) -> None:
    global _manager
    _manager = PluginsManager(cfg, api, log)

def before_lending() -> None:
    if _manager:
        _manager.before_lending()

def after_lending() -> None:
    if _manager:
        _manager.after_lending()

def on_bot_stop() -> None:
    if _manager:
        _manager.on_bot_stop()