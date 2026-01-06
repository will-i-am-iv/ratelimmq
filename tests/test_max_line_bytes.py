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


def _wait_listening(host: str, port: int, timeout_s: float = 3.0) -> None:
    deadline = time.time() + timeout_s
    last_err = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError as e:
            last_err = e
            time.sleep(0.05)
    raise RuntimeError(
        f"Server did not start listening on port {port} within {timeout_s:.1f}s (last_err={last_err})"
    )


def _send_and_recv(sock: socket.socket, line: str, timeout_s: float = 2.0) -> str:
    sock.settimeout(timeout_s)
    sock.sendall(line.encode("utf-8"))

    chunks: list[bytes] = []
    while True:
        b = sock.recv(4096)
        if not b:
            break
        chunks.append(b)
        if b"\n" in b:
            break

    return b"".join(chunks).decode("utf-8", errors="replace")


def test_oversized_line_returns_err_and_server_survives():
    host = "127.0.0.1"
    port = _free_port()

    env = os.environ.copy()
    env["RATELIMMQ_HOST"] = host
    env["RATELIMMQ_PORT"] = str(port)
    env["RATELIMMQ_MAX_LINE_BYTES"] = "16"  # intentionally small

    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "ratelimmq"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_listening(host, port, timeout_s=3.0)

        # Oversized line should return ERR
        with socket.create_connection((host, port), timeout=2.0) as sock:
            resp = _send_and_recv(sock, "X" * 200 + "\n")
            assert resp.startswith("ERR"), f"Expected ERR response, got: {resp!r}"

        # Server should still respond normally afterward
        with socket.create_connection((host, port), timeout=2.0) as sock:
            resp2 = _send_and_recv(sock, "PING\n")
            assert resp2.strip() == "PONG", f"Expected PONG, got: {resp2!r}"

        # SHUTDOWN should still work
        with socket.create_connection((host, port), timeout=2.0) as sock:
            resp3 = _send_and_recv(sock, "SHUTDOWN\n")
            assert resp3.strip() == "BYE", f"Expected BYE, got: {resp3!r}"

        proc.wait(timeout=3.0)

    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
