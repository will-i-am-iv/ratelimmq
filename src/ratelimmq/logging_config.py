from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict


def _json_formatter(record: logging.LogRecord) -> str:
    payload: Dict[str, Any] = {
        "level": record.levelname,
        "logger": record.name,
        "msg": record.getMessage(),
    }

    # Attach extra structured fields if provided
    extra = getattr(record, "extra", None)
    if isinstance(extra, dict):
        payload.update(extra)

    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _json_formatter(record)


def setup_logging() -> None:
    """
    Default: normal human-readable logs.
    If RATELIMMQ_LOG_JSON=1, output JSON lines.
    If RATELIMMQ_LOG_LEVEL is set (e.g. INFO/DEBUG), uses that.
    """
    level_str = os.environ.get("RATELIMMQ_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)

    if os.environ.get("RATELIMMQ_LOG_JSON", "0") == "1":
        handler.setFormatter(JsonLineFormatter())
    else:
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))

    root.addHandler(handler)
