"""Two-tier token bucket for Riot API rate limits.

Riot enforces:
  - **App rate limit**: total budget per key (personal: 20/s + 100/120s)
  - **Method rate limit**: per endpoint × region (e.g. match-v5 detail: 2000/10s prod)

State is held in Redis so multiple workers/instances share the budget.

For M1 we ship the in-memory implementation and Redis-backed variant later
when we go multi-worker. Both implement `acquire(cost)`.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class _Window:
    """Sliding-window counter. Stores timestamps of recent acquires."""

    capacity: int
    window_seconds: float
    _events: list[float] = field(default_factory=list)

    def _purge(self, now: float) -> None:
        cutoff = now - self.window_seconds
        # Trim from the head (sorted ascending by time)
        i = 0
        n = len(self._events)
        while i < n and self._events[i] < cutoff:
            i += 1
        if i > 0:
            del self._events[:i]

    def time_until_available(self, now: float) -> float:
        self._purge(now)
        if len(self._events) < self.capacity:
            return 0.0
        # Wait until the oldest event ages out
        return max(0.0, self._events[0] + self.window_seconds - now)

    def record(self, now: float) -> None:
        self._events.append(now)


class TokenBucket:
    """Composite of multiple sliding windows (App rate limit has 2: 1s + 120s)."""

    def __init__(self, limits: list[tuple[int, float]]) -> None:
        """limits: list of (capacity, window_seconds) pairs."""
        self._windows = [_Window(cap, win) for cap, win in limits]
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until all windows allow one more request, then record."""
        while True:
            async with self._lock:
                now = time.monotonic()
                wait_times = [w.time_until_available(now) for w in self._windows]
                wait = max(wait_times)
                if wait <= 0.0:
                    for w in self._windows:
                        w.record(now)
                    return
            await asyncio.sleep(wait + 0.01)

    def snapshot(self) -> list[dict[str, float | int]]:
        now = time.monotonic()
        return [
            {
                "capacity": w.capacity,
                "window_seconds": w.window_seconds,
                "used": sum(1 for t in w._events if t >= now - w.window_seconds),
            }
            for w in self._windows
        ]


# Personal key default budget (Riot docs as of 2025)
PERSONAL_APP_LIMITS: list[tuple[int, float]] = [
    (20, 1.0),     # 20 / 1s
    (100, 120.0),  # 100 / 120s
]

# Production key default (varies per key; can be raised dynamically from headers)
PRODUCTION_APP_LIMITS: list[tuple[int, float]] = [
    (500, 10.0),
    (30_000, 600.0),
]


class RegionLimiter:
    """Per-region app bucket + per-method buckets."""

    def __init__(self, app_limits: list[tuple[int, float]] | None = None) -> None:
        self._app = TokenBucket(app_limits or PERSONAL_APP_LIMITS)
        self._methods: dict[str, TokenBucket] = {}

    async def acquire(self, method_id: str | None = None) -> None:
        await self._app.acquire()
        if method_id is not None and method_id in self._methods:
            await self._methods[method_id].acquire()

    def configure_method(self, method_id: str, limits: list[tuple[int, float]]) -> None:
        self._methods[method_id] = TokenBucket(limits)


class RiotRateLimiter:
    """Top-level limiter dispatching to per-region buckets."""

    def __init__(self, app_limits: list[tuple[int, float]] | None = None) -> None:
        self._regions: dict[str, RegionLimiter] = {}
        self._app_limits = app_limits or PERSONAL_APP_LIMITS

    def _region(self, region: str) -> RegionLimiter:
        if region not in self._regions:
            self._regions[region] = RegionLimiter(self._app_limits)
        return self._regions[region]

    async def acquire(self, region: str, method_id: str | None = None) -> None:
        await self._region(region).acquire(method_id)
