# lolhelper-backend

FastAPI 後端 + ARQ workers。

## 開發

```bash
# 安裝相依
uv sync

# 跑 migration
uv run alembic upgrade head

# 啟動 API server
uv run uvicorn app.main:app --reload

# 啟動 worker(另一個 terminal)
uv run arq app.workers.settings.WorkerSettings

# 測試
uv run pytest

# Lint + typecheck
uv run ruff check .
uv run ruff format .
uv run mypy app
```

## 結構

```
app/
├── main.py              FastAPI app factory
├── settings.py          pydantic-settings
├── deps.py              FastAPI Depends
├── api/v1/              endpoints
├── core/                security/oauth/rate_limit/logging
├── db/                  SQLAlchemy session + models
├── schemas/             Pydantic request/response
├── services/            業務邏輯 (Riot client、stats engine、community dragon...)
├── workers/             ARQ tasks (crawler、aggregator)
└── utils/

alembic/                 DB migrations
tests/                   pytest
scripts/                 一次性腳本(seed、refresh metadata)
```
