#!/usr/bin/env bash
set -euo pipefail

# Defaults (can be overridden by env vars)
HOST="${RATELIMMQ_HOST:-127.0.0.1}"
PORT="${RATELIMMQ_PORT:-5555}"

# Week 3 limiter knobs (optional)
ENABLE_LIMITER="${RATELIMMQ_ENABLE_LIMITER:-0}"
CAPACITY="${RATELIMMQ_CAPACITY:-5}"
REFILL_RATE="${RATELIMMQ_REFILL_RATE:-1}"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="${PYTHONPATH:-src}"
export RATELIMMQ_HOST="$HOST"
export RATELIMMQ_PORT="$PORT"
export RATELIMMQ_ENABLE_LIMITER="$ENABLE_LIMITER"
export RATELIMMQ_CAPACITY="$CAPACITY"
export RATELIMMQ_REFILL_RATE="$REFILL_RATE"

echo "Starting ratelimmq on ${HOST}:${PORT}"
echo "Limiter: enabled=${ENABLE_LIMITER} capacity=${CAPACITY} refill_rate=${REFILL_RATE}"
echo
echo "Tip: connect with: nc ${HOST} ${PORT}"
echo

python3 -u src/ratelimmq/server.py
