from __future__ import annotations

from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response, pong, bye, err_unknown


async def ping(ctx: Context, req: Request) -> Response:
    return pong()


async def shutdown(ctx: Context, req: Request) -> Response:
    ctx.stop_event.set()
    return bye()


async def help_cmd(ctx: Context, req: Request) -> Response:
    # Not required by the Week 1 tests, but kept for completeness.
    return Response("OK\n")


async def unknown(ctx: Context, req: Request) -> Response:
    return err_unknown()
