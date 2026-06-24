"""JWT issue/verify + password-free auth helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from app.settings import Settings


class TokenError(Exception):
    """Raised on token verification failure."""


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int, settings: Settings) -> tuple[str, datetime]:
    """Short-lived JWT used as the API bearer/cookie. Returns (token, expires_at)."""
    expires_at = _now() + timedelta(seconds=settings.jwt_access_ttl_seconds)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(_now().timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def create_refresh_token(user_id: int, settings: Settings) -> tuple[str, str, datetime]:
    """Long-lived opaque random token. Returns (raw_token, sha256_hash, expires_at)."""
    raw = secrets.token_urlsafe(48)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = _now() + timedelta(seconds=settings.jwt_refresh_ttl_seconds)
    return raw, digest, expires_at


def hash_refresh(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def decode_access_token(token: str, settings: Settings) -> int:
    """Returns the user_id on success, raises TokenError otherwise."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as e:
        raise TokenError(f"invalid token: {e}") from e
    if payload.get("type") != "access":
        raise TokenError("not an access token")
    sub = payload.get("sub")
    if not sub:
        raise TokenError("missing sub claim")
    try:
        return int(sub)
    except (TypeError, ValueError) as e:
        raise TokenError(f"sub not an int: {sub}") from e
