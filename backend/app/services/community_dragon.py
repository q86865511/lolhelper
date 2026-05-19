"""Community Dragon: source for Arena augment metadata.

Riot's Data Dragon does NOT cover Arena augments — Community Dragon does.

Base URL: https://raw.communitydragon.org/latest/...
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

CDRAGON_BASE = "https://raw.communitydragon.org/latest"

# Locale codes available on CDragon: default (English), zh_tw, zh_cn, ja_jp, ko_kr, ...
DEFAULT_LOCALE = "zh_tw"


def _augments_url(locale: str) -> str:
    return f"{CDRAGON_BASE}/plugins/rcp-be-lol-game-data/global/{locale}/v1/cherry-augments.json"


def _items_url(locale: str) -> str:
    return f"{CDRAGON_BASE}/plugins/rcp-be-lol-game-data/global/{locale}/v1/items.json"


def _champion_summary_url(locale: str) -> str:
    return f"{CDRAGON_BASE}/plugins/rcp-be-lol-game-data/global/{locale}/v1/champion-summary.json"


async def fetch_arena_augments(locale: str = DEFAULT_LOCALE) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_augments_url(locale))
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "augments" in data:
            return data["augments"]
        if isinstance(data, list):
            return data
        log.warning("cdragon.augments.unexpected_shape", keys=list(data.keys())[:5])
        return []


async def fetch_items(locale: str = DEFAULT_LOCALE) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_items_url(locale))
        resp.raise_for_status()
        return resp.json()


async def fetch_champion_summary(locale: str = DEFAULT_LOCALE) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_champion_summary_url(locale))
        resp.raise_for_status()
        data = resp.json()
        return [c for c in data if c.get("id", -1) > 0]


def _arena_descriptive_url(locale: str) -> str:
    """Richer Arena augment data with descriptions, calculations, dataValues."""
    return f"{CDRAGON_BASE}/cdragon/arena/{locale}.json"


async def fetch_arena_augments_with_desc(locale: str = DEFAULT_LOCALE) -> list[dict[str, Any]]:
    """Returns augments enriched with `name`, `desc`, `tooltip`, `rarity`, icons.

    Distinct from `fetch_arena_augments` (which only has the lean
    name/icon/rarity record); this richer file lives at /cdragon/arena/{locale}.json.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_arena_descriptive_url(locale))
        resp.raise_for_status()
        data = resp.json()
        return list(data.get("augments", []))
