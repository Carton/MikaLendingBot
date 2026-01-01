"""
Tests for WebServer module.
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.modules import Lending, WebServer


class TestWebServer:
    @pytest.fixture(autouse=True)
    def setup_lending(self):
        Lending.lending_paused = False
        Lending.frrdelta_min = Decimal("0")
        Lending.frrdelta_max = Decimal("0")

    def test_initialize_web_server(self):
        mock_config = Mock()
        mock_config.get.side_effect = lambda _s, _k, d=None: d

        with patch("threading.Thread") as mock_thread:
            WebServer.initialize_web_server(mock_config)
            assert WebServer.web_server_ip == "0.0.0.0"
            assert WebServer.web_server_port == "8000"
            mock_thread.assert_called()

    def test_stop_web_server(self):
        WebServer.server = MagicMock()
        with patch("threading.Thread") as mock_thread:
            WebServer.stop_web_server()
            mock_thread.assert_called()

    def test_handler_logic(self):
        # Capture the QuietHandler class
        handler_class = None

        def mock_tcp_init(_self, _addr, handler):
            nonlocal handler_class
            handler_class = handler

        with (
            patch("socketserver.TCPServer.__init__", mock_tcp_init),
            patch("socketserver.TCPServer.serve_forever"),
            patch("socket.gethostname", return_value="localhost"),
            patch("socket.getaddrinfo", return_value=[]),
        ):
            WebServer.start_web_server()

        if handler_class:
            # Don't use spec= here to allow dynamic attributes like rfile
            handler = MagicMock()
            handler.wfile = MagicMock()
            handler.rfile = MagicMock()

            # Test /pause_lending
            handler.path = "/pause_lending"
            handler_class.do_GET(handler)
            assert Lending.lending_paused is True
            handler.send_response.assert_called_with(200)

            # Test /resume_lending
            handler.path = "/resume_lending"
            handler_class.do_GET(handler)
            assert Lending.lending_paused is False

            # Test /get_status
            handler.path = "/get_status"
            handler_class.do_GET(handler)
            handler.send_header.assert_called_with("Content-Type", "application/json")
            # Verify JSON output
            args, _ = handler.wfile.write.call_args
            resp = json.loads(args[0].decode("utf-8"))
            assert "lending_paused" in resp

            # Test /set_config (POST)
            handler.path = "/set_config"
            config_payload = json.dumps(
                {
                    "frrdelta_min": "0.0001",
                    "frrdelta_max": "0.0005",
                    "refreshRate": 60,
                }
            ).encode("utf-8")
            handler.headers = {"Content-Length": str(len(config_payload))}
            handler.rfile.read.return_value = config_payload

            # We need to mock save_web_settings to check if it's called
            with patch.object(WebServer, "save_web_settings") as mock_save:
                handler_class.do_POST(handler)
                assert Lending.frrdelta_min == Decimal("0.0001")
                assert Lending.frrdelta_max == Decimal("0.0005")
                handler.send_response.assert_any_call(200)
                mock_save.assert_called()

            # Test /get_settings
            handler.path = "/get_settings"
            # Mock get_web_settings
            with patch.object(WebServer, "get_web_settings") as mock_get:
                mock_get.return_value = {"refreshRate": 30}
                handler_class.do_GET(handler)
                handler.send_header.assert_called_with("Content-Type", "application/json")
                args, _ = handler.wfile.write.call_args
                resp = json.loads(args[0].decode("utf-8"))
                assert resp["refreshRate"] == 30

    def test_translate_path(self):
        handler_class = None

        def mock_tcp_init(_self, _addr, handler):
            nonlocal handler_class
            handler_class = handler

        with (
            patch("socketserver.TCPServer.__init__", mock_tcp_init),
            patch("socketserver.TCPServer.serve_forever"),
            patch("socket.gethostname", return_value="localhost"),
            patch("socket.getaddrinfo", return_value=[]),
        ):
            WebServer.start_web_server()

        if handler_class:
            handler = MagicMock()
            # Simple test for translate_path logic
            path = "/index.html?test=1"
            res = handler_class.translate_path(handler, path)
            assert "index.html" in res
            assert "www" in res

    def test_get_web_settings_defaults(self):
        # Test when file doesn't exist
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch.object(WebServer, "save_web_settings") as mock_save,
        ):
            # Ensure Lending.Config is not interfering (mocked in setup already) or we can specificially test fallback
            settings = WebServer.get_web_settings()
            assert settings["refreshRate"] == 30  # Default
            mock_save.assert_called()  # Should save defaults

    def test_get_web_settings_file_exists(self):
        file_content = json.dumps({"refreshRate": 45})
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.open", new_callable=MagicMock) as mock_file,
        ):
            # Setup mock file read
            mock_file.return_value.__enter__.return_value.read.return_value = file_content
            # mock json.load to read from the mock file handle
            with patch("json.load", return_value={"refreshRate": 45}):
                settings = WebServer.get_web_settings()
                assert settings["refreshRate"] == 45

    def test_save_web_settings(self):
        # Test saving merges with existing
        existing_content = {"refreshRate": 30}
        new_settings = {"refreshRate": 60, "other": "val"}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("json.load", return_value=existing_content),
            patch("json.dump") as mock_dump,
            patch("pathlib.Path.open", new_callable=MagicMock),
        ):
            WebServer.save_web_settings(new_settings)

            # Verify json.dump called with merged dict
            args, _ = mock_dump.call_args
            saved_dict = args[0]
            assert saved_dict["refreshRate"] == 60
            assert saved_dict["other"] == "val"
