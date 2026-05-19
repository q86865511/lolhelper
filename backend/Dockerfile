# Backend Dockerfile — uses uv for fast installs and a slim Python 3.12 base.
# Single-stage build for simplicity; final image is ~250MB.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# uv comes pre-built as a small static binary; copy it from astral-sh's image.
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

# System deps:
#  - libpq is bundled inside asyncpg so we don't need libpq-dev
#  - build-essential only needed if a wheel falls back to source build (rare)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy app source
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Default: run the API. Override with `arq app.workers.settings.WorkerSettings` for worker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
