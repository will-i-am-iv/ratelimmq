from __future__ import annotations

import argparse
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

from ratelimmq.fetcher import run_asyncio_fetch
from ratelimmq.metrics import summarize_latencies


def read_urls(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def fetch_blocking(url: str, timeout_s: float = 10.0) -> float:
    t0 = time.perf_counter()
    with urlopen(url, timeout=timeout_s) as r:
        _ = r.read(1024)  # read a little; enough to measure latency
    return time.perf_counter() - t0


def bench_sequential(urls: list[str]) -> tuple[list[float], float]:
    t0 = time.perf_counter()
    lat = [fetch_blocking(u) for u in urls]
    return lat, time.perf_counter() - t0


def bench_threads(urls: list[str], workers: int) -> tuple[list[float], float]:
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        lat = list(ex.map(fetch_blocking, urls))
    return lat, time.perf_counter() - t0


async def bench_asyncio(urls: list[str], concurrency: int) -> tuple[list[float], float]:
    t0 = time.perf_counter()
    results = await run_asyncio_fetch(urls, concurrency=concurrency)
    lat = [r.elapsed_s for r in results if r.ok]
    return lat, time.perf_counter() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls_file", help="text file with one URL per line")
    ap.add_argument("--mode", choices=["seq", "threads", "asyncio"], default="asyncio")
    ap.add_argument("--concurrency", type=int, default=50)
    args = ap.parse_args()

    urls = read_urls(args.urls_file)

    if args.mode == "seq":
        lat, total = bench_sequential(urls)
    elif args.mode == "threads":
        lat, total = bench_threads(urls, workers=args.concurrency)
    else:
        lat, total = asyncio.run(bench_asyncio(urls, concurrency=args.concurrency))

    s = summarize_latencies(lat, total_time_s=total)
    print(f"mode={args.mode} urls={len(urls)} ok={s.count} total_s={total:.3f}")
    print(f"p50={s.p50_ms:.1f}ms p95={s.p95_ms:.1f}ms p99={s.p99_ms:.1f}ms rps={s.rps:.1f}")


if __name__ == "__main__":
    main()
