import http.server
import json
import socket
import socketserver
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import Configuration


class WebServer:
    def __init__(self, config: Configuration.RootConfig, lending_engine: Any):
        self.config = config
        self.lending_engine = lending_engine
        self.server: socketserver.TCPServer | None = None
        self.web_server_ip = config.bot.web.host
        self.web_server_port = config.bot.web.port
        self.web_server_template = config.bot.web.template
        self.web_settings_file = "web_settings.json"
        self.DEFAULT_WEB_SETTINGS: dict[str, Any] = {
            "refreshRate": 30,
            "timespanNames": ["Year", "Month", "Week", "Day", "Hour"],
            "btcDisplayUnit": "BTC",
            "outputCurrencyDisplayMode": "all",
            "effRateMode": "lentperc",
            "frrdelta_min": -10,
            "frrdelta_max": 10,
        }

    def start(self) -> None:
        """
        Setup the web server and start the web server thread
        """
        print(
            f"Starting WebServer at {self.web_server_ip} on port {self.web_server_port} with template {self.web_server_template}"
        )

        thread = threading.Thread(target=self._run_server)
        thread.daemon = True
        thread.start()

    def _run_server(self) -> None:
        """
        Internal method to start the server loop
        """
        try:
            # We need to capture self in a variable that the inner class can access via closure
            # but in Python 3, it's better to just use the instance attributes.
            web_instance = self

            class QuietHandler(http.server.SimpleHTTPRequestHandler):
                real_server_path = Path(web_instance.web_server_template).resolve()
                logs_path = Path("logs").resolve()

                def log_message(self, _format_str: str, *_args: Any) -> None:
                    return

                def translate_path(self, path: str) -> str:
                    url_path = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
                    if url_path.startswith("logs/"):
                        return str(Path.cwd() / url_path)
                    root = Path.cwd() / web_instance.web_server_template
                    if not url_path:
                        url_path = "index.html"
                    return str(root / url_path)

                def end_headers(self) -> None:
                    path = self.path.split("?")[0]
                    if path.endswith((".json", ".js", ".css", ".html", ".htm")):
                        self.send_header("Cache-Control", "no-cache, must-revalidate")
                        self.send_header("Pragma", "no-cache")
                        self.send_header("Expires", "0")
                    super().end_headers()

                def send_head(self) -> Any:
                    local_path = self.translate_path(self.path)
                    resolved_path = Path(local_path).resolve()
                    in_www = str(resolved_path).startswith(str(self.real_server_path))
                    in_logs = str(resolved_path).startswith(str(self.logs_path))
                    if not (in_www or in_logs):
                        self.send_error(404, "These aren't the droids you're looking for")
                        return None
                    return super().send_head()

                def do_GET(self) -> None:
                    if self.path == "/pause_lending":
                        web_instance.lending_engine.lending_paused = True
                        web_instance.save_web_settings({"lending_paused": True})
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"Lending paused")
                    elif self.path == "/resume_lending":
                        web_instance.lending_engine.lending_paused = False
                        web_instance.save_web_settings({"lending_paused": False})
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"Lending resumed")
                    elif self.path == "/get_status":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()

                        strategies = {
                            cur: cfg.strategy
                            for cur, cfg in web_instance.lending_engine.coin_cfg.items()
                        }
                        status_data = {
                            "lending_paused": web_instance.lending_engine.lending_paused,
                            "lending_strategies": strategies,
                        }
                        self.wfile.write(json.dumps(status_data).encode("utf-8"))
                    elif self.path == "/get_settings":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            json.dumps(web_instance.get_web_settings()).encode("utf-8")
                        )
                    else:
                        super().do_GET()

                def do_POST(self) -> None:
                    if self.path == "/set_config":
                        content_length = int(self.headers["Content-Length"])
                        post_data = self.rfile.read(content_length)
                        config_data = json.loads(post_data.decode("utf-8"))

                        if "frrdelta_min" in config_data and "frrdelta_max" in config_data:
                            try:
                                web_instance.lending_engine.frrdelta_min = Decimal(
                                    str(config_data["frrdelta_min"])
                                )
                                web_instance.lending_engine.frrdelta_max = Decimal(
                                    str(config_data["frrdelta_max"])
                                )
                                if web_instance.lending_engine.log:
                                    web_instance.lending_engine.log.log(
                                        f"Settings updated by user: FRR Delta Min={web_instance.lending_engine.frrdelta_min}%, Max={web_instance.lending_engine.frrdelta_max}%"
                                    )
                                web_instance.save_web_settings(config_data)
                                response = {
                                    "success": True,
                                    "frrdelta_min": str(web_instance.lending_engine.frrdelta_min),
                                    "frrdelta_max": str(web_instance.lending_engine.frrdelta_max),
                                }
                            except (ValueError, TypeError, InvalidOperation) as e:
                                response = {"success": False, "error": str(e)}
                        else:
                            try:
                                web_instance.save_web_settings(config_data)
                                response = {"success": True}
                            except Exception as e:
                                response = {"success": False, "error": str(e)}

                        self.send_response(200 if response["success"] else 400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode("utf-8"))
                    else:
                        self.send_error(404, "File not found")

            socketserver.TCPServer.allow_reuse_address = True
            self.server = socketserver.ThreadingTCPServer(
                (self.web_server_ip, self.web_server_port), QuietHandler
            )

            # Host display logic
            if self.web_server_ip == "0.0.0.0":
                addresses = [
                    str(i[4][0])
                    for i in socket.getaddrinfo(
                        socket.gethostname().split(".")[0], self.web_server_port
                    )
                ]
                addresses = [i for i in addresses if ":" not in i]
                addresses.append("127.0.0.1")
                hosts = list(set(addresses))
            else:
                hosts = [self.web_server_ip]

            serving_msg = f"http://{hosts[0]}:{self.web_server_port}/lendingbot.html"
            for h in hosts[1:]:
                serving_msg += f", http://{h}:{self.web_server_port}/lendingbot.html"
            print(f"Started WebServer, lendingbot status available at {serving_msg}")
            self.server.serve_forever()
        except Exception as ex:
            print(f"Failed to start WebServer: {ex}")

    def stop(self) -> None:
        """
        Stop the web server
        """
        try:
            print("Stopping WebServer")
            if self.server:
                threading.Thread(target=self.server.shutdown).start()
        except Exception as ex:
            print(f"Failed to stop WebServer: {ex}")

    def get_web_settings(self) -> dict[str, Any]:
        """
        Retrieves the current web settings.
        """
        if not Path(self.web_settings_file).exists():
            settings = self.DEFAULT_WEB_SETTINGS.copy()
            # Initial seeding from lending_engine
            try:
                settings["frrdelta_min"] = float(self.lending_engine.frrdelta_min)
                settings["frrdelta_max"] = float(self.lending_engine.frrdelta_max)
            except (ValueError, AttributeError):
                pass
            self.save_web_settings(settings)
            return settings

        try:
            with Path(self.web_settings_file).open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else self.DEFAULT_WEB_SETTINGS.copy()
        except (json.JSONDecodeError, OSError):
            return self.DEFAULT_WEB_SETTINGS.copy()

    def save_web_settings(self, settings: dict[str, Any]) -> None:
        """
        Saves the given settings to the web_settings.json file.
        """
        try:
            current: dict[str, Any] = {}
            if Path(self.web_settings_file).exists():
                with Path(self.web_settings_file).open("r", encoding="utf-8") as f:
                    try:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            current = loaded
                    except json.JSONDecodeError:
                        pass
            current.update(settings)
            with Path(self.web_settings_file).open("w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)
        except OSError as e:
            print(f"Error saving web settings: {e}")


# Backward compatibility wrappers
_web_server: WebServer | None = None


def get_web_settings() -> dict[str, Any]:
    if _web_server:
        return _web_server.get_web_settings()
    # Fallback for early calls
    return {
        "refreshRate": 30,
        "timespanNames": ["Year", "Month", "Week", "Day", "Hour"],
        "btcDisplayUnit": "BTC",
        "outputCurrencyDisplayMode": "all",
        "effRateMode": "lentperc",
        "frrdelta_min": -10,
        "frrdelta_max": 10,
    }
