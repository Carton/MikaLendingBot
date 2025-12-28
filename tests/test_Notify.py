"""
Tests for Notify module.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules import Notify


class TestNotify:
    @patch("urllib.request.urlopen")
    def test_post_to_slack(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        Notify.post_to_slack("test", ["channel"], "token", "user")
        mock_urlopen.assert_called()

    @patch("urllib.request.urlopen")
    def test_check_urllib_response_error(self, _mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": False, "error": "failed"}).encode(
            "utf-8"
        )
        with pytest.raises(Notify.NotificationException):
            Notify.check_urllib_response(mock_response, "test")

    @patch("urllib.request.urlopen")
    def test_post_to_telegram_error(self, mock_urlopen):
        # Mock connection error
        mock_urlopen.side_effect = Exception("conn error")
        with pytest.raises(Notify.NotificationException) as exc:
            Notify.post_to_telegram("msg", ["123"], "botid")
        assert "probably configured incorrectly" in str(exc.value)

    @patch("urllib.request.urlopen")
    def test_post_to_pushbullet(self, mock_urlopen):
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        Notify.post_to_pushbullet("msg", "token", "devid")
        mock_urlopen.assert_called()

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
