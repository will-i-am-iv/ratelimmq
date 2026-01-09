[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

A Python asyncio project that started as a tiny TCP `PING/PONG` server (Week 1) and is evolving into a **high-throughput URL fetcher + rate limiter** with concurrency controls, backpressure, retries, and latency metrics.

---

## Technologies used

- Python 3.12
- `asyncio` (concurrency + I/O)
- `socket` (TCP tests / netcat usage)
- `pytest` (tests)
- GitHub Actions (CI)

---

## Features

### TCP server (foundation)
- ✅ Line-based TCP server: listens on `127.0.0.1:<PORT>`
- ✅ `PING` → `PONG`
- ✅ `SHUTDOWN` → `BYE` + clean stop
- ✅ Unknown command → `ERR unknown command`
- ✅ Integration tests that spin up the server, send commands, confirm clean shutdown

### Reliability guards
- ✅ Optional rate limiter hook (token bucket)
- ✅ Max-line-bytes guard (reject oversized lines without crashing/hanging)

### URL concurrency primitives
- ✅ Async dispatcher / worker pool with:
  - global concurrency cap (max total in-flight)
  - per-host concurrency cap (max in-flight per hostname)

---

## Keyboard shortcuts

While running the server in a terminal:
- `Ctrl + C` = stop the server process

In a `nc` (netcat) client session:
- `Ctrl + C` = exit `nc`

---

## The process

Milestones so far:
- Week 1: build + test a minimal asyncio TCP protocol server
- Week 3: add safety guards + optional limiter plumbing
- Week 4: add async dispatcher (global + per-host caps)
- (Next) build the URL fetcher pipeline + backpressure + retries + metrics writeup

---

## What I learned

- How asyncio servers read/write newline-delimited protocols (`StreamReader` / `StreamWriter`)
- How to make server shutdown deterministic so CI doesn’t hang
- Why “concurrency control” matters (global caps + per-host caps prevent overload)
- How to write tests that safely start subprocess servers and verify behavior

---

## How can it be improved

Next steps planned (the “high-throughput URL fetcher + rate limiter” roadmap):
- Bounded queue backpressure (don’t accept infinite work)
- Async URL fetching worker pool (async I/O)
- Per-host rate limiting + global concurrency cap (together)
- Retries with exponential backoff + jitter
- Metrics: p50/p95/p99 latency + requests/sec
- Compare implementations:
  - naive sequential
  - threads
  - asyncio
- Writeup: **“Why asyncio wins here + where it doesn’t”**

---

## Running the project

### Quick verify (tests)
```bash
PYTHONPATH=src python3 -m pytest -q

