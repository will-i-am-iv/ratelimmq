[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

A minimal line-based TCP server that responds to `PING` with `PONG`, supports a graceful `SHUTDOWN`, and is set up with tests + GitHub Actions CI.  
This repo will evolve into a rate-limited, correctness-tested message queue + benchmark harness.

## Changelog
- 2026-01-09: Docs — documented Week 4 async dispatcher (global + per-host caps) + demo snippet.

---

## Week 4: Async dispatcher (global + per-host caps)

This repo now includes an **async dispatcher** that runs many URL fetches concurrently, while enforcing:
- **global concurrency cap** (max total in-flight requests)
- **per-host concurrency cap** (max in-flight requests per hostname)

Why this matters: it prevents you from spamming one host and demonstrates real-world concurrency control.

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
    results = await run_pool(urls, fetch, limits=limits)
    print("ok:", [r.ok for r in results])
    print("status:", [r.status_code for r in results])
    print("bytes:", [r.bytes_read for r in results])

asyncio.run(main())

---

## Quick verify

A minimal **line-based TCP server** that responds to `PING` with `PONG`, supports a graceful `SHUTDOWN`, and is set up with **tests + GitHub Actions CI**.  
This repo will evolve into a **rate-limited, correctness-tested message queue** + **benchmark harness**.


---

## Technologies used

- Python 3.12
- `asyncio` (TCP server)
- `socket` (client/test connections)
- `pytest` (tests)
- GitHub Actions (CI)

---

## Features

- ✅ TCP server that listens on `127.0.0.1:<PORT>`
- ✅ `PING` → `PONG`
- ✅ `SHUTDOWN` → `BYE` + server stops cleanly
- ✅ Unknown command → `ERR unknown command`
- ✅ Integration tests that spin up the server, exercise commands, and shut it down
- ✅ CI badge stays green when tests pass

---

## What users can do

Connect with `nc` (netcat) and type these commands:

- `PING` (expects `PONG`)
- `SHUTDOWN` (expects `BYE`, then server exits)
- Any other line (expects `ERR unknown command`)

---

## Keyboard shortcuts

While running the server in a terminal:

- `Ctrl + C` = interrupt/stop the server process (manual stop)

In a `nc` client session:

- `Ctrl + C` = exit `nc`

---

## The process

1. Built a minimal TCP server with `asyncio.start_server`
2. Defined a simple, line-based protocol (`PING`, `SHUTDOWN`, default unknown)
3. Added a graceful shutdown mechanism so tests don't hang
4. Wrote integration tests that:
   - start the server as a subprocess on a free port
   - send commands over a socket
   - verify responses
   - confirm clean shutdown + exit code
5. Added a GitHub Actions workflow to run tests on every push/PR

---

## How I built it

- Used `asyncio.StreamReader` / `asyncio.StreamWriter` to read/write newline-delimited messages
- Added a shared `asyncio.Event` so `SHUTDOWN` can stop the server cleanly
- Tests launch the server with env vars (`RATELIMMQ_HOST`, `RATELIMMQ_PORT`)

---

## What I learned

- How to build a simple TCP protocol on top of `asyncio`
- How to reliably test network services (free port selection, subprocess control)
- How to keep CI consistently green by making shutdown deterministic

---

## How it could be improved

Next steps I plan to implement:
- Rate limiting (token bucket / leaky bucket) per client + global
- Message queue semantics: enqueue/dequeue, ack/nack, retries

Next steps I plan to implement:

- Rate limiting (token bucket / leaky bucket) per client + global
- Message queue semantics: enqueue/dequeue + correctness tests

---
