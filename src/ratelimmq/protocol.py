from dataclasses import dataclass

@dataclass(frozen=True)
class Request:
    cmd: str
    args: list[str]

def parse_line(line: str) -> Request:
    parts = line.strip().split()
    cmd = parts[0].upper() if parts else ""
    return Request(cmd=cmd, args=parts[1:])

def ok(payload: str = "") -> bytes:
    msg = "OK" if payload == "" else f"OK {payload}"
    return (msg + "\n").encode()

def err(message: str) -> bytes:
    return (f"ERR {message}\n").encode()
