from __future__ import annotations
from dataclasses import dataclass
import asyncio

@dataclass
class Context:
    stop_event: asyncio.Event
    # Week 3–6: add cache fields here (dict, ttl index, lru structure)
    # Week 3–6: add queue fields here (pending jobs, inflight, locks)
    # Week 7:   add rate limiter object here
    # Week 9+:  add metrics collector here
