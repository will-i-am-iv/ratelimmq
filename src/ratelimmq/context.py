from dataclasses import dataclass

@dataclass
class Context:
    # placeholders for later weeks (cache/queue/limiter)
    cache: object | None = None
    queue: object | None = None
    limiter: object | None = None
