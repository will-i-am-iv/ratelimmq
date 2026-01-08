from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Generic, Iterable, List, Optional, Tuple, TypeVar
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

    Returns results in the same order as input URLs.
    """
    urls_list = list(urls)
    out: List[Optional[T]] = [None] * len(urls_list)

    total_sem = asyncio.Semaphore(max(1, int(limits.total_concurrency)))
    host_sems = _HostSemaphores(limits.per_host_concurrency)

    q: asyncio.Queue[Tuple[int, str]] = asyncio.Queue()
    for i, u in enumerate(urls_list):
        q.put_nowait((i, u))

    async def worker() -> None:
        while True:
            try:
                i, u = q.get_nowait()
            except asyncio.QueueEmpty:
                return

            h = host_key(u)
            host_sem = await host_sems.get(h)

            # Acquire both limits. Always release in finally.
            await total_sem.acquire()
            await host_sem.acquire()
            try:
                out[i] = await fetch_one(u)
            finally:
                host_sem.release()
                total_sem.release()
                q.task_done()

    # Worker count: enough to keep the pool busy, but not huge.
    n_workers = min(len(urls_list), max(1, int(limits.total_concurrency)))
    tasks = [asyncio.create_task(worker()) for _ in range(n_workers)]
    await asyncio.gather(*tasks)

    # mypy/typing guard: all should be filled
    return [x for x in out if x is not None]
