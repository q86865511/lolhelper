"""Match-V5 payload helpers.

Parses Riot's Match-V5 response into rows ready for INSERT into matches +
participants. Keeps the parsing logic isolated so workers / scripts /
ingest API can all share it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Arena queue IDs (gameMode=CHERRY)
ARENA_QUEUE_IDS = (1700, 1710)
# Mayhem (blocked by Match-V5, only arrives via .exe LCU upload)
MAYHEM_QUEUE_ID = 2400


def patch_from_game_version(game_version: str | None) -> str | None:
    """'15.10.547.7926' -> '15.10'. Handles None / malformed gracefully."""
    if not game_version:
        return None
    parts = game_version.split(".")
    if len(parts) < 2:
        return None
    return f"{parts[0]}.{parts[1]}"


def platform_from_match_id(match_id: str) -> str:
    """'KR_7234567890' -> 'KR'. Falls back to empty if malformed."""
    if "_" in match_id:
        return match_id.split("_", 1)[0]
    return ""


def _items_from_participant(p: dict[str, Any]) -> list[int]:
    return [int(p.get(f"item{i}", 0) or 0) for i in range(7)]


def _augments_from_participant(p: dict[str, Any]) -> list[int]:
    """Extract Arena augment ids from a participant DTO.

    Arena participants have `playerAugment1`..`playerAugment6` fields. Missing
    or 0 values are skipped. Order is preserved (selection order matters for
    visualisation, but stats aggregate per-augment regardless).
    """
    out: list[int] = []
    for i in range(1, 7):
        val = p.get(f"playerAugment{i}")
        if isinstance(val, int) and val > 0:
            out.append(val)
    return out


def parse_match(payload: dict[str, Any], source: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Convert a Riot Match-V5 payload into (match_row, participant_rows)."""
    info = payload.get("info", {})
    metadata = payload.get("metadata", {})
    match_id: str = metadata.get("matchId", "")
    if not match_id:
        raise ValueError("payload missing metadata.matchId")

    game_creation_ms = int(info.get("gameCreation", 0))
    game_creation = datetime.fromtimestamp(game_creation_ms / 1000.0, tz=timezone.utc)
    game_version = info.get("gameVersion")
    patch = patch_from_game_version(game_version)
    platform = info.get("platformId") or platform_from_match_id(match_id)
    queue_id = int(info.get("queueId", 0))

    match_row: dict[str, Any] = {
        "match_id": match_id,
        "platform": platform[:8],
        "queue_id": queue_id,
        "game_mode": (info.get("gameMode") or "")[:16],
        "game_version": (game_version or "")[:32] or None,
        "patch": patch,
        "game_creation": game_creation,
        "game_duration": int(info.get("gameDuration", 0)) or None,
        "source": source,
        "ingested_at": datetime.now(timezone.utc),
        # We DON'T persist raw_blob by default to keep DB lean; opt-in via worker setting
        "raw_blob": None,
    }

    participant_rows: list[dict[str, Any]] = []
    for p in info.get("participants", []) or []:
        # Arena placement lives in subteamPlacement / placement (game version
        # dependent). We coalesce both.
        placement_raw = p.get("subteamPlacement") or p.get("placement")
        placement = int(placement_raw) if isinstance(placement_raw, int) and placement_raw > 0 else None

        sub_team = p.get("playerSubteamId")
        if isinstance(sub_team, int) and sub_team <= 0:
            sub_team = None

        participant_rows.append(
            {
                "match_id": match_id,
                "puuid": p.get("puuid") or "",
                "team_id": p.get("teamId"),
                "sub_team_id": sub_team,
                "placement": placement,
                "champion_id": int(p.get("championId", 0)),
                "champion_name": (p.get("championName") or "")[:32] or None,
                "win": bool(p.get("win")) if p.get("win") is not None else None,
                "kills": p.get("kills"),
                "deaths": p.get("deaths"),
                "assists": p.get("assists"),
                "damage_dealt": p.get("totalDamageDealtToChampions"),
                "damage_taken": p.get("totalDamageTaken"),
                "gold_earned": p.get("goldEarned"),
                "items": _items_from_participant(p),
                "augments": _augments_from_participant(p),
                "summoner_spell1": p.get("summoner1Id"),
                "summoner_spell2": p.get("summoner2Id"),
                "game_creation": game_creation,
                "queue_id": queue_id,
                "patch": patch,
            }
        )
    return match_row, participant_rows


def is_arena(queue_id: int) -> bool:
    return queue_id in ARENA_QUEUE_IDS


def is_mayhem(queue_id: int) -> bool:
    return queue_id == MAYHEM_QUEUE_ID
