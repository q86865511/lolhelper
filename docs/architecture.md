# LOL Helper — Architecture

## Why the system looks like this

Two structural facts shape every other decision:

1. **Arena (queueId 1700/1710)** is fully supported by Riot Match-V5 → server-side
   BFS crawler over puuids works.
2. **ARAM Mayhem (queueId 2400)** is **permanently blocked** by Riot at the API
   layer ([developer-relations#1109](https://github.com/RiotGames/developer-relations/issues/1109)).
   No third party (OP.GG, U.GG, metasrc, lolalytics) has Mayhem stats. The only
   legal source is each user's own LCU `/lol-match-history` (local to that PC).

So the system has **two ingest pipelines feeding one schema** — `participants.source`
distinguishes `riot_api` from `lcu_upload`.

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                            backend/                              │
│  FastAPI app (uvicorn) + ARQ worker, share Postgres + Redis     │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    │
│  │ /api/v1/*   │    │ ARQ tasks   │    │ Riot client       │    │
│  │ auth/stats/ │    │ - crawl     │────│ (rate-limited     │    │
│  │ ingest/live │    │ - aggregate │    │  per region)      │    │
│  └──────┬──────┘    │ - meta      │    └──────────────────┘    │
│         │           └──────┬──────┘                              │
│         └───────────┬──────┘                                     │
│                     ▼                                            │
│              Postgres + Redis                                    │
└─────────────────────────────────────────────────────────────────┘
        ▲                       ▲                       ▲
        │ /api/proxy/*          │ /api/v1/ingest/*       │ /api/v1/stats/*
        │                       │                       │
┌───────┴───────┐       ┌───────┴────────┐       ┌──────┴───────┐
│  frontend/    │       │   client/      │       │   any user   │
│  Next.js      │       │   Electron     │       │   browser    │
│  (SSR/ISR)    │       │   + LCU + UI   │       │              │
└───────────────┘       └────────────────┘       └──────────────┘
```

## Critical data flows

### Arena ingest (server-side)
```
seed (challenger/GM/master via league-v4)
  -> crawl_state (priority=10)
  -> dispatcher picks N puuids
  -> match-v5 ids?queue=1700&count=20
  -> fetch_match worker per match_id
  -> INSERT matches + participants
  -> INSERT crawl_state for new puuids (priority=0, depth+1)
```

### Mayhem ingest (client-side, crowdsource)
```
.exe at startup:
  read lockfile -> LCU base URL + auth
  GET /lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=100
  filter queueId === 2400, exclude already-uploaded (electron-store JSON)
  POST /api/v1/ingest/mayhem (one match per call) with JWT

.exe live:
  LCU WebSocket eog-stats-block event with queueId=2400 -> wait 10s -> upload
```

### Stats aggregation
```
worker every 2h:
  for each (queue_id, patch, augment_id, champion_id|NULL):
    games  = COUNT(*)
    wins   = COUNT(*) WHERE placement <= 4
    top1   = COUNT(*) WHERE placement = 1
    avg_placement = AVG(placement)
    pick_rate = games / total_matches_in_patch
    wilson_low = wilson_lower_bound(wins, games)
  bulk upsert augment_stats; assign tier S/A/B/C/D via percentile within patch.
```

### Real-time recommendation (M3)
```
LCU augment offer event -> overlay shows 3 choices
  -> POST /api/v1/live/recommend/augment
     {queue, champion_id, choices[], picked_augments[]}
  -> backend: Redis cache lookup (TTL 1h) | else query augment_stats × champion
  -> response sorted by wilson_low, plus marker for "best" choice
```

## Why these specific technology choices

| Decision | Why |
|----------|-----|
| FastAPI + asyncio | Riot API + LCU forwarding are I/O bound; async wins by 10x throughput |
| SQLAlchemy 2.0 async + asyncpg | Standard async stack; integrates with Alembic |
| Postgres monthly partitions on `matches`/`participants` | Two-year retention without VACUUM pain; drop old partitions trivially |
| ARQ over Celery | Async-native, lighter, Redis-backed; sufficient for our scale |
| GIN indexes on `augments[]` / `items[]` | "Find all participants who used augment X" is a hot query |
| Wilson lower bound for ranking | 5/5 (100% raw) ranks below 800/1000 (80%) — the right behaviour |
| Electron over Tauri (M1) | Better LCU library ecosystem; faster to ship; can migrate later if size matters |
| Always-on-top transparent window over Overwolf | No third-party SDK dep, no double review process |
| Google OAuth in MVP, RSO later | OAuth library mature, Riot RSO needs prod key approval |

## Non-goals (explicit)

- No simulated input or auto-actions in client (would violate Riot ToS)
- No DirectX hook / memory reads (Vanguard would trip; ToS violation)
- No scraping of OP.GG/U.GG; we link out only
- No Brawl mode (also blocked like Mayhem; not worth the LCU crowd-source cost yet)

## See also

- `docs/tos-compliance.md` — Riot Third Party Policy mapping
- `docs/data-pipeline.md` — crawler details (to be written when M1 ingest lands)
- `docs/ADR/` — individual decisions
