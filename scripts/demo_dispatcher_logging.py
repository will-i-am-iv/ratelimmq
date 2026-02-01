from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from ratelimmq.dispatcher import PoolLimits, run_pool
from ratelimmq.fetcher import fetch_one
from ratelimmq.logging_config import setup_logging
from ratelimmq.metrics import summarize_latencies


def read_urls(path: str) -> list[str]:
    p = Path(path)
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


async def main() -> None:
    setup_logging()

    ap = argparse.ArgumentParser()
    ap.add_argument("urls_file")
    ap.add_argument("--total", type=int, default=10)
    ap.add_argument("--per-host", type=int, default=2)
    ap.add_argument("--max-queue", type=int, default=10)
    ap.add_argument("--per-host-rps", type=float, default=0.0)
    ap.add_argument("--burst", type=float, default=0.0)

    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--base", type=float, default=0.05)
    ap.add_argument("--cap", type=float, default=0.5)
    ap.add_argument("--jitter", type=float, default=0.05)
    args = ap.parse_args()

    urls = read_urls(args.urls_file)

    limits = PoolLimits(
        total_concurrency=args.total,
        per_host_concurrency=args.per_host,
        max_queue=max(0, args.max_queue),
        per_host_rps=max(0.0, args.per_host_rps),
        per_host_burst=max(0.0, args.burst),
    )

    async def fetch(u: str):
        return await fetch_one(
            u,
            timeout_s=args.timeout,
            retries=args.retries,
            backoff_base_s=args.base,
            backoff_max_s=args.cap,
            jitter_s=args.jitter,
        )

    t0 = time.perf_counter()
    results = await run_pool(urls, fetch, limits=limits)
    total_s = time.perf_counter() - t0

    lat_s = [float(getattr(r, "elapsed_ms", 0.0)) / 1000.0 for r in results]
    s = summarize_latencies(lat_s, total_s=total_s)
    ok_count = sum(1 for r in results if getattr(r, "ok", False))

    print(
        f"pool_summary count={s.count} ok={ok_count} total_s={s.total_s:.3f} "
        f"rps={s.rps:.1f} p50_ms={s.p50_ms:.1f} p95_ms={s.p95_ms:.1f} p99_ms={s.p99_ms:.1f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
