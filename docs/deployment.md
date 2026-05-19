# 部署:Oracle Cloud Free Tier + Vercel + Cloudflare

零成本 MVP 部署架構。所有元件選用 always-free 方案。

## 架構總覽

```
┌────────────────────┐     ┌────────────────────┐
│  Cloudflare        │     │  GitHub            │
│  - DNS             │     │  - Repo + Actions  │
│  - Free TLS proxy  │     └──────────┬─────────┘
└─────────┬──────────┘                │ CI/CD
          │                           │
          ▼                           ▼
   ┌──────────────┐          ┌──────────────────┐
   │ lolhelper.app│          │ Oracle Cloud ARM │
   │ ─────────────│          │ Always-Free      │
   │ Vercel       │   API    │ Ubuntu 24.04     │
   │ (Next.js SSR)│─────────▶│ ─────────────────│
   │              │          │ • Caddy (TLS)    │
   └──────────────┘          │ • FastAPI x1-2   │
                             │ • ARQ worker     │
                             │ • Postgres 16    │
                             │ • Redis 7        │
                             └──────────────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │ Riot Games API   │
                             │ (4 region clstr) │
                             └──────────────────┘
```

| 元件 | 平台 | 規格 | 月費 |
|------|------|------|------|
| Backend + DB + Redis | Oracle Cloud ARM Ampere | 4 OCPU / 24GB RAM / 200GB | $0 |
| Frontend | Vercel Hobby | unlimited builds | $0 |
| DNS + TLS | Cloudflare | Free plan | $0 |
| 網域 | Namecheap / Cloudflare | `.app` ~$15/年 | ~$1.25 |
| **合計** | | | **~$1.25/月** |

## Step 1 — Oracle Cloud 帳號 + ARM Ampere 機器

### 1.1 開帳號

1. 進 https://www.oracle.com/cloud/free/ → **Start for free**
2. 信用卡驗證(不會扣款,只是身份驗證)
3. **選 Home Region 要慎重** — 開了不能改。建議選地理位置近的:
   - 台灣使用者推薦 **Japan East (Tokyo)** 或 **Singapore**
   - 韓國的 Seoul 也快
4. 等帳號啟用(通常幾分鐘,偶爾要 24h)

### 1.2 申請 ARM Ampere 機器

ARM Ampere A1 在 Always-Free 額度內最多可給:
- 4 OCPU + 24 GB RAM(可單機或拆多台)
- 200 GB block storage

⚠️ **熱門地區 ARM 容量常不足** — 「Out of capacity」是常態。對策:
- 寫腳本每 5-10 分鐘 try 一次直到搶到
- 或選非熱門地區(如 Phoenix)

#### 申請流程

1. Console 左上 **☰ → Compute → Instances → Create instance**
2. 設定:
   - **Name**: `lolhelper`
   - **Placement**: 預設 Availability Domain(後面試 AD1/AD2/AD3 都試試,有時某個 AD 有貨)
   - **Image**: **Canonical Ubuntu 24.04** (Minimal)
   - **Shape**: 點 Change Shape →
     - Instance type: **Virtual Machine**
     - Shape series: **Ampere (Arm)**
     - Shape: **VM.Standard.A1.Flex**
     - **OCPUs: 4**, **Memory: 24 GB**(吃滿 always-free)
   - **Networking**: Create new VCN(預設)
   - **SSH keys**: Generate + 下載 .pem 私鑰,**好好保存**(只有這次能下載)
   - **Boot volume**: 預設 50 GB(可改 200 GB,在 always-free 內)
3. **Create**
4. 如果「Out of capacity」→ 改 Availability Domain 重試,或 cron 腳本搶

### 1.3 開放 HTTP / HTTPS 連接埠

預設只開了 SSH(22)。要開 80 / 443:

1. Instance 詳情頁 → **Primary VNIC → Subnet** → 點進去
2. **Default Security List for vcn-...** → **Add Ingress Rules**
3. 新增兩條:
   - Source CIDR `0.0.0.0/0` | Protocol TCP | Dest Port `80`
   - Source CIDR `0.0.0.0/0` | Protocol TCP | Dest Port `443`
4. (Ubuntu firewall 預設可能也擋,後面 SSH 進去再開)

