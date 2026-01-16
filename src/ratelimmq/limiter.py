from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class TokenBucket:
    """
    Simple token bucket.

    - capacity: max tokens in the bucket (burst)
    - refill_rate: tokens per second
    - tokens: current token count
    - last_ts: last refill timestamp (seconds, monotonic)
    """
    capacity: float
    refill_rate: float
    tokens: float = 0.0
    last_ts: float = 0.0

    def __post_init__(self) -> None:
        self.capacity = float(self.capacity)
        self.refill_rate = float(self.refill_rate)
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if self.refill_rate < 0:
            raise ValueError("refill_rate must be >= 0")
        if self.last_ts == 0.0:
            self.last_ts = time.monotonic()
        if self.tokens == 0.0:
            self.tokens = self.capacity

    def _refill(self, now: float) -> None:
        if self.refill_rate <= 0:
            self.last_ts = now
            return
        dt = max(0.0, now - self.last_ts)
        self.last_ts = now
        self.tokens = min(self.capacity, self.tokens + dt * self.refill_rate)

    def allow(self, cost: float = 1.0, now: float | None = None) -> bool:
        if cost <= 0:
            raise ValueError("cost must be > 0")
        t = time.monotonic() if now is None else float(now)
        self._refill(t)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    def wait_time(self, cost: float = 1.0, now: float | None = None) -> float:
        """
        Returns seconds to wait until `cost` tokens are available.
        0.0 means "you can proceed now".
        """
        if cost <= 0:
            raise ValueError("cost must be > 0")
        t = time.monotonic() if now is None else float(now)
        self._refill(t)
        if self.tokens >= cost:
            return 0.0
        if self.refill_rate <= 0:
            return float("inf")
        missing = cost - self.tokens
        return missing / self.refill_rate
