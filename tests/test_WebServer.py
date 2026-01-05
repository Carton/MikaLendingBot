"""
Tests for WebServer module using Dependency Injection.
"""

import json
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch, ANY
import threading
import http.server

import pytest
from lendingbot.modules.WebServer import WebServer
from lendingbot.modules.Configuration import RootConfig, WebServerConfig, BotConfig


@pytest.fixture
def mock_config():
    return RootConfig(
        bot=BotConfig(
            web=WebServerConfig(
                host="0.0.0.0",
                port=8000,
                template="www"
            )
        )
    )

@pytest.fixture
def mock_lending_engine():
    engine = MagicMock()
    engine.lending_paused = False
    engine.frrdelta_min = Decimal("0")
    engine.frrdelta_max = Decimal("0")
    engine.coin_cfg = {}
    return engine

@pytest.fixture
def web_server(mock_config, mock_lending_engine):
    return WebServer(mock_config, mock_lending_engine)

class TestWebServer:
    def test_init(self, web_server):
        assert web_server.web_server_ip == "0.0.0.0"
        assert web_server.web_server_port == 8000
        assert web_server.web_server_template == "www"

    def test_start_server(self, web_server):
        with patch("threading.Thread") as mock_thread:
            web_server.start()
            mock_thread.assert_called()
            args, kwargs = mock_thread.call_args
            assert kwargs['target'] == web_server._run_server

    def test_stop_server(self, web_server):
        web_server.server = MagicMock()
        with patch("threading.Thread") as mock_thread:
            web_server.stop()
            # It should start a thread to shutdown the server
            mock_thread.assert_called()
            args, kwargs = mock_thread.call_args
            assert kwargs['target'] == web_server.server.shutdown

    def test_handler_logic(self, web_server, mock_lending_engine):
        # We need to simulate the inner QuietHandler.
        # Since _run_server defines the class locally, we can't import it easily.
        # But we can inspect how _run_server uses it.
        # It creates a subclass of SimpleHTTPRequestHandler.
        
        # We can extract the handler logic by patching TCPServer
        handler_class_capture = []
        
        def capture_handler(addr, handler_cls):
            handler_class_capture.append(handler_cls)
            return MagicMock()

        with patch("socketserver.ThreadingTCPServer", side_effect=capture_handler):
            with patch("socket.getaddrinfo", return_value=[]):
                # We need to break serve_forever to not block
                mock_server = MagicMock()
                mock_server.serve_forever.return_value = None
                
                # Override _run_server to avoid actual threading but run enough to capture handler
                # Actually _run_server does a lot. 
                # Let's patch threading.Thread to run synchronously for a moment? No.
                # Let's just call _run_server directly but mock serve_forever to return immediately?
                # But serve_forever blocks.
                pass

        # Alternative: We can access the Handler class via inspecting the server object if we let it create one?
        # Or we can just trust the logic if we could instantiate the handler directly.
        # The Handler class is defined INSIDE _run_server, so it captures 'web_instance'.
        # We must invoke _run_server to define it.
        
        with patch("socketserver.ThreadingTCPServer") as MockServer:
            mock_server_instance = MockServer.return_value
            # We want serve_forever to NOT block, just return.
            mock_server_instance.serve_forever.return_value = None
            
            with patch("socket.getaddrinfo", return_value=[]):
                 web_server._run_server()
            
            # Now we can retrieve the handler class from the call args to ThreadingTCPServer
            # call((ip, port), HandlerClass)
            args, _ = MockServer.call_args
            HandlerClass = args[1]
            
            # Now we can instantiate this HandlerClass with a mock request
            # HandlerClass(request, client_address, server)
            
            mock_request = MagicMock()
            mock_request.makefile.return_value = MagicMock()
            
            # We don't want the BaseHTTPRequestHandler __init__ to run fully as it tries to read the socket
            # So we patch it or just Mock the methods we need.
            # But the logic is in do_GET / do_POST.
            
            # Let's instantiate it but suppress __init__
            # Or better, just use the class methods directly if they don't depend on self too much (they do).
            
            # We can mock the superclass __init__
            with patch("http.server.SimpleHTTPRequestHandler.__init__", return_value=None):
                 handler = HandlerClass(mock_request, ("0.0.0.0", 1234), mock_server_instance)
                 # Manually set attributes usually set by __init__
                 handler.path = "/"
                 handler.headers = {}
                 handler.rfile = MagicMock()
                 handler.wfile = MagicMock()
                 handler.command = "GET"
                 handler.request_version = "HTTP/1.0"
                 handler.close_connection = True
                 handler.raw_requestline = ""
                 handler.requestline = ""
                 
                 # === Test /pause_lending ===
                 with patch.object(web_server, "save_web_settings") as mock_save:
                     handler.path = "/pause_lending"
                     handler.do_GET()
                     assert mock_lending_engine.lending_paused is True
                     mock_save.assert_called_with({"lending_paused": True})

                 # === Test /resume_lending ===
                 with patch.object(web_server, "save_web_settings") as mock_save:
                     handler.path = "/resume_lending"
                     handler.do_GET()
                     assert mock_lending_engine.lending_paused is False
                     mock_save.assert_called_with({"lending_paused": False})

                 # === Test /get_status ===
                 handler.path = "/get_status"
                 handler.do_GET()
                 # Verify write called with json
                 args, _ = handler.wfile.write.call_args
                 response = json.loads(args[0].decode("utf-8"))
                 assert "lending_paused" in response

                 # === Test /set_config (POST) ===
                 handler.path = "/set_config"
                 payload = json.dumps({
                     "frrdelta_min": "0.0001",
                     "frrdelta_max": "0.0005"
                 }).encode("utf-8")
                 handler.headers = {"Content-Length": str(len(payload))}
                 handler.rfile.read.return_value = payload
                 
                 with patch.object(web_server, "save_web_settings") as mock_save:
                     handler.do_POST()
                     assert mock_lending_engine.frrdelta_min == Decimal("0.0001")
                     assert mock_lending_engine.frrdelta_max == Decimal("0.0005")
                     mock_save.assert_called()

    def test_settings_persistence(self, web_server, tmp_path):
        # Use a temporary file for settings
        settings_file = tmp_path / "web_settings.json"
        web_server.web_settings_file = str(settings_file)
        
        # Test defaults
        settings = web_server.get_web_settings()
        assert settings["refreshRate"] == 30
        assert settings_file.exists()
        
        # Test save
        web_server.save_web_settings({"refreshRate": 60})
        with settings_file.open() as f:
            data = json.load(f)
            assert data["refreshRate"] == 60
            
        # Test reload
        settings = web_server.get_web_settings()
        assert settings["refreshRate"] == 60