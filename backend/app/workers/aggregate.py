"""Re-aggregate augment_stats and item_stats from the participants table.

Approach: one UPSERT per (queue × patch × champion-bucket × stat-id) row.
We run this every couple of hours; it's idempotent and CPU-bound on the DB.

For an MVP-scale dataset (< 10M participants) doing this in raw SQL is fast
enough. When data grows we can move to incremental aggregation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from app.core.logging import get_logger
from app.db.session import session_scope
from app.services.stats_engine import (
    ARENA_WIN_THRESHOLD,
    assign_tiers,
    wilson_lower_bound,
)
from app.utils.match import ARENA_QUEUE_IDS

log = get_logger(__name__)

# Minimum games required to publish a (champion, augment/item) bucket.
# Tuned low for MVP / early dataset; tighten as crawler accumulates data.
MIN_GAMES_PER_CHAMPION = 5
# Minimum games required to publish a global (champion=NULL) bucket.
MIN_GAMES_GLOBAL = 30


async def aggregate_arena_augments(patch: str | None = None) -> int:
    """Recompute augment_stats rows for Arena queues.

    If `patch` is None, aggregate every patch present in participants.
    Returns the number of upserted rows.
    """
    queue_ids = tuple(ARENA_QUEUE_IDS)
    placeholders = ",".join(str(q) for q in queue_ids)

    where_patch = "AND p.patch = :patch" if patch else "AND p.patch IS NOT NULL"
    params = {"win_thr": ARENA_WIN_THRESHOLD}
    if patch:
        params["patch"] = patch

    # 1) global per-augment aggregates (champion_id NULL)
    global_sql = text(
        f"""
        SELECT
            p.queue_id,
            UNNEST(p.augments) AS augment_id,
            NULL::INTEGER AS champion_id,
            p.patch,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND :win_thr THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p
        WHERE p.queue_id IN ({placeholders})
          AND p.augments IS NOT NULL
          AND p.placement IS NOT NULL
          {where_patch}
        GROUP BY p.queue_id, augment_id, p.patch
        """
    )

    # 2) per-champion × per-augment aggregates
    by_champion_sql = text(
        f"""
        SELECT
            p.queue_id,
            UNNEST(p.augments) AS augment_id,
            p.champion_id,
            p.patch,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND :win_thr THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p
        WHERE p.queue_id IN ({placeholders})
          AND p.augments IS NOT NULL
          AND p.placement IS NOT NULL
          {where_patch}
        GROUP BY p.queue_id, augment_id, p.champion_id, p.patch
        """
    )

    upserts = 0
    async with session_scope() as db:
        global_rows = (await db.execute(global_sql, params)).mappings().all()
        champ_rows = (await db.execute(by_champion_sql, params)).mappings().all()

    # Compute Wilson + tier in Python (more readable than SQL window functions).
    rows = _enrich_stats_rows(list(global_rows), is_global=True) + _enrich_stats_rows(
        list(champ_rows), is_global=False
    )
    if not rows:
        log.info("aggregate.augments.empty")
        return 0

    now = datetime.now(UTC)
    insert_sql = text(
        """
        INSERT INTO augment_stats
            (queue_id, augment_id, champion_id, patch, games, wins, top1,
             avg_placement, pick_rate, win_rate, wilson_low, tier, computed_at)
        VALUES
            (:queue_id, :augment_id, :champion_id, :patch, :games, :wins, :top1,
             :avg_placement, :pick_rate, :win_rate, :wilson_low, :tier, :computed_at)
        ON CONFLICT (queue_id, augment_id, champion_id, patch)
        DO UPDATE SET
            games = EXCLUDED.games,
            wins = EXCLUDED.wins,
            top1 = EXCLUDED.top1,
            avg_placement = EXCLUDED.avg_placement,
            pick_rate = EXCLUDED.pick_rate,
            win_rate = EXCLUDED.win_rate,
            wilson_low = EXCLUDED.wilson_low,
            tier = EXCLUDED.tier,
            computed_at = EXCLUDED.computed_at
        """
    )
    async with session_scope() as db:
        for r in rows:
            r["computed_at"] = now
            await db.execute(insert_sql, r)
            upserts += 1

    log.info("aggregate.augments.done", rows=upserts, patch=patch)
    return upserts


def _enrich_stats_rows(rows: list[dict], *, is_global: bool) -> list[dict]:
    """Adds win_rate, wilson_low, tier; filters by min sample size; assigns tier per-(queue,patch)."""
    min_games = MIN_GAMES_GLOBAL if is_global else MIN_GAMES_PER_CHAMPION

    eligible: list[dict] = []
    for r in rows:
        r = dict(r)  # copy
        games = int(r["games"])
        wins = int(r["wins"])
        if games < min_games:
            continue
        r["games"] = games
        r["wins"] = wins
        # top1 / avg_placement are only present for augment aggregates
        top1 = r.get("top1")
        r["top1"] = int(top1) if top1 is not None else 0
        if "avg_placement" not in r:
            r["avg_placement"] = None
        r["win_rate"] = round(wins / games, 4)
        r["wilson_low"] = round(wilson_lower_bound(wins, games), 4)
        # pick_rate left NULL for now; needs total-matches-per-patch context
        r["pick_rate"] = None
        eligible.append(r)

    # Tier within each (queue, patch) bucket
    by_bucket: dict[tuple[int, str], list[dict]] = {}
    for r in eligible:
        bucket = (r["queue_id"], r["patch"])
        by_bucket.setdefault(bucket, []).append(r)

    out: list[dict] = []
    for _bucket, bucket_rows in by_bucket.items():
        entries = [(r["augment_id"] if "augment_id" in r else r["item_id"], r["wilson_low"], r["games"]) for r in bucket_rows]
        # min_games already filtered above; assign_tiers uses 0 so all pass
        tiered = assign_tiers(entries, min_games=0)
        tier_by_key = {t.key: t.tier for t in tiered}
        for r in bucket_rows:
            key = r["augment_id"] if "augment_id" in r else r["item_id"]
            r["tier"] = tier_by_key.get(key)
            out.append(r)
    return out


# --- items aggregator (M2 — only run when we want item stats) --------------

async def aggregate_arena_items(patch: str | None = None) -> int:
    """Recompute item_stats — `build_position = -1` (any position)."""
    queue_ids = tuple(ARENA_QUEUE_IDS)
    placeholders = ",".join(str(q) for q in queue_ids)
    where_patch = "AND p.patch = :patch" if patch else "AND p.patch IS NOT NULL"
    params = {"win_thr": ARENA_WIN_THRESHOLD}
    if patch:
        params["patch"] = patch

    by_champion_sql = text(
        f"""
        SELECT
            p.queue_id,
            item_id,
            p.champion_id,
            p.patch,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND :win_thr THEN 1 ELSE 0 END) AS wins
        FROM participants p, UNNEST(p.items) AS item_id
        WHERE p.queue_id IN ({placeholders})
          AND item_id > 0
          AND p.items IS NOT NULL
          AND p.placement IS NOT NULL
          {where_patch}
        GROUP BY p.queue_id, item_id, p.champion_id, p.patch
        """
    )

    async with session_scope() as db:
        rows = list((await db.execute(by_champion_sql, params)).mappings().all())

    if not rows:
        log.info("aggregate.items.empty")
        return 0

    enriched = _enrich_stats_rows([dict(r) for r in rows], is_global=False)
    now = datetime.now(UTC)
    insert_sql = text(
        """
        INSERT INTO item_stats
            (queue_id, item_id, champion_id, patch, build_position,
             games, wins, win_rate, wilson_low, tier, computed_at)
        VALUES
            (:queue_id, :item_id, :champion_id, :patch, -1,
             :games, :wins, :win_rate, :wilson_low, :tier, :computed_at)
        ON CONFLICT (queue_id, item_id, champion_id, patch, build_position)
        DO UPDATE SET
            games = EXCLUDED.games,
            wins = EXCLUDED.wins,
            win_rate = EXCLUDED.win_rate,
            wilson_low = EXCLUDED.wilson_low,
            tier = EXCLUDED.tier,
            computed_at = EXCLUDED.computed_at
        """
    )
    upserts = 0
    async with session_scope() as db:
        for r in enriched:
            r["computed_at"] = now
            await db.execute(insert_sql, r)
            upserts += 1
    log.info("aggregate.items.done", rows=upserts, patch=patch)
    return upserts


# --- ARQ task wrappers ------------------------------------------------------

async def aggregate_arena_task(ctx: dict | None = None) -> dict[str, int]:
    augs = await aggregate_arena_augments(patch=None)
    items = await aggregate_arena_items(patch=None)
    return {"augments": augs, "items": items}
