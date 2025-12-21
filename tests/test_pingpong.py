import os
import socket
import subprocess
import sys
import time


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_listen(port: int, timeout_s: float = 2.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Server did not start listening on port {port} within {timeout_s}s")


def test_ping_pong_and_shutdown():
    port = _free_port()

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RATELIMMQ_HOST"] = "127.0.0.1"
    env["RATELIMMQ_PORT"] = str(port)

    proc = subprocess.Popen(
        [sys.executable, "src/ratelimmq/server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_listen(port)

        # PING -> PONG
        with socket.create_connection(("127.0.0.1", port), timeout=1.0) as s:
            s.sendall(b"PING\n")
            assert s.recv(1024) == b"PONG\n"

        # SHUTDOWN -> BYE, server exits
        with socket.create_connection(("127.0.0.1", port), timeout=1.0) as s:
            s.sendall(b"SHUTDOWN\n")
            assert s.recv(1024) == b"BYE\n"

        rc = proc.wait(timeout=3.0)
        assert rc == 0

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
