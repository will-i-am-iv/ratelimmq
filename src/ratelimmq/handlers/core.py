from __future__ import annotations

from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response


async def handle_ping(ctx: Context, req: Request) -> Response:
    return Response("PONG\n")


async def handle_shutdown(ctx: Context, req: Request) -> Response:
    ctx.stop_event.set()
    return Response("BYE\n")


async def handle_unknown(ctx: Context, req: Request) -> Response:
    return Response("ERR unknown command\n")
