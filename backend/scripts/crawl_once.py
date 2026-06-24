"""One-shot script: run a single crawl iteration without ARQ.

For each puuid pulled by the dispatcher, this runs `crawl_puuid_matches` and
then synchronously fetches each new match. Useful for smoke-testing the
pipeline before starting the long-running worker.

Usage:
    uv run python -m scripts.crawl_once [--batch 10] [--max-fetch 50]
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from app.core.logging import configure_logging, get_logger
from app.db.models import CrawlState, Match
from app.db.session import session_scope
from app.services.riot.client import get_riot_client
from app.services.riot.exceptions import RiotError, RiotForbidden, RiotNotFound
from app.utils.match import is_arena, parse_match
from app.workers.fetch_match import (
    _crawl_start_time_seconds,
    _expand_bfs,
    _insert_match,
    _mark_crawled,
)
from sqlalchemy import or_, select


async def crawl_once(batch: int, max_fetch: int) -> dict[str, int]:
    log = get_logger("crawl_once")
    client = get_riot_client()
    now = datetime.now(UTC)

    # Pick puuids (most stale, highest priority)
    async with session_scope() as db:
        stmt = (
            select(CrawlState.puuid, CrawlState.region_cluster)
            .where(
                CrawlState.done.is_(False),
                or_(
                    CrawlState.backoff_until.is_(None),
                    CrawlState.backoff_until <= now,
                ),
            )
            .order_by(CrawlState.priority.desc(), CrawlState.last_crawled_at.asc().nulls_first())
            .limit(batch)
        )
        puuids = (await db.execute(stmt)).all()

    if not puuids:
        log.warning("crawl_once.no_puuids — run seed_initial first")
        return {"puuids": 0}

    fetched = 0
    skipped = 0
    errors = 0
    matches_added = 0

    for puuid, cluster in puuids:
        if fetched >= max_fetch:
            break
        if not cluster:
            continue
        try:
            match_ids = await client.get_match_ids_by_puuid(
                puuid,
                cluster=cluster,
                queue=1700,
                count=100,  # Riot's max — 5× more candidates per list call
                start_time=_crawl_start_time_seconds(),
            )
        except (RiotForbidden, RiotNotFound) as e:
            log.info("crawl_once.skip", puuid=puuid[:12], error=type(e).__name__)
            await _mark_crawled(puuid, now, done=True)
            skipped += 1
            continue
        except RiotError as e:
            log.warning("crawl_once.list_error", puuid=puuid[:12], error=str(e))
            errors += 1
            continue

        # Filter out already-ingested
        async with session_scope() as db:
            existing = {
                row[0]
                for row in (
                    await db.execute(select(Match.match_id).where(Match.match_id.in_(match_ids)))
                ).all()
            }
        new_ids = [mid for mid in match_ids if mid not in existing]

        for mid in new_ids:
            if fetched >= max_fetch:
                break
            try:
                payload = await client.get_match(mid, cluster=cluster)
            except (RiotForbidden, RiotNotFound):
                continue
            except RiotError as e:
                log.warning("crawl_once.fetch_error", match_id=mid, error=str(e))
                continue

            try:
                match_row, parts = parse_match(payload, source="riot_api")
            except Exception as e:
                log.warning("crawl_once.parse_error", match_id=mid, error=str(e))
                continue

            if not is_arena(match_row["queue_id"]):
                continue

            await _insert_match(match_row, parts)
            await _expand_bfs(parts, cluster, discovered_by=puuid)
            matches_added += 1
            fetched += 1

        await _mark_crawled(puuid, now)
        log.info(
            "crawl_once.puuid_done",
            puuid=puuid[:12],
            cluster=cluster,
            listed=len(match_ids),
            new=len(new_ids),
        )

    log.info(
        "crawl_once.complete",
        puuids=len(puuids),
        matches_added=matches_added,
        skipped=skipped,
        errors=errors,
    )
    return {
        "puuids": len(puuids),
        "matches_added": matches_added,
        "skipped": skipped,
        "errors": errors,
    }


async def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=10, help="puuids to crawl this pass")
    parser.add_argument("--max-fetch", type=int, default=50, help="cap on match fetches")
    args = parser.parse_args()
    await crawl_once(args.batch, args.max_fetch)


if __name__ == "__main__":
    asyncio.run(main())
