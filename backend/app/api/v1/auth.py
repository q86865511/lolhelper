"""Google OAuth + JWT session endpoints.

Flow:
  1. Browser hits `GET /auth/google/url` → backend returns { url } pointing to
     Google's consent screen. State + nonce stored in short-lived signed
     cookies for CSRF protection.
  2. User signs in at Google → Google redirects to `GET /auth/google/callback`
     with `code` and `state`. We verify state, exchange code for tokens,
     find-or-create the user, issue our own JWT access + refresh tokens
     (refresh stored hashed in DB), set them as HttpOnly cookies, and
     redirect to the frontend.
  3. Frontend can then call `GET /auth/me` to get user info (cookie-based).
  4. `POST /auth/refresh` rotates access token using the refresh cookie.
  5. `POST /auth/logout` revokes the current refresh token.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.core import google_oauth
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_refresh,
)
from app.db.models import RefreshToken, User
from app.deps import DbDep, SettingsDep

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie names
COOKIE_ACCESS = "lh_access"
COOKIE_REFRESH = "lh_refresh"
COOKIE_OAUTH_STATE = "lh_oauth_state"
COOKIE_OAUTH_NONCE = "lh_oauth_nonce"

# Short-lived cookies for state during OAuth dance
_STATE_TTL_SECONDS = 600


def _is_secure(settings) -> bool:
    """Use Secure cookies in non-dev environments."""
    return not settings.is_development


def _set_session_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    settings,
) -> None:
    response.set_cookie(
        COOKIE_ACCESS,
        access_token,
        max_age=settings.jwt_access_ttl_seconds,
        httponly=True,
        secure=_is_secure(settings),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        COOKIE_REFRESH,
        refresh_token,
        max_age=settings.jwt_refresh_ttl_seconds,
        httponly=True,
        secure=_is_secure(settings),
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")


@router.get("/google/url")
async def google_url(response: Response, settings: SettingsDep) -> dict[str, str]:
    """Return the Google OAuth URL for the frontend to redirect the user to."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=503, detail="Google OAuth not configured (set GOOGLE_CLIENT_ID)."
        )
    state, nonce = google_oauth.gen_state_nonce()
    response.set_cookie(
        COOKIE_OAUTH_STATE, state,
        max_age=_STATE_TTL_SECONDS,
        httponly=True, secure=_is_secure(settings), samesite="lax", path="/",
    )
    response.set_cookie(
        COOKIE_OAUTH_NONCE, nonce,
        max_age=_STATE_TTL_SECONDS,
        httponly=True, secure=_is_secure(settings), samesite="lax", path="/",
    )
    url = google_oauth.build_authorize_url(settings, state=state, nonce=nonce)
    return {"url": url}


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google's redirect. On success, set session cookies and redirect to frontend."""
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/login?error={error}", status_code=302
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    expected_state = request.cookies.get(COOKIE_OAUTH_STATE)
    expected_nonce = request.cookies.get(COOKIE_OAUTH_NONCE)
    if not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="State mismatch (CSRF)")

    # Exchange code → tokens
    tokens = await google_oauth.exchange_code(code, settings)
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="Google returned no id_token")

    info = google_oauth.decode_id_token(id_token)
    if expected_nonce and info.get("nonce") and info["nonce"] != expected_nonce:
        raise HTTPException(status_code=400, detail="Nonce mismatch")
    sub = info.get("sub")
    email = info.get("email")
    name = info.get("name")
    picture = info.get("picture")
    if not sub or not email:
        raise HTTPException(status_code=502, detail="ID token missing sub/email")

    # Find or create user
    user = (await db.execute(select(User).where(User.google_sub == sub))).scalar_one_or_none()
    now = datetime.now(UTC)
    if user is None:
        user = User(
            google_sub=sub,
            email=email,
            display_name=name,
            avatar_url=picture,
            last_login_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        user.last_login_at = now
        if name and user.display_name != name:
            user.display_name = name
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
    user_id = user.id

    # Mint our own tokens
    access_token, _ = create_access_token(user_id, settings)
    raw_refresh, refresh_hash, refresh_expires = create_refresh_token(user_id, settings)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=refresh_hash,
            issued_at=now,
            expires_at=refresh_expires,
            user_agent=request.headers.get("user-agent", "")[:500] or None,
        )
    )
    await db.commit()

    # Redirect to frontend with cookies set
    resp = RedirectResponse(url=f"{settings.frontend_url}/auth/callback", status_code=302)
    _set_session_cookies(resp, access_token, raw_refresh, settings)
    resp.delete_cookie(COOKIE_OAUTH_STATE, path="/")
    resp.delete_cookie(COOKIE_OAUTH_NONCE, path="/")
    return resp


@router.post("/refresh")
async def refresh_session(
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    refresh_cookie: Annotated[str | None, Cookie(alias=COOKIE_REFRESH)] = None,
) -> dict[str, Any]:
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="No refresh token")
    tok_hash = hash_refresh(refresh_cookie)
    row = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == tok_hash)
        )
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if row.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    access_token, expires = create_access_token(row.user_id, settings)
    response.set_cookie(
        COOKIE_ACCESS,
        access_token,
        max_age=settings.jwt_access_ttl_seconds,
        httponly=True,
        secure=_is_secure(settings),
        samesite="lax",
        path="/",
    )
    return {"expires_at": expires.isoformat()}


@router.post("/logout")
async def logout(
    response: Response,
    db: DbDep,
    refresh_cookie: Annotated[str | None, Cookie(alias=COOKIE_REFRESH)] = None,
) -> dict[str, str]:
    if refresh_cookie:
        tok_hash = hash_refresh(refresh_cookie)
        row = (
            await db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == tok_hash)
            )
        ).scalar_one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = datetime.now(UTC)
            await db.commit()
    _clear_session_cookies(response)
    return {"status": "logged_out"}


@router.get("/me")
async def me(
    db: DbDep,
    settings: SettingsDep,
    access_cookie: Annotated[str | None, Cookie(alias=COOKIE_ACCESS)] = None,
) -> dict[str, Any]:
    if not access_cookie:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        user_id = decode_access_token(access_cookie, settings)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "consent_upload": user.consent_upload,
    }


@router.delete("/me")
async def delete_account(
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    access_cookie: Annotated[str | None, Cookie(alias=COOKIE_ACCESS)] = None,
) -> dict[str, str]:
    """Soft-delete the current user (GDPR right to erasure)."""
    if not access_cookie:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        user_id = decode_access_token(access_cookie, settings)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    user.deleted_at = datetime.now(UTC)
    # Revoke all refresh tokens
    from sqlalchemy import update
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    _clear_session_cookies(response)
    return {"status": "deleted"}
