import asyncio

HOST = "127.0.0.1"
PORT = 5555

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr = writer.get_extra_info("peername")
    print(f"Client connected: {addr}")

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            msg = line.decode("utf-8").strip()
            if msg.upper() == "PING":
                writer.write(b"PONG\n")
            else:
                writer.write(b"ERR unknown command\n")

            await writer.drain()

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"Client disconnected: {addr}")

async def main() -> None:
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    print(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())