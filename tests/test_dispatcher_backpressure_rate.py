import asyncio

from ratelimmq.dispatcher import PoolLimits, run_pool


def test_bounded_queue_does_not_deadlock():
    urls = ["https://a.example/x"] * 50
    limits = PoolLimits(total_concurrency=5, per_host_concurrency=5, max_queue=2)

    async def _run():
        async def fetch_one(url: str) -> str:
            await asyncio.sleep(0.001)
            return url

        out = await run_pool(urls, fetch_one, limits=limits)
        assert len(out) == len(urls)

    asyncio.run(_run())


def test_per_host_token_bucket_advances_time():
    # per_host_rps=2, burst=1, need 5 tokens total => ~2 seconds of refill time after first token
    urls = ["https://a.example/x"] * 5
    limits = PoolLimits(
        total_concurrency=5,
        per_host_concurrency=5,
        max_queue=5,
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

        out = await run_pool(urls, fetch_one, limits=limits, clock=clock, sleeper=sleeper)
        assert len(out) == len(urls)
        assert now >= 2.0 - 1e-9

    asyncio.run(_run())
