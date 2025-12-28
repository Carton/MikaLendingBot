from typing import Any

from .. import plugins
from .Logger import Logger


api: Any = None
log: Logger | None = None
config: Any = None
notify_config: dict[str, Any] = {}
active_plugins: list[Any] = []


def init(cfg1: Any, api1: Any, log1: Logger, notify_conf1: dict[str, Any]) -> None:
    global api, log, config, notify_config
    api = api1
    log = log1
    config = cfg1
    notify_config = notify_conf1

    plugin_names = config.get_plugins_config()
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
