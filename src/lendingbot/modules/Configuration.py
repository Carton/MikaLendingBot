import configparser
import os
import shutil
from decimal import Decimal
from typing import Any


config = configparser.ConfigParser()
Data: Any = None
# This module is the middleman between the bot and a ConfigParser object, so that we can add extra functionality
# without clogging up lendingbot.py with all the config logic. For example, added a default value to get().


def init(file_location: str, data: Any = None) -> configparser.ConfigParser:
    global Data
    Data = data
    loaded_files = config.read(file_location, encoding="utf-8")
    if len(loaded_files) != 1:
        # Copy default config file if not found
        try:
            shutil.copy("default.cfg.example", file_location)
            print(
                f"\ndefault.cfg.example has been copied to {file_location}\n"
                "Edit it with your API key and custom settings.\n"
            )
            input("Press Enter to acknowledge and exit...")
            exit(1)
        except Exception as ex:
            msg = str(ex)
            print(f"Failed to automatically copy config. Please do so manually. Error: {msg}")
            exit(1)
    if config.has_option("BOT", "coinconfig"):
        print(
            "'coinconfig' has been removed, please use section coin config instead.\n"
            "See: http://poloniexlendingbot.readthedocs.io/en/latest/configuration.html#config-per-coin"
        )
        exit(1)
    return config


def has_option(category: str, option: str) -> bool:
    try:
        return bool(os.environ.get(f"{category}_{option}")) or config.has_option(category, option)
    except Exception:
        return config.has_option(category, option)


def getboolean(category: str, option: str, default_value: bool = False) -> bool:
    if has_option(category, option):
        env_val = os.environ.get(f"{category}_{option}")
        if env_val is not None:
            return env_val.lower() in ("true", "1", "t", "y", "yes")
        return config.getboolean(category, option)
    else:
        return default_value


def get(
    category: str,
    option: str,
    default_value: Any = False,
    lower_limit: float | bool = False,
    upper_limit: float | bool = False,
) -> Any:
    if has_option(category, option):
        value = os.environ.get(f"{category}_{option}")
        if value is None:
            value = config.get(category, option)
        try:
            if lower_limit is not False and float(value) < float(lower_limit):
                print(
                    f"WARN: [{category}]-{option}'s value: '{value}' is below the minimum limit: {lower_limit}, which will be used instead."
                )
                value = str(lower_limit)
            if upper_limit is not False and float(value) > float(upper_limit):
                print(
                    f"WARN: [{category}]-{option}'s value: '{value}' is above the maximum limit: {upper_limit}, which will be used instead."
                )
                value = str(upper_limit)
            return value
        except ValueError:
            if default_value is None:
                print(
                    f"ERROR: [{category}]-{option} is not allowed to be left empty. Please check your config."
                )
                exit(1)
            return default_value
    else:
        if default_value is None:
            print(
                f"ERROR: [{category}]-{option} is not allowed to be left unset. Please check your config."
            )
            exit(1)
        return default_value


# Below: functions for returning some config values that require special treatment.


def get_exchange() -> str:
    """
    Returns used exchange
    """
    try:
        val = os.environ.get("API_EXCHANGE", get("API", "exchange", "Poloniex"))
        return str(val).upper()
    except Exception:
        return "POLONIEX"


def get_coin_cfg() -> dict[str, Any]:
    coin_cfg: dict[str, Any] = {}
    for cur in get_all_currencies():
        if config.has_section(cur):
            try:
                coin_cfg[cur] = {}
                coin_cfg[cur]["minrate"] = (Decimal(config.get(cur, "mindailyrate"))) / 100
                coin_cfg[cur]["maxactive"] = Decimal(config.get(cur, "maxactiveamount"))
                coin_cfg[cur]["maxtolend"] = Decimal(config.get(cur, "maxtolend"))
                coin_cfg[cur]["maxpercenttolend"] = (
                    Decimal(config.get(cur, "maxpercenttolend"))
                ) / 100
                coin_cfg[cur]["maxtolendrate"] = (Decimal(config.get(cur, "maxtolendrate"))) / 100
                coin_cfg[cur]["gapmode"] = get_gap_mode(cur, "gapmode")
                coin_cfg[cur]["gapbottom"] = Decimal(get(cur, "gapbottom", False, 0))
                coin_cfg[cur]["gaptop"] = Decimal(
                    get(cur, "gaptop", False, coin_cfg[cur]["gapbottom"])
                )
                coin_cfg[cur]["frrasmin"] = getboolean(
                    cur, "frrasmin", getboolean("BOT", "frrasmin")
                )
                coin_cfg[cur]["frrdelta_min"] = Decimal(get(cur, "frrdelta_min", 0.0000))
                coin_cfg[cur]["frrdelta_max"] = Decimal(get(cur, "frrdelta_max", 0.00008))

            except Exception as ex:
                msg = str(ex)
                print(
                    f"Coin Config for {cur} parsed incorrectly, please refer to the documentation. "
                    f"Error: {msg}"
                )
                # Need to raise this exception otherwise the bot will continue if you configured one cur correctly
                raise
    return coin_cfg