### 1.4 SSH 進機器

```bash
chmod 600 ~/Downloads/lolhelper-key.pem
ssh -i ~/Downloads/lolhelper-key.pem ubuntu@<your-instance-public-ip>
```

Windows PowerShell:
```powershell
icacls C:\path\to\lolhelper-key.pem /reset
icacls C:\path\to\lolhelper-key.pem /grant:r "${env:USERNAME}:(R)"
icacls C:\path\to\lolhelper-key.pem /inheritance:r
ssh -i C:\path\to\lolhelper-key.pem ubuntu@<public-ip>
```

### 1.5 開 Ubuntu 內部 firewall

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## Step 2 — 機器上安裝 Docker 與依賴

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg ufw git

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker  # 或 logout 再登入

# Docker compose v2 已內建在 docker
docker --version
docker compose version
```

## Step 3 — Clone repo + 設定 .env

```bash
cd ~
git clone https://github.com/<your-user>/<repo-name>.git lolhelper
cd lolhelper

cp .env.example .env
nano .env  # 填入下列
```

`.env` 必填項:

```env
# --- Database ---
POSTGRES_PASSWORD=<32 字元隨機字串,如 openssl rand -hex 16>

# --- Riot ---
RIOT_API_KEYS=RGAPI-xxxxx          # 24h personal key(部署後盡快申請 production)
RIOT_SEED_REGIONS=KR,JP1,TW2,NA1,EUW1,BR1

# --- App ---
APP_ENV=production
APP_CORS_ORIGINS=https://lolhelper.app,https://www.lolhelper.app

# --- Auth ---
GOOGLE_CLIENT_ID=<從 Google Console>
GOOGLE_CLIENT_SECRET=<從 Google Console>
GOOGLE_REDIRECT_URI=https://lolhelper.app/api/proxy/auth/google/callback
JWT_SECRET=<openssl rand -hex 32>

# --- Frontend (used by backend for redirects) ---
FRONTEND_URL=https://lolhelper.app
REVALIDATE_SECRET=<openssl rand -hex 16>
```

## Step 4 — 啟動服務

```bash
# 啟動 Postgres + Redis(本機 only)
docker compose -f infra/docker-compose.yml up -d postgres redis

# Build backend image
docker build -f backend/Dockerfile -t lolhelper-backend backend/

# 跑 migration
docker run --rm --network=infra_default --env-file=.env \
  lolhelper-backend uv run alembic upgrade head

# 拉 metadata
docker run --rm --network=infra_default --env-file=.env \
  lolhelper-backend uv run python -m scripts.refresh_metadata

# Seed 高分牌位 puuid
docker run --rm --network=infra_default --env-file=.env \
  lolhelper-backend uv run python -m scripts.seed_initial --all
```

(實作時:寫一個 `docker-compose.prod.yml` 把 backend + worker + caddy 都包進去自動跑,
這裡先示範手動。完整生產 compose 待補。)

## Step 5 — Caddy reverse proxy + TLS

```bash
sudo apt install -y caddy
sudo nano /etc/caddy/Caddyfile
```

```caddy
api.lolhelper.app {
    encode gzip
    reverse_proxy 127.0.0.1:8000
    @cors {
        method OPTIONS
    }
    respond @cors 204
}
```

```bash
sudo systemctl reload caddy
```

Caddy 會**自動申請 Let's Encrypt 憑證**並啟用 HTTPS,不用設定。

## Step 6 — Cloudflare DNS

1. 註冊 https://www.cloudflare.com/(免費)
2. **Add a Site** → 輸入網域 → 選 Free plan
3. Cloudflare 會給您 2 個 nameserver,到網域註冊商(Namecheap / GoDaddy)改 NS 到 Cloudflare
4. 在 Cloudflare DNS 區加:
   - `api.lolhelper.app` → A 紀錄 → Oracle VM 公網 IP → **Proxy off**(讓 Caddy 處理 TLS)
   - `lolhelper.app` 與 `www` → 後面指向 Vercel(見 Step 7)

## Step 7 — Vercel 部署前端

1. 進 https://vercel.com,用 GitHub 登入
2. **Add New → Project** → 選 lolhelper repo
3. **Framework Preset**: Next.js
4. **Root Directory**: `frontend`
5. **Build Command**: 預設 `next build`
6. **Environment Variables**:
   - `NEXT_PUBLIC_API_URL` = `https://api.lolhelper.app`
   - `REVALIDATE_SECRET` = 跟 backend 一樣的值
