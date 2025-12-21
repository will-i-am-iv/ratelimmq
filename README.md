[![CI](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml/badge.svg)](https://github.com/will-i-am-iv/ratelimmq/actions/workflows/ci.yml)

# RateLimMQ

Week 1: minimal TCP server that responds to `PING` with `PONG`.

This repo will evolve into a rate-limited, correctness-tested message queue + benchmarking harness.

## Quickstart

### Run the server
```bash
PYTHONPATH=src python3 src/ratelimmq/server.py
