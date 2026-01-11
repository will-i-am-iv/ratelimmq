from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional


class _JsonFormatter(logging.Formatter):
    """Basic JSON log formatter using only stdlib."""

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Include extra fields safely (anything not in the standard LogRecord set)
        standard = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process",
        }
        for k, v in record.__dict__.items():
            if k not in standard and not k.startswith("_"):
                base[k] = v

        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)


def configure_logging(
    *,
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> None:
    """
    Configure logging ONCE for the whole process.

    - level: "DEBUG", "INFO", ...
    - fmt: "json" or "plain"
    """
    # If logging is already configured, don't add duplicate handlers.
    root = logging.getLogger()
    if root.handlers:
        return

    level = (level or os.environ.get("RATELIMMQ_LOG_LEVEL", "INFO")).upper()
    fmt = (fmt or os.environ.get("RATELIMMQ_LOG_FORMAT", "json")).lower()

    handler = logging.StreamHandler(sys.stdout)

    if fmt == "plain":
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    else:
        handler.setFormatter(_JsonFormatter())

    root.setLevel(level)
    root.addHandler(handler)
