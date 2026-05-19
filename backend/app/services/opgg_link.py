"""OP.GG URL builders (we link out, never scrape)."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

OPGG_BASE = "https://www.op.gg"

OpggRegion = Literal[
    "kr", "jp", "na", "euw", "eune", "oce", "br", "lan", "las", "ru", "tr", "sg", "ph", "th", "tw", "vn",
]

# Riot platform -> OP.GG region segment
PLATFORM_TO_OPGG: dict[str, OpggRegion] = {
    "KR": "kr", "JP1": "jp", "NA1": "na", "EUW1": "euw", "EUN1": "eune",
    "OC1": "oce", "BR1": "br", "LA1": "lan", "LA2": "las", "RU": "ru",
    "TR1": "tr", "SG2": "sg", "PH2": "ph", "TH2": "th", "TW2": "tw", "VN2": "vn",
}


def opgg_champion_url(champ_key: str, *, mode: Literal["arena", "aram"] = "arena") -> str:
    """e.g. opgg_champion_url('Yasuo') -> 'https://www.op.gg/modes/arena/yasuo/build'"""
    if mode == "arena":
        return f"{OPGG_BASE}/modes/arena/{quote(champ_key.lower())}/build"
    return f"{OPGG_BASE}/modes/aram/{quote(champ_key.lower())}/build"


def opgg_summoner_url(platform: str, game_name: str, tag_line: str) -> str | None:
    region = PLATFORM_TO_OPGG.get(platform.upper())
    if region is None:
        return None
    name = quote(f"{game_name}-{tag_line}", safe="")
    return f"{OPGG_BASE}/summoners/{region}/{name}"
