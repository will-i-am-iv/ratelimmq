from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar
from urllib.parse import urlparse

from ratelimmq.limiter import TokenBucket

T = TypeVar("T")


def host_key(url: str) -> str:
    """Normalize URL to a host key used for per-host limiting."""
    p = urlparse(url)
    host = (p.hostname or "").strip().lower()
    return host or "unknown"


@dataclass(frozen=True)
class PoolLimits:
    # concurrency caps
    total_concurrency: int = 50
    per_host_concurrency: int = 10

    # bounded queue backpressure:
    # 0 means "unbounded" (asyncio.Queue default behavior)
    max_queue: int = 0

    # per-host token bucket rate limiting (requests/sec):
    # set per_host_rps > 0 to enable
    per_host_rps: float = 0.0
    per_host_burst: float = 1.0


class _HostSemaphores:
    """Lazily creates an asyncio.Semaphore per host."""
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


class _HostBuckets:
    """Lazily creates a TokenBucket per host, plus a lock per host."""
    def __init__(
        self,
        *,
        refill_rate: float,
        capacity: float,
        clock: Callable[[], float],
        sleeper: Callable[[float], Awaitable[None]],
    ) -> None:
        self._refill_rate = float(refill_rate)
        self._capacity = float(capacity)
        self._clock = clock
        self._sleep = sleeper

        self._buckets: Dict[str, TokenBucket] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_pair(self, host: str) -> Tuple[TokenBucket, asyncio.Lock]:
        async with self._global_lock:
            b = self._buckets.get(host)
            lk = self._locks.get(host)
            if b is None:
                b = TokenBucket(capacity=self._capacity, refill_rate=self._refill_rate)
                self._buckets[host] = b
            if lk is None:
                lk = asyncio.Lock()
                self._locks[host] = lk
            return b, lk

    async def acquire(self, host: str, cost: float = 1.0) -> None:
        """Wait until host bucket has >= cost tokens, then consume."""
        if self._refill_rate <= 0:
            # enabled but misconfigured; treat as "never refill" => would block forever
            # so we just don't throttle.
            return

        while True:
            bucket, lk = await self._get_pair(host)
            async with lk:
                now = self._clock()
                if bucket.allow(cost=cost, now=now):
                    return
                wait_s = bucket.wait_time(cost=cost, now=now)

            # wait outside lock
            if wait_s == float("inf"):
                return
            await self._sleep(max(0.0, wait_s))


async def run_pool(
    urls: Iterable[str],
    fetch_one: Callable[[str], Awaitable[T]],
    *,
    limits: PoolLimits = PoolLimits(),
    clock: Optional[Callable[[], float]] = None,
    sleeper: Optional[Callable[[float], Awaitable[None]]] = None,
) -> List[T]:
    """
    Worker pool that:
      - caps total in-flight fetches (global semaphore)
      - caps in-flight fetches per host (per-host semaphore)
      - optionally applies bounded-queue backpressure (max_queue)
      - optionally applies per-host token-bucket rate limiting (per_host_rps)
    """
    urls_list = list(urls)
    if not urls_list:
        return []

    total_sem = asyncio.Semaphore(max(1, int(limits.total_concurrency)))
    host_sems = _HostSemaphores(limits.per_host_concurrency)

    _clock = clock or time.monotonic
    _sleep = sleeper or asyncio.sleep

    buckets: Optional[_HostBuckets] = None
    if float(limits.per_host_rps) > 0:
        burst = float(limits.per_host_burst) if limits.per_host_burst > 0 else 1.0
        buckets = _HostBuckets(
            refill_rate=float(limits.per_host_rps),
            capacity=burst,
            clock=_clock,
            sleeper=_sleep,
        )

    q: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue(maxsize=max(0, int(limits.max_queue)))
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

                # Rate limit FIRST (so we don't hold concurrency slots while waiting)
                if buckets is not None:
                    await buckets.acquire(h, cost=1.0)

                host_sem = await host_sems.get(h)
                async with total_sem:
                    async with host_sem:
                        out[i] = await fetch_one(u)
            finally:
                q.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(n_workers)]

    # Producer: enqueue work, then enqueue sentinels
    for i, u in enumerate(urls_list):
        await q.put((i, u))
    for _ in range(n_workers):
        await q.put(None)

    await q.join()
    await asyncio.gather(*workers)

    # out should be fully filled
    assert all(x is not None for x in out)
    return [x for x in out if x is not None]
