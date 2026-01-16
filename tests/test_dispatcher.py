import asyncio

from ratelimmq.dispatcher import PoolLimits, run_pool


def test_pool_respects_global_and_per_host_caps():
    urls = (["https://a.example/x"] * 20) + (["https://b.example/y"] * 20)
    limits = PoolLimits(total_concurrency=7, per_host_concurrency=3)

    async def _run():
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

            await asyncio.sleep(0.02)

            async with lock:
                global_inflight -= 1
                per_host_inflight[host] -= 1
            return host

        results = await run_pool(urls, fetch_one, limits=limits)
        assert len(results) == len(urls)
        assert max_global <= limits.total_concurrency
        assert max_a <= limits.per_host_concurrency
        assert max_b <= limits.per_host_concurrency

    asyncio.run(_run())


def test_pool_with_bounded_queue_does_not_deadlock():
    urls = ["https://a.example/x"] * 30
    limits = PoolLimits(total_concurrency=5, per_host_concurrency=5, max_queue=2)

    async def _run():
        async def fetch_one(url: str) -> str:
            await asyncio.sleep(0.005)
            return url

        results = await run_pool(urls, fetch_one, limits=limits)
        assert len(results) == len(urls)

    asyncio.run(_run())


def test_pool_per_host_token_bucket_advances_time():
    # 5 requests, per_host_rps=2, burst=1 => needs ~2.0s of "refill time"
    urls = ["https://a.example/x"] * 5
    limits = PoolLimits(
        total_concurrency=5,
        per_host_concurrency=5,
        per_host_rps=2.0,
        per_host_burst=1.0,
    )

    async def _run():
        now = 0.0

        def clock() -> float:
            return now

        async def sleeper(dt: float) -> None:
            nonlocal now
            now += dt
            await asyncio.sleep(0)  # yield

        async def fetch_one(url: str) -> str:
            return url

        results = await run_pool(urls, fetch_one, limits=limits, clock=clock, sleeper=sleeper)
        assert len(results) == len(urls)
        assert now >= 2.0 - 1e-9

    asyncio.run(_run())
