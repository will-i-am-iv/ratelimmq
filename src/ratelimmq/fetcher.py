from __future__ import annotations

import asyncio
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FetchResult:
    url: str
    ok: bool
    status_code: Optional[int]
    bytes: int
    elapsed_ms: float
    error: Optional[str]

    # Backwards-compat alias (if any older code used `status`)
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read

def _fetch_blocking(url: str, timeout_s: float) -> tuple[bool, Optional[int], int, Optional[str]]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status_code = getattr(resp, "status", None)
            body = resp.read()
            return True, status_code, len(body), None
    except Exception as e:
        return False, None, 0, f"{type(e).__name__}: {e}"


async def fetch_one(url: str, *, timeout_s: float = 10.0) -> FetchResult:
    t0 = time.perf_counter()
    ok, status_code, nbytes, err = await asyncio.to_thread(_fetch_blocking, url, timeout_s)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return FetchResult(
        url=url,
        ok=ok,
        status_code=status_code,
        bytes=nbytes,
        elapsed_ms=elapsed_ms,
        error=err,
    )
