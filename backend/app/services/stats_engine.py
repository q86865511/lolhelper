"""Statistics computations: Wilson score interval, tier assignment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

# 95% confidence
Z_95 = 1.959963984540054


def wilson_lower_bound(wins: int, total: int, z: float = Z_95) -> float:
    """Wilson score interval lower bound for a binomial proportion.

    Used as the ranking metric: penalises small samples so e.g. 5/5 (100%)
    ranks below 800/1000 (80%).

    Reference: https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval
    """
    if total <= 0:
        return 0.0
    if wins < 0 or wins > total:
        raise ValueError(f"invalid wins={wins} total={total}")

    p_hat = wins / total
    denom = 1.0 + (z * z) / total
    center = p_hat + (z * z) / (2.0 * total)
    margin = z * math.sqrt(
        (p_hat * (1.0 - p_hat) / total) + ((z * z) / (4.0 * total * total))
    )
    return max(0.0, min(1.0, (center - margin) / denom))


def wilson_upper_bound(wins: int, total: int, z: float = Z_95) -> float:
    if total <= 0:
        return 1.0
    p_hat = wins / total
    denom = 1.0 + (z * z) / total
    center = p_hat + (z * z) / (2.0 * total)
    margin = z * math.sqrt(
        (p_hat * (1.0 - p_hat) / total) + ((z * z) / (4.0 * total * total))
    )
    return max(0.0, min(1.0, (center + margin) / denom))


# --- Tier assignment ----------------------------------------------------------

# Configurable cutoffs (percentile thresholds within a population).
DEFAULT_TIER_CUTOFFS: tuple[tuple[str, float], ...] = (
    ("S", 0.95),
    ("A", 0.80),
    ("B", 0.50),
    ("C", 0.20),
    ("D", 0.00),
)


@dataclass(frozen=True)
class TieredEntry:
    key: object
    wilson_low: float
    games: int
    tier: str


def assign_tiers(
    entries: Iterable[tuple[object, float, int]],
    min_games: int,
    cutoffs: tuple[tuple[str, float], ...] = DEFAULT_TIER_CUTOFFS,
) -> list[TieredEntry]:
    """Given (key, wilson_low, games) tuples, sort and assign S/A/B/C/D tiers.

    Entries with `games < min_games` are dropped (insufficient sample).
    Cutoffs are *percentile* thresholds within the eligible set.
    """
    eligible = [(k, w, g) for (k, w, g) in entries if g >= min_games]
    if not eligible:
        return []

    eligible.sort(key=lambda x: x[1], reverse=True)
    n = len(eligible)
    out: list[TieredEntry] = []
    for idx, (k, w, g) in enumerate(eligible):
        # idx=0 is the best -> highest percentile
        percentile = 1.0 - (idx / max(1, n - 1)) if n > 1 else 1.0
        tier = next(
            (label for label, threshold in cutoffs if percentile >= threshold),
            "D",
        )
        out.append(TieredEntry(key=k, wilson_low=w, games=g, tier=tier))
    return out


# --- Arena-specific "win" semantics ------------------------------------------

ARENA_WIN_THRESHOLD = 4  # placement <= 4 counts as a "win" (advances)


def arena_is_win(placement: int | None) -> bool:
    """Arena 'win' = top 4 finish (advances to second round)."""
    return placement is not None and 1 <= placement <= ARENA_WIN_THRESHOLD


def arena_is_top1(placement: int | None) -> bool:
    return placement == 1
