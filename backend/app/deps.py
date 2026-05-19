"""FastAPI dependencies — request-scoped objects (db session, redis, current user)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.settings import Settings, get_settings

# --- Settings ---
SettingsDep = Annotated[Settings, Depends(get_settings)]

# --- DB session ---
DbDep = Annotated[AsyncSession, Depends(get_db)]


# --- Redis (lazy singleton, one pool) ---
_redis: aioredis.Redis | None = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    yield _redis


RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# --- Optional client version (for compatibility checks) ---
async def get_client_version(
    x_client_version: Annotated[str | None, Header(alias="X-Client-Version")] = None,
) -> str | None:
    return x_client_version


ClientVersionDep = Annotated[str | None, Depends(get_client_version)]


# --- Auth (placeholder; real implementation comes with auth.py in M1.5) ---
async def get_current_user_id(
    settings: SettingsDep,
    cookie: Annotated[str | None, Header(alias="cookie")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> int | None:
    """Returns user_id when a valid access token is present, else None.

    Cookie takes precedence (web flow); falls back to `Authorization: Bearer`
    so the .exe client can authenticate without cookie support.
    """
    # Local import avoids a circular dep (auth.py imports from this module).
    from app.api.v1.auth import COOKIE_ACCESS
    from app.core.security import TokenError, decode_access_token

    token: str | None = None
    if cookie:
        for chunk in cookie.split(";"):
            k, _, v = chunk.strip().partition("=")
            if k == COOKIE_ACCESS and v:
                token = v
                break
    if token is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        return decode_access_token(token, settings)
    except TokenError:
        return None


CurrentUserIdDep = Annotated[int | None, Depends(get_current_user_id)]


async def require_user(user_id: CurrentUserIdDep) -> int:
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


RequireUserDep = Annotated[int, Depends(require_user)]
