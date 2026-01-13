from __future__ import annotations

import argparse
import asyncio
import time
from typing import List

from ratelimmq.dispatcher import PoolLimits, run_pool
from ratelimmq.fetcher import fetch_one
from ratelimmq.logging_config import setup_logging
from ratelimmq.metrics import summarize_latencies


def read_urls(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


async def _fetch(u: str, timeout_s: float) -> object:
    return await fetch_one(u, timeout_s=timeout_s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls_file", help="text file with one URL per line")
    ap.add_argument("--total", type=int, default=10, help="global concurrency cap")
    ap.add_argument("--per-host", type=int, default=2, help="per-host concurrency cap")
    ap.add_argument("--max-queue", type=int, default=0, help="bounded queue size (0 = unbounded)")
    ap.add_argument("--timeout", type=float, default=3.0, help="per-request timeout seconds")
    args = ap.parse_args()

    setup_logging()

    urls = read_urls(args.urls_file)
    limits = PoolLimits(total_concurrency=args.total, per_host_concurrency=args.per_host)
    max_queue = None if args.max_queue <= 0 else args.max_queue

    t0 = time.perf_counter()
    results = asyncio.run(
        run_pool(
            urls,
            lambda u: _fetch(u, timeout_s=args.timeout),
            limits=limits,
            max_queue=max_queue,
        )
    )
    total_s = time.perf_counter() - t0

    ok = [bool(getattr(r, "ok", False)) for r in results]
    ok_count = sum(1 for x in ok if x)

    # Print a clean summary line every run (even if logs are JSON)
    lat_s = []
    for r in results:
        ms = getattr(r, "elapsed_ms", None)
        if ms is not None:
            lat_s.append(float(ms) / 1000.0)

    if lat_s:
        s = summarize_latencies(lat_s, total_s=total_s)
        print(
            f"pool_summary count={s.count} ok={ok_count} total_s={s.total_s:.3f} "
            f"rps={s.rps:.1f} p50_ms={s.p50_ms:.1f} p95_ms={s.p95_ms:.1f} p99_ms={s.p99_ms:.1f}"
        )

    print(f"done: {ok_count}/{len(results)} ok")


if __name__ == "__main__":
    main()
