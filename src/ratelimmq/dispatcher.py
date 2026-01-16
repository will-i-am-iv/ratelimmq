from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


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
    # Backpressure: cap how many items can sit in the queue waiting for workers.
    # None => auto (2x total_concurrency, clamped to [1, len(urls)]).
    queue_max: Optional[int] = None


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
) -> List[T]:
    """
    Run a worker pool that:
      - caps total in-flight fetches (global semaphore)
      - caps in-flight fetches per host (per-host semaphore)
      - uses a bounded queue to avoid unbounded buffering (backpressure)

    Returns results in the same order as input URLs.
    """
    urls_list = list(urls)
    out: List[Optional[T]] = [None] * len(urls_list)

    # Edge case
    if not urls_list:
        return []

    total_sem = asyncio.Semaphore(max(1, int(limits.total_concurrency)))
    host_sems = _HostSemaphores(limits.per_host_concurrency)

    # Backpressure queue sizing
    if limits.queue_max is None:
        auto_max = max(1, min(len(urls_list), int(limits.total_concurrency) * 2))
        qmax = auto_max
    else:
        qmax = max(1, min(len(urls_list), int(limits.queue_max)))

    q: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue(maxsize=qmax)

    async def producer() -> None:
        for i, u in enumerate(urls_list):
            # await put => if queue is full, producer waits (backpressure)
            await q.put((i, u))

        # Send one sentinel per worker to stop them cleanly
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

                # Acquire both limits, always release in finally
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

    prod_task = asyncio.create_task(producer())
    workers = [asyncio.create_task(worker()) for _ in range(n_workers)]

    # Wait for producer to enqueue everything
    await prod_task
    # Wait until queue fully processed
    await q.join()
    # Ensure workers exit (they should, because sentinels were queued)
    await asyncio.gather(*workers)

    # typing guard: fetch_one should always return T
    return [x for x in out if x is not None]
