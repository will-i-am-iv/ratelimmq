from __future__ import annotations

from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response


async def ping(ctx: Context, req: Request) -> Response:
    return Response("PONG\n")


async def shutdown(ctx: Context, req: Request) -> Response:
    ctx.stop_event.set()
    return Response("BYE\n")


async def help_cmd(ctx: Context, req: Request) -> Response:
    return Response("OK commands: PING SHUTDOWN HELP\n")


async def unknown(ctx: Context, req: Request) -> Response:
    return Response("ERR unknown command\n")
