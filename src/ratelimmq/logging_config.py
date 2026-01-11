from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict


_DEFAULT_LEVEL = "INFO"
_DEFAULT_FORMAT = "text"  # or "json"

# LogRecord has a lot of built-in attributes; we don't want to dump all of them.
_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Include "extra=" fields cleanly
        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        if extras:
            base.update(extras)

        # Include exception info if present
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()

        extras = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        if extras:
            # render extras as key=value
            extra_str = " ".join(f"{k}={extras[k]!r}" for k in sorted(extras))
            msg = f"{msg} {extra_str}"

        if record.exc_info:
            msg = f"{msg}\n{self.formatException(record.exc_info)}"

        return msg


def setup_logging() -> None:
    """
    Configure logging based on env vars:
      - RATELIMMQ_LOG_LEVEL: DEBUG/INFO/WARNING/ERROR (default INFO)
      - RATELIMMQ_LOG_FORMAT: text/json (default text)

    This is safe for CI (stdlib only).
    """
    level_str = os.environ.get("RATELIMMQ_LOG_LEVEL", _DEFAULT_LEVEL).upper()
    fmt = os.environ.get("RATELIMMQ_LOG_FORMAT", _DEFAULT_FORMAT).lower()

    level = getattr(logging, level_str, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_TextFormatter())

    root = logging.getLogger()
    root.setLevel(level)

    # Replace handlers so reruns don't double-log
    root.handlers = [handler]


# Backwards-compatible aliases (if other files used a different name earlier)
configure_logging = setup_logging
init_logging = setup_logging
