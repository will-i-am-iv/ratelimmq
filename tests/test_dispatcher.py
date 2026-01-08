import asyncio

from ratelimmq.dispatcher import PoolLimits, run_pool


def test_pool_respects_global_and_per_host_caps():
    # Make URLs that map to 2 different hosts
    urls = (["https://a.example/x"] * 20) + (["https://b.example/y"] * 20)

    limits = PoolLimits(total_concurrency=7, per_host_concurrency=3)

    async def _run():
        # Track concurrency live
        lock = asyncio.Lock()
        global_inflight = 0
        per_host_inflight = {"a.example": 0, "b.example": 0}
        max_global = 0
        max_a = 0
        max_b = 0

        async def fetch_one(url: str) -> str:
            nonlocal global_inflight, max_global, max_a, max_b
            host = "a.example" if "a.example" in url else "b.example"

            async with lock:
                global_inflight += 1
                per_host_inflight[host] += 1
                max_global = max(max_global, global_inflight)
                max_a = max(max_a, per_host_inflight["a.example"])
                max_b = max(max_b, per_host_inflight["b.example"])

            # Simulate I/O
            await asyncio.sleep(0.02)

            async with lock:
                global_inflight -= 1
                per_host_inflight[host] -= 1

            return host

        results = await run_pool(urls, fetch_one, limits=limits)

        # Ensure we got back one result per URL
        assert len(results) == len(urls)

        # The whole point: never exceed caps
        assert max_global <= limits.total_concurrency
        assert max_a <= limits.per_host_concurrency
        assert max_b <= limits.per_host_concurrency

    asyncio.run(_run())
