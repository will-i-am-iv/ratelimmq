[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

A minimal asyncio TCP server (Week 1) that responds to:

- `PING` → `PONG`
- `SHUTDOWN` → `BYE` (server exits cleanly)
- unknown command → `ERR unknown command`

This repo is evolving into a **correctness-tested, rate-limited, high-throughput URL fetcher + benchmark harness** to prove:

- concurrency + async I/O
- backpressure
- per-host throttling + global caps
- retries + latency metrics (p50/p95/p99, rps)

---

## Changelog

- **2026-01-09:** Docs — Week 4 async dispatcher (global + per-host caps) + demo snippet (formatted).
- **2026-01-05:** Server rejects oversized lines cleanly (no crash) + max-line-bytes guard.
- **2026-01-03:** Week 4 — worker pool with global + per-host concurrency caps (dispatcher).
- **2025-12-31:** Week 3 — token bucket limiter + tests.

---

## Quick verify

```bash
PYTHONPATH=src python3 -m pytest -q
```

---

## Run locally (Week 1 TCP server)

### Terminal 1 — start the server
```bash
PYTHONPATH=src RATELIMMQ_HOST=127.0.0.1 RATELIMMQ_PORT=5555 python3 -u src/ratelimmq/server.py
```

You should see something like:
- `listening on ('127.0.0.1', 5555)`

### Terminal 2 — talk to it (netcat)
```bash
printf "PING\n" | nc 127.0.0.1 5555
printf "SHUTDOWN\n" | nc 127.0.0.1 5555
```

Expected:
- `PONG`
- `BYE`

---

## Week 4: Async dispatcher (global + per-host caps)

The dispatcher runs many URL fetches concurrently while enforcing:

- **global concurrency cap** (max total in-flight requests)
- **per-host concurrency cap** (max in-flight per hostname)

Why this matters:
- It prevents you from accidentally **spamming one host**
- It models real-world systems where you must respect host limits and keep overall concurrency stable

### Dispatcher quick demo (runs locally)

PYTHONPATH=src python3 - <<'PY'
import asyncio
from ratelimmq.fetcher import fetch_one
from ratelimmq.dispatcher import run_pool, PoolLimits

urls = [
    "http://example.com/",
    "http://example.com/",
    "http://example.com/",
]

async def fetch(u: str):
    return await fetch_one(u, timeout_s=3.0)

async def main():
    limits = PoolLimits(total_concurrency=10, per_host_concurrency=2)
    results = await run_pool(urls, fetch_one=fetch, limits=limits)
    print("ok:", [r.ok for r in results])
    print("status:", [r.status_code for r in results])
    print("bytes:", [r.bytes_read for r in results])

asyncio.run(main())
PY
```

---

## Safety: max line length guard (server)

The server rejects oversized input lines so a client can’t blow up memory or crash the process.

- If a line is too long → server responds with `ERR line too long`
- Server stays alive and still supports `SHUTDOWN`

Optional env var:
- `RATELIMMQ_MAX_LINE_BYTES` (default: 4096; minimum enforced: 32)

Example:
```bash
PYTHONPATH=src RATELIMMQ_MAX_LINE_BYTES=64 python3 -u src/ratelimmq/server.py
```

---

## Week 3: Token bucket rate limiter (optional)

The server can optionally enforce a token bucket limiter. It is enabled only when requested.

Env vars:
- `RATELIMMQ_ENABLE_LIMITER=1` (enable)
- `RATELIMMQ_CAPACITY=5`
- `RATELIMMQ_REFILL_RATE=1`

Example:
```bash
PYTHONPATH=src RATELIMMQ_ENABLE_LIMITER=1 RATELIMMQ_CAPACITY=5 RATELIMMQ_REFILL_RATE=1 python3 -u src/ratelimmq/server.py
```

---

## Scripts

If present in your repo:

### Verify helper
Runs py_compile + pytest in one go:
```bash
./scripts/verify.sh
```

### Run helper
Starts the server with common env vars:
```bash
./scripts/run_local.sh
```

---

## Roadmap (next milestones)

**High-throughput URL fetcher + rate limiter (asyncio)**

Build:
- async worker pool
- per-host rate limiting + global concurrency cap
- bounded queue backpressure (so producers can’t overwhelm consumers)
- retry with exponential backoff
- metrics: p50/p95/p99 latency + requests/sec
- compare implementations:
  - naive sequential
  - threads
  - asyncio

Writeup target:
- “Why asyncio wins here + where it doesn’t”
