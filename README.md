[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ
---

_Last updated: 2025-12-29_

### Quick verify
```bash
PYTHONPATH=src python3 -m pytest -q
A minimal **line-based TCP server** (Week 1) that responds to `PING` with `PONG`, supports a graceful `SHUTDOWN`, and is set up with **tests + GitHub Actions CI**.  
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
- `Ctrl + C` → interrupt/stop the server process (manual stop)
- In a `nc` client session:
  - `Ctrl + C` → exit `nc`

---

## The process
1. Built a minimal TCP server with `asyncio.start_server`
2. Defined a simple, line-based protocol (`PING`, `SHUTDOWN`, default error)
3. Added a graceful shutdown mechanism so tests don’t hang
4. Wrote integration tests that:
   - start the server as a subprocess on a free port
   - send commands over a socket
   - verify responses
   - confirm clean shutdown + exit code
5. Added GitHub Actions workflow to run tests on every push/PR

---

## How I built it
- Used `asyncio.StreamReader/StreamWriter` to read/write newline-delimited messages
- Added a shared `asyncio.Event` (or equivalent) so `SHUTDOWN` can signal the server to close
- Tests launch the server with env vars (`RATELIMMQ_HOST`, `RATELIMMQ_PORT`) and poll until it’s listening

---

## What I learned
- How to build a simple TCP protocol on top of `asyncio`
- How to reliably test network services (free port selection, readiness polling, subprocess lifecycle)
- How to keep CI consistently green by making shutdown deterministic

---

## How it could be improved
Next steps I plan to implement:
- Rate limiting (token bucket / leaky bucket) per client + global
- Message queue semantics: enqueue/dequeue, ack/nack, retries
- Backpressure + bounded queues
- Better protocol design (request IDs, structured responses, error codes)
- Benchmark harness (throughput, p50/p95/p99 latency) + charts

---

## How to run the project

### 1) Create + activate a virtual environment
```bash
cd ~/Desktop/ratelimmq
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip pytest
