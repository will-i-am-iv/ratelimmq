from __future__ import annotations

import asyncio

from ratelimmq.logging_config import configure_logging


def main() -> None:
    # Configure logging ONCE, right when the program starts
    configure_logging()

    # Now run the server entrypoint
    from ratelimmq.server import main as server_main

    asyncio.run(server_main())


if __name__ == "__main__":
    main()
