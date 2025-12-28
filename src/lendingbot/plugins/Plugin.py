from typing import Any


class Plugin:
    def __init__(self, cfg1: Any, api1: Any, log1: Any, notify_config1: Any) -> None:
        self.api = api1
        self.config = cfg1
        self.notify_config = notify_config1
        self.log = log1

    # override this to run plugin init code
    def on_bot_init(self) -> None:
        self.log.log(f"{self.__class__.__name__} plugin initializing...")

    # override this to run plugin loop code before lending
    def before_lending(self) -> None:
        pass

    # override this to run plugin loop code after lending
    def after_lending(self) -> None:
        pass

    # override this to run plugin stop code
    # since the bot can be killed, there is not guarantee this will be called.
    def on_bot_stop(self) -> None:
        pass
