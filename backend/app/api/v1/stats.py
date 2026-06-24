"""Aggregated statistics queries.

Arena augments come in two flavours:
  - **Hex** (海克斯): have a rarity (Silver/Gold/Prismatic), picked at the round
    boundaries — the meta-relevant ones.
  - **Event** (事件選擇): no rarity, appear in special event rounds — picked
    based on situation, less about champion synergy.

Endpoints accept `with_rarity` to slice between these. Champion ranking and
per-champion detail default to hex-only because event picks aren't tied to
champion choice.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, text

from app.deps import DbDep
from app.services.stats_engine import assign_tiers, wilson_lower_bound

router = APIRouter(prefix="/stats", tags=["stats"])


ARENA_QUEUE_IDS = (1700, 1710)
MAYHEM_QUEUE_ID = 2400

# Special sentinel: passing "all" disables the patch filter (combine all patches).
PATCH_ALL = "all"

# Sort priority for tier badges. Higher = better. Used as the primary sort key
# so the leaderboard groups by tier (all S together, then A, B, ...) and uses
# win_rate as the secondary tie-breaker within each tier.
_TIER_ORDER: dict[str | None, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, None: 0}


def _tier_then_winrate_sort_key(row: dict[str, Any]) -> tuple[int, float]:
    """Sort key for descending-by-tier-then-by-win_rate ordering."""
    return (_TIER_ORDER.get(row.get("tier"), 0), float(row.get("win_rate") or 0.0))


def _current_patch_or_none(patch: str | None) -> str | None:
    """Pass-through. Will become smarter when patches table is populated."""
    return patch


async def _resolve_patches(db, patch_param: str | None) -> list[str]:
    """Decide which patch(es) to filter on.

    - `patch_param == "all"`: return [] (no filter).
    - Specific value like "16.9": return [it].
    - None / empty: return [latest_patch] if any data exists, else [].
    """
    if patch_param == PATCH_ALL:
        return []
    if patch_param:
        return [patch_param]

    sql = text(
        """
        SELECT patch
        FROM matches
        WHERE queue_id IN (1700, 1710) AND patch IS NOT NULL
        GROUP BY patch
        ORDER BY
            (split_part(patch, '.', 1))::INT DESC,
            (split_part(patch, '.', 2))::INT DESC
        LIMIT 1
        """
    )
    row = (await db.execute(sql)).first()
    if not row:
        return []
    return [row[0]]


async def _resolve_patches_with_fallback(
    db,
    patch_param: str | None,
    *,
    champion_id: int | None,
    min_games_threshold: int,
) -> tuple[list[str], bool]:
    """Like _resolve_patches but expands to the previous patch when the
    latest one alone has fewer than `min_games_threshold` matching games for
    this champion (or globally if champion_id is None).

    Returns (patches, fell_back_to_prior).
    """
    patches = await _resolve_patches(db, patch_param)
    if patch_param or len(patches) == 0:
        # Explicit patch or no data — no fallback semantics
        return patches, False

    # We have latest patch only. Check sample size for it.
    if champion_id is not None:
        count_sql = text(
            """
            SELECT COUNT(*) FROM participants
            WHERE queue_id IN (1700, 1710)
              AND champion_id = :cid
              AND placement IS NOT NULL
              AND patch = :patch
            """
        )
        params = {"cid": champion_id, "patch": patches[0]}
    else:
        count_sql = text(
            """
            SELECT COUNT(*) FROM participants
            WHERE queue_id IN (1700, 1710)
              AND placement IS NOT NULL
              AND patch = :patch
            """
        )
        params = {"patch": patches[0]}

    n = (await db.execute(count_sql, params)).scalar_one()
    if n is None or n < min_games_threshold:
        # Pull one more older patch
        more_sql = text(
            """
            SELECT patch
            FROM matches
            WHERE queue_id IN (1700, 1710) AND patch IS NOT NULL AND patch != :latest
            GROUP BY patch
            ORDER BY
                (split_part(patch, '.', 1))::INT DESC,
                (split_part(patch, '.', 2))::INT DESC
            LIMIT 1
            """
        )
        row = (await db.execute(more_sql, {"latest": patches[0]})).first()
        if row:
            return [patches[0], row[0]], True
    return patches, False


def _rarity_join_filter(stmt, with_rarity: bool | None):
    """If with_rarity is set, JOIN augments and filter on rarity null-ness."""
    from app.db.models import Augment, AugmentStat

    if with_rarity is None:
        return stmt
    stmt = stmt.join(Augment, Augment.id == AugmentStat.augment_id)
    if with_rarity:
        return stmt.where(Augment.rarity.is_not(None))
    return stmt.where(Augment.rarity.is_(None))


@router.get("/arena/augments")
async def arena_augments(
    db: DbDep,
    patch: Annotated[
        str | None,
        Query(description="Specific patch, or 'all' for all patches. Default: latest patch only."),
    ] = None,
    champion_id: Annotated[int | None, Query(ge=1)] = None,
    min_games: Annotated[int, Query(ge=0)] = 30,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    with_rarity: Annotated[
        bool | None,
        Query(description="true = hex augments only; false = event-choice augments only; omit = all"),
    ] = None,
) -> dict[str, Any]:
    """Augment leaderboard. Defaults to the latest patch only."""
    patches = await _resolve_patches(db, patch)
    patch_clause, patch_params = _patch_clause(patches, alias="s")

    rarity_join = ""
    rarity_where = ""
    if with_rarity is True:
        rarity_join = "JOIN augments a ON a.id = s.augment_id"
        rarity_where = "AND a.rarity IS NOT NULL"
    elif with_rarity is False:
        rarity_join = "JOIN augments a ON a.id = s.augment_id"
        rarity_where = "AND a.rarity IS NULL"

    champ_filter = "AND s.champion_id = :champion_id" if champion_id is not None else "AND s.champion_id IS NULL"

    sql = text(
        f"""
        SELECT
            s.augment_id,
            SUM(s.games) AS games,
            SUM(s.wins) AS wins,
            SUM(COALESCE(s.top1, 0)) AS top1,
            CASE WHEN SUM(s.games) > 0
                 THEN (SUM(s.avg_placement * s.games) / SUM(s.games))::NUMERIC(4,2)
                 ELSE NULL END AS avg_placement,
            MAX(s.computed_at) AS computed_at
        FROM augment_stats s
        {rarity_join}
        WHERE s.queue_id IN (1700, 1710)
          {champ_filter}
          {patch_clause}
          {rarity_where}
        GROUP BY s.augment_id
        HAVING SUM(s.games) >= :min_games
        ORDER BY SUM(s.games) DESC
        """
    )
    params: dict[str, Any] = {"min_games": min_games, **patch_params}
    if champion_id is not None:
        params["champion_id"] = champion_id

    raw = (await db.execute(sql, params)).mappings().all()

    enriched = []
    for r in raw:
        g = int(r["games"])
        w = int(r["wins"])
        enriched.append(
            {
                "augment_id": int(r["augment_id"]),
                "champion_id": champion_id,
                "games": g,
                "wins": w,
                "top1": int(r["top1"]),
                "win_rate": round(w / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
                "avg_placement": float(r["avg_placement"]) if r["avg_placement"] is not None else None,
            }
        )

    # Tier ranks by Wilson lower bound — balances win rate and sample size,
    # so a 5/5 (100%) augment doesn't outrank a 800/1000 (80%) one.
    tier_entries = [(a["augment_id"], a["wilson_low"], a["games"]) for a in enriched]
    tiered = assign_tiers(tier_entries, min_games=0)
    tier_by_id = {t.key: t.tier for t in tiered}
    for a in enriched:
        a["tier"] = tier_by_id.get(a["augment_id"])

    enriched.sort(key=_tier_then_winrate_sort_key, reverse=True)
    enriched = enriched[:limit]

    updated_at: datetime | None = max((r["computed_at"] for r in raw), default=None)
    return {
        "patch": patch,
        "patches_used": patches,
        "queue_ids": list(ARENA_QUEUE_IDS),
        "sample_size": sum(a["games"] for a in enriched),
        "updated_at": updated_at.isoformat() if updated_at else None,
        "with_rarity": with_rarity,
        "augments": enriched,
    }


@router.get("/arena/augments/{augment_id}")
async def arena_augment_detail(
    augment_id: int,
    db: DbDep,
    patch: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    from app.db.models import AugmentStat

    patch = _current_patch_or_none(patch)
    stmt = (
        select(AugmentStat)
        .where(
            AugmentStat.queue_id.in_(ARENA_QUEUE_IDS),
            AugmentStat.augment_id == augment_id,
        )
        .order_by(AugmentStat.wilson_low.desc())
    )
    if patch:
        stmt = stmt.where(AugmentStat.patch == patch)

    rows = (await db.execute(stmt)).scalars().all()
    overall = next((r for r in rows if r.champion_id is None), None)
    by_champion = [r for r in rows if r.champion_id is not None]

    return {
        "augment_id": augment_id,
        "patch": patch,
        "overall": (
            {
                "games": overall.games,
                "win_rate": float(overall.win_rate),
                "wilson_low": float(overall.wilson_low),
                "tier": overall.tier,
            }
            if overall
            else None
        ),
        "by_champion": [
            {
                "champion_id": r.champion_id,
                "games": r.games,
                "win_rate": float(r.win_rate),
                "wilson_low": float(r.wilson_low),
                "tier": r.tier,
            }
            for r in by_champion[:50]
        ],
    }


@router.get("/arena/champions")
async def arena_champions(
    db: DbDep,
    patch: Annotated[
        str | None,
        Query(description="Specific patch or 'all'. Default: latest patch only."),
    ] = None,
    min_games: Annotated[int, Query(ge=0)] = 10,
) -> dict[str, Any]:
    """Per-champion Arena Top4 win rate. Defaults to latest patch only."""
    patches = await _resolve_patches(db, patch)
    patch_clause, patch_params = _patch_clause(patches, alias="p")

    sql = text(
        f"""
        SELECT
            p.champion_id,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p
        WHERE p.queue_id IN (1700, 1710)
          AND p.placement IS NOT NULL
          {patch_clause}
        GROUP BY p.champion_id
        HAVING COUNT(*) >= :min_games
        ORDER BY 2 DESC
        """
    )
    params: dict[str, Any] = {"min_games": min_games, **patch_params}
    raw = (await db.execute(sql, params)).mappings().all()

    enriched = []
    for r in raw:
        games = int(r["games"])
        wins = int(r["wins"])
        enriched.append(
            {
                "champion_id": int(r["champion_id"]),
                "games": games,
                "wins": wins,
                "top1": int(r["top1"]),
                "win_rate": round(wins / games, 4) if games else 0.0,
                "wilson_low": round(wilson_lower_bound(wins, games), 4),
                "avg_placement": float(r["avg_placement"]) if r["avg_placement"] is not None else None,
            }
        )

    # Tier from Wilson lower bound — considers both win rate and sample size.
    tier_entries = [(c["champion_id"], c["wilson_low"], c["games"]) for c in enriched]
    tiered = assign_tiers(tier_entries, min_games=0)
    tier_by_id = {t.key: t.tier for t in tiered}
    for c in enriched:
        c["tier"] = tier_by_id.get(c["champion_id"])

    enriched.sort(key=_tier_then_winrate_sort_key, reverse=True)

    return {
        "patch": patch,
        "patches_used": patches,
        "min_games": min_games,
        "total_champions": len(enriched),
        "champions": enriched,
    }


# Item category bounds — keep aligned with frontend/src/lib/item-category.ts
ITEM_CATEGORY_FILTERS: dict[str, str] = {
    "boots": "AND 'Boots' = ANY(i.tags)",
    "prismatic": (
        "AND ((i.id BETWEEN 228000 AND 228999 AND COALESCE(i.gold,0) >= 2750)"
        " OR (i.id BETWEEN 443000 AND 447999 AND COALESCE(i.gold,0) >= 2750))"
    ),
    "core": (
        "AND COALESCE(i.gold, 0) >= 1000"
        " AND NOT ('Boots' = ANY(COALESCE(i.tags, ARRAY[]::text[])))"
        " AND NOT (i.id BETWEEN 228000 AND 228999 AND COALESCE(i.gold,0) >= 2750)"
        " AND NOT (i.id BETWEEN 443000 AND 447999 AND COALESCE(i.gold,0) >= 2750)"
    ),
}


@router.get("/arena/items")
async def arena_items(
    db: DbDep,
    patch: Annotated[
        str | None,
        Query(description="Specific patch or 'all'. Default: latest patch only."),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="boots | prismatic | core. Omit for all."),
    ] = None,
    min_games: Annotated[int, Query(ge=0)] = 30,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict[str, Any]:
    """Cross-champion item leaderboard.

    Computed directly from `participants.items[]`. Each item appears once,
    summed across champions and (when no patch specified) across patches.
    """
    patches = await _resolve_patches(db, patch)
    patch_clause, patch_params = _patch_clause(patches, alias="p")
    category_clause = ""
    if category:
        if category not in ITEM_CATEGORY_FILTERS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown category '{category}'. Valid: boots, prismatic, core.",
            )
        category_clause = ITEM_CATEGORY_FILTERS[category]

    # Total Arena player-games in scope (denominator for pick rate)
    total_sql = text(
        f"""
        SELECT COUNT(*) AS total
        FROM participants p
        WHERE p.queue_id IN (1700, 1710)
          AND p.placement IS NOT NULL
          {patch_clause}
        """
    )
    total_games = (await db.execute(total_sql, patch_params)).scalar_one() or 0

    items_sql = text(
        f"""
        SELECT
            it_id AS item_id,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins
        FROM participants p, UNNEST(p.items) AS it_id
        JOIN items i ON i.id = it_id
        WHERE p.queue_id IN (1700, 1710)
          AND p.placement IS NOT NULL
          AND it_id > 0
          {category_clause}
          {patch_clause}
        GROUP BY it_id
        HAVING COUNT(*) >= :min_games
        """
    )
    params: dict[str, Any] = {"min_games": min_games, **patch_params}
    raw = (await db.execute(items_sql, params)).mappings().all()

    enriched = []
    for r in raw:
        g = int(r["games"])
        w = int(r["wins"])
        enriched.append(
            {
                "item_id": int(r["item_id"]),
                "games": g,
                "wins": w,
                "win_rate": round(w / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
            }
        )

    tier_entries = [(i["item_id"], i["wilson_low"], i["games"]) for i in enriched]
    tiered = assign_tiers(tier_entries, min_games=0)
    tier_map = {t.key: t.tier for t in tiered}
    for i in enriched:
        i["tier"] = tier_map.get(i["item_id"])
    enriched.sort(key=_tier_then_winrate_sort_key, reverse=True)
    enriched = enriched[:limit]

    return {
        "patch": patch,
        "patches_used": patches,
        "category": category,
        "total_player_games": total_games,
        "items": enriched,
    }


def _patch_clause(patches: list[str], alias: str = "p") -> tuple[str, dict[str, str]]:
    """Build a 'AND <alias>.patch IN (...)' clause + params dict. Empty list -> no clause."""
    if not patches:
        return "", {}
    if len(patches) == 1:
        return f"AND {alias}.patch = :patch_0", {"patch_0": patches[0]}
    placeholders = ", ".join(f":patch_{i}" for i in range(len(patches)))
    return f"AND {alias}.patch IN ({placeholders})", {
        f"patch_{i}": p for i, p in enumerate(patches)
    }


@router.get("/arena/champions/{champion_id}")
async def arena_champion_detail(
    champion_id: int,
    db: DbDep,
    patch: Annotated[
        str | None,
        Query(description="Specific patch like '16.9', or 'all' for all patches. Default: latest patch only."),
    ] = None,
    top: Annotated[int, Query(ge=1, le=100)] = 25,
    with_rarity: Annotated[
        bool,
        Query(description="Limit augments to hex (default true)"),
    ] = True,
    min_item_gold: Annotated[
        int,
        Query(description="Min gold to include. Default 100 keeps boots (~500g) and prismatic so the UI can categorize."),
    ] = 100,
    min_games: Annotated[int, Query(ge=1, description="Per-row minimum games before display")] = 3,
) -> dict[str, Any]:
    """Recommend augments + items for a champion in Arena. Latest patch only."""
    patches = await _resolve_patches(db, patch)
    patch_clause_p, patch_params = _patch_clause(patches, alias="p")

    # ---- Champion overall summary from participants ----
    overall_sql = text(
        f"""
        SELECT
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p
        WHERE p.queue_id IN (1700, 1710)
          AND p.champion_id = :cid
          AND p.placement IS NOT NULL
          {patch_clause_p}
        """
    )
    params_overall: dict[str, Any] = {"cid": champion_id, **patch_params}
    overall = (await db.execute(overall_sql, params_overall)).mappings().first()
    overall_summary = None
    if overall and overall["games"]:
        g = int(overall["games"])
        w = int(overall["wins"])
        overall_summary = {
            "games": g,
            "wins": w,
            "top1": int(overall["top1"]),
            "win_rate": round(w / g, 4),
            "wilson_low": round(wilson_lower_bound(w, g), 4),
            "avg_placement": float(overall["avg_placement"]) if overall["avg_placement"] is not None else None,
        }

    # ---- Augments computed directly from participants (bypass aggregator) ----
    rarity_join = ""
    rarity_where = ""
    if with_rarity:
        rarity_join = "JOIN augments a ON a.id = aug_id"
        rarity_where = "AND a.rarity IS NOT NULL"

    aug_sql = text(
        f"""
        SELECT
            aug_id AS augment_id,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p, UNNEST(p.augments) AS aug_id
        {rarity_join}
        WHERE p.queue_id IN (1700, 1710)
          AND p.champion_id = :cid
          AND p.placement IS NOT NULL
          {rarity_where}
          {patch_clause_p}
        GROUP BY aug_id
        HAVING COUNT(*) >= :min_games
        """
    )
    params_aug: dict[str, Any] = {"cid": champion_id, "min_games": min_games, **patch_params}
    aug_raw = (await db.execute(aug_sql, params_aug)).mappings().all()

    augments_enriched = []
    for r in aug_raw:
        g = int(r["games"])
        w = int(r["wins"])
        augments_enriched.append(
            {
                "augment_id": int(r["augment_id"]),
                "games": g,
                "wins": w,
                "top1": int(r["top1"]),
                "win_rate": round(w / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
                "avg_placement": float(r["avg_placement"]) if r["avg_placement"] is not None else None,
            }
        )
    aug_tier_entries = [(a["augment_id"], a["wilson_low"], a["games"]) for a in augments_enriched]
    aug_tiered = assign_tiers(aug_tier_entries, min_games=0)
    aug_tier_map = {t.key: t.tier for t in aug_tiered}
    for a in augments_enriched:
        a["tier"] = aug_tier_map.get(a["augment_id"])
    augments_enriched.sort(key=_tier_then_winrate_sort_key, reverse=True)
    augments_enriched = augments_enriched[:top]

    # ---- Items computed directly from participants ----
    item_sql = text(
        f"""
        SELECT
            it_id AS item_id,
            COUNT(*) AS games,
            SUM(CASE WHEN p.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            MAX(i.gold) AS gold
        FROM participants p, UNNEST(p.items) AS it_id
        JOIN items i ON i.id = it_id
        WHERE p.queue_id IN (1700, 1710)
          AND p.champion_id = :cid
          AND p.placement IS NOT NULL
          AND it_id > 0
          AND COALESCE(i.gold, 0) >= :min_gold
          {patch_clause_p}
        GROUP BY it_id
        HAVING COUNT(*) >= :min_games
        """
    )
    params_item: dict[str, Any] = {
        "cid": champion_id,
        "min_gold": min_item_gold,
        "min_games": min_games,
        **patch_params,
    }
    item_raw = (await db.execute(item_sql, params_item)).mappings().all()

    items_enriched = []
    for r in item_raw:
        g = int(r["games"])
        w = int(r["wins"])
        items_enriched.append(
            {
                "item_id": int(r["item_id"]),
                "games": g,
                "wins": w,
                "win_rate": round(w / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
            }
        )
    item_tier_entries = [(i["item_id"], i["wilson_low"], i["games"]) for i in items_enriched]
    item_tiered = assign_tiers(item_tier_entries, min_games=0)
    item_tier_map = {t.key: t.tier for t in item_tiered}
    for i in items_enriched:
        i["tier"] = item_tier_map.get(i["item_id"])
    items_enriched.sort(key=_tier_then_winrate_sort_key, reverse=True)
    # Bigger limit here so frontend can categorise (boots / prismatic / core)
    items_enriched = items_enriched[: top * 4]

    # ---- Champion synergies (Arena 2v2: same sub_team_id in same match) ----
    synergy_sql = text(
        f"""
        SELECT
            p2.champion_id AS partner_id,
            COUNT(*) AS games,
            SUM(CASE WHEN p1.placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN p1.placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(p1.placement)::NUMERIC(4,2) AS avg_placement
        FROM participants p1
        JOIN participants p2
          ON p1.match_id = p2.match_id
         AND p1.game_creation = p2.game_creation
         AND p1.sub_team_id = p2.sub_team_id
         AND p1.id <> p2.id
        WHERE p1.queue_id IN (1700, 1710)
          AND p1.champion_id = :cid
          AND p1.placement IS NOT NULL
          AND p1.sub_team_id IS NOT NULL
          {patch_clause_p.replace("p.patch", "p1.patch")}
        GROUP BY p2.champion_id
        HAVING COUNT(*) >= :min_games
        """
    )
    params_syn: dict[str, Any] = {
        "cid": champion_id,
        "min_games": min_games,
        **patch_params,
    }
    syn_raw = (await db.execute(synergy_sql, params_syn)).mappings().all()

    synergies = []
    for r in syn_raw:
        g = int(r["games"])
        w = int(r["wins"])
        synergies.append(
            {
                "partner_champion_id": int(r["partner_id"]),
                "games": g,
                "wins": w,
                "top1": int(r["top1"]),
                "win_rate": round(w / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
                "avg_placement": float(r["avg_placement"]) if r["avg_placement"] is not None else None,
            }
        )
    syn_tier_entries = [(s["partner_champion_id"], s["wilson_low"], s["games"]) for s in synergies]
    syn_tiered = assign_tiers(syn_tier_entries, min_games=0)
    syn_tier_map = {t.key: t.tier for t in syn_tiered}
    for s in synergies:
        s["tier"] = syn_tier_map.get(s["partner_champion_id"])
    synergies.sort(key=_tier_then_winrate_sort_key, reverse=True)
    synergies = synergies[: top * 2]

    # ---- Core build paths: most common 2-3 item combinations ----
    # For each participant, take CORE items (gold >= 1500, not boots, not prismatic),
    # sorted by id for canonical grouping. GROUP BY the sorted tuple.
    build_sql = text(
        f"""
        WITH per_participant AS (
            SELECT
                p.placement,
                ARRAY(
                    SELECT it
                    FROM unnest(p.items) AS it
                    WHERE it > 0
                      AND EXISTS (
                        SELECT 1 FROM items i
                        WHERE i.id = it
                          AND COALESCE(i.gold, 0) >= 1500
                          AND NOT 'Boots' = ANY(COALESCE(i.tags, ARRAY[]::text[]))
                          AND NOT (i.id BETWEEN 228000 AND 228999 AND COALESCE(i.gold,0) >= 2750)
                          AND NOT (i.id BETWEEN 443000 AND 447999 AND COALESCE(i.gold,0) >= 2750)
                      )
                    ORDER BY it
                    LIMIT 3
                ) AS build
            FROM participants p
            WHERE p.queue_id IN (1700, 1710)
              AND p.champion_id = :cid
              AND p.placement IS NOT NULL
              {patch_clause_p}
        )
        SELECT
            build,
            COUNT(*) AS games,
            SUM(CASE WHEN placement BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN placement = 1 THEN 1 ELSE 0 END) AS top1,
            AVG(placement)::NUMERIC(4,2) AS avg_placement
        FROM per_participant
        WHERE array_length(build, 1) >= 2
        GROUP BY build
        HAVING COUNT(*) >= :min_games
        ORDER BY COUNT(*) DESC
        """
    )
    params_build: dict[str, Any] = {
        "cid": champion_id,
        "min_games": min_games,
        **patch_params,
    }
    build_raw = (await db.execute(build_sql, params_build)).mappings().all()

    build_paths = []
    champ_total_games = overall_summary["games"] if overall_summary else 0
    for r in build_raw:
        g = int(r["games"])
        w = int(r["wins"])
        t1 = int(r["top1"])
        build_paths.append(
            {
                "items": list(r["build"]),
                "games": g,
                "wins": w,
                "top1": t1,
                "win_rate": round(w / g, 4) if g else 0.0,
                "top1_rate": round(t1 / g, 4) if g else 0.0,
                "wilson_low": round(wilson_lower_bound(w, g), 4),
                "pick_rate": round(g / champ_total_games, 4) if champ_total_games > 0 else None,
                "avg_placement": float(r["avg_placement"]) if r["avg_placement"] is not None else None,
            }
        )
    bp_tier_entries = [
        (tuple(b["items"]), b["wilson_low"], b["games"]) for b in build_paths
    ]
    bp_tiered = assign_tiers(bp_tier_entries, min_games=0)
    bp_tier_map = {t.key: t.tier for t in bp_tiered}
    for b in build_paths:
        b["tier"] = bp_tier_map.get(tuple(b["items"]))
    build_paths.sort(key=_tier_then_winrate_sort_key, reverse=True)
    build_paths = build_paths[: top]

    return {
        "champion_id": champion_id,
        "patch": patch,
        "patches_used": patches,
        "with_rarity": with_rarity,
        "min_item_gold": min_item_gold,
        "overall": overall_summary,
        "top_augments": augments_enriched,
        "top_items": items_enriched,
        "synergies": synergies,
        "build_paths": build_paths,
    }
