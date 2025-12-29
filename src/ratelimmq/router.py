from ratelimmq.handlers.core import ping, shutdown, help_cmd, unknown

ROUTES = {
    "PING": ping,
    "SHUTDOWN": shutdown,
    "HELP": help_cmd,
}

async def dispatch(ctx, req):
    cmd = (req.cmd or "").upper()
    handler = ROUTES.get(cmd, unknown)
    return await handler(ctx, req)
