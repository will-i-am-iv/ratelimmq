from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

from ratelimmq.host_ratelimit import HostTokenBuckets

T = TypeVar("T")


def host_key(url: str) -> str:
    p = urlparse(url)
    host = (p.hostname or "").strip().lower()
    return host or "unknown"


@dataclass(frozen=True)
class PoolLimits:
    # Concurrency caps
    total_concurrency: int = 50
    per_host_concurrency: int = 10

    # Backpressure (0 = unbounded queue)
    max_queue: int = 0

    # Per-host token bucket (0 disables)
    per_host_rps: float = 0.0
    per_host_burst: float = 0.0


class _HostSemaphores:
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
    clock: Optional[Callable[[], float]] = None,
    sleeper: Optional[Callable[[float], Awaitable[None]]] = None,
) -> List[T]:
    """
    Worker pool with:
      - global concurrency cap
      - per-host concurrency cap
      - bounded queue backpressure (optional)
      - per-host token-bucket rate limiting (optional)

    Returns results in the same order as input URLs.
    """
    urls_list = list(urls)
    if not urls_list:
        return []

    _clock = clock or time.monotonic
    _sleep = sleeper or asyncio.sleep

    total_sem = asyncio.Semaphore(max(1, int(limits.total_concurrency)))
    host_sems = _HostSemaphores(limits.per_host_concurrency)

    buckets: Optional[HostTokenBuckets] = None
    if float(limits.per_host_rps) > 0:
        burst = float(limits.per_host_burst) if limits.per_host_burst > 0 else max(1.0, float(limits.per_host_rps))
        buckets = HostTokenBuckets(rps=float(limits.per_host_rps), burst=burst, clock=_clock, sleeper=_sleep)  # type: ignore[arg-type]

    qmax = max(0, int(limits.max_queue))
    q: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue(maxsize=qmax)

    out: List[Optional[T]] = [None] * len(urls_list)
    n_workers = min(len(urls_list), max(1, int(limits.total_concurrency)))

    async def worker() -> None:
        while True:
            item = await q.get()
            try:
                if item is None:
                    return

                i, u = item
                h = host_key(u)

                # Rate limit first (don’t hold concurrency slots while waiting)
                if buckets is not None:
                    await buckets.acquire(h, cost=1.0)

                host_sem = await host_sems.get(h)

                await total_sem.acquire()
                await host_sem.acquire()
                try:
                    out[i] = await fetch_one(u)
                finally:
                    host_sem.release()
                    total_sem.release()
            finally:
                q.task_done()

    # Start workers first (prevents deadlock when max_queue is small)
    workers = [asyncio.create_task(worker()) for _ in range(n_workers)]

    # Producer: enqueue work (await put => backpressure)
    for i, u in enumerate(urls_list):
        await q.put((i, u))

    # Stop workers with sentinels
    for _ in range(n_workers):
        await q.put(None)

    await q.join()
    await asyncio.gather(*workers)

    assert all(x is not None for x in out)
    return [x for x in out if x is not None]
