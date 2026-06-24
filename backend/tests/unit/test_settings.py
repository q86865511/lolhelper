"""Settings loading tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.settings import Settings, get_settings


def test_settings_loads_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RIOT_API_KEYS", "k1,k2,k3")
    monkeypatch.setenv("APP_CORS_ORIGINS", "https://a.com,https://b.com")
    # 正式環境必須提供非預設密鑰，否則啟動防呆會擋下
    monkeypatch.setenv("JWT_SECRET", "a-real-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://lolhelper:strongpw@db:5432/lolhelper")
    s = Settings()
    assert s.app_env == "production"
    assert s.riot_api_keys == ["k1", "k2", "k3"]
    assert s.app_cors_origins == ["https://a.com", "https://b.com"]
    assert s.is_production
    assert not s.is_development


def test_production_rejects_default_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """正式環境沿用預設 JWT secret 時應拒絕啟動。"""
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://lolhelper:strongpw@db:5432/lolhelper")
    # 移除 conftest 預設的 JWT_SECRET，讓設定沿用預設值 change_me_in_production
    monkeypatch.delenv("JWT_SECRET", raising=False)
    # pydantic 會把 model_validator 內的 ValueError 包成 ValidationError
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings()


def test_development_allows_default_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """開發環境沿用預設值不應被防呆擋下。"""
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    s = Settings()
    assert s.is_development


def test_settings_defaults() -> None:
    get_settings.cache_clear()
    s = Settings()
    assert s.app_env in {"development", "staging", "production"}
    assert s.app_port == 8000
    assert s.jwt_algorithm == "HS256"
