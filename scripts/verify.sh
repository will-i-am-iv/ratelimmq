#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "Running syntax check (py_compile)..."
git ls-files '*.py' | xargs python3 -m py_compile

echo "Running tests..."
python3 -m pytest -q

echo "OK ✅"
