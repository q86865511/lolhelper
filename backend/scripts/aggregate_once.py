"""One-shot script to recompute augment_stats and item_stats.

Usage:
    uv run python -m scripts.aggregate_once
    uv run python -m scripts.aggregate_once --patch 15.10
"""

from __future__ import annotations

import argparse
import asyncio

from app.core.logging import configure_logging, get_logger
from app.workers.aggregate import aggregate_arena_augments, aggregate_arena_items


async def main() -> None:
    configure_logging()
    log = get_logger("aggregate_once")
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", help="restrict to one patch (e.g. 15.10)")
    args = parser.parse_args()

    augs = await aggregate_arena_augments(patch=args.patch)
    items = await aggregate_arena_items(patch=args.patch)
    log.info("aggregate_once.complete", augments=augs, items=items, patch=args.patch)


if __name__ == "__main__":
    asyncio.run(main())
