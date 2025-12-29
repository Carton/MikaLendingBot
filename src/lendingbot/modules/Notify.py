import importlib.util
import json
import smtplib
import urllib.parse
import urllib.request
from typing import Any


IRC_LOADED = importlib.util.find_spec("irc") is not None

IRC_CLIENT: Any | None = None
IRC_SERVER: Any | None = None


class NotificationException(Exception):
    pass


def check_urllib_response(response: Any, platform: str) -> None:
    response_str = response.read().decode("utf-8")
    response_obj = json.loads(response_str)
    if not response_obj.get("ok"):
        msg = f"Error connecting to {platform}, got response: {response_obj}"
        raise NotificationException(msg)


def post_to_slack(msg: str, channels: list[str], token: str, username: str) -> None:
    """
    Posts a message to one or more Slack channels.

    Args:
        msg: The message text.
        channels: List of Slack channel names/IDs.
        token: Slack API token.
        username: The username to display the message as.
    """
    for channel in channels:
        post_data = {"text": msg, "channel": channel, "token": token, "username": username}
        enc_post_data = urllib.parse.urlencode(post_data).encode("utf-8")
        url = "https://slack.com/api/chat.postMessage"
        req = urllib.request.Request(url, data=enc_post_data)
        with urllib.request.urlopen(req) as response:
            check_urllib_response(response, "slack")


def post_to_telegram(msg: str, chat_ids: list[str], bot_id: str) -> None:
    """
    Sends a message to one or more Telegram chat IDs.

    Args:
        msg: The message text.
        chat_ids: List of Telegram chat IDs.
        bot_id: The Telegram bot ID.
    """
    for chat_id in chat_ids:
        post_data = {"chat_id": chat_id, "text": msg}
        enc_post_data = urllib.parse.urlencode(post_data).encode("utf-8")
        url = f"https://api.telegram.org/bot{bot_id}/sendMessage"
        try:
            req = urllib.request.Request(url, data=enc_post_data)
            with urllib.request.urlopen(req) as response:
                check_urllib_response(response, "telegram")
        except Exception as e:
            msg_err = "Your bot id is probably configured incorrectly"
            raise NotificationException(f"{e}\n{msg_err}") from e


def send_email(
    msg: str,
    email_login_address: str,
    email_login_password: str,
    email_smtp_server: str,
    email_smtp_port: int,
    email_to_addresses: list[str],
    email_smtp_starttls: bool,
) -> None:
    """
    Sends an email notification via SMTP.

    Args:
        msg: The message body.
        email_login_address: SMTP login username.
        email_login_password: SMTP login password.
        email_smtp_server: SMTP server address.
        email_smtp_port: SMTP server port.
        email_to_addresses: List of recipient addresses.
        email_smtp_starttls: Whether to use STARTTLS.
    """
    subject = "Lending bot"
    # ... rest of function

    email_text = "\r\n".join(
        [
            f"From: {email_login_address}",
            f"To: {', '.join(email_to_addresses)}",
            f"Subject: {subject}",
            "",
            f"{msg}",
        ]
    )

    try:
        if email_smtp_starttls:
            server = smtplib.SMTP(email_smtp_server, email_smtp_port)
            server.ehlo()
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(email_smtp_server, email_smtp_port)
        server.ehlo()
        server.login(email_login_address, email_login_password)
        server.sendmail(email_login_address, email_to_addresses, email_text)
        server.close()
    except Exception as e:
        print(f"Could not send email, got error {e}")
        raise NotificationException(e) from e


def post_to_pushbullet(msg: str, token: str, deviceid: str) -> None:
    post_data = {"body": msg, "device_iden": deviceid, "title": "Poloniex Bot", "type": "note"}
    req = urllib.request.Request(
        "https://api.pushbullet.com/v2/pushes",
        data=json.dumps(post_data).encode("utf-8"),
        headers={"Content-Type": "application/json", "Access-Token": token},
    )
    try:
        with urllib.request.urlopen(req):
            pass
    except Exception as e:
        print(f"Could not send pushbullet, got error {e}")
        raise NotificationException(e) from e


def post_to_irc(
    msg: str, host: str, port: int, nick: str, ident: str, realname: str, target: str
) -> None:
    """
    Log into an IRC server and send a message to a channel.

    Args:
        msg: The message to send.
        host: IRC server hostname.
        port: IRC server port.
        nick: IRC nickname.
        ident: IRC identity.
        realname: IRC real name.
        target: Target channel or user.
    """
    global IRC_CLIENT, IRC_SERVER
    if not IRC_LOADED:
        print("IRC module not available, please run 'pip install irc'")
        return

    from irc import client  # Optional dependency

    if IRC_CLIENT is None:
        IRC_CLIENT = client.Reactor()
        IRC_SERVER = IRC_CLIENT.server()

    if IRC_SERVER:
        IRC_SERVER.connect(host, port, nick)
        if client.is_channel(target):
            IRC_SERVER.join(target)
        for line in msg.splitlines():
            IRC_SERVER.privmsg(target, line)


def send_notification(_msg: str, notify_conf: dict[str, Any]) -> None:
    """
    Dispatches a notification message to all configured platforms.

    Args:
        _msg: The message to send.
        notify_conf: Notification configuration dictionary.
    """
    nc = notify_conf
    msg = _msg if ("notify_prefix" not in nc) else f"{nc['notify_prefix']} {_msg}"

    if nc.get("email"):
        send_email(
            msg,
            nc["email_login_address"],
            nc["email_login_password"],
            nc["email_smtp_server"],
            int(nc["email_smtp_port"]),
            nc["email_to_addresses"],
            nc["email_smtp_starttls"],
        )
    if nc.get("slack"):
        post_to_slack(msg, nc["slack_channels"], nc["slack_token"], nc["slack_username"])
    if nc.get("telegram"):
        post_to_telegram(msg, nc["telegram_chat_ids"], nc["telegram_bot_id"])
    if nc.get("pushbullet"):
        post_to_pushbullet(msg, nc["pushbullet_token"], nc["pushbullet_deviceid"])
    if nc.get("irc"):
        if IRC_LOADED:
            post_to_irc(
                msg,
                nc["irc_host"],
                int(nc["irc_port"]),
                nc["irc_nick"],
                nc["irc_ident"],
                nc["irc_realname"],
                nc["irc_target"],
            )
        else:
            print("IRC module not available, please run 'pip install irc'")
