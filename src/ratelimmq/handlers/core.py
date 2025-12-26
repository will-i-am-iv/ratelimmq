cat > src/ratelimmq/handlers/core.py <<'PY'
from __future__ import annotations

from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response, pong, bye, err_unknown

async def ping(ctx: Context, req: Request) -> Response:
    return pong()

async def shutdown(ctx: Context, req: Request) -> Response:
    ctx.stop_event.set()
    return bye()

async def unknown(ctx: Context, req: Request) -> Response:
    return err_unknown()
PY
