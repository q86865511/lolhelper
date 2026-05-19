# LOL Helper — Claude 開發指引

OP.GG 風 LoL 統計工具,聚焦「**競技場 Arena**」與「**海克斯大亂鬥 Mayhem**」。

## 架構速覽

- **backend/**: Python 3.12 + FastAPI + asyncio + httpx + SQLAlchemy(async)+ ARQ worker
- **frontend/**: Next.js 15 App Router + Tailwind
- **client/**: Electron + React + TS(M2 開發中,雙視窗:主視窗 + always-on-top overlay)
- **packages/shared-types/**: TS types 共用
- **infra/**: docker-compose、Caddyfile
- DB: PostgreSQL 16(月分區)、Redis(快取 + ARQ 佇列)
- 認證: Google OAuth + JWT (HttpOnly cookie)

## 關鍵領域知識

### Mayhem API 被 Riot 永久封鎖
- ARAM Mayhem(queueId=2400)與 Brawl(queueId=2300)Match-V5 API 回 403
- Riot 員工已於 [GitHub Issue #1109](https://github.com/RiotGames/developer-relations/issues/1109) 公開確認是 intended,**無開放計畫**
- 所有第三方網站(OP.GG / U.GG / metasrc)都沒有 Mayhem 全球統計 — **不是技術問題,是政策問題**
- 唯一解:.exe 讀本機 LCU `/lol-match-history/v1/products/lol/{puuid}/matches` crowdsource

### 統計算法
- Arena 「勝率」= `placement <= 4` rate(進入第二輪)
- Tier 用 **Wilson score interval 下界** 計算(避免小樣本 100% 排第一)
- Tier:S(前 5%)/ A(5-20%)/ B(20-50%)/ C(50-80%)/ D(80-100%)
- **所有 endpoint 排序都是 Tier-first,Tier 內 win_rate desc**(見 `_TIER_ORDER` in backend / `tierOrder()` in frontend)

### 裝備分類
- `lib/item-category.ts`(前端)+ `ITEM_CATEGORY_FILTERS`(後端 stats.py)同步維護
- **稜鏡**:`228xxx` 或 `443xxx-447xxx` 且 gold ≥ 2750
- **鞋子**:tag 含 `Boots`
- **核心**:gold ≥ 1000 且非鞋非稜鏡

### Riot ToS 紅線
- ✅ 允許:Match-V5 + Community Dragon 聚合、讀本機 LCU、純資訊 always-on-top overlay
- ❌ 禁止:讀遊戲記憶體、自動操作、隱蔽資訊、影響公平性
- Overlay 永遠只顯示資訊,**絕不**模擬輸入或自動點擊

## 開發習慣

- Python:用 `uv`(不是 pip/poetry),套件鎖在 `uv.lock`
- 後端 async:全部 `async def`,DB 用 `asyncpg` + SQLAlchemy 2.0 async
- 命名:snake_case Python、camelCase TS、PascalCase React component / SQLAlchemy model
- 設定:**全部** 走 pydantic-settings 讀 `.env`,**不要** 在程式碼 hardcode 任何 URL / secret
- 日誌:structlog JSON 輸出
- API:版本前綴 `/api/v1`,Pydantic v2 schemas
- 前端表格 sort:`useState<{col, dir} | null>(null)` — null 代表用 server 已排好的順序
- 前端 client-side fetch:走 `/api/proxy/*`(Next.js rewrite 到 backend),server-side fetch 直接打 backend URL

## 已實作的 endpoint

```
/api/v1/auth/google/url       — 取得 Google OAuth URL
/api/v1/auth/google/callback  — OAuth 回呼,設 cookie 跳前端
/api/v1/auth/refresh          — 換新 access token
/api/v1/auth/logout           — 撤銷 + 清 cookie
/api/v1/auth/me               — 當前使用者(GET / DELETE)

/api/v1/meta/health           — 健康檢查
/api/v1/meta/augments         — Augment metadata
/api/v1/meta/items            — Item metadata(含描述)
/api/v1/meta/champions        — Champion metadata
/api/v1/meta/patches          — Patch 列表

/api/v1/stats/arena/augments  — 全 augment 排行(with_rarity 切換 hex/event)
/api/v1/stats/arena/champions — 英雄列表(整體勝率)
/api/v1/stats/arena/champions/{id} — 英雄詳情(augments / items / synergies / build_paths)
/api/v1/stats/arena/items     — 裝備全表(category=boots/prismatic/core)
```

## 不要做

- 不要引入 MongoDB、Django、Vue、Flask(技術棧已固定)
- 不要繞過 Riot Mayhem API 限制(會被吊銷 key)
- 不要在 client 用 SetWindowsHookEx / DirectX hook(違反 ToS)
- 不要 commit `.env`、API key、JWT secret
- 不要把 Wilson 改成 raw win_rate 排序(5/5=100% 會變第一,失去信心區間意義)
- 不要在表格元件預設 sort 為 `"win_rate"`,要用 `null`(代表用 server 已排好的 tier-first 順序)

## 重要檔案位置

- 設計文件:`docs/architecture.md`
- 合規檢查清單:`docs/tos-compliance.md`
- 部署:`docs/deployment.md`(Oracle Cloud + Vercel)
- ADR 決策紀錄:`docs/ADR/`
- 後端設定:`backend/app/settings.py`
- DB models:`backend/app/db/models/`
- Riot client:`backend/app/services/riot/client.py`
- 統計引擎:`backend/app/services/stats_engine.py`
- Stats API:`backend/app/api/v1/stats.py`
- Auth API:`backend/app/api/v1/auth.py`
- 前端表格元件:`frontend/src/components/{augment,item,synergy,build-paths}-table.tsx`
- Tier order helper:`frontend/src/lib/tier-order.ts` + `_TIER_ORDER` in backend stats.py
