from __future__ import annotations

import asyncio
import logging
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("ratelimmq.fetcher")


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

    # Backwards-compat aliases (older code/tests might look for these)
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read


def _fetch_blocking(url: str, timeout_s: float) -> Tuple[bool, Optional[int], int, Optional[str]]:
    """
    Blocking URL fetch. Returns:
      (ok, status_code, bytes_read, error)
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status_code = getattr(resp, "status", None)
            body = resp.read()
            return True, status_code, len(body), None

    except urllib.error.HTTPError as e:
        # HTTPError is raised for non-2xx/3xx responses in urllib
        code = getattr(e, "code", None)
        reason = getattr(e, "reason", "")
        return False, code, 0, f"HTTPError {code}: {reason}"

    except Exception as e:
        return False, None, 0, f"{type(e).__name__}: {e}"


def _is_retryable(ok: bool, status_code: Optional[int]) -> bool:
    if ok:
        return False
    # Network failures, DNS failures, timeouts, etc.
    if status_code is None:
        return True
    # Common retryable HTTP statuses
    return status_code in {408, 429, 500, 502, 503, 504}


def _backoff_seconds(attempt_index: int, base: float, cap: float, jitter: float) -> float:
    """
    attempt_index: 0,1,2,...
    delay = min(cap, base * 2^attempt) + random(0..jitter)
    """
    delay = min(cap, base * (2 ** attempt_index))
    if jitter > 0:
        delay += random.uniform(0.0, jitter)
    return delay


async def fetch_one(
    url: str,
    *,
    timeout_s: float = 10.0,
    retries: int = 0,
    backoff_base_s: float = 0.2,
    backoff_max_s: float = 2.0,
    jitter_s: float = 0.05,
) -> FetchResult:
    """
    Fetch one URL.

    retries=0 means "try once, no retries".
    retries=3 means "up to 4 total attempts".
    """
    last: Optional[FetchResult] = None

    for attempt in range(retries + 1):
        logger.info(
            "fetch_start",
            extra={"url": url, "timeout_s": timeout_s, "attempt": attempt + 1, "retries": retries},
        )

        t0 = time.perf_counter()
        ok, status_code, nbytes, err = await asyncio.to_thread(_fetch_blocking, url, timeout_s)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        res = FetchResult(
            url=url,
            ok=ok,
            status_code=status_code,
            bytes_read=nbytes,
            elapsed_ms=elapsed_ms,
            error=err,
        )
        last = res

        logger.info(
            "fetch_done",
            extra={
                "url": url,
                "attempt": attempt + 1,
                "ok": ok,
                "status_code": status_code,
                "bytes_read": nbytes,
                "elapsed_ms": round(elapsed_ms, 3),
                "error": err,
            },
        )

        # Success: stop immediately
        if ok:
            return res

        # Retry if allowed + retryable
        if attempt < retries and _is_retryable(ok, status_code):
            sleep_s = _backoff_seconds(attempt, backoff_base_s, backoff_max_s, jitter_s)
            logger.warning(
                "fetch_retry",
                extra={
                    "url": url,
                    "attempt": attempt + 1,
                    "sleep_s": round(sleep_s, 3),
                    "status_code": status_code,
                    "error": err,
                },
            )
            await asyncio.sleep(sleep_s)
            continue

        break

    # If we reach here, we failed all attempts
    assert last is not None
    return last
