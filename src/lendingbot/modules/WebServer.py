import http.server
import json
import socket
import socketserver
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import Lending


server: socketserver.TCPServer | None = None
web_server_ip: str = "0.0.0.0"
web_server_port: str = "8000"
web_server_template: str = "www"


def initialize_web_server(config: Any) -> None:
    """
    Setup the web server, retrieving the configuration parameters
    and starting the web server thread
    """
    global web_server_ip, web_server_port, web_server_template

    # Check for custom web server address
    composite_web_server_address = config.get("BOT", "customWebServerAddress", "0.0.0.0").split(":")

    # associate web server ip address
    web_server_ip = composite_web_server_address[0]

    # check for IP:PORT legacy format
    if len(composite_web_server_address) > 1:
        # associate web server port
        web_server_port = composite_web_server_address[1]
    else:
        # Check for custom web server port
        web_server_port = config.get("BOT", "customWebServerPort", "8000")

    # Check for custom web server template
    web_server_template = config.get("BOT", "customWebServerTemplate", "www")

    print(
        f"Starting WebServer at {web_server_ip} on port {web_server_port} with template {web_server_template}"
    )

    thread = threading.Thread(target=start_web_server)
    thread.daemon = True
    thread.start()


def start_web_server() -> None:
    """
    Start the web server
    """
    try:
        port = int(web_server_port)
        host = web_server_ip

        # Do not attempt to fix code warnings in the below class, it is perfect.
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            real_server_path = Path(web_server_template).resolve()

            # quiet server logs
            def log_message(self, _format_str: str, *_args: Any) -> None:
                return

            def translate_path(self, path: str) -> str:
                # In Python 3, translate_path is a bit different.
                # We need to prepend the web_server_template to the path.

                # Simple implementation:
                root = Path.cwd() / web_server_template
                # Strip query parameters and fragments
                url_path = path.split("?", 1)[0]
                url_path = url_path.split("#", 1)[0]
                url_path = url_path.lstrip("/")
                if not url_path:
                    url_path = "index.html"

                final_path = root / url_path
                return str(final_path)

            def end_headers(self) -> None:
                # Prevent caching for JSON files (dynamic data)
                if self.path.split("?")[0].endswith(".json"):
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                super().end_headers()

            def send_head(self) -> Any:
                local_path = self.translate_path(self.path)
                # Security check to prevent directory traversal
                resolved_path = Path(local_path).resolve()
                if resolved_path.parent != self.real_server_path and not str(
                    resolved_path
                ).startswith(str(self.real_server_path)):
                    self.send_error(404, "These aren't the droids you're looking for")
                    return None
                return super().send_head()

            def do_GET(self) -> None:
                if self.path == "/pause_lending":
                    Lending.lending_paused = True
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Lending paused")
                elif self.path == "/resume_lending":
                    Lending.lending_paused = False
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Lending resumed")
                elif self.path == "/get_status":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps({"lending_paused": Lending.lending_paused}).encode("utf-8")
                    )
                else:
                    super().do_GET()

            def do_POST(self) -> None:
                if self.path == "/set_config":
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length)
                    config_data = json.loads(post_data.decode("utf-8"))

                    # Update configuration values
                    if "frrdelta_min" in config_data and "frrdelta_max" in config_data:
                        try:
                            Lending.frrdelta_min = Decimal(str(config_data["frrdelta_min"]))
                            Lending.frrdelta_max = Decimal(str(config_data["frrdelta_max"]))
                            response = {
                                "success": True,
                                "frrdelta_min": str(Lending.frrdelta_min),
                                "frrdelta_max": str(Lending.frrdelta_max),
                            }
                        except (ValueError, TypeError, InvalidOperation) as e:
                            response = {"success": False, "error": str(e)}
                    else:
                        response = {"success": False, "error": "Invalid configuration key"}

                    self.send_response(200 if response["success"] else 400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                else:
                    self.send_error(404, "File not found")

        global server
        socketserver.TCPServer.allow_reuse_address = True
        server = socketserver.TCPServer((host, port), QuietHandler)
        if host == "0.0.0.0":
            # Get all addresses that we could listen on the port specified
            addresses = [
                str(i[4][0]) for i in socket.getaddrinfo(socket.gethostname().split(".")[0], port)
            ]
            addresses = [i for i in addresses if ":" not in i]  # Filter out all IPv6 addresses
            addresses.append("127.0.0.1")  # getaddrinfo doesn't always get localhost
            hosts = list(set(addresses))  # Make list unique
        else:
            hosts = [host]

        serving_msg = f"http://{hosts[0]}:{port}/lendingbot.html"
        for h in hosts[1:]:
            serving_msg += f", http://{h}:{port}/lendingbot.html"
        print(f"Started WebServer, lendingbot status available at {serving_msg}")
        server.serve_forever()
    except Exception as ex:
        msg = str(ex)
        print(f"Failed to start WebServer: {msg}")


def stop_web_server() -> None:
    """
    Stop the web server
    """
    try:
        print("Stopping WebServer")
        if server:
            threading.Thread(target=server.shutdown).start()
    except Exception as ex:
        msg = str(ex)
        print(f"Failed to stop WebServer: {msg}")
