"""Arena BFS crawl dispatcher.

Picks the next batch of puuids to crawl from `crawl_state`, ordered by
priority desc + staleness, and enqueues `crawl_puuid_matches_task` for each.
Runs every few minutes via ARQ cron.

Single-worker assumption: in-memory rate limiter is enough. For multi-worker
we'd swap RiotRateLimiter for a Redis-backed implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select

from app.core.logging import get_logger
from app.db.models import CrawlState
from app.db.session import session_scope

log = get_logger(__name__)

# How many puuids to crawl per dispatch cycle (cluster-aware, see below)
DEFAULT_BATCH_SIZE = 30
# Don't re-crawl a puuid within this window (high-elo) — tuned per priority
MIN_RECRAWL_HOURS_HIGH_PRIO = 12
MIN_RECRAWL_HOURS_NORMAL = 72


async def dispatch_once(redis, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    """Pick next puuids and enqueue crawl tasks. Idempotent."""
    now = datetime.now(UTC)
    cutoff_high = now - timedelta(hours=MIN_RECRAWL_HOURS_HIGH_PRIO)
    cutoff_low = now - timedelta(hours=MIN_RECRAWL_HOURS_NORMAL)

    async with session_scope() as db:
        # priority>=10 (seeded high-elo) re-crawl every 12h
        # priority<10 (BFS discoveries) re-crawl every 72h
        stmt = (
            select(CrawlState.puuid, CrawlState.region_cluster, CrawlState.priority)
            .where(
                CrawlState.done.is_(False),
                or_(
                    CrawlState.backoff_until.is_(None),
                    CrawlState.backoff_until <= now,
                ),
                or_(
                    CrawlState.last_crawled_at.is_(None),
                    and_(CrawlState.priority >= 10, CrawlState.last_crawled_at <= cutoff_high),
                    and_(CrawlState.priority < 10, CrawlState.last_crawled_at <= cutoff_low),
                ),
            )
            .order_by(CrawlState.priority.desc(), CrawlState.last_crawled_at.asc().nulls_first())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        rows = (await db.execute(stmt)).all()

    enqueued = 0
    by_cluster: dict[str, int] = {}
    for puuid, cluster, _prio in rows:
        if not cluster:
            continue
        # Default queue (arq:queue) — see fetch_match.py for why
        await redis.enqueue_job("crawl_puuid_matches_task", puuid, cluster)
        enqueued += 1
        by_cluster[cluster] = by_cluster.get(cluster, 0) + 1

    log.info("dispatch.done", enqueued=enqueued, by_cluster=by_cluster)
    return {"enqueued": enqueued, "by_cluster": by_cluster}


# --- ARQ task wrapper -------------------------------------------------------

async def dispatch_crawl_task(ctx: dict) -> dict[str, Any]:
    return await dispatch_once(ctx["redis"])
