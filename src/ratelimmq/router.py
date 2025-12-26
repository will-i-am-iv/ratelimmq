from ratelimmq.context import Context
from ratelimmq.protocol import Request
from ratelimmq.handlers.core import ping, shutdown, help_cmd, unknown

ROUTES = {
    "PING": ping,
    "SHUTDOWN": shutdown,
    "HELP": help_cmd,
}

async def dispatch(req: Request, ctx: Context) -> bytes:
    handler = ROUTES.get(req.cmd, unknown)
    return await handler(req, ctx)
