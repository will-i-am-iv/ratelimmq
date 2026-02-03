[![CI](.github/badges/ci.svg)](.github/workflows/ci.yml)

# RateLimMQ

A correctness-tested async “systems kata” in Python: start from a minimal TCP protocol, then evolve into a rate-limited dispatcher + fetcher with backpressure, retries, and latency metrics.

**Core idea:** *rate limiting controls pace; concurrency caps control in-flight; backpressure prevents memory blowups.*

---

## What’s in here

- **TCP server protocol (Week 1)**: `PING → PONG`, `SHUTDOWN → BYE`, unknown → error
- **Dispatcher**: global + per-host concurrency caps + bounded queue backpressure (`max_queue`)
- **Rate limiting**: per-host token bucket (`per_host_rps`, `per_host_burst`)
- **Fetcher reliability**: retries with exponential backoff + jitter
- **Observability**: JSON structured logging + one-line latency summary (p50/p95/p99 + rps)

---

## Technologies used

- Python 3.12
- `asyncio`
- `pytest`
- GitHub Actions CI

---

## Quick start

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt  # if you have it
# or at minimum:
python3 -m pip install -U pytest
```

### Tests
```bash
PYTHONPATH=src python3 -m pytest -q
```

---

## Run locally: TCP server demo (Week 1)

### Terminal 1 — start the server
```bash
PYTHONPATH=src RATELIMMQ_HOST=127.0.0.1 RATELIMMQ_PORT=5555 \
  python3 -u src/ratelimmq/server.py
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

## Dispatcher demo (bounded queue + per-host caps + per-host rate limit)

This demo runs the dispatcher against a URL list and prints a one-line summary (rps + p50/p95/p99).

### 1) Create a URL list
Use the included example file:
```bash
cp urls.example.txt urls.txt
```

Or make your own:
```bash
cat > urls.txt << 'EOF'
http://example.com/
http://example.com/
http://example.com/
EOF
```

### 2) Run the dispatcher demo

Run the provided script with environment variables to control concurrency and rate limits:

```bash
PYTHONPATH=src \
RATELIMMQ_GLOBAL_CONCURRENCY=50 \
RATELIMMQ_PER_HOST_CONCURRENCY=10 \
RATELIMMQ_MAX_QUEUE=200 \
RATELIMMQ_PER_HOST_RPS=5 \
RATELIMMQ_PER_HOST_BURST=10 \
python3 -u scripts/demo_dispatcher_logging.py urls.txt
```

### Expected output (example)
You’re looking for a **single summary line** like:
- `rps=12.4 p50=83ms p95=210ms p99=330ms`
or JSON like:
- `{"rps":12.4,"p50_ms":83,"p95_ms":210,"p99_ms":330}`

### What to try (quick experiments)
- **Backpressure:** set `RATELIMMQ_MAX_QUEUE=10` and watch throughput cap sooner (less buffering).
- **Per-host cap:** set `RATELIMMQ_PER_HOST_CONCURRENCY=1` and watch latency climb.
- **Rate limit:** set `RATELIMMQ_PER_HOST_RPS=1` and confirm rps flattens near 1×hosts.

---

## Configuration (env vars)

These are the knobs you’ll use most when demoing:

| Env var | Meaning | Typical |
|---|---|---|
| `RATELIMMQ_HOST` / `RATELIMMQ_PORT` | TCP server bind address | `127.0.0.1` / `5555` |
| `RATELIMMQ_GLOBAL_CONCURRENCY` | total in-flight requests across all hosts | `20–200` |
| `RATELIMMQ_PER_HOST_CONCURRENCY` | max in-flight per host | `2–20` |
| `RATELIMMQ_MAX_QUEUE` | bounded queue size (backpressure) | `50–500` |
| `RATELIMMQ_PER_HOST_RPS` | token bucket refill rate per host | `1–20` |
| `RATELIMMQ_PER_HOST_BURST` | token bucket burst per host | `1–50` |
| `RATELIMMQ_RETRIES` | retry attempts for fetch failures | `2–5` |
| `RATELIMMQ_BACKOFF_BASE_MS` | base backoff in ms | `50–200` |
| `RATELIMMQ_BACKOFF_MAX_MS` | max backoff cap in ms | `500–5000` |
| `RATELIMMQ_LOG_JSON` | structured logs (`1` to enable) | `0/1` |

---

## The process

- **Week 1:** minimal TCP server + tests
- **Week 3:** limiter plumbing + safety guards (max line bytes)
- **Week 4+:** dispatcher + fetcher reliability + observability

---

## What I learned

- Concurrency control is not optional (caps prevent overload)
- Backpressure prevents unbounded memory growth
- Rate limiting controls pace; concurrency caps control in-flight
- Retries need backoff + jitter to avoid retry storms

---

## Video demo (add this when ready)

### Option A: YouTube (simplest)
Add a link:
```md
**Demo:** https://youtu.be/XXXX
```

### Option B: attach a video to GitHub and embed
1) Upload an `.mp4` in a GitHub Issue comment (or PR comment)
2) Copy the generated `https://user-images...mp4` URL and paste it here.

---

## How it can be improved

- Switch to a true async HTTP client (`aiohttp`) for fully async sockets
- Add benchmark charts / writeup with comparisons
- Optional caching (TTL/LRU) on the fetcher path

