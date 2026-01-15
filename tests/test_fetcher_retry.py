import asyncio
import http.server
import socketserver
import threading

from ratelimmq.fetcher import fetch_one


class _FlakyHandler(http.server.BaseHTTPRequestHandler):
    counter = 0
    fail_for = 2

    def do_GET(self):
        type(self).counter += 1
        if type(self).counter <= type(self).fail_for:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"fail\n")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok\n")

    def log_message(self, format, *args):
        # silence default http server logging
        return


def _start_server():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _FlakyHandler)
    host, port = httpd.server_address
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, host, port


def test_fetch_one_retries_eventually_succeeds():
    _FlakyHandler.counter = 0
    httpd, host, port = _start_server()
    try:
        url = f"http://{host}:{port}/"
        res = asyncio.run(
            fetch_one(
                url,
                timeout_s=2.0,
                retries=3,
                backoff_base_s=0.01,
                backoff_max_s=0.02,
                jitter_s=0.0,
            )
        )
        assert res.ok is True
        assert res.status_code == 200
        assert res.bytes_read > 0
    finally:
        httpd.shutdown()
