from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _percentile(sorted_vals: list[float], p: float) -> float:
    """
    Nearest-rank percentile.
    p is in [0, 100].
    """
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    # nearest-rank: k = ceil(p/100 * n)
    n = len(sorted_vals)
    k = int((p / 100.0) * n)
    if (p / 100.0) * n > k:
        k += 1
    k = max(1, min(n, k))
    return sorted_vals[k - 1]


@dataclass(frozen=True)
class LatencySummary:
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    rps: float


def summarize_latencies(latencies_s: Iterable[float], total_time_s: float) -> LatencySummary:
    vals = [float(x) for x in latencies_s if x is not None]
    vals.sort()
    count = len(vals)
    p50 = _percentile(vals, 50) * 1000.0
    p95 = _percentile(vals, 95) * 1000.0
    p99 = _percentile(vals, 99) * 1000.0
    rps = (count / total_time_s) if total_time_s > 0 else 0.0
    return LatencySummary(count=count, p50_ms=p50, p95_ms=p95, p99_ms=p99, rps=rps)
