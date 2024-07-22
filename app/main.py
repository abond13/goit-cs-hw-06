import mimetypes
import pathlib
import socket
import urllib.parse
from datetime import datetime
from multiprocessing import Process
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from http.server import HTTPServer, BaseHTTPRequestHandler

HTTPD_PORT = 3000
SOCKETD_PORT = 5000

class HttpHandler(BaseHTTPRequestHandler):
    PATH_PREFIX = '/var/lib/www'

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file(f'{self.PATH_PREFIX}/index.html')
        elif pr_url.path == '/message':
            self.send_html_file(f'{self.PATH_PREFIX}/message.html')
        else:
            if pathlib.Path().joinpath(f'{self.PATH_PREFIX}/{pr_url.path[1:]}').exists():
                self.send_static()
            else:
                self.send_html_file(f'{self.PATH_PREFIX}/error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(f'{self.PATH_PREFIX}/{self.path}')
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'{self.PATH_PREFIX}/{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_to_socket(data)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_to_socket(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(message, ('', SOCKETD_PORT))

def run_httpd(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', HTTPD_PORT)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def run_socketd():
    with MongoClient(
                    "mongodb://root:example@mongo:27017/?retryWrites=true&w=majority",
                    server_api=ServerApi('1')
                    ) as client:
        db = client.messages
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('', SOCKETD_PORT))
            print('Socket is binded and listening')
            while True:
                data, addr = s.recvfrom(1024)
                data_parse = urllib.parse.unquote_plus(data.decode())
                print(f"Message \"{data_parse}\" from {addr}")
                data_dict = urllib.parse.parse_qs(data_parse)
                if ('username' in data_dict.keys()) and ('message' in data_dict.keys()):
                    data_dict["date"] = datetime.now().isoformat()
                    print(data_dict)
                    db.messages.insert_one(data_dict)

if __name__ == '__main__':
    Process(target=run_httpd).start()
    Process(target=run_socketd).start()