"""Application settings loaded from environment variables.

All configuration goes through this module; no hard-coded URLs or secrets elsewhere.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# 已知的不安全預設值，正式環境不得沿用
_INSECURE_JWT_SECRET = "change_me_in_production"
_INSECURE_DB_PASSWORD = "changeme_in_production"

# Walk up from this file (backend/app/settings.py) to find the monorepo root .env
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    """All env-driven config in one place."""

    model_config = SettingsConfigDict(
        # Try backend/.env first, fall back to project root .env.
        # pydantic-settings reads in order; later files override earlier.
        env_file=(str(_PROJECT_ROOT / ".env"), str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "lolhelper"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://lolhelper:changeme_in_production@localhost:5432/lolhelper"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Riot API ---
    riot_api_keys: Annotated[list[str], NoDecode] = Field(default_factory=list)
    riot_default_cluster: Literal["americas", "asia", "europe", "sea"] = "asia"
    riot_seed_regions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["KR", "JP1", "TW2"]
    )
    riot_request_timeout_seconds: float = 10.0

    # --- Auth ---
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    # Default points to the frontend proxy so the cookies the backend sets land
    # on the SAME origin the user is browsing (localhost:3000). Production uses
    # the real domain.
    google_redirect_uri: str = "http://localhost:3000/api/proxy/auth/google/callback"
    jwt_secret: SecretStr = SecretStr("change_me_in_production")
    jwt_algorithm: Literal["HS256", "RS256"] = "HS256"
    jwt_access_ttl_seconds: int = 900  # 15 minutes
    jwt_refresh_ttl_seconds: int = 2_592_000  # 30 days

    # --- ISR webhook ---
    revalidate_secret: SecretStr = SecretStr("")
    frontend_url: str = "http://localhost:3000"

    # --- OAuth loopback for .exe client ---
    oauth_loopback_redirect_uri: str = "http://127.0.0.1:51820/auth/cb"

    @field_validator("app_cors_origins", "riot_api_keys", "riot_seed_regions", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Allow comma-separated string from env (CORS_ORIGINS=a,b,c)."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> "Settings":
        """正式環境啟動防呆：拒絕沿用預設密鑰，避免弱密碼上線。"""
        if self.app_env == "production":
            insecure: list[str] = []
            if self.jwt_secret.get_secret_value() == _INSECURE_JWT_SECRET:
                insecure.append("JWT_SECRET")
            if _INSECURE_DB_PASSWORD in self.database_url:
                insecure.append("DATABASE_URL")
            if insecure:
                raise ValueError(
                    "正式環境（APP_ENV=production）偵測到未設定的預設密鑰: "
                    + ", ".join(insecure)
                    + "。請在 .env 設定安全值後再啟動。"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton accessor."""
    return Settings()
