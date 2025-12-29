from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class Context:
    # Used by SHUTDOWN to stop the server cleanly.
    stop_event: asyncio.Event

    # Placeholders for later weeks (cache/queue/limiter)
    cache: Any | None = None
    queue: Any | None = None
    limiter: Any | None = None
