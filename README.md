# LOL Helper

League of Legends 統計工具,專注 **競技場 Arena** 與 **海克斯大亂鬥 Mayhem** 兩個遊戲模式。
OP.GG 風的英雄頁 + augment / 裝備 / 核心組建 / 隊友 排行 + 即將推出的 Windows .exe 客戶端。

## 元件

| 目錄 | 用途 | 技術 |
|------|------|------|
| `backend/` | API + 爬蟲 + 聚合 | Python 3.12 / FastAPI / asyncio / SQLAlchemy 2 async / asyncpg / ARQ |
| `frontend/` | 統計網站(SEO + 瀏覽) | Next.js 15 App Router / TypeScript / Tailwind |
| `client/` | Windows .exe(M2 開發中) | Electron / React / TypeScript |
| `packages/shared-types/` | TS 共用型別 | — |
| `infra/` | 部署設定 | docker-compose / Caddy |

## 為什麼有 .exe?

Riot **永久封鎖**了 ARAM Mayhem(queueId=2400)與 Brawl(queueId=2300)的 Match-V5 API,
所有第三方網站(OP.GG / U.GG / metasrc)都無法取得這兩個模式的全球統計
([Riot 員工於 GitHub Issue #1109 公開確認](https://github.com/RiotGames/developer-relations/issues/1109))。
唯一可行的資料來源是讓使用者本機 LCU 上傳對戰資料聚合 — 這就是 .exe 客戶端的核心職責。

Arena(queueId=1700)的 Match-V5 是開放的,後端走標準 BFS puuid 爬蟲。

## 功能(M1 完成度 ~95%)

**已實作**:
- ✅ Riot Match-V5 BFS 爬蟲(4 region cluster 並行,自動 rate-limit)
- ✅ Wilson 信心區間 + S/A/B/C/D 分級
- ✅ 全 zh_tw 中文化(augment / 英雄 / 裝備名稱與描述)
- ✅ 跨 patch 聚合,預設只用最新版
- ✅ 英雄個別頁(OP.GG 風,左 sidebar + 右詳情)
- ✅ Augment 依稀有度切換(銀/金/稜鏡)
- ✅ 裝備分類(鞋子/稜鏡/核心)
- ✅ **核心組建**(item combo)勝率排行
- ✅ **英雄搭配**(synergies)同隊勝率
- ✅ Tooltip 顯示效果(Riot 描述清洗 markup)
- ✅ 可排序欄位 + Tier-優先排序(Tier > 勝率)
- ✅ Google OAuth 登入 + JWT cookie session

**M1 剩下**:
- ⏳ 技能順序 / 技能點法(需 Match-V5 timeline endpoint,工程較大)
- ⏳ 部署到雲端(Oracle Cloud + Vercel,文件見 `docs/deployment.md`)

**M2 規劃**:Windows .exe 客戶端(Electron / LCU 偵測 / Mayhem 上傳 / overlay)

**M3 規劃**:遊戲中即時 overlay(LCU + Live Client Data API)

## 開發環境需求

- **Node.js** ≥ 20.10 + **pnpm** ≥ 9
- **Python 3.12** + [**uv**](https://github.com/astral-sh/uv)
- **Docker Desktop**(本地 Postgres + Redis)
- **Riot API key**(免費 24h)— [取得](https://developer.riotgames.com/)
- **Google OAuth Client**(可選,登入功能)— [Google Console](https://console.cloud.google.com/apis/credentials)

## 起手式(本地開發)

```bash
# 1. 安裝相依
pnpm install
cd backend && uv sync && cd ..

# 2. 複製環境變數
cp .env.example .env
# 編輯 .env:
#   RIOT_API_KEYS=RGAPI-...                 # 必填
#   GOOGLE_CLIENT_ID=...                    # 可選(登入用)
#   GOOGLE_CLIENT_SECRET=...
#   JWT_SECRET=$(openssl rand -hex 32)      # 必填

# 3. 啟動本地 Postgres + Redis
pnpm infra:up

# 4. 跑 DB migration
pnpm backend:migrate

# 5. 拉 augment / 英雄 / 裝備 metadata(zh_tw + EN)
cd backend && uv run python -m scripts.refresh_metadata && cd ..

# 6. Seed 高分牌位 puuid(KR + JP1 + TW2)
cd backend && uv run python -m scripts.seed_initial --all && cd ..

# 7. 啟動 backend
pnpm backend:dev

# 8. 啟動 worker(另一個 terminal — 持續爬資料)
pnpm backend:worker

# 9. 啟動前端(另一個 terminal)
pnpm frontend:dev
```

開 http://localhost:3000

## 觀察進度

```bash
docker exec lolhelper-postgres psql -U lolhelper -d lolhelper -c '
SELECT
  (SELECT count(*) FROM matches WHERE queue_id IN (1700,1710)) AS matches,
  (SELECT count(*) FROM participants WHERE queue_id IN (1700,1710)) AS participants;
'
```

Personal API key 限速 100 req/2min,4 cluster 並行可達 ~100-150 場/分,**一天約 50,000 場**。

## 部署

見 [`docs/deployment.md`](docs/deployment.md) — **Oracle Cloud Free Tier ARM Ampere**(免費)
+ **Vercel hobby**(免費)+ **Cloudflare DNS**(免費)= **零成本部署 MVP**。

## 法律聲明

This product isn't endorsed by Riot Games and doesn't reflect the views or opinions
of Riot Games or anyone officially involved in producing or managing League of Legends.
League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc.

關於本工具如何處理 Riot 政策邊界,見 [`docs/tos-compliance.md`](docs/tos-compliance.md)。

## 授權

MIT(待 LICENSE 補上)
