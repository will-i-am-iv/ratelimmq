[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

## Technologies used
- Python 3.12
- asyncio
- pytest
- GitHub Actions CI

## Features
- TCP server protocol: `PING → PONG`, `SHUTDOWN → BYE`, unknown → error
- Global + per-host concurrency caps (dispatcher)
- Bounded queue backpressure (`max_queue`)
- Per-host token bucket rate limiting (`per_host_rps`, `per_host_burst`)
- Retries with exponential backoff + jitter (fetcher)
- JSON structured logging + latency summary (p50/p95/p99 + rps)

## Keyboard shortcuts
- `Ctrl + C` to stop the server or any running script in terminal
- `Ctrl + C` to exit `nc`

## The process
- Week 1: minimal TCP server + tests
- Week 3: limiter plumbing + safety guards (max line bytes)
- Week 4+: dispatcher + fetcher reliability + observability

## What I learned
- Concurrency control is not optional (caps prevent overload)
- Backpressure prevents unbounded memory growth
- Rate limiting controls *pace*; concurrency caps control *in-flight*
- Retries need backoff + jitter to avoid retry storms

## How can it be improved
- Switch to true async HTTP client (aiohttp) for full async sockets
- Add benchmark charts / markdown writeup with comparisons
- Optional caching (TTL/LRU) on the fetcher path

## Running the project
### Tests
```bash
PYTHONPATH=src python3 -m pytest -q
