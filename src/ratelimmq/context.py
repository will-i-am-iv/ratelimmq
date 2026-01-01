from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from ratelimmq.limiter import TokenBucket


@dataclass
class Context:
    stop_event: asyncio.Event
    cache: Any | None = None
    queue: Any | None = None
    limiter: TokenBucket | None = None
