import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ratelimmq.fetcher import fetch_one


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # keep tests quiet
        return


def test_fetch_one_local_http():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = httpd.server_address

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        url = f"http://{host}:{port}/"
        res = asyncio.run(fetch_one(url, timeout_s=3.0))
        assert res.ok is True
        assert res.status_code == 200
        assert res.bytes_read > 0
    finally:
        httpd.shutdown()
        httpd.server_close()
