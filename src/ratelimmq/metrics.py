from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import math


@dataclass(frozen=True)
class LatencySummary:
    count: int
    total_s: float
    rps: float

    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float

    min_ms: float
    max_ms: float


def _quantile_ms(sorted_vals_s: list[float], q: float) -> float:
    """
    Linear-interpolated quantile.
    q in [0,1]. Returns milliseconds.
    """
    n = len(sorted_vals_s)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals_s[0] * 1000.0

    q = min(1.0, max(0.0, float(q)))
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals_s[lo] * 1000.0
    frac = pos - lo
    v = sorted_vals_s[lo] * (1.0 - frac) + sorted_vals_s[hi] * frac
    return v * 1000.0


def summarize_latencies(latencies_s: Iterable[float], total_s: Optional[float] = None) -> LatencySummary:
    """
    Summarize request latencies (seconds) into p50/p95/p99 + mean/min/max (ms) and rps.

    - latencies_s: iterable of per-request latencies in seconds
    - total_s: wall-clock duration in seconds (recommended). If None, we fall back to sum(latencies).
    """
    vals = [float(x) for x in latencies_s if x is not None]
    vals = [x for x in vals if x >= 0.0]

    vals.sort()
    count = len(vals)

    if total_s is None:
        total_s = float(sum(vals)) if count else 0.0
    total_s = float(total_s)

    rps = (count / total_s) if total_s > 0 else 0.0

    if count == 0:
        return LatencySummary(
            count=0,
            total_s=total_s,
            rps=rps,
            mean_ms=0.0,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
        )

    mean_ms = (sum(vals) / count) * 1000.0
    min_ms = vals[0] * 1000.0
    max_ms = vals[-1] * 1000.0

    return LatencySummary(
        count=count,
        total_s=total_s,
        rps=rps,
        mean_ms=mean_ms,
        p50_ms=_quantile_ms(vals, 0.50),
        p95_ms=_quantile_ms(vals, 0.95),
        p99_ms=_quantile_ms(vals, 0.99),
        min_ms=min_ms,
        max_ms=max_ms,
    )


def format_prometheus_text(s: LatencySummary) -> str:
    """
    Prometheus-style exposition text WITHOUT requiring prometheus_client.
    You can later serve this on /metrics with your own tiny HTTP handler.
    """
    lines = [
        "# TYPE ratelimmq_requests_total gauge",
        f"ratelimmq_requests_total {s.count}",
        "# TYPE ratelimmq_total_seconds gauge",
        f"ratelimmq_total_seconds {s.total_s:.6f}",
        "# TYPE ratelimmq_rps gauge",
        f"ratelimmq_rps {s.rps:.6f}",
        "# TYPE ratelimmq_latency_mean_ms gauge",
        f"ratelimmq_latency_mean_ms {s.mean_ms:.6f}",
        "# TYPE ratelimmq_latency_p50_ms gauge",
        f"ratelimmq_latency_p50_ms {s.p50_ms:.6f}",
        "# TYPE ratelimmq_latency_p95_ms gauge",
        f"ratelimmq_latency_p95_ms {s.p95_ms:.6f}",
        "# TYPE ratelimmq_latency_p99_ms gauge",
        f"ratelimmq_latency_p99_ms {s.p99_ms:.6f}",
        "# TYPE ratelimmq_latency_min_ms gauge",
        f"ratelimmq_latency_min_ms {s.min_ms:.6f}",
        "# TYPE ratelimmq_latency_max_ms gauge",
        f"ratelimmq_latency_max_ms {s.max_ms:.6f}",
        "",
    ]
    return "\n".join(lines)
