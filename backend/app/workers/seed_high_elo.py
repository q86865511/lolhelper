"""Seed the BFS crawler with Challenger + Grandmaster puuids.

Run once at startup (or daily) to ensure the crawler always has fresh
high-elo entry points. High-elo seeds give us the strongest meta signal —
champion + augment win rates from low-MMR games are noisy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.models import CrawlState
from app.db.session import session_scope
from app.services.riot.client import get_riot_client, platform_to_cluster
from app.services.riot.exceptions import RiotError
from app.settings import get_settings

log = get_logger(__name__)


async def _entry_puuid(client, entry: dict[str, Any], platform: str) -> str | None:
    """League-V4 entries may have puuid directly (newer API) or only summonerId.

    Falls back to a Summoner-V4 lookup if puuid is absent.
    """
    puuid = entry.get("puuid")
    if isinstance(puuid, str) and puuid:
        return puuid
    summoner_id = entry.get("summonerId")
    if not summoner_id:
        return None
    # summoner-v4 by summonerId — adds a network call per entry, expensive
    try:
        host = f"{platform.lower()}.api.riotgames.com"
        data = await client.get(
            host,
            f"/lol/summoner/v4/summoners/{summoner_id}",
            region_key=platform.upper(),
            method_id="summoner-v4-id",
        )
        return data.get("puuid")
    except RiotError as e:
        log.warning("seed.summoner_lookup_failed", summoner_id=summoner_id, error=str(e))
        return None


async def seed_platform(platform: str, *, include_master: bool = False) -> int:
    """Seed crawl_state from challenger + grandmaster (+ optional master).

    Returns the number of puuids added or refreshed.
    """
    client = get_riot_client()
    cluster = platform_to_cluster(platform)
    now = datetime.now(timezone.utc)

    leagues = []
    try:
        chal = await client.get_challenger_league(platform=platform)
        leagues.append(("CHALLENGER", chal))
    except RiotError as e:
        log.warning("seed.challenger_failed", platform=platform, error=str(e))

    try:
        gm = await client.get_grandmaster_league(platform=platform)
        leagues.append(("GRANDMASTER", gm))
    except RiotError as e:
        log.warning("seed.grandmaster_failed", platform=platform, error=str(e))

    if include_master:
        try:
            mst = await client.get_master_league(platform=platform)
            leagues.append(("MASTER", mst))
        except RiotError as e:
            log.warning("seed.master_failed", platform=platform, error=str(e))

    rows: list[dict[str, Any]] = []
    seen_puuids: set[str] = set()
    for tier_name, league in leagues:
        entries = league.get("entries", []) if isinstance(league, dict) else []
        for entry in entries:
            puuid = await _entry_puuid(client, entry, platform)
            if not puuid or puuid in seen_puuids:
                continue
            seen_puuids.add(puuid)
            rows.append(
                {
                    "puuid": puuid,
                    "region_cluster": cluster,
                    "platform": platform.upper(),
                    "priority": 10,
                    "depth": 0,
                    "done": False,
                    "discovered_by": None,
                }
            )
        log.info("seed.tier", platform=platform, tier=tier_name, entries=len(entries))

    if not rows:
        return 0

    # Upsert: bump priority back to 10 if already known, refresh region
    async with session_scope() as db:
        stmt = pg_insert(CrawlState).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["puuid"],
            set_={
                "region_cluster": stmt.excluded.region_cluster,
                "platform": stmt.excluded.platform,
                "priority": 10,
                "done": False,
            },
        )
        await db.execute(stmt)
    log.info("seed.upsert.done", platform=platform, count=len(rows))
    _ = now  # placeholder — could persist last_seeded_at on a meta table
    return len(rows)


async def seed_all(include_master: bool = False) -> dict[str, int]:
    """Seed every platform listed in `RIOT_SEED_REGIONS`."""
    settings = get_settings()
    out: dict[str, int] = {}
    for platform in settings.riot_seed_regions:
        out[platform] = await seed_platform(platform, include_master=include_master)
    return out


# --- ARQ task wrapper --------------------------------------------------------

async def seed_high_elo_task(ctx: dict | None = None) -> dict[str, int]:  # noqa: ARG001
    return await seed_all(include_master=False)
