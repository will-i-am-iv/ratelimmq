from __future__ import annotations

import asyncio
import logging
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


log = logging.getLogger("ratelimmq.fetcher")


@dataclass(frozen=True)
class FetchResult:
    # REQUIRED (no defaults) must come first
    url: str
    ok: bool
    status_code: Optional[int]
    bytes_read: int
    elapsed_ms: float

    # OPTIONAL (defaults) must come last
    error: Optional[str] = None

    # Backwards-compat aliases (older code/tests may use these)
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read


def _fetch_blocking(url: str, timeout_s: float) -> tuple[bool, Optional[int], int, Optional[str]]:
    """
    Blocking HTTP GET using urllib (runs in a thread via asyncio.to_thread).
    Returns: (ok, status_code, bytes_read, error_str)
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status_code = getattr(resp, "status", None)
            body = resp.read()
            return True, status_code, len(body), None
    except Exception as e:
        return False, None, 0, f"{type(e).__name__}: {e}"


async def fetch_one(url: str, *, timeout_s: float = 10.0) -> FetchResult:
    """
    Async wrapper around a blocking urllib fetch.
    """
    t0 = time.perf_counter()

    # A small structured "start" log
    log.info("fetch_start", extra={"url": url, "timeout_s": timeout_s})

    ok, status_code, nbytes, err = await asyncio.to_thread(_fetch_blocking, url, timeout_s)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # A small structured "done" log
    log.info(
        "fetch_done",
        extra={
            "url": url,
            "ok": ok,
            "status_code": status_code,
            "bytes_read": nbytes,
            "elapsed_ms": round(elapsed_ms, 3),
            "error": err,
        },
    )

    return FetchResult(
        url=url,
        ok=ok,
        status_code=status_code,
        bytes_read=nbytes,
        elapsed_ms=elapsed_ms,
        error=err,
    )
