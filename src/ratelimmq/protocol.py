from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    cmd: str
    args: list[str]


@dataclass(frozen=True)
class Response:
    line: str


def parse_line(raw: bytes) -> Request:
    line = raw.decode("utf-8", errors="replace").strip()
    if not line:
        return Request(cmd="", args=[])
    parts = line.split()
    return Request(cmd=parts[0].upper(), args=parts[1:])
