[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

A Python asyncio project evolving from a minimal TCP PING/PONG server into a **high-throughput URL fetcher + rate limiter**.

---

## Technologies

- Python 3.12
- asyncio (async I/O + concurrency)
- socket / netcat (local TCP testing)
- pytest (tests)
- GitHub Actions (CI)
- ThreadPoolExecutor (threads benchmark mode)

---

## Features

### Week 1: Minimal TCP server
- Listens on `127.0.0.1:<PORT>`
- `PING` → `PONG`
- `SHUTDOWN` → `BYE` and server exits cleanly
- Any unknown command → `ERR unknown command`

### Week 3: Rate limiting + safety guards
- Optional token-bucket limiter (enable via env var)
- Always allows `SHUTDOWN` even when rate-limited
- Rejects oversized client lines safely (no hanging/crashing)

### Week 4: Async dispatcher (global + per-host caps)
- Worker pool to process many URL fetches concurrently
- Global concurrency cap (max total in-flight requests)
- Per-host concurrency cap (max in-flight requests per hostname)

### Bench tools
- Compare `seq` vs `threads` vs `asyncio`
- Latency summary (p50 / p95 / p99) + requests/sec

---

## Keyboard shortcuts

While running the server:
- **Ctrl + C** → stop the server process

In a `nc` client session:
- **Ctrl + C** → exit `nc`

---

## The process

### Changelog
- **2026-01-09**: Docs — reorganized README + Week 4 dispatcher demo.
- **2026-01-05**: Server rejects oversized lines cleanly (no crash) + max-line-bytes guard.
- **2026-01-03**: Week 4 — async dispatcher with global + per-host caps.
- **2025-12-31**: Week 3 — token bucket limiter + tests.
- **2025-12-29**: Week 1/2 — TCP protocol + routing stabilized, tests green.

---

## What I learned

- How to structure an asyncio server using `StreamReader` / `StreamWriter`
- How to build deterministic integration tests around network services
- Why “caps” matter: global concurrency + per-host limits prevent overload
- How to debug CI failures and keep tests consistently green
- How to make a server robust (don’t hang/crash on bad input)

---

## How can it be improved

Next commits will build the “real” project target:

- **Backpressure**: bounded queue for producer/worker coordination
- **Per-host rate limiting** (not just per-host concurrency)
- **Retries** with exponential backoff
- **Metrics**: p50/p95/p99 latency, requests/sec, error rates
- **Implementation comparison** writeup:
  - naive sequential
  - threads
  - asyncio
  - “why asyncio wins here + where it doesn’t”

---

## Running the project

### 1) Setup
```bash
cd "/Users/a15106/Desktop/ME/Personal/CAL/Misc/Github Projects/ratelimmq"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip pytest
