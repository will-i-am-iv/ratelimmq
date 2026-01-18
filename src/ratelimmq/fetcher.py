from __future__ import annotations

import asyncio
import random
import time
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FetchResult:
    """
    Result of a single URL fetch attempt sequence (may include retries).
    """
    url: str
    ok: bool
    status_code: Optional[int]
    bytes_read: int
    elapsed_ms: float
    error: Optional[str] = None

    # New: how many attempts were made total (1 = no retries)
    attempts: int = 1

    # Back-compat aliases (older code/tests may reference these names)
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read


def _fetch_blocking(url: str, timeout_s: float) -> Tuple[bool, Optional[int], int, Optional[str]]:
    """
    Blocking HTTP fetch using urllib (runs inside a thread via asyncio.to_thread).
    Returns: (ok, status_code, bytes_read, error_string)
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status_code = getattr(resp, "status", None)
            body = resp.read()
            return True, status_code, len(body), None
    except Exception as e:
        # urllib raises HTTPError for non-2xx; it has `.code` (status)
        status_code = getattr(e, "code", None)
        return False, status_code, 0, f"{type(e).__name__}: {e}"


def _is_retryable_status(status_code: Optional[int], retry_statuses: Sequence[int]) -> bool:
    # If we don't have a status_code (DNS error, timeout, etc.) treat it as retryable.
    if status_code is None:
        return True
    return int(status_code) in set(int(x) for x in retry_statuses)


def _full_jitter_delay(attempt: int, base_s: float, cap_s: float, jitter: bool) -> float:
    """
    Exponential backoff with optional "full jitter":
      max_delay = min(cap, base * 2^attempt)
      delay = uniform(0, max_delay)   (if jitter)
      delay = max_delay              (if no jitter)
    """
    base_s = max(0.0, float(base_s))
    cap_s = max(0.0, float(cap_s))

    max_delay = min(cap_s, base_s * (2 ** attempt))
    if max_delay <= 0:
        return 0.0
    return random.uniform(0.0, max_delay) if jitter else max_delay


async def fetch_one(
    url: str,
    *,
    timeout_s: float = 10.0,
    retries: int = 0,
    backoff_base_s: float = 0.2,
    backoff_cap_s: float = 5.0,
    jitter: bool = True,
    retry_statuses: Sequence[int] = (408, 429, 500, 502, 503, 504),
) -> FetchResult:
    """
    Fetch one URL with optional retries.

    retries = 0 means "try once".
    Backoff happens between failed attempts (retryable only).
    """
    retries = max(0, int(retries))

    t0 = time.perf_counter()
    attempt = 0

    while True:
        ok, status_code, bytes_read, err = await asyncio.to_thread(_fetch_blocking, url, float(timeout_s))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if ok:
            return FetchResult(
                url=url,
                ok=True,
                status_code=status_code,
                bytes_read=bytes_read,
                elapsed_ms=elapsed_ms,
                error=None,
                attempts=attempt + 1,
            )

        retryable = _is_retryable_status(status_code, retry_statuses)

        if (attempt >= retries) or (not retryable):
            return FetchResult(
                url=url,
                ok=False,
                status_code=status_code,
                bytes_read=bytes_read,
                elapsed_ms=elapsed_ms,
                error=err,
                attempts=attempt + 1,
            )

        # Sleep before the next attempt
        delay_s = _full_jitter_delay(attempt, backoff_base_s, backoff_cap_s, jitter)
        if delay_s > 0:
            await asyncio.sleep(delay_s)

        attempt += 1


def collect_latencies_s(results: Iterable[FetchResult]) -> list[float]:
    """
    Helper: convert FetchResult.elapsed_ms -> seconds for metrics summarization.
    """
    out: list[float] = []
    for r in results:
        out.append(float(r.elapsed_ms) / 1000.0)
    return out
