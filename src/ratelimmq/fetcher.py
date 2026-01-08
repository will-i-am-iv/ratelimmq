from __future__ import annotations

import asyncio
import ssl
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

try:
    # Your repo already has a TokenBucket class used for rate limiting.
    from ratelimmq.limiter import TokenBucket  # type: ignore
except Exception:  # pragma: no cover
    TokenBucket = None  # type: ignore


@dataclass(frozen=True)
class FetchResult:
    url: str
    ok: bool
    status_code: int
    elapsed_s: float
    bytes_read: int
    error: str = ""


def _parse_url(url: str) -> tuple[str, str, int, str, bool]:
    """
    Returns: (scheme, host, port, path_with_query, is_https)
    """
    u = urlsplit(url)
    if u.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme: {u.scheme!r}")
    host = u.hostname or ""
    if not host:
        raise ValueError("missing hostname")
    is_https = u.scheme == "https"
    port = u.port or (443 if is_https else 80)
    path = u.path or "/"
    if u.query:
        path = f"{path}?{u.query}"
    return u.scheme, host, port, path, is_https


async def fetch_one(
    url: str,
    *,
    timeout_s: float = 10.0,
    max_bytes: int = 512_000,
    user_agent: str = "ratelimmq-fetcher/0.1",
) -> FetchResult:
    t0 = time.perf_counter()
    status_code = 0
    bytes_read = 0

    try:
        _, host, port, path, is_https = _parse_url(url)
        ssl_ctx = ssl.create_default_context() if is_https else None

        async def _do() -> FetchResult:
            nonlocal status_code, bytes_read
            reader, writer = await asyncio.open_connection(host, port, ssl=ssl_ctx)

            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: {user_agent}\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            )
            writer.write(req.encode("utf-8"))
            await writer.drain()

            # Status line
            line = await reader.readline()
            if not line:
                raise RuntimeError("empty response")
            try:
                parts = line.decode("utf-8", errors="replace").strip().split()
                # HTTP/1.1 200 OK
                status_code = int(parts[1]) if len(parts) >= 2 else 0
            except Exception:
                status_code = 0

            # Headers
            while True:
                h = await reader.readline()
                if not h or h in (b"\r\n", b"\n"):
                    break

            # Body (bounded)
            while bytes_read < max_bytes:
                chunk = await reader.read(min(4096, max_bytes - bytes_read))
                if not chunk:
                    break
                bytes_read += len(chunk)

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

            elapsed = time.perf_counter() - t0
            return FetchResult(url=url, ok=True, status_code=status_code, elapsed_s=elapsed, bytes_read=bytes_read)

        return await asyncio.wait_for(_do(), timeout=timeout_s)

    except Exception as e:
        elapsed = time.perf_counter() - t0
        return FetchResult(url=url, ok=False, status_code=status_code, elapsed_s=elapsed, bytes_read=bytes_read, error=str(e))


class HostLimiter:
    """
    Per-host token bucket limiter. If TokenBucket isn't available, limiter is disabled.
    """
    def __init__(self, *, capacity: float = 5.0, refill_rate: float = 5.0) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._buckets: dict[str, object] = {}

    def _bucket(self, host: str):
        if TokenBucket is None:
            return None
        b = self._buckets.get(host)
        if b is None:
            b = TokenBucket(capacity=self.capacity, refill_rate=self.refill_rate)  # type: ignore
            self._buckets[host] = b
        return b

    def allow(self, host: str) -> bool:
        b = self._bucket(host)
        if b is None:
            return True
        return bool(b.allow())  # type: ignore


async def run_asyncio_fetch(
    urls: list[str],
    *,
    concurrency: int = 50,
    queue_max: int = 500,
    per_host_capacity: float = 5.0,
    per_host_refill_rate: float = 5.0,
    timeout_s: float = 10.0,
) -> list[FetchResult]:
    """
    Async worker pool:
      - bounded queue => backpressure
      - semaphore => global concurrency cap
      - HostLimiter => per-host rate limit
    """
    q: asyncio.Queue[Optional[str]] = asyncio.Queue(maxsize=queue_max)
    sem = asyncio.Semaphore(concurrency)
    limiter = HostLimiter(capacity=per_host_capacity, refill_rate=per_host_refill_rate)

    results: list[FetchResult] = []

    async def producer() -> None:
        for u in urls:
            await q.put(u)
        for _ in range(concurrency):
            await q.put(None)

    async def worker() -> None:
        while True:
            u = await q.get()
            if u is None:
                return

            # Per-host rate limiting
            try:
                _, host, _, _, _ = _parse_url(u)
            except Exception:
                host = ""

            # Wait until allowed (simple sleep loop; good enough for the first slice)
            while host and not limiter.allow(host):
                await asyncio.sleep(0.01)

            async with sem:
                res = await fetch_one(u, timeout_s=timeout_s)
                results.append(res)

    prod_task = asyncio.create_task(producer())
    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]

    await prod_task
    await asyncio.gather(*workers)
    return results
