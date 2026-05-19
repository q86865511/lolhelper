"""Match fetching workers.

Two ARQ tasks:
  * `crawl_puuid_matches_task(puuid, cluster)` — list a player's recent Arena
    matches and enqueue fetch_match_task for each new one.
  * `fetch_match_task(match_id, cluster)` — fetch one match's detail and
    upsert matches + participants. Discovers new puuids → upserts crawl_state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.models import CrawlState, Match
from app.db.session import session_scope
from app.services.riot.client import get_riot_client, platform_to_cluster
from app.services.riot.exceptions import RiotError, RiotForbidden, RiotNotFound
from app.utils.match import ARENA_QUEUE_IDS, is_arena, parse_match

log = get_logger(__name__)

# How many recent match IDs to pull per puuid per cycle. Riot caps this at 100;
# using the max means each "list" call yields up to 5× more candidate matches
# without burning extra rate-limit budget on listings.
MATCH_LIST_BATCH = 100
# Cap BFS depth so we don't expand forever
MAX_BFS_DEPTH = 5
# Don't ingest matches older than this — current-patch meta is what matters,
# and ancient Arena cycles have very different augment / item pools.
MAX_MATCH_AGE_DAYS = 180


def _crawl_start_time_seconds() -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_MATCH_AGE_DAYS)
    return int(cutoff.timestamp())


# ---------------------------------------------------------------------------
# crawl_puuid_matches: list recent matches for a puuid, enqueue fetches
# ---------------------------------------------------------------------------

async def crawl_puuid_matches(
    redis,
    puuid: str,
    cluster: str,
    *,
    queue: int = 1700,
) -> dict[str, int]:
    client = get_riot_client()
    now = datetime.now(timezone.utc)

    try:
        match_ids = await client.get_match_ids_by_puuid(
            puuid,
            cluster=cluster,
            queue=queue,
            count=MATCH_LIST_BATCH,
            start_time=_crawl_start_time_seconds(),
        )
    except (RiotNotFound, RiotForbidden) as e:
        log.warning("crawl.puuid.skip", puuid=puuid[:12], error=str(e))
        await _mark_crawled(puuid, now, done=True)
        return {"new_ids": 0, "skipped": 1}
    except RiotError as e:
        log.warning("crawl.puuid.error", puuid=puuid[:12], error=str(e))
        return {"new_ids": 0, "error": 1}

    if not match_ids:
        await _mark_crawled(puuid, now)
        return {"new_ids": 0}

    new_ids = await _filter_unseen_match_ids(match_ids)

    enqueued = 0
    for mid in new_ids:
        # NOTE: do NOT pass _queue_name — WorkerSettings uses ARQ's default queue
        # ("arq:queue"). Passing a custom name routes jobs to a queue the worker
        # never listens on, orphaning them in Redis.
        await redis.enqueue_job("fetch_match_task", mid, cluster)
        enqueued += 1

    await _mark_crawled(puuid, now)

    log.info(
        "crawl.puuid.done",
        puuid=puuid[:12],
        cluster=cluster,
        listed=len(match_ids),
        enqueued=enqueued,
    )
    return {"listed": len(match_ids), "enqueued": enqueued}


async def _filter_unseen_match_ids(match_ids: list[str]) -> list[str]:
    """Return only match IDs that don't yet exist in the matches table."""
    if not match_ids:
        return []
    async with session_scope() as db:
        stmt = select(Match.match_id).where(Match.match_id.in_(match_ids))
        existing = {row[0] for row in (await db.execute(stmt)).all()}
    return [mid for mid in match_ids if mid not in existing]


async def _mark_crawled(puuid: str, when: datetime, *, done: bool = False) -> None:
    """Update last_crawled_at on an existing crawl_state row."""
    from sqlalchemy import update

    async with session_scope() as db:
        values: dict[str, Any] = {"last_crawled_at": when}
        if done:
            values["done"] = True
        await db.execute(update(CrawlState).where(CrawlState.puuid == puuid).values(**values))


# ---------------------------------------------------------------------------
# fetch_match: pull one match detail, INSERT, fan out new puuids
# ---------------------------------------------------------------------------

async def fetch_match(match_id: str, cluster: str, *, discovered_by: str | None = None) -> dict[str, Any]:
    client = get_riot_client()

    try:
        payload = await client.get_match(match_id, cluster=cluster)
    except RiotForbidden:
        log.info("fetch_match.forbidden", match_id=match_id)
        return {"status": "forbidden"}
    except RiotNotFound:
        log.info("fetch_match.notfound", match_id=match_id)
        return {"status": "notfound"}
    except RiotError as e:
        log.warning("fetch_match.error", match_id=match_id, error=str(e))
        return {"status": "error"}

    try:
        match_row, participants = parse_match(payload, source="riot_api")
    except Exception as e:  # noqa: BLE001
        log.warning("fetch_match.parse_failed", match_id=match_id, error=str(e))
        return {"status": "parse_error"}

    if not is_arena(match_row["queue_id"]):
        # We're crawling queue=1700 explicitly but some by-puuid responses may
        # leak adjacent queues if the API filter isn't honoured. Skip silently.
        return {"status": "skipped_non_arena"}

    await _insert_match(match_row, participants)
    await _expand_bfs(participants, cluster, discovered_by=discovered_by)

    return {"status": "ok", "match_id": match_id, "participants": len(participants)}


async def _insert_match(
    match_row: dict[str, Any], participants: list[dict[str, Any]]
) -> None:
    """INSERT match + participants atomically. No-op if match already exists."""
    from app.db.models import Participant

    async with session_scope() as db:
        existing = await db.execute(
            select(Match.match_id).where(Match.match_id == match_row["match_id"])
        )
        if existing.scalar_one_or_none() is not None:
            return
        await db.execute(pg_insert(Match).values(match_row))
        if participants:
            await db.execute(pg_insert(Participant).values(participants))


async def _expand_bfs(
    participants: list[dict[str, Any]],
    cluster: str,
    *,
    discovered_by: str | None,
) -> None:
    """Add any new puuids in this match to crawl_state for BFS expansion."""
    if not participants:
        return
    rows = []
    for p in participants:
        puuid = p.get("puuid")
        if not puuid:
            continue
        rows.append(
            {
                "puuid": puuid,
                "region_cluster": cluster,
                "platform": "",  # filled lazily when we hit summoner-v4
                "priority": 0,
                "depth": 1,
                "done": False,
                "discovered_by": discovered_by,
            }
        )
    if not rows:
        return
    async with session_scope() as db:
        stmt = pg_insert(CrawlState).values(rows)
        # If puuid already in crawl_state, do nothing (keep its existing
        # priority / depth so seeded high-elo puuids retain priority=10).
        stmt = stmt.on_conflict_do_nothing(index_elements=["puuid"])
        await db.execute(stmt)


# --- ARQ task wrappers ------------------------------------------------------

async def crawl_puuid_matches_task(ctx: dict, puuid: str, cluster: str) -> dict[str, Any]:
    return await crawl_puuid_matches(ctx["redis"], puuid, cluster)


async def fetch_match_task(
    ctx: dict, match_id: str, cluster: str, discovered_by: str | None = None  # noqa: ARG001
) -> dict[str, Any]:
    return await fetch_match(match_id, cluster, discovered_by=discovered_by)
