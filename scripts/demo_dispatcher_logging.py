from __future__ import annotations

import argparse
import asyncio
import logging
import time
from pathlib import Path
from typing import List

from ratelimmq.dispatcher import PoolLimits, run_pool
from ratelimmq.fetcher import fetch_one
from ratelimmq.logging_config import setup_logging
from ratelimmq.metrics import summarize_latencies


def read_urls(path: str) -> List[str]:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines()
    urls: List[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        urls.append(s)
    return urls


async def _fetch(u: str, timeout_s: float) -> object:
    # fetch_one returns a FetchResult dataclass
    return await fetch_one(u, timeout_s=timeout_s)


async def run_demo(urls: List[str], total: int, per_host: int, timeout_s: float) -> None:
    log = logging.getLogger("ratelimmq.demo_dispatcher")

    limits = PoolLimits(total_concurrency=total, per_host_concurrency=per_host)

    t0 = time.perf_counter()
    results = await run_pool(
        urls,
        fetch_one=lambda u: _fetch(u, timeout_s=timeout_s),
        limits=limits,
    )
    total_s = time.perf_counter() - t0

    # results are FetchResult objects (from ratelimmq.fetcher)
    ok = sum(1 for r in results if getattr(r, "ok", False))
    count = len(results)

    # metrics wants latencies in SECONDS
    lat_s = []
    for r in results:
        elapsed_ms = float(getattr(r, "elapsed_ms", 0.0))
        lat_s.append(elapsed_ms / 1000.0)

    summary = summarize_latencies(lat_s, total_s=total_s)

    # 1) Structured-ish summary log (works well for JSON log format too)
    log.info(
        "pool_summary count=%d ok=%d total_s=%.3f rps=%.1f p50_ms=%.1f p95_ms=%.1f p99_ms=%.1f",
        count,
        ok,
        summary.total_s,
        summary.rps,
        summary.p50_ms,
        summary.p95_ms,
        summary.p99_ms,
    )

    # 2) Human-friendly summary line (easy to read in terminal / screenshots)
    print(
        f"Summary: ok={ok}/{count} total={summary.total_s:.2f}s "
        f"rps={summary.rps:.1f} p50={summary.p50_ms:.1f}ms "
        f"p95={summary.p95_ms:.1f}ms p99={summary.p99_ms:.1f}ms"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Demo: dispatcher + structured logging + metrics summary")
    ap.add_argument("urls_file", help="Text file with one URL per line")
    ap.add_argument("--total", type=int, default=10, help="Global concurrency cap")
    ap.add_argument("--per-host", type=int, default=2, help="Per-host concurrency cap")
    ap.add_argument("--timeout", type=float, default=3.0, help="Per-request timeout (seconds)")
    args = ap.parse_args()

    setup_logging()

    urls = read_urls(args.urls_file)
    asyncio.run(run_demo(urls, total=args.total, per_host=args.per_host, timeout_s=args.timeout))


if __name__ == "__main__":
    main()
