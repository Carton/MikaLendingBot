import json
import os
import threading
from decimal import Decimal, InvalidOperation

import modules.Lending as Lending


server = None
web_server_ip = "0.0.0.0"
web_server_port = "8000"
web_server_template = "www"


def initialize_web_server(config):
    '''
    Setup the web server, retrieving the configuration parameters
    and starting the web server thread
    '''
    global web_server_ip, web_server_port, web_server_template

    # Check for custom web server address
    compositeWebServerAddress = config.get('BOT', 'customWebServerAddress', '0.0.0.0').split(":")

    # associate web server ip address
    web_server_ip = compositeWebServerAddress[0]

    # check for IP:PORT legacy format
    if (len(compositeWebServerAddress) > 1):
        # associate web server port
        web_server_port = compositeWebServerAddress[1]
    else:
        # Check for custom web server port
        web_server_port = config.get('BOT', 'customWebServerPort', '8000')

    # Check for custom web server template
    web_server_template = config.get('BOT', 'customWebServerTemplate', 'www')

    print(f'Starting WebServer at {web_server_ip} on port {web_server_port} with template {web_server_template}'
          )

    thread = threading.Thread(target=start_web_server)
    thread.deamon = True
    thread.start()


def start_web_server():
    '''
    Start the web server
    '''
    import socket

    import SimpleHTTPServer
    import SocketServer

    try:
        port = int(web_server_port)
        host = web_server_ip

        # Do not attempt to fix code warnings in the below class, it is perfect.
        class QuietHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
            real_server_path = os.path.abspath(web_server_template)

            # quiet server logs
            def log_message(self, format, *args):
                return

            # serve from web_server_template folder under current working dir
            def translate_path(self, path):
                return SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, '/' + web_server_template + path)

            def send_head(self):
                local_path = self.translate_path(self.path)
                if os.path.commonprefix((os.path.abspath(local_path), self.real_server_path)) != self.real_server_path:
                    self.send_error(404, "These aren't the droids you're looking for")
                    return None
                return SimpleHTTPServer.SimpleHTTPRequestHandler.send_head(self)

            def do_GET(self):
                if self.path == '/pause_lending':
                    Lending.lending_paused = True
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Lending paused')
                elif self.path == '/resume_lending':
                    Lending.lending_paused = False
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'Lending resumed')
                elif self.path == '/get_status':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"lending_paused": Lending.lending_paused}))
                else:
                    return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

            def do_POST(self):
                if self.path == '/set_config':
                    content_length = int(self.headers['Content-Length'])  # 获取数据长度
                    post_data = self.rfile.read(content_length)  # 读取POST数据
                    config_data = json.loads(post_data)

                    # 更新配置值
                    if 'frrdelta_min' in config_data and 'frrdelta_max' in config_data:
                        try:
                            Lending.frrdelta_min = Decimal(config_data['frrdelta_min'])
                            Lending.frrdelta_max = Decimal(config_data['frrdelta_max'])
                            response = {"success": True, "frrdelta_min": str(Lending.frrdelta_min), "frrdelta_max": str(Lending.frrdelta_max)}
                        except (ValueError, TypeError, InvalidOperation) as e:
                            response = {"success": False, "error": str(e)}
                    else:
                        response = {"success": False, "error": "Invalid configuration key"}

                    # 发送响应
                    self.send_response(200 if response["success"] else 400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response))
                else:
                    self.send_error(404, "File not found")

        global server
        SocketServer.TCPServer.allow_reuse_address = True
        server = SocketServer.TCPServer((host, port), QuietHandler)
        if host == "0.0.0.0":
            # Get all addresses that we could listen on the port specified
            addresses = [i[4][0] for i in socket.getaddrinfo(socket.gethostname().split('.')[0], port)]
            addresses = [i for i in addresses if ':' not in i]  # Filter out all IPv6 addresses
            addresses.append('127.0.0.1')  # getaddrinfo doesn't always get localhost
            hosts = list(set(addresses))  # Make list unique
        else:
            hosts = [host]
        serving_msg = f"http://{hosts[0]}:{port}/lendingbot.html"
        for host in hosts[1:]:
            serving_msg += f", http://{host}:{port}/lendingbot.html"
        print(f'Started WebServer, lendingbot status available at {serving_msg}')
        server.serve_forever()
    except Exception as ex:
        ex.message = ex.message if ex.message else str(ex)
        print(f'Failed to start WebServer: {ex.message}')


def stop_web_server():
    '''
    Stop the web server
    '''
    try:
        print("Stopping WebServer")
        threading.Thread(target=server.shutdown).start()
    except Exception as ex:
        ex.message = ex.message if ex.message else str(ex)
        print(f"Failed to stop WebServer: {ex.message}")
