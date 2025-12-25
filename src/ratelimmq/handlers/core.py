from __future__ import annotations
from ratelimmq.context import Context
from ratelimmq.protocol import Request, Response, resp_err

async def handle_ping(ctx: Context, req: Request) -> Response:
    return Response("PONG\n")

async def handle_shutdown(ctx: Context, req: Request) -> Response:
    # Tell client BYE, then stop server.
    ctx.stop_event.set()
    return Response("BYE\n")

async def handle_help(ctx: Context, req: Request) -> Response:
    return Response(
        "OK commands: PING, SHUTDOWN, HELP\n"
    )

async def handle_unknown(ctx: Context, req: Request) -> Response:
    return resp_err("unknown command")
