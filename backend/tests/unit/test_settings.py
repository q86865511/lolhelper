"""Settings loading tests."""

from __future__ import annotations

import pytest

from app.settings import Settings, get_settings


def test_settings_loads_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RIOT_API_KEYS", "k1,k2,k3")
    monkeypatch.setenv("APP_CORS_ORIGINS", "https://a.com,https://b.com")
    s = Settings()
    assert s.app_env == "production"
    assert s.riot_api_keys == ["k1", "k2", "k3"]
    assert s.app_cors_origins == ["https://a.com", "https://b.com"]
    assert s.is_production
    assert not s.is_development


def test_settings_defaults() -> None:
    get_settings.cache_clear()
    s = Settings()
    assert s.app_env in {"development", "staging", "production"}
    assert s.app_port == 8000
    assert s.jwt_algorithm == "HS256"
