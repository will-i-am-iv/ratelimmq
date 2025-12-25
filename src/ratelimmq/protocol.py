from __future__ import annotations
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Request:
    raw: str
    cmd: str
    args: List[str]

@dataclass(frozen=True)
class Response:
    line: str  # must include trailing \n

def parse_request(raw_line: bytes) -> Request:
    # Normalize: decode → strip → split
    raw = raw_line.decode("utf-8", errors="replace").strip()
    parts = raw.split()
    if not parts:
        return Request(raw=raw, cmd="", args=[])
    cmd = parts[0].upper()
    args = parts[1:]
    return Request(raw=raw, cmd=cmd, args=args)

def resp_ok(msg: str = "") -> Response:
    return Response(f"OK{(' ' + msg) if msg else ''}\n")

def resp_err(msg: str) -> Response:
    return Response(f"ERR {msg}\n")

def resp_value(msg: str) -> Response:
    # For GET later: VALUE <something>
    return Response(f"VALUE {msg}\n")
