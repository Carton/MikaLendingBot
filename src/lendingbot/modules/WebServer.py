import http.server
import json
import socket
import socketserver
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import Configuration, Lending


server: socketserver.TCPServer | None = None
web_server_ip: str = "0.0.0.0"
web_server_port: str = "8000"
web_server_template: str = "www"


def initialize_web_server(config: Configuration.RootConfig) -> None:
    """
    Setup the web server, retrieving the configuration parameters
    and starting the web server thread
    """
    global web_server_ip, web_server_port, web_server_template

    web_server_ip = config.bot.web.host
    web_server_port = str(config.bot.web.port)
    web_server_template = config.bot.web.template

    print(
        f"Starting WebServer at {web_server_ip} on port {web_server_port} with template {web_server_template}"
    )

    thread = threading.Thread(target=start_web_server)
    thread.daemon = True
    thread.start()


web_settings_file: str = "web_settings.json"
DEFAULT_WEB_SETTINGS: dict[str, Any] = {
    "refreshRate": 30,
    "timespanNames": ["Year", "Month", "Week", "Day", "Hour"],
    "btcDisplayUnit": "BTC",
    "outputCurrencyDisplayMode": "all",
    "effRateMode": "lentperc",
    "frrdelta_min": -10,
    "frrdelta_max": 10,
}


def get_web_settings() -> dict[str, Any]:
    """
    Retrieves the current web settings.
    If the settings file doesn't exist, it creates one using defaults,
    potentially merged with legacy default.cfg values for FRR.
    """
    if not Path(web_settings_file).exists():
        # Start with defaults
        settings = DEFAULT_WEB_SETTINGS.copy()

        # Merge legacy config if available (Factory Defaults)
        # We access Lending.frrdelta_min/max which are loaded from default.cfg in Lending.init()
        # BUT, to avoid circular dependency issues if get_web_settings is called early,
        # we'll trust that if this file doesn't exist, it's a fresh start or first migration.
        # If Lending has already initialized these from default.cfg, we can peek at them.

        # Actually, a cleaner way for the VERY FIRST run is:
        # If Lending is initialized, use its current values (which came from default.cfg)
        # to seed the web_settings.
        # We check a knownInitialized variable or just try to access the values.
        try:
            settings["frrdelta_min"] = float(Lending.frrdelta_min)
            settings["frrdelta_max"] = float(Lending.frrdelta_max)
        except (ValueError, AttributeError):
            pass

        save_web_settings(settings)
        return settings

    try:
        with Path(web_settings_file).open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return DEFAULT_WEB_SETTINGS.copy()
    except (json.JSONDecodeError, OSError):
        return DEFAULT_WEB_SETTINGS.copy()


def save_web_settings(settings: dict[str, Any]) -> None:
    """
    Saves the given settings to the web_settings.json file.
    """
    try:
        current: dict[str, Any] = {}
        if Path(web_settings_file).exists():
            with Path(web_settings_file).open("r", encoding="utf-8") as f:
                try:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        current = loaded
                except json.JSONDecodeError:
                    pass

        current.update(settings)
        with Path(web_settings_file).open("w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
    except OSError as e:
        print(f"Error saving web settings: {e}")


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
            logs_path = Path("logs").resolve()

            # quiet server logs
            def log_message(self, _format_str: str, *_args: Any) -> None:
                return

            def translate_path(self, path: str) -> str:
                # Strip query parameters and fragments first
                url_path = path.split("?", 1)[0]
                url_path = url_path.split("#", 1)[0]
                url_path = url_path.lstrip("/")

                # Handle /logs/ virtual path - map to project root logs/ directory
                if url_path.startswith("logs/"):
                    return str(Path.cwd() / url_path)

                # Default: serve from web_server_template (www/)
                root = Path.cwd() / web_server_template
                if not url_path:
                    url_path = "index.html"

                final_path = root / url_path
                return str(final_path)

            def end_headers(self) -> None:
                # Prevent caching for JSON files (dynamic data) and static assets to ensure updates are seen immediately
                path = self.path.split("?")[0]
                if path.endswith((".json", ".js", ".css", ".html", ".htm")):
                    # "no-cache" means: cache is allowed, but MUST revalidate with server (check ETag/Last-Modified) before use.
                    # This allows 304 Not Modified responses (fast) while ensuring updates are seen.
                    self.send_header("Cache-Control", "no-cache, must-revalidate")
                    self.send_header("Pragma", "no-cache")
                    # Expires 0 is still good for broad compatibility to force revalidation check
                    self.send_header("Expires", "0")
                super().end_headers()

            def send_head(self) -> Any:
                local_path = self.translate_path(self.path)
                # Security check to prevent directory traversal
                resolved_path = Path(local_path).resolve()
                # Allow access to both www/ and logs/ directories
                in_www = str(resolved_path).startswith(str(self.real_server_path))
                in_logs = str(resolved_path).startswith(str(self.logs_path))
                if not (in_www or in_logs):
                    self.send_error(404, "These aren't the droids you're looking for")
                    return None
                return super().send_head()

            def do_GET(self) -> None:
                if self.path == "/pause_lending":
                    Lending.lending_paused = True
                    save_web_settings({"lending_paused": True})
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Lending paused")
                elif self.path == "/resume_lending":
                    Lending.lending_paused = False
                    save_web_settings({"lending_paused": False})
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Lending resumed")
                elif self.path == "/get_status":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()

                    strategies = {
                        cur: cfg.strategy for cur, cfg in Lending.coin_cfg.items()
                    }

                    status_data = {
                        "lending_paused": Lending.lending_paused,
                        "lending_strategies": strategies,
                    }
                    self.wfile.write(json.dumps(status_data).encode("utf-8"))
                elif self.path == "/get_settings":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(get_web_settings()).encode("utf-8"))
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
                            if Lending.log:
                                Lending.log.log(
                                    f"Settings updated by user: FRR Delta Min={Lending.frrdelta_min}%, Max={Lending.frrdelta_max}%"
                                )

                            # Save all received settings specific to web persistence
                            save_web_settings(config_data)

                            response = {
                                "success": True,
                                "frrdelta_min": str(Lending.frrdelta_min),
                                "frrdelta_max": str(Lending.frrdelta_max),
                            }
                        except (ValueError, TypeError, InvalidOperation) as e:
                            response = {"success": False, "error": str(e)}
                    else:
                        # Even if FRR params aren't present (partial update?), save what we have
                        # But typically the UI sends everything or specific subsets.
                        # For now, let's allow partial updates for other web settings
                        try:
                            save_web_settings(config_data)
                            response = {"success": True}
                        except Exception as e:
                            response = {"success": False, "error": str(e)}

                    self.send_response(200 if response["success"] else 400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                else:
                    self.send_error(404, "File not found")

        global server
        socketserver.TCPServer.allow_reuse_address = True
        server = socketserver.ThreadingTCPServer((host, port), QuietHandler)
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
