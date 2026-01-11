from __future__ import annotations

import asyncio
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from ratelimmq.logging_utils import get_logger, log_event

log = get_logger("ratelimmq.fetcher")


@dataclass(frozen=True)
class FetchResult:
    # REQUIRED (no defaults)
    url: str
    ok: bool
    status_code: Optional[int]
    bytes_read: int
    elapsed_ms: float
    # OPTIONAL (defaults last)
    error: Optional[str] = None

    # Backward-compatibility aliases
    @property
    def status(self) -> Optional[int]:
        return self.status_code

    @property
    def bytes(self) -> int:
        return self.bytes_read


def _fetch_blocking(url: str, timeout_s: float) -> tuple[bool, Optional[int], int, Optional[str]]:
    """Run a blocking HTTP GET using urllib, wrapped by asyncio.to_thread."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ratelimmq/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status_code = getattr(resp
