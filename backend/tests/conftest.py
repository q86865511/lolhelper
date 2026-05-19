"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide safe defaults so tests don't read ambient .env."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("RIOT_API_KEYS", "RGAPI-test-key")
    monkeypatch.setenv("JWT_SECRET", "test_secret_change_me")
    # Force re-read of settings cache
    from app.settings import get_settings
    get_settings.cache_clear()
