#!/usr/bin/env bash
set -euo pipefail

# Defaults (override by exporting before running)
export RATELIMMQ_HOST="${RATELIMMQ_HOST:-127.0.0.1}"
export RATELIMMQ_PORT="${RATELIMMQ_PORT:-5555}"

# Optional limiter (Week 3)
export RATELIMMQ_ENABLE_LIMITER="${RATELIMMQ_ENABLE_LIMITER:-0}"
export RATELIMMQ_CAPACITY="${RATELIMMQ_CAPACITY:-5}"
export RATELIMMQ_REFILL_RATE="${RATELIMMQ_REFILL_RATE:-1}"

# Run via module entrypoint (preferred)
PYTHONPATH=src python3 -u -m ratelimmq
