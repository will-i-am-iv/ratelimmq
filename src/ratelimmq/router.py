from __future__ import annotations

from typing import Awaitable, Callable

from ratelimmq.context import Context
from ratelimmq.handlers.core import handle_ping, handle_shutdown, handle_unknown
from ratelimmq.protocol import Request, Response

Handler = Callable[[Context, Request], Awaitable[Response]]

ROUTES: dict[str, Handler] = {
    "PING": handle_ping,
    "SHUTDOWN": handle_shutdown,
}


async def dispatch(ctx: Context, req: Request) -> Response:
    handler = ROUTES.get(req.cmd, handle_unknown)
    return await handler(ctx, req)