def get_min_loan_sizes() -> dict[str, Decimal]:
    min_loan_sizes: dict[str, Decimal] = {}
    for cur in get_all_currencies():
        if config.has_section(cur):
            try:
                min_loan_sizes[cur] = Decimal(get(cur, "minloansize", lower_limit=0.005))
            except Exception as ex:
                msg = str(ex)
                print(
                    f"minloansize for {cur} parsed incorrectly, please refer to the documentation. "
                    f"Error: {msg}"
                )
                # Bomb out if something isn't configured correctly
                raise
    return min_loan_sizes


def get_currencies_list(option: str, section: str = "BOT") -> list[str]:
    if config.has_option(section, option):
        full_list = get_all_currencies()
        cur_list: list[str] = []
        raw_cur_list = config.get(section, option).split(",")
        for raw_cur in raw_cur_list:
            cur = raw_cur.strip(" ").upper()
            if cur == "ALL":
                return full_list
            elif cur == "ACTIVE":
                if Data:
                    cur_list += Data.get_lending_currencies()
            else:
                if cur in full_list:
                    cur_list.append(cur)
        return list(set(cur_list))
    else:
        return []


def get_gap_mode(category: str, option: str) -> str | bool:
    if config.has_option(category, option):
        full_list = ["raw", "rawbtc", "relative"]
        raw_val = get(category, "gapmode", False)
        if not raw_val:
            return False
        value = str(raw_val).lower().strip(" ")
        if value not in full_list:
            print(
                f"ERROR: Invalid entry '{value}' for [{category}]-gapMode. Please check your config. Allowed values are: {', '.join(full_list)}"
            )
            exit(1)
        return value.lower()
    else:
        return False


def get_all_currencies() -> list[str]:
    """
    Get list of all supported currencies by exchange
    """
    exchange = get_exchange()
    if config.has_option(exchange, "all_currencies"):
        cur_list = []
        raw_cur_list = config.get(exchange, "all_currencies").split(",")
        for raw_cur in raw_cur_list:
            cur = raw_cur.strip(" ").upper()
            if cur and cur[0] != "#":  # Blacklisting: E.g. ETH, #BTG, QTUM
                cur_list.append(cur)
        return cur_list
    elif exchange == "POLONIEX":
        # default, compatibility to old 'Poloniex only' config
        return [
            "STR",
            "BTC",
            "BTS",
            "CLAM",
            "DOGE",
            "DASH",
            "LTC",
            "MAID",
            "XMR",
            "XRP",
            "ETH",
            "FCT",
        ]
    else:
        raise Exception(
            f"ERROR: List of supported currencies must defined in [{exchange}] all_currencies."
        )


def get_notification_config() -> dict[str, Any]:
    notify_conf: dict[str, Any] = {"enable_notifications": config.has_section("notifications")}

    # For boolean parameters
    for conf in [
        "notify_tx_coins",
        "notify_xday_threshold",
        "notify_new_loans",
        "notify_caught_exception",
        "email",
        "slack",
        "telegram",
        "pushbullet",
        "irc",
    ]:
        notify_conf[conf] = getboolean("notifications", conf)

    # For string-based parameters
    for conf in ["notify_prefix"]:
        _val = get("notifications", conf, "").strip()
        if len(_val) > 0:
            notify_conf[conf] = _val

    # in order not to break current config, parsing for False
    notify_summary_minutes_raw = get("notifications", "notify_summary_minutes")
    notify_conf["notify_summary_minutes"] = (
        0 if notify_summary_minutes_raw == "False" else int(notify_summary_minutes_raw)
    )

    if notify_conf["email"]:
        for conf in [
            "email_login_address",
            "email_login_password",
            "email_smtp_server",
            "email_smtp_port",
            "email_to_addresses",
            "email_smtp_starttls",
        ]:
            notify_conf[conf] = get("notifications", conf)
        notify_conf["email_to_addresses"] = notify_conf["email_to_addresses"].split(",")

    if notify_conf["slack"]:
        for conf in ["slack_token", "slack_channels", "slack_username"]:
            notify_conf[conf] = get("notifications", conf)
        notify_conf["slack_channels"] = notify_conf["slack_channels"].split(",")
        if not notify_conf["slack_username"]:
            notify_conf["slack_username"] = "Slack API Tester"

    if notify_conf["telegram"]:
        for conf in ["telegram_bot_id", "telegram_chat_ids"]:
            notify_conf[conf] = get("notifications", conf)
        notify_conf["telegram_chat_ids"] = notify_conf["telegram_chat_ids"].split(",")

    if notify_conf["pushbullet"]:
        for conf in ["pushbullet_token", "pushbullet_deviceid"]:
            notify_conf[conf] = get("notifications", conf)

    if notify_conf["irc"]:
        for conf in ["irc_host", "irc_port", "irc_nick", "irc_ident", "irc_realname", "irc_target"]:
            notify_conf[conf] = get("notifications", conf)
        notify_conf["irc_port"] = int(notify_conf["irc_port"])
        notify_conf["irc_debug"] = getboolean("notifications", "irc_debug")

    return notify_conf


def get_plugins_config() -> list[str]:
    active_plugins: list[str] = []
    if config.has_option("BOT", "plugins"):
        active_plugins = [p.strip() for p in config.get("BOT", "plugins").split(",") if p.strip()]
    return active_plugins
