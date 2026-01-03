"""
Allows running the server as a module:

  PYTHONPATH=src python3 -m ratelimmq
"""

import asyncio

from ratelimmq.server import main


def _run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    _run()
