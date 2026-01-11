from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional


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


def summarize_latencies(
    latencies_s: Iterable[float],
    total_time_s: Optional[float] = None,
    *,
    # Back-compat alias: some callers may pass total_s=
    total_s: Optional[float] = None,
) -> LatencySummary:
    """
    Summarize request latencies (seconds) into p50/p95/p99 + mean/min/max (ms) and rps.

    - latencies_s: iterable of per-request latencies in seconds.
    - total_time_s: wall-clock duration in seconds (recommended). Used to compute rps.
    - total_s: alias for total_time_s (kept for older code).
    """
    vals = [float(x) for x in latencies_s if x is not None]
    vals = [x for x in vals if x >= 0.0]
    vals.sort()

    count = len(vals)

    if total_time_s is None and total_s is not None:
        total_time_s = float(total_s)

    if total_time_s is None:
        # Fallback: if caller didn't provide wall-clock, use sum of latencies.
        total_time_s = float(sum(vals)) if count else 0.0

    total_time_s = float(total_time_s) if total_time_s and total_time_s > 0 else 0.0
    rps = (count / total_time_s) if total_time_s > 0 else 0.0

    if count == 0:
        return LatencySummary(
            count=0,
            total_s=total_time_s,
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
        total_s=total_time_s,
        rps=rps,
        mean_ms=mean_ms,
        p50_ms=_quantile_ms(vals, 0.50),
        p95_ms=_quantile_ms(vals, 0.95),
        p99_ms=_quantile_ms(vals, 0.99),
        min_ms=min_ms,
        max_ms=max_ms,
    )


# -------------------------------
# Optional Prometheus integration
# -------------------------------
# CI should NOT require prometheus_client. If it's missing, these become no-ops.

_HAS_PROM = False
try:
    from prometheus_client import Counter, Histogram, start_http_server  # type: ignore

    _HAS_PROM = True
except Exception:
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    start_http_server = None  # type: ignore


_REQ_TOTAL = None
_REQ_LATENCY_S = None
_PROM_STARTED = False


def start_prometheus(port: int = 8000) -> bool:
    """Start /metrics endpoint. Returns False if prometheus_client isn't installed."""
    global _PROM_STARTED, _REQ_TOTAL, _REQ_LATENCY_S

    if not _HAS_PROM or start_http_server is None:
        return False
    if _PROM_STARTED:
        return True

    _REQ_TOTAL = Counter(
        "ratelimmq_requests_total",
        "Total HTTP fetch requests",
        ["outcome"],
    )
    _REQ_LATENCY_S = Histogram(
        "ratelimmq_request_latency_seconds",
        "HTTP fetch request latency in seconds",
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
    )

    start_http_server(int(port))
    _PROM_STARTED = True
    return True


def prom_observe(outcome: str, elapsed_s: float) -> None:
    """Record metrics if Prometheus is enabled; otherwise no-op."""
    if not _HAS_PROM:
        return
    if _REQ_TOTAL is None or _REQ_LATENCY_S is None:
        return

    try:
        _REQ_TOTAL.labels(outcome=outcome).inc()
        _REQ_LATENCY_S.observe(float(elapsed_s))
    except Exception:
        return
