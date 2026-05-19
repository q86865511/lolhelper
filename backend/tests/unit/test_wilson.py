"""Wilson score interval tests.

Reference values computed against an independent implementation (statsmodels /
manual formula) at z=1.959963984540054 (95% confidence).
"""

from __future__ import annotations

import math

import pytest

from app.services.stats_engine import (
    assign_tiers,
    wilson_lower_bound,
    wilson_upper_bound,
)


class TestWilsonLowerBound:
    def test_zero_total_returns_zero(self) -> None:
        assert wilson_lower_bound(0, 0) == 0.0

    def test_zero_wins(self) -> None:
        # 0/100 -> effectively zero (within float epsilon)
        assert wilson_lower_bound(0, 100) < 1e-9

    def test_full_wins_small_sample_is_penalised(self) -> None:
        # 5/5 should NOT be 100%; small-sample penalty
        five_of_five = wilson_lower_bound(5, 5)
        thousand_of_thousand = wilson_lower_bound(1000, 1000)
        assert five_of_five < 0.7
        assert thousand_of_thousand > 0.99
        assert thousand_of_thousand > five_of_five

    def test_known_value_50_of_100(self) -> None:
        # ~0.4040 expected (95% Wilson lower for 50/100)
        val = wilson_lower_bound(50, 100)
        assert math.isclose(val, 0.4038, abs_tol=0.005)

    def test_known_value_500_of_1000(self) -> None:
        val = wilson_lower_bound(500, 1000)
        # ~0.4688
        assert math.isclose(val, 0.4688, abs_tol=0.005)

    def test_monotonic_in_total_when_rate_constant(self) -> None:
        # When win_rate is held at 0.6, more samples => higher lower bound
        a = wilson_lower_bound(6, 10)
        b = wilson_lower_bound(60, 100)
        c = wilson_lower_bound(600, 1000)
        assert a < b < c

    def test_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            wilson_lower_bound(-1, 10)
        with pytest.raises(ValueError):
            wilson_lower_bound(11, 10)


class TestWilsonUpperBound:
    def test_upper_above_lower(self) -> None:
        lo = wilson_lower_bound(50, 100)
        hi = wilson_upper_bound(50, 100)
        assert hi > lo
        assert hi > 0.5  # observed rate is 0.5; upper should exceed it


class TestAssignTiers:
    def test_empty_returns_empty(self) -> None:
        assert assign_tiers([], min_games=10) == []

    def test_filters_min_games(self) -> None:
        entries = [("a", 0.8, 5), ("b", 0.7, 100)]
        result = assign_tiers(entries, min_games=10)
        assert len(result) == 1
        assert result[0].key == "b"

    def test_top_entry_gets_S(self) -> None:
        entries = [
            ("worst", 0.30, 100),
            ("mid1", 0.45, 100),
            ("mid2", 0.50, 100),
            ("best", 0.60, 100),
        ]
        result = assign_tiers(entries, min_games=10)
        # sorted desc, best is first
        assert result[0].key == "best"
        assert result[0].tier == "S"
        assert result[-1].key == "worst"
        assert result[-1].tier == "D"

    def test_single_entry_is_S(self) -> None:
        result = assign_tiers([("only", 0.5, 100)], min_games=10)
        assert len(result) == 1
        assert result[0].tier == "S"
