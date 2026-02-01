from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class _TokenBucket:
    capacity: float
    refill_rate: float
    tokens: float
    last_ts: float

    def refill(self, now: float) -> None:
        dt = max(0.0, now - self.last_ts)
        self.last_ts = now
        self.tokens = min(self.capacity, self.tokens + dt * self.refill_rate)

    def allow(self, cost: float, now: float) -> bool:
        self.refill(now)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    def wait_time(self, cost: float, now: float) -> float:
        self.refill(now)
        if self.tokens >= cost:
            return 0.0
        if self.refill_rate <= 0:
            return float("inf")
        missing = cost - self.tokens
        return missing / self.refill_rate


class HostTokenBuckets:
    """
    Per-host token buckets with per-host locks.
    Safe for concurrent asyncio access.
    """

    def __init__(
        self,
        *,
        rps: float,
        burst: float,
        clock: Callable[[], float],
        sleeper: Callable[[float], asyncio.Future],
    ) -> None:
        self._rps = float(rps)
        self._burst = float(burst)
        self._clock = clock
        self._sleep = sleeper

        self._buckets: Dict[str, _TokenBucket] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def enabled(self) -> bool:
        return self._rps > 0.0

    async def _get(self, host: str) -> tuple[_TokenBucket, asyncio.Lock]:
        async with self._global_lock:
            b = self._buckets.get(host)
            lk = self._locks.get(host)
            if b is None:
                cap = self._burst if self._burst > 0 else max(1.0, self._rps)
                now = self._clock()
                b = _TokenBucket(capacity=cap, refill_rate=self._rps, tokens=cap, last_ts=now)
                self._buckets[host] = b
            if lk is None:
                lk = asyncio.Lock()
                self._locks[host] = lk
            return b, lk

    async def acquire(self, host: str, *, cost: float = 1.0) -> None:
        """
        Wait until a token is available for this host, then consume it.
        """
        if not self.enabled():
            return

        while True:
            bucket, lk = await self._get(host)
            async with lk:
                now = self._clock()
                if bucket.allow(cost, now):
                    return
                wait_s = bucket.wait_time(cost, now)

            if wait_s == float("inf"):
                return
            await self._sleep(max(0.0, wait_s))
