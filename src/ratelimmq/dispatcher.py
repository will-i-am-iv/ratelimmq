from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

from ratelimmq.metrics import summarize_latencies

T = TypeVar("T")

log = logging.getLogger("ratelimmq.dispatcher")


def host_key(url: str) -> str:
    """
    Normalize a URL into a host key used for per-host limiting.
    Examples:
      - https://example.com/a    -> example.com
      - http://example.com:8080  -> example.com
    """
    p = urlparse(url)
    host = (p.hostname or "").strip().lower()
    return host or "unknown"


@dataclass(frozen=True)
class PoolLimits:
    total_concurrency: int = 50
    per_host_concurrency: int = 10


class _HostSemaphores:
    """Lazily creates an asyncio.Semaphore per host (thread-safe via an asyncio.Lock)."""

    def __init__(self, per_host: int) -> None:
        self._per_host = max(1, int(per_host))
        self._sems: Dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    async def get(self, host: str) -> asyncio.Semaphore:
        async with self._lock:
            sem = self._sems.get(host)
            if sem is None:
                sem = asyncio.Semaphore(self._per_host)
                self._sems[host] = sem
            return sem


async def run_pool(
    urls: Iterable[str],
    fetch_one: Callable[[str], Awaitable[T]],
    *,
    limits: PoolLimits = PoolLimits(),
) -> List[T]:
    """
    Run a worker pool that:
      - caps total in-flight fetches (global semaphore)
      - caps in-flight fetches per host (per-host semaphore)
    Returns results in the same order as input URLs.
    """
    urls_list = list(urls)
    out: List[Optional[T]] = [None] * len(urls_list)

    total_limit = max(1, int(limits.total_concurrency))
    per_host_limit = max(1, int(limits.per_host_concurrency))

    total_sem = asyncio.Semaphore(total_limit)
    host_sems = _HostSemaphores(per_host_limit)

    q: asyncio.Queue[Tuple[int, str]] = asyncio.Queue()
    for i, u in enumerate(urls_list):
        q.put_nowait((i, u))

    pool_t0 = time.perf_counter()

    async def worker() -> None:
        while True:
            try:
                i, u = q.get_nowait()
            except asyncio.QueueEmpty:
                return

            h = host_key(u)
            host_sem = await host_sems.get(h)

            # Acquire BOTH limits. Always release in finally.
            await total_sem.acquire()
            await host_sem.acquire()
            item_t0 = time.perf_counter()

            try:
                log.info("fetch_start url=%s host=%s idx=%d", u, h, i)
                res = await fetch_one(u)
                out[i] = res

                # Best-effort introspection (works with your FetchResult)
                status = getattr(res, "status_code", None)
                ok = getattr(res, "ok", None)
                bytes_read = getattr(res, "bytes_read", None)
                elapsed_ms = getattr(res, "elapsed_ms", None)

                # Fallback if elapsed_ms isn't present
                if elapsed_ms is None:
                    elapsed_ms = (time.perf_counter() - item_t0) * 1000.0

                log.info(
                    "fetch_done url=%s host=%s idx=%d ok=%s status=%s bytes=%s elapsed_ms=%.2f",
                    u,
                    h,
                    i,
                    ok,
                    status,
                    bytes_read,
                    float(elapsed_ms),
                )
            except Exception as e:
                log.exception("fetch_error url=%s host=%s idx=%d err=%r", u, h, i, e)
                raise
            finally:
                host_sem.release()
                total_sem.release()
                q.task_done()

    # Worker count: enough to keep pool busy, but not huge.
    n_workers = min(len(urls_list), total_limit)
    tasks = [asyncio.create_task(worker()) for _ in range(max(1, n_workers))]
    await asyncio.gather(*tasks)

    results: List[T] = [x for x in out if x is not None]
    total_s = time.perf_counter() - pool_t0

    # Summary metrics (best-effort, based on FetchResult.elapsed_ms)
    lat_s: List[float] = []
    ok_count = 0
    for r in results:
        ok = getattr(r, "ok", False)
        if ok:
            ok_count += 1
        elapsed_ms = getattr(r, "elapsed_ms", None)
        if elapsed_ms is not None:
            lat_s.append(float(elapsed_ms) / 1000.0)

    if lat_s:
        s = summarize_latencies(lat_s, total_s=total_s)
        log.info(
            "pool_summary count=%d ok=%d total_s=%.3f rps=%.2f p50_ms=%.1f p95_ms=%.1f p99_ms=%.1f",
            s.count,
            ok_count,
            s.total_s,
            s.rps,
            s.p50_ms,
            s.p95_ms,
            s.p99_ms,
        )
    else:
        log.info("pool_summary count=%d ok=%d total_s=%.3f", len(results), ok_count, total_s)

    return results
