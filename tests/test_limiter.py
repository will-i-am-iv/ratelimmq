from ratelimmq.limiter import TokenBucket


def test_token_bucket_capacity_consumption():
    b = TokenBucket(capacity=3, refill_rate=0)
    assert b.allow(now=0.0)
    assert b.allow(now=0.0)
    assert b.allow(now=0.0)
    assert not b.allow(now=0.0)


def test_token_bucket_refill_allows_later():
    b = TokenBucket(capacity=2, refill_rate=1)  # 1 token/sec
    assert b.allow(now=0.0)
    assert b.allow(now=0.0)
    assert not b.allow(now=0.0)

    # after 1 second, should have refilled 1 token
    assert b.allow(now=1.0)
    assert not b.allow(now=1.0)


def test_token_bucket_refill_caps_at_capacity():
    b = TokenBucket(capacity=2, refill_rate=10)
    assert b.allow(now=0.0)
    assert b.allow(now=0.0)
    assert not b.allow(now=0.0)

    # after a lot of time, should cap at capacity=2 (not exceed)
    assert b.allow(now=100.0)
    assert b.allow(now=100.0)
    assert not b.allow(now=100.0)
