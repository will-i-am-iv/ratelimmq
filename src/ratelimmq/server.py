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
    """
    One TCP client session:
      - Read one newline-terminated line at a time
      - Reject oversized lines with a clean ERR response
      - Optionally enforce rate limiting (but always allow SHUTDOWN)
    """
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break  # client closed

            # Oversized line guard (bytes, includes newline)
            if len(raw) > max_line_bytes:
                writer.write(LINE_TOO_LONG_ERR.encode("utf-8"))
                await writer.drain()
                continue

            line = raw.decode("utf-8", errors="replace")
            req = parse_line(line)

            # Optional limiter: allow SHUTDOWN even when limited
            cmd = (getattr(req, "cmd", "") or "").upper()
            if ctx.limiter is not None and cmd != "SHUTDOWN" and not ctx.limiter.allow():
                writer.write(RATE_LIMIT_ERR.encode("utf-8"))
                await writer.drain()
                continue

            resp = await dispatch(ctx, req)
            writer.write(resp.line.encode("utf-8"))
            await writer.drain()

            if ctx.stop_event.is_set():
                break

    except Exception:
        # If something unexpected happens, avoid hanging the client:
        # close the connection cleanly.
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        raise

    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main() -> None:
    host = os.environ.get("RATELIMMQ_HOST", "127.0.0.1")
    port = int(os.environ.get("RATELIMMQ_PORT", "5555"))

    # Max line length (bytes). Keep minimum sane.
    max_line_bytes = int(os.environ.get("RATELIMMQ_MAX_LINE_BYTES", "4096"))
    if max_line_bytes < 32:
        max_line_bytes = 32

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

    # IMPORTANT: do NOT pass asyncio's `limit=` here.
    # We enforce max bytes ourselves above.
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, ctx, max_line_bytes),
        host,
        port,
    )

    addrs = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    print(f"listening on {addrs}", flush=True)

    async with server:
        await stop_event.wait()

    print("shutdown complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
