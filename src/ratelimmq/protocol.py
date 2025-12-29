def parse_line(raw) -> Request:
    # raw can be bytes (from asyncio StreamReader) or str
    if isinstance(raw, (bytes, bytearray)):
        line = raw.decode("utf-8", errors="replace")
    else:
        line = str(raw)

    parts = line.strip().split()
    if not parts:
        return Request(cmd="", args=[])

    cmd = parts[0].upper()
    args = parts[1:]
    return Request(cmd=cmd, args=args)
