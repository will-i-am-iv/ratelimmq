from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

from ratelimmq.metrics import summarize_latencies

T = TypeVar("T")

logger = logging.getLogger("ratelimmq.dispatcher")


def host_key(url: str) -> str:
    """
    Normalize a URL into a host key used for per-host limiting.
    Examples:
      - https://example.com/a -> example.com
      - http://example.com:8080 -> example.com
    """
    p = urlparse(url)
    host = (p.hostname or "").strip().lower()
    return host or "unknown"


@dataclass(frozen=True)
class PoolLimits:
    total_concurrency: int = 50
    per_host_concurrency: int = 10


class _HostSemaphores:
    """
    Lazily creates an asyncio.Semaphore per host.
    """
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
    max_queue: Optional[int] = None,
) -> List[T]:
    """
    Run a worker pool that:
      - caps total in-flight fetches (global semaphore)
      - caps in-flight fetches per host (per-host semaphore)
      - optionally applies backpressure via a bounded queue (max_queue)

    Returns results in the same order as input URLs.
    """
    urls_list = list(urls)
    out: List[Optional[T]] = [None] * len(urls_list)

    total_sem = asyncio.Semaphore(max(1, int(limits.total_concurrency)))
    host_sems = _HostSemaphores(limits.per_host_concurrency)

    # Backpressure: if max_queue is set, producer will block when queue is full.
    q_max = 0 if (max_queue is None) else max(1, int(max_queue))
    q: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue(maxsize=q_max)

    async def producer(n_workers: int) -> None:
        for i, u in enumerate(urls_list):
            await q.put((i, u))
        # One sentinel per worker so everyone exits
        for _ in range(n_workers):
            await q.put(None)

    async def worker() -> None:
        while True:
            item = await q.get()
            try:
                if item is None:
                    return

                i, u = item
                h = host_key(u)
                host_sem = await host_sems.get(h)

                # Acquire both limits; always release in finally.
                await total_sem.acquire()
                await host_sem.acquire()
                try:
                    out[i] = await fetch_one(u)
                finally:
                    host_sem.release()
                    total_sem.release()
            finally:
                q.task_done()

    n_workers = min(len(urls_list), max(1, int(limits.total_concurrency)))
    t0 = time.perf_counter()

    producer_task = asyncio.create_task(producer(n_workers))
    worker_tasks = [asyncio.create_task(worker()) for _ in range(n_workers)]

    await asyncio.gather(producer_task)
    await q.join()
    await asyncio.gather(*worker_tasks)

    total_s = time.perf_counter() - t0

    results: List[T] = [x for x in out if x is not None]

    # Try to summarize (works with FetchResult objects that have elapsed_ms + ok)
    try:
        lat_s = []
        ok_count = 0
        for r in results:
            ok = bool(getattr(r, "ok", False))
            ok_count += 1 if ok else 0
            elapsed_ms = getattr(r, "elapsed_ms", None)
            if elapsed_ms is not None:
                lat_s.append(float(elapsed_ms) / 1000.0)

        if lat_s:
            s = summarize_latencies(lat_s, total_s=total_s)
            logger.info(
                "pool_summary",
                extra={
                    "count": s.count,
                    "ok": ok_count,
                    "total_s": s.total_s,
                    "rps": s.rps,
                    "p50_ms": s.p50_ms,
                    "p95_ms": s.p95_ms,
                    "p99_ms": s.p99_ms,
                },
            )
    except Exception:
        # Never fail the pool because metrics/logging broke
        logger.exception("pool_summary_failed")

    return results
