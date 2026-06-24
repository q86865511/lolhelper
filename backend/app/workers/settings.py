"""ARQ worker configuration.

Runs scheduled cron jobs + reactive tasks. Started via:
    uv run arq app.workers.settings.WorkerSettings
"""

from __future__ import annotations

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.logging import configure_logging, get_logger
from app.settings import get_settings
from app.workers.aggregate import aggregate_arena_task
from app.workers.crawl_arena import dispatch_crawl_task
from app.workers.fetch_match import crawl_puuid_matches_task, fetch_match_task
from app.workers.refresh_meta import refresh_meta_all
from app.workers.seed_high_elo import seed_high_elo_task

log = get_logger(__name__)


async def startup(ctx: dict) -> None:
    configure_logging()
    settings = get_settings()
    log.info("worker.startup", env=settings.app_env, riot_keys=len(settings.riot_api_keys))
    ctx["settings"] = settings


async def shutdown(ctx: dict) -> None:
    log.info("worker.shutdown")
    from app.db.session import dispose_engine
    from app.services.riot.client import close_riot_client

    await close_riot_client()
    await dispose_engine()


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    url = settings.redis_url.removeprefix("redis://")
    host, _, port_db = url.partition(":")
    port, _, db = port_db.partition("/")
    return RedisSettings(
        host=host or "localhost",
        port=int(port or "6379"),
        database=int(db or "0"),
    )


class WorkerSettings:
    """ARQ entrypoint."""

    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    # Job concurrency per worker process. Bounded by Riot rate limit, not CPU.
    max_jobs = 10
    job_timeout = 120  # seconds per task
    keep_result = 60

    functions = [
        seed_high_elo_task,
        dispatch_crawl_task,
        crawl_puuid_matches_task,
        fetch_match_task,
        aggregate_arena_task,
        refresh_meta_all,
    ]

    cron_jobs = [
        # Dispatch crawl every 3 minutes
        cron(dispatch_crawl_task, minute=set(range(0, 60, 3)), run_at_startup=False),
        # Re-seed high elo every 24h at 03:30 UTC
        cron(seed_high_elo_task, hour={3}, minute={30}, run_at_startup=False),
        # Aggregate stats every 2 hours
        cron(aggregate_arena_task, hour=set(range(0, 24, 2)), minute={10}, run_at_startup=False),
        # Refresh Riot metadata daily at 05:10 UTC
        cron(refresh_meta_all, hour={5}, minute={10}, run_at_startup=False),
    ]
