[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

A minimal line-based TCP server (Week 1) that responds to `PING` with `PONG`, supports a graceful `SHUTDOWN`, and is set up with tests + GitHub Actions CI.

This repo is evolving into a correctness-tested, rate-limited message queue + benchmark harness.

---

## Technologies used
- Python 3.12
- `asyncio` (TCP server + concurrency)
- `socket` / netcat (client/test connections)
- `pytest` (tests)
- GitHub Actions (CI)

---

## Features
- ✅ TCP server that listens on `127.0.0.1:<PORT>`
- ✅ `PING` → `PONG`
- ✅ `SHUTDOWN` → `BYE` + server stops cleanly
- ✅ Unknown command → `ERR unknown command`
- ✅ Optional rate limiting (token bucket)
- ✅ Oversized line protection (server returns `ERR line too long` without crashing)
- ✅ Async dispatcher (worker pool) with:
  - global concurrency cap
  - per-host concurrency cap
  - optional bounded queue backpressure (`max_queue`)
- ✅ Latency metrics helpers (p50/p95/p99 + rps)
- ✅ Structured JSON logging (optional)

---

## Keyboard shortcuts
While running the server in a terminal:
- `Ctrl + C` → interrupt/stop the server process (manual stop)

In a `nc` client session:
- `Ctrl + C` → exit `nc`

---

## The process
1. Built a minimal TCP server with `asyncio.start_server`
2. Defined a simple, line-based protocol (`PING`, `SHUTDOWN`, default error)
3. Added safe shutdown behavior so tests don’t hang
4. Added correctness tests that start the server on a free port and verify responses
5. Added rate limiting + max-line-length guardrails
6. Built an async dispatcher that demonstrates real-world concurrency control

---

## What I learned
- How to build a simple TCP protocol on top of `asyncio`
- How to test network services reliably (free port selection, readiness polling, subprocess lifecycle)
- How to enforce concurrency limits (global + per-host caps)
- What “backpressure” means and why bounded queues matter
- Why structured logs are useful for async debugging

---

## How it could be improved
Next steps I plan to implement:
- Retry with exponential backoff (network failures)
- Per-host rate limiting (not just per-host concurrency caps)
- Better protocol + response structure (request IDs, structured errors)
- Benchmark harness + writeup: “why asyncio wins here + where it doesn’t”
- Video demo (TODO)

---

## Running the project

### 1) Create + activate a virtual environment
```bash
cd "/Users/a15106/Desktop/ME/Personal/CAL/Misc/Github Projects/ratelimmq"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip pytest


