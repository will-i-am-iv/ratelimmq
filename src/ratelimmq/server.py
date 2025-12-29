import asyncio
import os
import signal

from ratelimmq.context import Context
from ratelimmq.protocol import parse_line
from ratelimmq.router import dispatch


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ctx: Context):
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break

            req = parse_line(raw)
            raw = await reader.readline()
            if not raw:
                break  # client closed

            line = raw.decode("utf-8", errors="replace")
            req = parse_line(line)

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


async def main():
    host = os.environ.get("RATELIMMQ_HOST", "127.0.0.1")
    port = int(os.environ.get("RATELIMMQ_PORT", "5555"))

    stop_event = asyncio.Event()
    ctx = Context(stop_event=stop_event)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    server = await asyncio.start_server(lambda r, w: handle_client(r, w, ctx), host, port)
    addrs = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    print(f"listening on {addrs}", flush=True)

    async with server:
        await stop_event.wait()
        server.close()
        await server.wait_closed()

    print("shutdown complete", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
