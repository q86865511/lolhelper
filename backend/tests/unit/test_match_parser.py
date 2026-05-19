"""Parse a realistic Arena match payload and verify the row shape."""

from __future__ import annotations

import json
from pathlib import Path

from app.utils.match import (
    is_arena,
    is_mayhem,
    parse_match,
    patch_from_game_version,
    platform_from_match_id,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "arena_match_min.json"


def test_patch_from_game_version() -> None:
    assert patch_from_game_version("15.10.547.7926") == "15.10"
    assert patch_from_game_version("14.1.500.1") == "14.1"
    assert patch_from_game_version(None) is None
    assert patch_from_game_version("") is None
    assert patch_from_game_version("garbage") is None


def test_platform_from_match_id() -> None:
    assert platform_from_match_id("KR_7234567890") == "KR"
    assert platform_from_match_id("NA1_999") == "NA1"
    assert platform_from_match_id("nounderscore") == ""


def test_is_arena_and_mayhem() -> None:
    assert is_arena(1700) and is_arena(1710)
    assert not is_arena(450)
    assert is_mayhem(2400)
    assert not is_mayhem(1700)


def test_parse_arena_match_min() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    match_row, parts = parse_match(payload, source="riot_api")

    assert match_row["match_id"] == "KR_7234567890"
    assert match_row["platform"] == "KR"
    assert match_row["queue_id"] == 1700
    assert match_row["game_mode"] == "CHERRY"
    assert match_row["patch"] == "15.10"
    assert match_row["source"] == "riot_api"
    assert match_row["game_creation"].year == 2025

    assert len(parts) == 4

    yasuo = parts[0]
    assert yasuo["puuid"] == "puuid-a"
    assert yasuo["champion_id"] == 157
    assert yasuo["placement"] == 1
    assert yasuo["sub_team_id"] == 1
    # 6 augment slots, but only 4 valid (slot 5/6 are 0)
    assert yasuo["augments"] == [1205, 7, 8, 9]
    # 7 item slots (0..6); zeros preserved for indexing positions
    assert yasuo["items"] == [6671, 3072, 0, 0, 0, 0, 3340]

    lee_sin = parts[2]
    assert lee_sin["placement"] == 8
    assert lee_sin["augments"] == [1205]  # only one augment

    # All participants share game_creation / queue_id / patch (denormalised)
    creations = {p["game_creation"] for p in parts}
    assert len(creations) == 1
    assert all(p["queue_id"] == 1700 for p in parts)
    assert all(p["patch"] == "15.10" for p in parts)
