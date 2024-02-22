from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote_plus, parse_qs
from threading import Thread, Event
from mimetypes import guess_type
from datetime import datetime
from pathlib import Path
import logging
import socket
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

SERVER_HOST = ('localhost', 3000)
SOCKET_HOST = ('localhost', 5000)
shutdown_event = Event()

class HTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urlparse(self.path)
        if pr_url.path == '/':
            self.send_html('index.html')
        elif pr_url.path == '/message':
            self.send_html('message.html')
        else:
            if Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html('error.html', 404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))

        logger.info("Data received!")
        self.send_data_to_sock(data)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_data_to_sock(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, SOCKET_HOST)

    def send_html(self, file_name: str, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(file_name, 'rb') as fd:
            self.wfile.write(fd.read())        

    def send_static(self):
        self.send_response(200)
        mt = guess_type(self.path)
        if mt:
            self.send_header('Content-Type', mt[0])
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as fd:
            self.wfile.write(fd.read())


def run_server(
        server_cls: type[HTTPServer],
        handler_cls: type[HTTPHandler],
        server_addr: tuple[str, int]
    ) -> None:
    http = server_cls(server_addr, handler_cls)
    try:
        logger.info(f"Server started on {server_addr[0]}:{server_addr[1]}\n")
        while not shutdown_event.is_set():    
            http.handle_request()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info("\nServer stopped")
        http.server_close()


def run_socket_server(host: tuple[str, int]) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(host)
    logger.info(f"Socket server started on {host[0]}:{host[1]}")
    try:
        while not shutdown_event.is_set():
            data = sock.recv(1024).decode('utf-8')
            data_parse = unquote_plus(data)
            data_dict = parse_qs(data_parse)
            data_dict = {k: v[0]  for k, v in data_dict.items()}
            logger.info(f'Write data to json: {data_dict}')

            ctime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

            if Path('./storage/data.json').exists():
                with open('./storage/data.json', 'r+') as fd:
                    try:
                        existing_data = json.load(fd)
                    except json.JSONDecodeError:
                        existing_data = {}
            else:
                existing_data = {}
            
            existing_data[ctime] = data_dict

            with open('./storage/data.json', 'w') as fd:
                json.dump(existing_data, fd, indent=4)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info("\nSocket server stopped")
        sock.close()


if __name__ == '__main__':
    http_server = Thread(
        target=run_server, args=(HTTPServer, HTTPHandler, SERVER_HOST)
    )
    socket_server = Thread(
        target=run_socket_server, args=(SOCKET_HOST,)
    )

    http_server.start()
    socket_server.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        shutdown_event.set()

    http_server.join()
    socket_server.join()
