"""Metadata endpoints — health, patches, champions, augments, items.

These are read-mostly endpoints, cacheable, no auth required.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select, text

from app.deps import DbDep, RedisDep, SettingsDep

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/health")
async def health(
    db: DbDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    """Liveness + dependency check."""
    db_ok = False
    redis_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        pong = await redis.ping()
        redis_ok = bool(pong)
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "env": settings.app_env,
        "db": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "riot_keys_loaded": len(settings.riot_api_keys),
    }


@router.get("/patches")
async def list_patches(db: DbDep) -> dict[str, list[dict[str, Any]]]:
    from app.db.models import Patch

    rows = (
        await db.execute(select(Patch).order_by(Patch.version.desc()).limit(20))
    ).scalars().all()
    return {
        "patches": [
            {
                "version": p.version,
                "released_at": p.released_at.isoformat() if p.released_at else None,
                "is_current": p.is_current,
            }
            for p in rows
        ]
    }


@router.get("/augments")
async def list_augments(db: DbDep) -> dict[str, list[dict[str, Any]]]:
    from app.db.models import Augment

    rows = (
        await db.execute(select(Augment).where(Augment.active.is_(True)))
    ).scalars().all()
    return {
        "augments": [
            {
                "id": a.id,
                "name": a.name,
                "rarity": a.rarity,
                "description": a.description,
                "icon_path": a.icon_path,
            }
            for a in rows
        ]
    }


@router.get("/champions")
async def list_champions(db: DbDep) -> dict[str, list[dict[str, Any]]]:
    from app.db.models import Champion

    rows = (await db.execute(select(Champion).order_by(Champion.name))).scalars().all()
    return {
        "champions": [
            {
                "id": c.id,
                "key": c.key,
                "name": c.name,
                "title": c.title,
                "tags": c.tags,
                "icon_path": c.icon_path,
            }
            for c in rows
        ]
    }


@router.get("/items")
async def list_items(db: DbDep) -> dict[str, list[dict[str, Any]]]:
    from app.db.models import Item

    rows = (await db.execute(select(Item).order_by(Item.id))).scalars().all()
    return {
        "items": [
            {
                "id": it.id,
                "name": it.name,
                "description": it.description,
                "gold": it.gold,
                "tags": it.tags,
                "icon_path": it.icon_path,
            }
            for it in rows
        ]
    }
