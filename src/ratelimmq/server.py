from __future__ import annotations

import asyncio
import os
import signal

from ratelimmq.context import Context
from ratelimmq.protocol import parse_line
from ratelimmq.router import dispatch

RATE_LIMIT_ERR = "ERR rate limited\n"
LINE_TOO_LONG_ERR = "ERR line too long\n"


async def _drain_to_newline(reader: asyncio.StreamReader) -> None:
    """
    Best-effort: discard bytes until we see a newline or EOF.
    This prevents oversized lines from poisoning the next command.
    """
    while True:
        chunk = await reader.read(1024)
        if not chunk:
            return
        if b"\n" in chunk:
            return


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    ctx: Context,
    max_line_bytes: int,
) -> None:
    try:
        while True:
            try:
                raw = await reader.readline()
            except (asyncio.LimitOverrunError, ValueError):
                # Client sent a line longer than the StreamReader can buffer.
                # Drain to newline, respond with a clean error, keep server alive.
                await _drain_to_newline(reader)
                writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                await writer.drain()
                continue

            if not raw:
                break  # client closed

            # Enforce our own max line size (excluding the trailing newline)
            payload = raw[:-1] if raw.endswith(b"\n") else raw
            if len(payload) > max_line_bytes:
                writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                await writer.drain()
                continue

            line = raw.decode("utf-8", errors="replace")
            req = parse_line(line)

            # Week 3: optional limiter (only enabled when RATELIMMQ_ENABLE_LIMITER=1)
            # Keep SHUTDOWN always allowed (so you can always stop the server).
            if ctx.limiter is not None and req.cmd.upper() != "SHUTDOWN":
                if not ctx.limiter.allow():
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

    # Max line length (bytes, excluding newline). Clamp to keep it reasonable.
    max_line_bytes = int(os.environ.get("RATELIMMQ_MAX_LINE_BYTES", "4096"))
    if max_line_bytes < 32:
        max_line_bytes = 32

    stop_event = asyncio.Event()
    ctx = Context(stop_event=stop_event)

    # Optional limiter
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
