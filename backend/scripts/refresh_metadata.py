"""One-shot script to populate augments / champions / items metadata.

Usage:
    uv run python -m scripts.refresh_metadata
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.workers.refresh_meta import refresh_meta_all


async def main() -> None:
    configure_logging()
    log = get_logger("refresh_metadata")
    counts = await refresh_meta_all()
    log.info("refresh_metadata.complete", **counts)


if __name__ == "__main__":
    asyncio.run(main())
