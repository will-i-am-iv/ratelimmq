import asyncio

import ratelimmq.fetcher as f


def test_fetch_one_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_blocking(url: str, timeout_s: float):
        calls["n"] += 1
        # fail once with retryable status, then succeed
        if calls["n"] == 1:
            return False, 503, 0, "HTTPError: 503"
        return True, 200, 5, None

    async def fake_to_thread(func, *args):
        return func(*args)

    sleeps = []

    async def fake_sleep(s: float):
        sleeps.append(float(s))

    # Make backoff deterministic: return max delay
    monkeypatch.setattr(f.random, "uniform", lambda a, b: b)
    monkeypatch.setattr(f, "_fetch_blocking", fake_blocking)
    monkeypatch.setattr(f.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(f.asyncio, "sleep", fake_sleep)

    res = asyncio.run(
        f.fetch_one(
            "http://example.com/",
            timeout_s=0.1,
            retries=2,
            backoff_base_s=0.2,
            backoff_cap_s=5.0,
            jitter=True,
        )
    )

    assert res.ok is True
    assert res.status_code == 200
    assert res.attempts == 2
    assert calls["n"] == 2
    # attempt=0 backoff => max_delay=0.2
    assert sleeps == [0.2]


def test_fetch_one_does_not_retry_on_non_retryable_status(monkeypatch):
    calls = {"n": 0}

    def fake_blocking(url: str, timeout_s: float):
        calls["n"] += 1
        return False, 400, 0, "HTTPError: 400"

    async def fake_to_thread(func, *args):
        return func(*args)

    sleeps = []

    async def fake_sleep(s: float):
        sleeps.append(float(s))

    monkeypatch.setattr(f, "_fetch_blocking", fake_blocking)
    monkeypatch.setattr(f.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(f.asyncio, "sleep", fake_sleep)

    res = asyncio.run(
        f.fetch_one(
            "http://example.com/",
            timeout_s=0.1,
            retries=5,  # even with retries, 400 should not retry
        )
    )

    assert res.ok is False
    assert res.status_code == 400
    assert res.attempts == 1
    assert calls["n"] == 1
    assert sleeps == []
