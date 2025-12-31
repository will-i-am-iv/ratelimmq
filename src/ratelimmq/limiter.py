from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass
class TokenBucket:
    """
    Simple token bucket limiter.

    capacity: max tokens in the bucket
    refill_rate: tokens per second
    """
    capacity: float
    refill_rate: float
    tokens: float | None = None
    last_ts: float | None = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        if self.refill_rate < 0:
            raise ValueError("refill_rate must be >= 0")

        now = time.monotonic()
        if self.tokens is None:
            self.tokens = float(self.capacity)
        if self.last_ts is None:
            self.last_ts = now

    def _refill(self, now: float) -> None:
        assert self.tokens is not None
        assert self.last_ts is not None

        elapsed = max(0.0, now - self.last_ts)
        self.tokens = min(float(self.capacity), self.tokens + elapsed * float(self.refill_rate))
        self.last_ts = now

    def allow(self, cost: float = 1.0, now: float | None = None) -> bool:
        """
        Returns True if the bucket has >= cost tokens; consumes cost tokens.
        If now is provided, it is used for deterministic testing.
        """
        if cost <= 0:
            raise ValueError("cost must be > 0")

        t = time.monotonic() if now is None else float(now)
        self._refill(t)

        assert self.tokens is not None
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
