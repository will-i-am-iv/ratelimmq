from __future__ import annotations
from typing import Awaitable, Callable, Dict

from ratelimmq.context import Context
from ratelimmq.protocol import Request
from ratelimmq.handlers.core import (
    handle_ping,
    handle_shutdown,
    handle_help,
    handle_unknown,
)

Handler = Callable[[Context, Request], Awaitable]

COMMANDS: Dict[str, Handler] = {
    "PING": handle_ping,
    "SHUTDOWN": handle_shutdown,
    "HELP": handle_help,
}

async def dispatch(ctx: Context, req: Request):
    # Empty line → error (or ignore; your choice)
    if not req.cmd:
        return await handle_unknown(ctx, req)

    handler = COMMANDS.get(req.cmd, handle_unknown)
    return await handler(ctx, req)
