import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ratelimmq.fetcher import fetch_one


class _FlakyHandler(BaseHTTPRequestHandler):
    # class-level counters so the test can check how many requests happened
    count = 0
    fail_first = 2

    def do_GET(self):
        type(self).count += 1
        if type(self).count <= type(self).fail_first:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"fail")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def log_message(self, fmt, *args):
        # silence server logs in tests
        return


class _NotFoundHandler(BaseHTTPRequestHandler):
    count = 0

    def do_GET(self):
        type(self).count += 1
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"nope")

    def log_message(self, fmt, *args):
        return


def _start_server(handler_cls):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    host, port = httpd.server_address
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, host, port


def test_fetch_retries_then_succeeds():
    _FlakyHandler.count = 0
    _FlakyHandler.fail_first = 2
    httpd, host, port = _start_server(_FlakyHandler)
    try:
        url = f"http://{host}:{port}/"
        res = asyncio.run(
            fetch_one(
                url,
                timeout_s=3.0,
                retries=3,
                backoff_base_s=0.01,
                backoff_max_s=0.05,
                jitter_s=0.0,
            )
        )
        assert res.ok is True
        assert res.status_code == 200
        # 2 failures + 1 success
        assert _FlakyHandler.count == 3
    finally:
        httpd.shutdown()


def test_fetch_does_not_retry_on_404():
    _NotFoundHandler.count = 0
    httpd, host, port = _start_server(_NotFoundHandler)
    try:
        url = f"http://{host}:{port}/"
        res = asyncio.run(
            fetch_one(
                url,
                timeout_s=3.0,
                retries=5,
                backoff_base_s=0.01,
                backoff_max_s=0.05,
                jitter_s=0.0,
            )
        )
        assert res.ok is False
        assert res.status_code == 404
        # should only hit once
        assert _NotFoundHandler.count == 1
    finally:
        httpd.shutdown()
