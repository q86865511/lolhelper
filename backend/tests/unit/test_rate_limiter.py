"""Rate limiter behaviour tests."""

from __future__ import annotations

import time

import pytest
from app.services.riot.rate_limiter import RiotRateLimiter, TokenBucket


@pytest.mark.asyncio
async def test_bucket_allows_burst_within_capacity() -> None:
    bucket = TokenBucket([(5, 1.0)])
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    # 5 acquires fit in the window with no waiting
    assert elapsed < 0.2


@pytest.mark.asyncio
async def test_bucket_blocks_on_capacity() -> None:
    bucket = TokenBucket([(3, 0.5)])
    for _ in range(3):
        await bucket.acquire()
    # 4th must wait ~0.5s
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert 0.4 < elapsed < 0.8


@pytest.mark.asyncio
async def test_multi_window_takes_strictest_limit() -> None:
    bucket = TokenBucket([(10, 0.1), (3, 1.0)])
    for _ in range(3):
        await bucket.acquire()
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    # Bound by 3/1s, so 4th waits ~1s
    assert 0.9 < elapsed < 1.3


@pytest.mark.asyncio
async def test_region_isolation() -> None:
    limiter = RiotRateLimiter(app_limits=[(2, 0.5)])
    # Two regions should NOT share budget — each has its own bucket
    await limiter.acquire("kr")
    await limiter.acquire("kr")
    start = time.monotonic()
    await limiter.acquire("na")  # different region, should not block
    await limiter.acquire("na")
    elapsed = time.monotonic() - start
    assert elapsed < 0.2
