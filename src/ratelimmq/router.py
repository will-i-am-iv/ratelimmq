from __future__ import annotations

from typing import Awaitable, Callable

from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response
from ratelimmq.handlers.core import ping, shutdown, help_cmd, unknown

Handler = Callable[[Context, Request], Awaitable[Response]]

ROUTES: dict[str, Handler] = {
    "PING": ping,
    "SHUTDOWN": shutdown,
    "HELP": help_cmd,
}


async def dispatch(ctx: Context, req: Request) -> Response:
    handler = ROUTES.get(req.cmd, unknown)
    return await handler(ctx, req)
