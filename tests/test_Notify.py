"""
Tests for Notify module.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from lendingbot.modules import Notify


def _ok_response():
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    return mock_response


def _http_error_response():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_response.json.return_value = {"ok": True}
    return mock_response


class TestNotify:
    @patch("lendingbot.modules.Notify.requests.post")
    def test_post_to_slack(self, mock_post):
        mock_post.return_value = _ok_response()

        Notify.post_to_slack("test", ["channel"], "token", "user")
        mock_post.assert_called()

    def test_check_response_error(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "failed"}
        with pytest.raises(Notify.NotificationException):
            Notify.check_response(mock_response, "test")

    @patch("lendingbot.modules.Notify.requests.post")
    def test_slack_http_error_raises(self, mock_post):
        mock_post.return_value = _http_error_response()
        with pytest.raises(requests.HTTPError):
            Notify.post_to_slack("test", ["channel"], "token", "user")

    @patch("lendingbot.modules.Notify.requests.post")
    def test_telegram_http_error_wrapped(self, mock_post):
        mock_post.return_value = _http_error_response()
        with pytest.raises(Notify.NotificationException) as exc:
            Notify.post_to_telegram("msg", ["123"], "botid")
        assert "probably configured incorrectly" in str(exc.value)

    @patch("lendingbot.modules.Notify.requests.post")
    def test_post_to_telegram_error(self, mock_post):
        # Mock connection error
        mock_post.side_effect = Exception("conn error")
        with pytest.raises(Notify.NotificationException) as exc:
            Notify.post_to_telegram("msg", ["123"], "botid")
        assert "probably configured incorrectly" in str(exc.value)

    @patch("lendingbot.modules.Notify.requests.post")
    def test_post_to_pushbullet(self, mock_post):
        mock_post.return_value = _ok_response()
        Notify.post_to_pushbullet("msg", "token", "devid")
        mock_post.assert_called()

    @patch("smtplib.SMTP")
    def test_send_email_error(self, mock_smtp):
        mock_instance = MagicMock()
        mock_instance.login.side_effect = Exception("Login failed")
        mock_smtp.return_value = mock_instance
        with pytest.raises(Notify.NotificationException):
            Notify.send_email("msg", "from", "pass", "host", 587, ["to"], True)

    def test_post_to_irc(self):
        # Coverage for IRC method
        mock_client = MagicMock()
        mock_server = MagicMock()
        mock_client.server.return_value = mock_server

        # Mock the entire irc module
        with patch.dict("sys.modules", {"irc": MagicMock(), "irc.client": MagicMock()}):
            import irc.client

            irc.client.Reactor = MagicMock(return_value=mock_client)
            irc.client.is_channel = MagicMock(return_value=True)

            Notify.IRC_LOADED = True
            Notify.post_to_irc("msg", "host", 6667, "nick", "id", "name", "#chan")
            mock_server.connect.assert_called()
            mock_server.privmsg.assert_called()

    def test_send_notification_all_platforms(self):
        # Comprehensive notification config test
        with (
            patch("lendingbot.modules.Notify.send_email") as m_email,
            patch("lendingbot.modules.Notify.post_to_slack") as m_slack,
            patch("lendingbot.modules.Notify.post_to_telegram") as m_tele,
            patch("lendingbot.modules.Notify.post_to_pushbullet") as m_push,
            patch("lendingbot.modules.Notify.post_to_irc") as m_irc,
        ):
            Notify.IRC_LOADED = True
            conf = {
                "email": True,
                "slack": True,
                "telegram": True,
                "pushbullet": True,
                "irc": True,
                "email_login_address": "a",
                "email_login_password": "p",
                "email_smtp_server": "s",
                "email_smtp_port": 25,
                "email_to_addresses": [],
                "email_smtp_starttls": False,
                "slack_channels": [],
                "slack_token": "t",
                "slack_username": "u",
                "telegram_chat_ids": [],
                "telegram_bot_id": "b",
                "pushbullet_token": "pt",
                "pushbullet_deviceid": "pd",
                "irc_host": "h",
                "irc_port": 6667,
                "irc_nick": "n",
                "irc_ident": "i",
                "irc_realname": "rn",
                "irc_target": "t",
            }
            Notify.send_notification("hello", conf)
            assert m_email.called
            assert m_slack.called
            assert m_tele.called
            assert m_push.called
            assert m_irc.called

    def test_send_notification_prefix(self):
        # We only test the logic of prefixing here, as sub-methods are tested above
        with patch("lendingbot.modules.Notify.post_to_slack") as mock_slack:
            notify_conf = {
                "slack": True,
                "slack_channels": ["ch"],
                "slack_token": "tk",
                "slack_username": "un",
                "notify_prefix": "[BOT]",
            }
            Notify.send_notification("hello", notify_conf)
            mock_slack.assert_called_with("[BOT] hello", ["ch"], "tk", "un")
