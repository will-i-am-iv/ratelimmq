"""
Lightweight structured logging utilities for RateLimMQ.
No external dependencies. Uses JSON for log output.
"""

from __future__ import annotations
import json
import sys
import time
from typing import Any, Dict, Optional


def _ts_iso() -> str:
    """Return UTC timestamp in ISO 8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(event: str, **fields: Any) -> None:
    """
    Print a structured JSON log line to stdout.
    - event: name of the event (string)
    - **fields: any additional structured data (url, latency, etc.)
    """
    record: Dict[str, Any] = {
        "timestamp": _ts_iso(),
        "event": event,
    }
    record.update(fields)

    try:
        line = json.dumps(record, separators=(",", ":"))
    except Exception as e:
        # fallback to plain text if serialization fails
        line = f'{{"timestamp":"{_ts_iso()}","event":"error","error":"{e}"}}'

    print(line, file=sys.stdout, flush=True)


def log_fetch_result(
    url: str,
    status_code: Optional[int],
    bytes_read: int,
    elapsed_s: float,
    outcome: str,
) -> None:
    """
    Log a single HTTP fetch result.
    """
    log_event(
        "fetch_complete",
        url=url,
        status_code=status_code,
        bytes_read=bytes_read,
        elapsed_ms=elapsed_s * 1000.0,
        outcome=outcome,
    )


# Example usage:
# log_fetch_result("http://example.com", 200, 5123, 0.152, "success")
