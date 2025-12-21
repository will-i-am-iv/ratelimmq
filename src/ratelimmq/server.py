import asyncio
import os
import signal

# Simple line-based TCP protocol:
#   PING      -> PONG
#   SHUTDOWN  -> BYE (and stops server)
#   anything else -> ERR unknown command

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, stop_event: asyncio.Event):
    try:
        while True:
            data = await reader.readline()
            if not data:
                break  # client closed
            line = data.decode("utf-8", errors="replace").strip()

            if line == "PING":
                writer.write(b"PONG\n")
                await writer.drain()
            elif line == "SHUTDOWN":
                writer.write(b"BYE\n")
                await writer.drain()
                stop_event.set()
                break
            else:
                writer.write(b"ERR unknown command\n")
                await writer.drain()
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

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Some platforms don't support signal handlers in asyncio (not an issue for macOS/Linux CI).
            pass

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, stop_event),
        host,
        port,
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"listening on {addrs}")

    async with server:
        await stop_event.wait()
        server.close()
        await server.wait_closed()
    print("shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
