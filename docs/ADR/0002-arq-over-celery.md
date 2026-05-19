# ADR 0002 — ARQ over Celery for background jobs

**Date**: 2026-05-18
**Status**: Accepted

## Context

Need a task queue for:
- Crawler dispatch (BFS over puuids)
- Match detail fetcher
- Stats aggregation
- Daily metadata refresh

Both ARQ and Celery are mature; Celery is far more popular in Python.

## Decision

Use **ARQ**:
- Native async (matches FastAPI / asyncpg / httpx stack)
- Redis-only (we already need Redis for rate limit + cache)
- Built-in cron syntax
- Smaller surface area (~3k LoC vs Celery's ~50k)

## Why not Celery

- Synchronous worker model fights with async-everywhere
- Needs a separate broker concept on top of Redis (or RabbitMQ)
- Result backend is overkill for our fire-and-forget tasks
- We don't need most of Celery's features (workflows, canvas, etc.)

## Consequences

- ✅ Same async model end-to-end; can `await` Riot client inside tasks
- ⚠️ Smaller community; if a corner case bites we have to read source
- ⚠️ No "flower" equivalent; we'll build a `/meta/worker-status` endpoint
