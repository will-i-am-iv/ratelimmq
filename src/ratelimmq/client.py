from ratelimmq.fetcher import fetch_one, FetchResult

async def fetch_all(
    urls: Iterable[str],
    *,
    limits: PoolLimits = PoolLimits(),
    timeout_s: float = 10.0,
) -> List[FetchResult]:
    async def _one(u: str) -> FetchResult:
        return await fetch_one(u, timeout_s=timeout_s)

    return await run_pool(urls, _one, limits=limits)
