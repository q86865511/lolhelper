# Next Steps — implementation roadmap

The M1 skeleton is complete and verified:
- ✅ Monorepo (pnpm + Turborepo + uv) bootstrapped
- ✅ Postgres 16 + Redis running via docker-compose
- ✅ Alembic migration creates all 9 logical tables + 8 monthly partitions
- ✅ FastAPI live at `http://127.0.0.1:8000`; `/api/v1/meta/health` returns
  `{db: ok, redis: ok}`
- ✅ Riot client + rate limiter + stats engine implemented
- ✅ 22 unit tests pass

## To finish M1 (Arena stats site)

1. **Get a Riot API key** (free, 24-hour expiry):
   - <https://developer.riotgames.com/> → sign in with Riot account → copy key
   - Put in `.env` as `RIOT_API_KEYS=RGAPI-...`

2. **Populate metadata** (one-shot):
   ```bash
   cd backend
   uv run python -m scripts.refresh_metadata
   # Should INSERT ~200 champions, ~250 items, ~120 augments
   ```

3. **Implement crawler** (`backend/app/workers/`):
   - `seed_high_elo.py` — pull challenger/GM puuids per platform → INSERT crawl_state
   - `crawl_arena.py` — dispatcher that picks N puuids and enqueues fetch_match
   - `fetch_match.py` — single-match fetch + INSERT
   Hook into `WorkerSettings.functions` and `WorkerSettings.cron_jobs`.

4. **Implement aggregator** (`backend/app/workers/aggregate.py`):
   - GROUP BY (queue_id, augment_id, champion_id, patch)
   - Use `stats_engine.wilson_lower_bound` + `assign_tiers`
   - UPSERT into `augment_stats` / `item_stats`

5. **Implement auth**:
   - `backend/app/api/v1/auth.py` Google OAuth + JWT (authlib does most of it)
   - Wire `deps.get_current_user_id` to actually parse the JWT

6. **Spin up frontend**:
   ```bash
   pnpm install
   pnpm frontend:dev   # http://localhost:3000
   ```
   - Fill in `frontend/src/app/arena/champions/[champKey]/page.tsx` (ISR)
   - Hit `/api/proxy/stats/arena/champions/{id}` from server component

7. **Run end-to-end validation**:
   - Crawl for 24h → `SELECT count(*) FROM matches WHERE queue_id IN (1700,1710)` ≥ 5000
   - `curl /api/v1/stats/arena/augments?patch=current` → ≥ 30 rows
   - Playwright: home page renders < 2s, shows ≥ 10 augments

## To start M2 (.exe client + Mayhem ingest)

1. `pnpm install` to install Electron deps
2. `pnpm client:dev` to run Electron in dev mode
3. Implement `client/src/main/lcu/client.ts` (HTTPS request + ignore self-signed cert)
4. Implement `client/src/main/lcu/websocket.ts` (subscribe to gameflow / champ-select events)
5. Implement `client/src/main/ingest/uploader.ts` (electron-store JSON dedupe + retry queue)
6. Backend: `app/api/v1/ingest.py` with JWT auth + duplicate detection

## To start M3 (overlay + live recommendation)

1. Wire `Live Client Data API` polling at 1Hz when gameflow=InProgress
2. Overlay component: `AugmentPanel.tsx` listens to `live:augment-offer` IPC
3. Backend `live.py` endpoints with Redis cache
4. Hotkey registration (Alt+Q toggle) via Electron `globalShortcut`

## Things to circle back on

- Apply for Riot **production key** once site is live and has a contact email
- Decide on a domain name (currently planning `lolhelper.app` — check availability)
- Privacy policy + ToS pages (draft once Mayhem upload is ready to ship)
- Code signing certificate for `.exe` (skip for early beta; revisit before
  wider distribution)
- Consider Cloudflare Turnstile on `/api/v1/ingest/*` to reduce spam upload
  attempts
