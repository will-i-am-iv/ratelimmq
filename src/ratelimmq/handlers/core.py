from ratelimmq.context import Context
from ratelimmq.protocol import Request, ok, err

async def ping(req: Request, ctx: Context) -> bytes:
    return ok("PONG")

async def shutdown(req: Request, ctx: Context) -> bytes:
    return ok("BYE")

async def help_cmd(req: Request, ctx: Context) -> bytes:
    return ok("commands: PING, SHUTDOWN, HELP")

async def unknown(req: Request, ctx: Context) -> bytes:
    return err("unknown command")
