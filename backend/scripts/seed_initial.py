"""One-shot script: seed crawl_state with Challenger + GM puuids.

Usage:
    uv run python -m scripts.seed_initial             # uses RIOT_SEED_REGIONS from .env
    uv run python -m scripts.seed_initial KR JP1      # explicit platforms
    uv run python -m scripts.seed_initial --all       # all 4 cluster's main regions
    uv run python -m scripts.seed_initial --master    # also include MASTER tier (~adds 200-700 per region)
"""

from __future__ import annotations

import asyncio
import sys

from app.core.logging import configure_logging, get_logger
from app.workers.seed_high_elo import seed_platform

# One platform per cluster covers all 4 regional rate-limit buckets,
# giving 4× parallel throughput vs a single cluster.
ALL_REGIONS = [
    # asia cluster
    "KR", "JP1",
    # americas cluster
    "NA1", "BR1", "LA1", "LA2",
    # europe cluster
    "EUW1", "EUN1", "TR1", "RU",
    # sea cluster
    "TW2", "OC1", "SG2", "TH2", "VN2", "PH2",
]


async def main() -> None:
    configure_logging()
    log = get_logger("seed_initial")

    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    include_master = "--master" in flags
    all_regions = "--all" in flags

    if all_regions:
        regions = ALL_REGIONS
    elif args:
        regions = args
    else:
        from app.settings import get_settings
        regions = get_settings().riot_seed_regions

    log.info("seed_initial.start", regions=regions, include_master=include_master)

    totals: dict[str, int] = {}
    for platform in regions:
        try:
            count = await seed_platform(platform, include_master=include_master)
            totals[platform] = count
        except Exception as e:  # noqa: BLE001
            log.warning("seed_initial.platform_failed", platform=platform, error=str(e))
            totals[platform] = 0

    log.info("seed_initial.complete", totals=totals, total=sum(totals.values()))


if __name__ == "__main__":
    asyncio.run(main())
