from typing import Any

from .. import plugins
from . import Configuration
from .Logger import Logger


api: Any = None
log: Logger | None = None
config: Configuration.RootConfig = None # type: ignore
notify_config: dict[str, Any] = {}
active_plugins: list[Any] = []


def init(cfg1: Configuration.RootConfig, api1: Any, log1: Logger, notify_conf1: dict[str, Any]) -> None:
    global api, log, config, notify_config
    api = api1
    log = log1
    config = cfg1
    notify_config = notify_conf1

    plugin_names = []
    if config.plugins.account_stats.get("enabled"):
        plugin_names.append("AccountStats")
    if config.plugins.charts.get("enabled"):
        plugin_names.append("Charts")
    for name in plugin_names:
        try:
            plugin_class = getattr(plugins, name)
            instance = plugin_class(config, api, log, notify_config)
            instance.on_bot_init()
            active_plugins.append(instance)
        except AttributeError:
            log.log_error(f"Plugin {name} not found in plugins folder")
        except Exception as ex:
            log.log_error(f"Error initializing plugin {name}: {ex}")


def before_lending() -> None:
    for plugin in active_plugins:
        try:
            plugin.before_lending()
        except Exception as ex:
            if log:
                log.log_error(
                    f"Error in before_lending for plugin {plugin.__class__.__name__}: {ex}"
                )


def after_lending() -> None:
    for plugin in active_plugins:
        try:
            plugin.after_lending()
        except Exception as ex:
            if log:
                log.log_error(
                    f"Error in after_lending for plugin {plugin.__class__.__name__}: {ex}"
                )


def on_bot_stop() -> None:
    for plugin in active_plugins:
        try:
            plugin.on_bot_stop()
        except Exception as ex:
            if log:
                log.log_error(f"Error in on_bot_stop for plugin {plugin.__class__.__name__}: {ex}")
