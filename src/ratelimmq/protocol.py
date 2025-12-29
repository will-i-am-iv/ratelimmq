from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    cmd: str
    args: list[str]


@dataclass(frozen=True)
class Response:
    # A single line to write back to the client (must end with \n)
    line: str


def parse_line(line: str) -> Request:
    parts = line.strip().split()
    if not parts:
        return Request(cmd="", args=[])
    return Request(cmd=parts[0].upper(), args=parts[1:])


def pong() -> Response:
    return Response("PONG\n")


def bye() -> Response:
    return Response("BYE\n")


def err_unknown() -> Response:
    return Response("ERR unknown command\n")
