#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2016, Kovid Goyal <kovid at kovidgoyal.net>

import http.server
import os
import posixpath
import socketserver
import sys
import tempfile
import threading


def sign_file_(path: str) -> None:
    with open(path, 'a') as f:
        f.write('\n\rTODO: Implement me!')


def sign_file(fname: str, fdata: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=fname) as f:
        f.write(fdata)
        f.flush()
        sign_file_(f.name)
        # in case the file was deleted and recreated, re-open it
        with open(f.name, 'rb') as s:
            return s.read()


def sign_file_in_client(path: str) -> None:
    from urllib.request import Request, urlopen
    port = os.environ['SIGN_SERVER_PORT']
    with open(path, 'rb') as f:
        data = f.read()
    rq = Request(f'http://localhost:{port}/{os.path.basename(path)}', data=data)
    with urlopen(rq) as res:
        data = res.read()
        if res.status == 200:
            with open(path, 'wb') as f:
                f.write(data)
        else:
            print(f'Sign request failed with http code: {res.status}', file=sys.stderr)
            sys.stderr.write(data)
            sys.stderr.flush()
            raise SystemExit(1)


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)

    def do_POST(self) -> None:
        content_length = int(self.headers['Content-Length'])
        fname = posixpath.basename(self.path)
        post_data = self.rfile.read(content_length)
        try:
            response_data = sign_file(fname, post_data)
        except Exception as err:
            self.send_error(500, f'Signing of {fname} failed with error: {err}')
        else:
            self.send_response(200)
            self.send_header('Content-type', self.headers.get('Content-Type', 'application/octet-stream'))
            self.send_header('Content-Length', str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)


def create_server() -> socketserver.ThreadingTCPServer:
    # Use port 0 to let the OS select a random available port
    httpd = socketserver.ThreadingTCPServer(('localhost', 0), MyHttpRequestHandler)
    return httpd


def run_server() -> socketserver.ThreadingTCPServer:
    httpd = create_server()
    print(f'Sign server starting on http://{str(httpd.server_address[0])}:{httpd.server_address[1]}')
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return httpd


def develop() -> None:
    httpd = create_server()
    print(f'Server starting on http://{str(httpd.server_address[0])}:{httpd.server_address[1]}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == '__main__':
    develop()
