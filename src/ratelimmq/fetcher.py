from __future__ import annotations

import asyncio
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


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

    # Backwards-compat aliases (older code/tests might use these)
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read


def _fetch_blocking(url: str, timeout_s: float) -> tuple[bool, Optional[int], int, Optional[str]]:
    """
    Blocking HTTP fetch using urllib. Returns:
      (ok, status_code, bytes_read, error)
    """
    req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", None)
            if status is None:
                status = getattr(resp, "code", None)
            status_code = int(status) if status is not None else None
            body = resp.read()
            ok = status_code is not None and 200 <= status_code < 400
            return ok, status_code, len(body), None

    except urllib.error.HTTPError as e:
        # HTTPError is still a response; read body if possible
        try:
            body = e.read()
            nbytes = len(body)
        except Exception:
            nbytes = 0
        code = getattr(e, "code", None)
        status_code = int(code) if code is not None else None
        return False, status_code, nbytes, f"HTTPError {status_code}"

    except Exception as e:
        return False, None, 0, f"{type(e).__name__}: {e}"


def _is_retryable(status_code: Optional[int], err: Optional[str]) -> bool:
    # If we didn't even get a status code, it's almost always a network-type failure → retry.
    if status_code is None:
        return True
    # Retry common "try again" situations.
    if status_code in (429, 500, 502, 503, 504):
        return True
    return False


def _sleep_seconds(attempt_index: int, backoff_base_s: float, backoff_max_s: float, jitter_s: float) -> float:
    """
    attempt_index: 0 for first retry delay, 1 for second retry delay, etc.
    delay = min(max, base * 2^attempt) + uniform(0, jitter)
    """
    base = max(0.0, float(backoff_base_s))
    cap = max(0.0, float(backoff_max_s))
    delay = base * (2.0**attempt_index)
    if cap > 0:
        delay = min(delay, cap)
    if jitter_s > 0:
        delay += random.uniform(0.0, float(jitter_s))
    return max(0.0, delay)


async def fetch_one(
    url: str,
    *,
    timeout_s: float = 10.0,
    retries: int = 0,
    backoff_base_s: float = 0.25,
    backoff_max_s: float = 5.0,
    jitter_s: float = 0.1,
) -> FetchResult:
    """
    Fetch a single URL (async wrapper around a blocking fetch), with optional retries.

    - Retries happen on network errors (no status_code) and on retryable status codes (429/5xx).
    - Backoff is exponential with small jitter: base*2^n + jitter.
    - elapsed_ms reports total time since the first attempt started (includes waits).
    """
    t0 = time.perf_counter()
    retries = max(0, int(retries))

    last: Optional[FetchResult] = None

    # attempts = 1 + retries
    for attempt in range(retries + 1):
        if attempt > 0:
            # sleep before retry
            delay = _sleep_seconds(attempt_index=attempt - 1, backoff_base_s=backoff_base_s, backoff_max_s=backoff_max_s, jitter_s=jitter_s)
            if delay > 0:
                await asyncio.sleep(delay)

        ok, status_code, nbytes, err = await asyncio.to_thread(_fetch_blocking, url, timeout_s)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        last = FetchResult(
            url=url,
            ok=ok,
            status_code=status_code,
            bytes_read=nbytes,
            elapsed_ms=elapsed_ms,
            error=err,
        )

        if ok:
            return last

        # If not ok and not retryable, stop immediately.
        if not _is_retryable(status_code, err):
            return last

    # If we get here, all attempts failed.
    assert last is not None
    return last
