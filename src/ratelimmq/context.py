cat > src/ratelimmq/context.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
import asyncio
from typing import Any

@dataclass
class Context:
    # Used to shut down the server gracefully (Week 1+2)
    stop_event: asyncio.Event

    # Placeholders for later weeks (cache/queue/limiter)
    cache: Any | None = None
    queue: Any | None = None
    limiter: Any | None = None
PY