7. Deploy
8. Vercel 會自動發 `lolhelper.vercel.app`。在 Cloudflare DNS 加 CNAME `lolhelper.app` → `cname.vercel-dns.com.`,Proxy 可開可關
9. Vercel **Domains** 頁加 `lolhelper.app` + `www.lolhelper.app`,Vercel 會驗證

## Step 8 — Google OAuth Console 更新 redirect URIs

1. 進 https://console.cloud.google.com/apis/credentials
2. 編輯 OAuth client → Authorized redirect URIs 加:
   - `https://lolhelper.app/api/proxy/auth/google/callback`
3. 移除舊的 `http://localhost:...`(production 用)

## Step 9 — 跑 ARQ worker(常駐)

機器上,把 worker 設成 systemd service 讓它常駐:

```bash
sudo nano /etc/systemd/system/lolhelper-worker.service
```

```ini
[Unit]
Description=LOL Helper ARQ Worker
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/lolhelper
ExecStart=/usr/bin/docker run --rm --name lolhelper-worker \
  --network=infra_default --env-file=/home/ubuntu/lolhelper/.env \
  lolhelper-backend uv run arq app.workers.settings.WorkerSettings
Restart=always
RestartSec=10
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lolhelper-worker
sudo journalctl -u lolhelper-worker -f
```

## Step 10 — DB 備份

```bash
sudo nano /etc/cron.d/lolhelper-backup
```

```cron
0 4 * * * ubuntu docker exec lolhelper-postgres pg_dump -U lolhelper lolhelper | gzip > /home/ubuntu/backups/db-$(date +\%Y\%m\%d).sql.gz
0 5 * * 0 ubuntu find /home/ubuntu/backups -name 'db-*.sql.gz' -mtime +30 -delete
```

(可選)同步到 Cloudflare R2(10GB free):用 `rclone`。

## Step 11 — Production Riot API key 申請

部署後立刻申請。Personal key 100req/2min 太慢,Production 是 ~30,000 req/10min(300x)。

1. 進 https://developer.riotgames.com/app-type
2. 選 **Personal API key application**
3. 表單:
   - App name: LOL Helper
   - URL: https://lolhelper.app
   - 描述用途、預期流量、不變現
   - **重點**:截圖網站證明真的有東西
4. 等 1-2 週審核

獲核可後新 key 直接替換 `.env` 的 `RIOT_API_KEYS`,重啟 worker 即可。

## Step 12 — 上線檢查清單

- [ ] `curl https://api.lolhelper.app/api/v1/meta/health` 回 `{status: ok}`
- [ ] `https://lolhelper.app` 開首頁能渲染
- [ ] 點英雄頁有資料(若 worker 才剛啟動,等 15 分鐘累積)
- [ ] Google 登入 → 跳 Google → 跳回 → nav 顯示頭像
- [ ] ARQ worker `sudo systemctl status lolhelper-worker` 是 active
- [ ] DB 備份 cron 隔天可以看到 backup 檔案

## 監控(後加)

- **Sentry**(免費 5k events/月)接前後端錯誤
- **Cloudflare Analytics** 看流量
- **Grafana** + Prometheus 看 DB / API 指標(自架,有空再做)

## 預估流量上限

| 指標 | Oracle ARM 4 OCPU / 24GB | 何時要升級 |
|------|--------------------------|----------|
| DAU | ~5,000 | 超過要拆 DB 出去 |
| 同時連線 | ~500 | uvicorn workers 加到 4-8 |
| DB 大小 | ~50 GB | 200GB block storage 還很久 |
| Riot API 呼叫 | 取決於 key | Production key 可達 ~30k req/10min |

到瓶頸時可:
1. 升級到 Oracle 付費實例(從 free 4 OCPU 升 8 OCPU 才開始要錢)
2. 拆 DB 到獨立機器
3. 加 CDN(Cloudflare 已有部分)
4. ARQ worker 加實例

零成本架構至少撐到第一個千級 DAU 沒問題。
