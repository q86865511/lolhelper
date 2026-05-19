"""OP.GG URL builder tests."""

from __future__ import annotations

from app.services.opgg_link import opgg_champion_url, opgg_summoner_url


def test_arena_champion_url() -> None:
    assert (
        opgg_champion_url("Yasuo", mode="arena")
        == "https://www.op.gg/modes/arena/yasuo/build"
    )


def test_aram_champion_url() -> None:
    assert opgg_champion_url("Lulu", mode="aram") == "https://www.op.gg/modes/aram/lulu/build"


def test_summoner_url_known_platform() -> None:
    url = opgg_summoner_url("KR", "Hide on Bush", "KR1")
    assert url is not None
    assert "/summoners/kr/" in url
    # space in name should be percent-encoded
    assert "Hide%20on%20Bush" in url
    assert "KR1" in url


def test_summoner_url_unknown_platform_returns_none() -> None:
    assert opgg_summoner_url("XYZ9", "name", "tag") is None
