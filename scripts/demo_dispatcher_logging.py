from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ratelimmq.dispatcher import PoolLimits, run_pool
from ratelimmq.fetcher import fetch_one


def read_urls(path: str) -> list[str]:
    p = Path(path)
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls_file", help="text file with one URL per line")
    ap.add_argument("--total", type=int, default=50, help="global concurrency cap")
    ap.add_argument("--per-host", type=int, default=10, help="per-host concurrency cap")
    ap.add_argument("--timeout", type=float, default=3.0, help="per-request timeout (seconds)")
    args = ap.parse_args()

    urls = read_urls(args.urls_file)
    limits = PoolLimits(total_concurrency=args.total, per_host_concurrency=args.per_host)

    async def fetch(u: str):
        return await fetch_one(u, timeout_s=args.timeout)

    results = await run_pool(urls, fetch, limits=limits)
    ok = sum(1 for r in results if getattr(r, "ok", False))
    print(f"done: {ok}/{len(results)} ok")


if __name__ == "__main__":
    asyncio.run(main())
