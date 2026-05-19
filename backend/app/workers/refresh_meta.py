"""Refresh static Riot metadata (augments, items, champions) from Community Dragon.

Runs daily. Idempotent: UPSERT keyed on `id`.

Fetches the primary locale (zh_tw for Taiwan users) and falls back to English
(`default`) for entries the primary locale doesn't translate. The merged set
of names lands in the `name` column of each metadata table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.models import Augment, Champion, Item
from app.db.session import session_scope
from app.services import community_dragon

log = get_logger(__name__)

PRIMARY_LOCALE = "zh_tw"
FALLBACK_LOCALE = "default"  # English

_RARITY_MAP: dict[str, int] = {
    "kSilver": 1,
    "kGold": 2,
    "kPrismatic": 3,
}


def _coerce_rarity(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _RARITY_MAP.get(value)
    return None


def _augment_name(entry: dict[str, Any]) -> str | None:
    """Augment name: prefer nameTRA (the localized name in CDragon)."""
    for key in ("nameTRA", "name", "simpleNameTRA"):
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _augment_icon(entry: dict[str, Any]) -> str | None:
    for key in ("iconLarge", "iconSmall", "augmentLargeIconPath", "augmentSmallIconPath"):
        v = entry.get(key)
        if isinstance(v, str) and v:
            return v
    return None


async def refresh_augments() -> int:
    # The "lean" file gives us official IDs + nameTRA, the "rich" file has
    # description/tooltip. We merge them by id.
    primary_lean = await community_dragon.fetch_arena_augments(PRIMARY_LOCALE)
    fallback_lean = await community_dragon.fetch_arena_augments(FALLBACK_LOCALE)
    rich = await community_dragon.fetch_arena_augments_with_desc(PRIMARY_LOCALE)
    if not primary_lean and not fallback_lean and not rich:
        log.warning("refresh_augments.empty")
        return 0

    fallback_names: dict[int, str] = {}
    for a in fallback_lean:
        aid = a.get("id")
        if isinstance(aid, int):
            n = _augment_name(a)
            if n:
                fallback_names[aid] = n

    rich_by_id: dict[int, dict[str, Any]] = {}
    for r in rich:
        rid = r.get("id")
        if isinstance(rid, int):
            rich_by_id[rid] = r

    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    sources: list[dict[str, Any]] = list(primary_lean) + [
        a for a in fallback_lean if a.get("id") not in {p.get("id") for p in primary_lean}
    ]
    for a in sources:
        aug_id = a.get("id")
        if not isinstance(aug_id, int) or aug_id in seen:
            continue
        seen.add(aug_id)
        rich_entry = rich_by_id.get(aug_id, {})
        name = _augment_name(a) or rich_entry.get("name") or fallback_names.get(aug_id) or str(aug_id)
        description = (
            rich_entry.get("desc")
            or rich_entry.get("tooltip")
            or a.get("desc")
            or a.get("tooltip")
            or a.get("descriptionTRA")
        )
        rows.append(
            {
                "id": aug_id,
                "name": name,
                "rarity": _coerce_rarity(a.get("rarity") or rich_entry.get("rarity")),
                "description": description,
                "icon_path": _augment_icon(a) or rich_entry.get("iconLarge") or rich_entry.get("iconSmall"),
                "active": True,
                "updated_at": now,
            }
        )
    if not rows:
        return 0
    async with session_scope() as db:
        stmt = pg_insert(Augment).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "rarity": stmt.excluded.rarity,
                "description": stmt.excluded.description,
                "icon_path": stmt.excluded.icon_path,
                "active": True,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
    log.info("refresh_augments.done", count=len(rows), with_desc=sum(1 for r in rows if r["description"]))
    return len(rows)


async def refresh_champions() -> int:
    primary = await community_dragon.fetch_champion_summary(PRIMARY_LOCALE)
    fallback = await community_dragon.fetch_champion_summary(FALLBACK_LOCALE)

    fallback_by_id = {c["id"]: c for c in fallback if isinstance(c.get("id"), int)}
    now = datetime.now(timezone.utc)
    rows = []
    seen: set[int] = set()
    sources = list(primary) + [c for c in fallback if c.get("id") not in {p.get("id") for p in primary}]
    for c in sources:
        cid = c.get("id")
        if not isinstance(cid, int) or cid in seen or cid <= 0:
            continue
        seen.add(cid)
        name = c.get("name") or fallback_by_id.get(cid, {}).get("name") or str(cid)
        # alias stays English (e.g. "Yasuo") since OP.GG / data dragon use it
        alias = c.get("alias") or fallback_by_id.get(cid, {}).get("alias") or name
        portrait = c.get("squarePortraitPath") or fallback_by_id.get(cid, {}).get("squarePortraitPath")
        rows.append(
            {
                "id": cid,
                "key": alias,
                "name": name,
                "title": c.get("description"),
                "tags": c.get("roles") or fallback_by_id.get(cid, {}).get("roles") or [],
                "icon_path": portrait,
                "updated_at": now,
            }
        )
    if not rows:
        return 0
    async with session_scope() as db:
        stmt = pg_insert(Champion).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "key": stmt.excluded.key,
                "name": stmt.excluded.name,
                "title": stmt.excluded.title,
                "tags": stmt.excluded.tags,
                "icon_path": stmt.excluded.icon_path,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
    log.info("refresh_champions.done", count=len(rows), locale=PRIMARY_LOCALE)
    return len(rows)


async def refresh_items() -> int:
    primary = await community_dragon.fetch_items(PRIMARY_LOCALE)
    fallback = await community_dragon.fetch_items(FALLBACK_LOCALE)

    fallback_by_id = {it["id"]: it for it in fallback if isinstance(it.get("id"), int)}
    now = datetime.now(timezone.utc)
    rows = []
    seen: set[int] = set()
    sources = list(primary) + [it for it in fallback if it.get("id") not in {p.get("id") for p in primary}]
    for it in sources:
        item_id = it.get("id")
        if not isinstance(item_id, int) or item_id in seen or item_id <= 0:
            continue
        seen.add(item_id)
        fallback_item = fallback_by_id.get(item_id, {})
        name = it.get("name") or fallback_item.get("name") or str(item_id)
        description = it.get("description") or fallback_item.get("description")
        rows.append(
            {
                "id": item_id,
                "name": name,
                "description": description,
                "gold": (it.get("priceTotal") or it.get("price")),
                "tags": it.get("categories") or [],
                "icon_path": it.get("iconPath"),
                "updated_at": now,
            }
        )
    if not rows:
        return 0
    async with session_scope() as db:
        stmt = pg_insert(Item).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "gold": stmt.excluded.gold,
                "tags": stmt.excluded.tags,
                "icon_path": stmt.excluded.icon_path,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
    log.info("refresh_items.done", count=len(rows), with_desc=sum(1 for r in rows if r["description"]))
    return len(rows)


async def refresh_meta_all(ctx: dict | None = None) -> dict[str, int]:  # noqa: ARG001
    return {
        "augments": await refresh_augments(),
        "champions": await refresh_champions(),
        "items": await refresh_items(),
    }
