from __future__ import annotations

import asyncio
import os
import signal

from ratelimmq.context import Context
from ratelimmq.protocol import parse_line
from ratelimmq.router import dispatch

RATE_LIMIT_ERR = "ERR rate limited\n"


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    ctx: Context,
) -> None:
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break  # client closed

            line = raw.decode("utf-8", errors="replace")
            req = parse_line(line)

            # Week 3: optional limiter (disabled unless RATELIMMQ_ENABLE_LIMITER=1)
            if ctx.limiter is not None and req.cmd != "SHUTDOWN" and not ctx.limiter.allow():
                writer.write(RATE_LIMIT_ERR.encode("utf-8"))
                await writer.drain()
                continue

            resp = await dispatch(ctx, req)

            writer.write(resp.line.encode("utf-8"))
            await writer.drain()

            if ctx.stop_event.is_set():
                break
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main() -> None:
    host = os.environ.get("RATELIMMQ_HOST", "127.0.0.1")
    port = int(os.environ.get("RATELIMMQ_PORT", "5555"))

    stop_event = asyncio.Event()
    ctx = Context(stop_event=stop_event)

    # Enable limiter only when explicitly requested
    if os.environ.get("RATELIMMQ_ENABLE_LIMITER", "0") == "1":
        from ratelimmq.limiter import TokenBucket

        capacity = float(os.environ.get("RATELIMMQ_CAPACITY", "5"))
        refill_rate = float(os.environ.get("RATELIMMQ_REFILL_RATE", "1"))
        ctx.limiter = TokenBucket(capacity=capacity, refill_rate=refill_rate)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, ctx),
        host,
        port,
    )

    addrs = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    print(f"listening on {addrs}", flush=True)

    async with server:
        await stop_event.wait()
        server.close()
        await server.wait_closed()

    print("shutdown complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
