from __future__ import annotations

import asyncio
import os
import signal

from ratelimmq.context import Context
from ratelimmq.protocol import parse_line
from ratelimmq.router import dispatch

RATE_LIMIT_ERR = "ERR rate limited\n"
LINE_TOO_LONG_ERR = "ERR line too long\n"


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    ctx: Context,
    max_line_bytes: int,
) -> None:
    async def drain_until_newline() -> None:
        """
        If a client sends an oversized line, asyncio can raise exceptions,
        but the oversized bytes may still be buffered. Drain until newline
        so the next command starts cleanly.
        """
        while True:
            chunk = await reader.read(1024)
            if not chunk:
                return
            if b"\n" in chunk:
                return

    try:
        while True:
            try:
                raw = await reader.readline()
            except asyncio.LimitOverrunError:
                await drain_until_newline()
                writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                await writer.drain()
                continue
            except ValueError as e:
                # asyncio may raise ValueError: "Separator is found, but chunk is longer than limit"
                if "chunk is longer than limit" in str(e):
                    await drain_until_newline()
                    writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                    await writer.drain()
                    continue
                raise

            if not raw:
                break  # client closed

            if len(raw) > max_line_bytes + 1:
                writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                await writer.drain()
                continue

            line = raw.decode("utf-8", errors="replace")
            req = parse_line(line)

            # If limiter is enabled, allow SHUTDOWN even when limited so tests/users can stop the server
            if ctx.limiter is not None and not ctx.limiter.allow():
                if getattr(req, "cmd", "").upper() != "SHUTDOWN":
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

    max_line_bytes = int(os.environ.get("RATELIMMQ_MAX_LINE_BYTES", "4096"))
    if max_line_bytes < 32:
        max_line_bytes = 32  # keep reasonable

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
        lambda r, w: handle_client(r, w, ctx, max_line_bytes),
        host,
        port,
        # internal StreamReader limit for readline()/readuntil()
        limit=max_line_bytes + 1,
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
